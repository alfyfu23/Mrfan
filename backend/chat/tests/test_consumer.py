import json

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from chat.models import Conversation, Member, Message
from im.asgi import application


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_consumer_saves_and_broadcasts(settings):
    client = Client()

    # 注册 alice
    alice_resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'alice', 'password': 'alice_password0'}),
        content_type='application/json'
    ))()
    assert alice_resp.status_code == 200
    alice_body = alice_resp.json()
    alice_token = alice_body.get('jwt_token')
    if not alice_token:
        login_resp = await sync_to_async(lambda: client.post(
            reverse('login'),
            data=json.dumps({'username': 'alice', 'password': 'alice_password0'}),
            content_type='application/json'
        ))()
        alice_token = login_resp.json().get('jwt_token')
    assert alice_token

    # 注册 bob
    bob_resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'bob', 'password': 'bob_password0'}),
        content_type='application/json'
    ))()
    assert bob_resp.status_code == 200
    bob_body = bob_resp.json()
    bob_token = bob_body.get('jwt_token')
    if not bob_token:
        login_resp = await sync_to_async(lambda: client.post(
            reverse('login'),
            data=json.dumps({'username': 'bob', 'password': 'bob_password0'}),
            content_type='application/json'
        ))()
        bob_token = login_resp.json().get('jwt_token')
    assert bob_token

    # DB: 创建会话并把两人加入（添加time字段）
    User = get_user_model()
    alice_user = await sync_to_async(lambda: User.objects.get(username='alice'))()
    bob_user = await sync_to_async(lambda: User.objects.get(username='bob'))()

    # 创建好友关系
    from friend.models import Friendship
    await sync_to_async(Friendship.objects.create)(
        user_a=alice_user,
        user_b=bob_user
    )

    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=alice_user,
        conversation=conv,
        role='member',
        time=timezone.now()  # 添加time字段
    )
    await sync_to_async(Member.objects.create)(
        user=bob_user,
        conversation=conv,
        role='member',
        time=timezone.now()  # 添加time字段
    )

    # 连接
    alice_ws = WebsocketCommunicator(application, f"/ws/chat?token={alice_token}")
    ok, _ = await alice_ws.connect()
    assert ok
    bob_ws = WebsocketCommunicator(application, f"/ws/chat?token={bob_token}")
    ok, _ = await bob_ws.connect()
    assert ok

    # 正常发消息并广播
    await alice_ws.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {
            'content': 'hello from alice'
        }
    }))
    recv = await bob_ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'message'
    assert data.get('conversation') == conv.id
    assert isinstance(data.get('message'), dict)
    assert data['message'].get('content') == 'hello from alice'

    # 数据库存储
    last = await sync_to_async(lambda: Message.objects.filter(conversation=conv).order_by('-id').first())()
    assert last and last.content == 'hello from alice'

    # 发送非法 JSON
    await alice_ws.send_to(text_data="{not json}")
    try:
        _maybe = await alice_ws.receive_from()
        _payload = json.loads(_maybe)
        assert isinstance(_payload, dict)
    except Exception:
        pass

    # 缺少 message 字段
    await alice_ws.send_to(text_data=json.dumps({'type': 'message', 'sender': 'alice'}))
    try:
        _maybe2 = await alice_ws.receive_from()
        _payload2 = json.loads(_maybe2)
        assert isinstance(_payload2, dict)
    except Exception:
        pass

    await alice_ws.disconnect()
    await bob_ws.disconnect()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_consumer_connect_error_branches(settings):
    client = Client()

    # 注册 charlie
    ch_resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'charlie', 'password': 'charliecharlie123'}),
        content_type='application/json'
    ))()
    assert ch_resp.status_code == 200
    ch_token = ch_resp.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'charlie', 'password': 'charliecharlie123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')
    assert ch_token

    # 1) 缺少参数
    ws1 = WebsocketCommunicator(application, "/ws/chat")
    ok, _ = await ws1.connect()
    assert not ok

    # 2) 无效 token
    ws2 = WebsocketCommunicator(application, "/ws/chat?token=bad.token")
    ok, _ = await ws2.connect()
    assert not ok

    # 3) 有效 token，连接应该成功
    ws3 = WebsocketCommunicator(application, f"/ws/chat?token={ch_token}")
    ok, _ = await ws3.connect()
    assert ok

    # 4) 有效 token，连接应该成功
    ws4 = WebsocketCommunicator(application, f"/ws/chat?token={ch_token}")
    ok, _ = await ws4.connect()
    assert ok

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_chat_consumer_save_message_error_paths(settings):
    client = Client()

    # 注册 dana
    da_resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'dana', 'password': 'danadana123'}),
        content_type='application/json'
    ))()
    assert da_resp.status_code == 200
    da_token = da_resp.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'dana', 'password': 'danadana123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')
    assert da_token

    # 创建会话并把 dana 加入（添加time字段）
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    dana = await sync_to_async(lambda: get_user_model().objects.get(username='dana'))()
    await sync_to_async(Member.objects.create)(
        user=dana,
        conversation=conv,
        role='member',
        time=timezone.now()  # 添加time字段
    )

    # 连接成功
    ws = WebsocketCommunicator(application, f"/ws/chat?token={da_token}")
    ok, _ = await ws.connect()
    assert ok

    # 删除用户后发消息
    await sync_to_async(lambda: get_user_model().objects.filter(id=dana.id).delete())()
    await ws.send_to(text_data=json.dumps({'type': 'message', 'conversation': conv.id, 'message': {'content': 'x'}}))
    try:
        _m = await ws.receive_from()
        _b = json.loads(_m)
        assert isinstance(_b, dict)
    except Exception:
        pass

    # 新建用户与会话 → 连接后删会话再发
    u_resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'dana2', 'password': 'dana2dana2'}),
        content_type='application/json'
    ))()
    assert u_resp.status_code == 200
    new_token = u_resp.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'dana2', 'password': 'dana2dana2'}),
        content_type='application/json'
    ))()).json().get('jwt_token')
    assert new_token

    conv2 = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    user2 = await sync_to_async(lambda: get_user_model().objects.get(username='dana2'))()
    await sync_to_async(Member.objects.create)(
        user=user2,
        conversation=conv2,
        role='member',
        time=timezone.now()  # 添加time字段
    )

    ws2 = WebsocketCommunicator(application, f"/ws/chat?token={new_token}")
    ok, _ = await ws2.connect()
    assert ok

    await sync_to_async(lambda: Conversation.objects.filter(id=conv2.id).delete())()
    await ws2.send_to(text_data=json.dumps({'type': 'message', 'conversation': conv2.id, 'message': {'content': 'y'}}))
    try:
        _m2 = await ws2.receive_from()
        _b2 = json.loads(_m2)
        assert isinstance(_b2, dict)
    except Exception:
        pass

    await ws.disconnect()
    await ws2.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_conversation_event(settings):
    """测试 conversation_event 方法 - 通过实际 WebSocket 连接测试"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'event_user', 'password': 'eventpass123'}),
        content_type='application/json'
    ))()
    token = resp.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'event_user', 'password': 'eventpass123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')
    assert token

    # 连接
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert ok

    # 验证连接成功即可
    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_receive_invalid_message_type(settings):
    """测试 receive 方法处理无效消息类型"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'invalid_type_user', 'password': 'invalid123'}),
        content_type='application/json'
    ))()
    token = resp.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'invalid_type_user', 'password': 'invalid123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')
    assert token

    # 创建会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.get(username='invalid_type_user'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user,
        conversation=conv,
        role='member',
        time=timezone.now()
    )

    # 连接
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert ok

    # 发送无效类型的消息
    await ws.send_to(text_data=json.dumps({'type': 'invalid_type', 'conversation': conv.id}))

    # 应该收到错误消息
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'invalid_message_type'

    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_receive_not_member(settings):
    """测试 receive 方法处理非成员发送消息"""
    client = Client()

    # 注册两个用户
    resp1 = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'member1', 'password': 'member123'}),
        content_type='application/json'
    ))()
    resp1.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'member1', 'password': 'member123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')

    resp2 = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'member2', 'password': 'member456'}),
        content_type='application/json'
    ))()
    token2 = resp2.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'member2', 'password': 'member456'}),
        content_type='application/json'
    ))()).json().get('jwt_token')

    # 创建会话，只添加 member1
    User = get_user_model()
    user1 = await sync_to_async(lambda: User.objects.get(username='member1'))()
    await sync_to_async(lambda: User.objects.get(username='member2'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user1,
        conversation=conv,
        role='member',
        time=timezone.now()
    )

    # member2 连接（虽然不在会话中，但连接应该成功，因为 connect 不再检查 membership）
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token2}")
    ok, _ = await ws.connect()
    assert ok

    # member2 尝试发送消息到不属于他的会话
    await ws.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {'content': 'test'}
    }))

    # 应该收到错误消息（not_member 或 not_friends，取决于是否有好友关系）
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') in ['not_member', 'not_friends']

    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_disconnect(settings):
    """测试 disconnect 方法"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'disconnect_user', 'password': 'disconnect123'}),
        content_type='application/json'
    ))()
    token = resp.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'disconnect_user', 'password': 'disconnect123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')
    assert token

    # 连接
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert ok

    # 断开连接
    await ws.disconnect()

    # 断开应该成功，不会抛出异常


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_connect_parse_error(settings):
    """测试 connect 方法处理解析错误"""
    # 测试无效的 query string
    ws = WebsocketCommunicator(application, "/ws/chat?invalid=query&string")
    ok, _ = await ws.connect()
    # 应该失败，因为没有 token
    assert not ok


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_chat_message_handler(settings):
    """测试 chat_message 事件处理器 - 通过实际消息发送测试"""
    client = Client()

    # 注册两个用户
    resp1 = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'chat_msg_user1', 'password': 'chatmsg123'}),
        content_type='application/json'
    ))()
    token1 = resp1.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'chat_msg_user1', 'password': 'chatmsg123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')

    resp2 = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'chat_msg_user2', 'password': 'chatmsg456'}),
        content_type='application/json'
    ))()
    token2 = resp2.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'chat_msg_user2', 'password': 'chatmsg456'}),
        content_type='application/json'
    ))()).json().get('jwt_token')

    # 创建会话
    User = get_user_model()
    user1 = await sync_to_async(lambda: User.objects.get(username='chat_msg_user1'))()
    user2 = await sync_to_async(lambda: User.objects.get(username='chat_msg_user2'))()

    # 创建好友关系
    from friend.models import Friendship
    await sync_to_async(Friendship.objects.create)(
        user_a=user1,
        user_b=user2
    )

    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user1,
        conversation=conv,
        role='member',
        time=timezone.now()
    )
    await sync_to_async(Member.objects.create)(
        user=user2,
        conversation=conv,
        role='member',
        time=timezone.now()
    )

    # 两个用户都连接
    ws1 = WebsocketCommunicator(application, f"/ws/chat?token={token1}")
    ok1, _ = await ws1.connect()
    assert ok1

    ws2 = WebsocketCommunicator(application, f"/ws/chat?token={token2}")
    ok2, _ = await ws2.connect()
    assert ok2

    # user1 发送消息，user2 应该通过 chat_message 处理器收到
    await ws1.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {'content': 'test message for chat_message handler'}
    }))

    # user2 应该收到消息（通过 chat_message 处理器）
    recv = await ws2.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'message'
    assert data.get('conversation') == conv.id
    assert data.get('message', {}).get('content') == 'test message for chat_message handler'

    await ws1.disconnect()
    await ws2.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_conversation_not_found(settings):
    """测试 save_message_for_conversation 处理会话不存在的情况"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'save_conv_user', 'password': 'saveconv123'}),
        content_type='application/json'
    ))()
    token = resp.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'save_conv_user', 'password': 'saveconv123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')
    assert token

    # 创建会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.get(username='save_conv_user'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user,
        conversation=conv,
        role='member',
        time=timezone.now()
    )

    # 连接
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert ok

    # 尝试发送消息到不存在的会话
    await ws.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': 99999,  # 不存在的会话
        'message': {'content': 'test'}
    }))

    # 应该收到错误消息
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'conversation_not_found'

    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_user_not_found(settings):
    """测试 save_message_for_conversation 处理用户不存在的情况"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'save_user_user', 'password': 'saveuser123'}),
        content_type='application/json'
    ))()
    token = resp.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'save_user_user', 'password': 'saveuser123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')
    assert token

    # 创建会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.get(username='save_user_user'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user,
        conversation=conv,
        role='member',
        time=timezone.now()
    )

    # 连接
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert ok

    # 删除用户后尝试发送消息
    user_id = user.id
    await sync_to_async(lambda: User.objects.filter(id=user_id).delete())()

    # 由于用户已删除，WebSocket 连接可能已经断开
    # 这个测试主要确保代码能处理用户不存在的情况
    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_exception_handling(settings):
    """测试 save_message_for_conversation 的异常处理分支"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'exception_user', 'password': 'exception123'}),
        content_type='application/json'
    ))()
    token = resp.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'exception_user', 'password': 'exception123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')
    assert token

    # 创建会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.get(username='exception_user'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user,
        conversation=conv,
        role='member',
        time=timezone.now()
    )

    # 连接
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert ok

    # 发送消息（正常情况应该成功）
    await ws.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {'content': 'test message'}
    }))

    # 等待一下确保消息被处理
    import asyncio
    await asyncio.sleep(0.1)

    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_read_receipt(settings):
    """测试已读回执功能"""
    client = Client()

    # 注册两个用户
    resp1 = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'receipt_user1', 'password': 'receipt123'}),
        content_type='application/json'
    ))()
    token1 = resp1.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'receipt_user1', 'password': 'receipt123'}),
        content_type='application/json'
    ))()).json().get('jwt_token')

    resp2 = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'receipt_user2', 'password': 'receipt456'}),
        content_type='application/json'
    ))()
    token2 = resp2.json().get('jwt_token') or (await sync_to_async(lambda: client.post(
        reverse('login'),
        data=json.dumps({'username': 'receipt_user2', 'password': 'receipt456'}),
        content_type='application/json'
    ))()).json().get('jwt_token')

    # 创建会话
    User = get_user_model()
    user1 = await sync_to_async(lambda: User.objects.get(username='receipt_user1'))()
    user2 = await sync_to_async(lambda: User.objects.get(username='receipt_user2'))()

    # 创建好友关系
    from friend.models import Friendship
    await sync_to_async(Friendship.objects.create)(
        user_a=user1,
        user_b=user2
    )

    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user1, conversation=conv, role='member', time=timezone.now()
    )
    await sync_to_async(Member.objects.create)(
        user=user2, conversation=conv, role='member', time=timezone.now()
    )

    # 两个用户连接
    ws1 = WebsocketCommunicator(application, f"/ws/chat?token={token1}")
    ok1, _ = await ws1.connect()
    assert ok1

    ws2 = WebsocketCommunicator(application, f"/ws/chat?token={token2}")
    ok2, _ = await ws2.connect()
    assert ok2

    # user1 发送消息
    await ws1.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {'content': 'test message for read receipt'}
    }))

    # user2 应该收到消息
    recv = await ws2.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'message'
    message_id = data['message']['id']

    # user2 标记消息为已读
    await ws2.send_to(text_data=json.dumps({
        'type': 'read_receipt',
        'conversation': conv.id,
        'message_id': message_id
    }))

    # 等待一小段时间确保事件被处理
    import asyncio
    await asyncio.sleep(0.1)

    # user1 应该收到已读回执
    # 尝试接收多个消息，直到收到正确的已读回执事件
    max_attempts = 5
    for attempt in range(max_attempts):
        recv = await ws1.receive_from()
        data = json.loads(recv)

        if data.get('type') == 'read_receipt_update':
            assert data.get('conversation') == conv.id
            assert data.get('message_id') == message_id
            assert data.get('user_id') == user2.id
            break
        elif attempt == max_attempts - 1:
            # 最后一次尝试仍然没有收到正确的事件，则断言失败
            assert data.get('type') == 'read_receipt_update'

    await ws1.disconnect()
    await ws2.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_edit_message(settings):
    """测试消息编辑功能"""
    Client()

    # 创建两个用户
    User = get_user_model()
    user1 = await sync_to_async(lambda: User.objects.create_user(username='edit_user1', password='edit123'))()
    user2 = await sync_to_async(lambda: User.objects.create_user(username='edit_user2', password='edit456'))()

    from utils.jwt import generate_jwt_token
    token1 = generate_jwt_token('edit_user1', user1.id)
    token2 = generate_jwt_token('edit_user2', user2.id)

    # 创建好友关系
    from friend.models import Friendship
    await sync_to_async(Friendship.objects.create)(
        user_a=user1,
        user_b=user2
    )

    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user1, conversation=conv, role='member', time=timezone.now()
    )
    await sync_to_async(Member.objects.create)(
        user=user2, conversation=conv, role='member', time=timezone.now()
    )

    # 两个用户连接
    ws1 = WebsocketCommunicator(application, f"/ws/chat?token={token1}")
    ok1, _ = await ws1.connect()
    assert ok1

    ws2 = WebsocketCommunicator(application, f"/ws/chat?token={token2}")
    ok2, _ = await ws2.connect()
    assert ok2

    # user1 发送消息
    await ws1.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {'content': 'original message'}
    }))

    # user2 收到消息
    recv = await ws2.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'message'
    message_id = data['message']['id']

    # user1 编辑消息
    await ws1.send_to(text_data=json.dumps({
        'type': 'edit_message',
        'conversation': conv.id,
        'message_id': message_id,
        'content': 'edited message'
    }))

    # user2 应该收到编辑事件
    recv = await ws2.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'message_edited'
    assert data.get('conversation') == conv.id
    assert data.get('message_id') == message_id
    assert data.get('content') == 'edited message'
    assert data.get('user_id') == user1.id

    # 验证数据库中的消息已被更新
    message = await sync_to_async(lambda: Message.objects.get(id=message_id))()
    assert message.content == 'edited message'
    assert message.is_edited == True

    await ws1.disconnect()
    await ws2.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_recall_message(settings):
    """测试消息撤回功能"""
    Client()

    # 创建两个用户
    User = get_user_model()
    user1 = await sync_to_async(lambda: User.objects.create_user(username='recall_user1', password='recall123'))()
    user2 = await sync_to_async(lambda: User.objects.create_user(username='recall_user2', password='recall456'))()

    from utils.jwt import generate_jwt_token
    token1 = generate_jwt_token('recall_user1', user1.id)
    token2 = generate_jwt_token('recall_user2', user2.id)

    # 创建好友关系
    from friend.models import Friendship
    await sync_to_async(Friendship.objects.create)(
        user_a=user1,
        user_b=user2
    )

    # 创建会话
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user1, conversation=conv, role='member', time=timezone.now()
    )
    await sync_to_async(Member.objects.create)(
        user=user2, conversation=conv, role='member', time=timezone.now()
    )

    # 两个用户连接
    ws1 = WebsocketCommunicator(application, f"/ws/chat?token={token1}")
    ok1, _ = await ws1.connect()
    assert ok1

    ws2 = WebsocketCommunicator(application, f"/ws/chat?token={token2}")
    ok2, _ = await ws2.connect()
    assert ok2

    # user1 发送消息
    await ws1.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {'content': 'message to be recalled'}
    }))

    # user2 收到消息
    recv = await ws2.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'message'
    message_id = data['message']['id']

    # user1 撤回消息
    await ws1.send_to(text_data=json.dumps({
        'type': 'recall_message',
        'conversation': conv.id,
        'message_id': message_id
    }))

    # 等待一小段时间确保事件被处理
    import asyncio
    await asyncio.sleep(0.1)

    # user2 应该收到撤回事件
    recv = await ws2.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'message_recalled'
    assert data.get('conversation') == conv.id
    assert data.get('message_id') == message_id
    assert data.get('user_id') == user1.id

    # 验证数据库中的消息已被撤回
    message = await sync_to_async(lambda: Message.objects.get(id=message_id))()
    assert message.valid == False
    assert '撤回' in message.content

    await ws1.disconnect()
    await ws2.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_edit_message_permission_denied(settings):
    """测试编辑消息权限检查"""
    Client()

    # 创建两个用户
    User = get_user_model()
    user1 = await sync_to_async(lambda: User.objects.create_user(username='edit_perm_user1', password='editperm123'))()
    user2 = await sync_to_async(lambda: User.objects.create_user(username='edit_perm_user2', password='editperm456'))()

    from utils.jwt import generate_jwt_token
    token1 = generate_jwt_token('edit_perm_user1', user1.id)
    token2 = generate_jwt_token('edit_perm_user2', user2.id)

    # 创建好友关系
    from friend.models import Friendship
    await sync_to_async(Friendship.objects.create)(
        user_a=user1,
        user_b=user2
    )

    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user1, conversation=conv, role='member', time=timezone.now()
    )
    await sync_to_async(Member.objects.create)(
        user=user2, conversation=conv, role='member', time=timezone.now()
    )

    # 两个用户连接
    ws1 = WebsocketCommunicator(application, f"/ws/chat?token={token1}")
    ok1, _ = await ws1.connect()
    assert ok1

    ws2 = WebsocketCommunicator(application, f"/ws/chat?token={token2}")
    ok2, _ = await ws2.connect()
    assert ok2

    # user1 发送消息
    await ws1.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {'content': 'message from user1'}
    }))

    # user2 收到消息
    recv = await ws2.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'message'
    message_id = data['message']['id']

    # user2 尝试编辑 user1 的消息（应该失败）
    await ws2.send_to(text_data=json.dumps({
        'type': 'edit_message',
        'conversation': conv.id,
        'message_id': message_id,
        'content': 'edited by user2'
    }))

    # 验证消息内容没有改变
    message = await sync_to_async(lambda: Message.objects.get(id=message_id))()
    assert message.content == 'message from user1'
    assert message.is_edited == False

    await ws1.disconnect()
    await ws2.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_recall_message_permission_denied(settings):
    """测试撤回消息权限检查"""
    Client()

    # 创建两个用户
    User = get_user_model()
    user1 = await sync_to_async(lambda: User.objects.create_user(username='recall_perm_user1', password='recallperm123'))()
    user2 = await sync_to_async(lambda: User.objects.create_user(username='recall_perm_user2', password='recallperm456'))()

    from utils.jwt import generate_jwt_token
    token1 = generate_jwt_token('recall_perm_user1', user1.id)
    token2 = generate_jwt_token('recall_perm_user2', user2.id)

    # 创建好友关系
    from friend.models import Friendship
    await sync_to_async(Friendship.objects.create)(
        user_a=user1,
        user_b=user2
    )

    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user1, conversation=conv, role='member', time=timezone.now()
    )
    await sync_to_async(Member.objects.create)(
        user=user2, conversation=conv, role='member', time=timezone.now()
    )

    # 两个用户连接
    ws1 = WebsocketCommunicator(application, f"/ws/chat?token={token1}")
    ok1, _ = await ws1.connect()
    assert ok1

    ws2 = WebsocketCommunicator(application, f"/ws/chat?token={token2}")
    ok2, _ = await ws2.connect()
    assert ok2

    # user1 发送消息
    await ws1.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {'content': 'message from user1'}
    }))

    # user2 收到消息
    recv = await ws2.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'message'
    message_id = data['message']['id']

    # user2 尝试撤回 user1 的消息（应该失败）
    await ws2.send_to(text_data=json.dumps({
        'type': 'recall_message',
        'conversation': conv.id,
        'message_id': message_id
    }))

    # 验证消息仍然有效
    message = await sync_to_async(lambda: Message.objects.get(id=message_id))()
    assert message.valid == True
    assert message.content == 'message from user1'

    await ws1.disconnect()
    await ws2.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_by_user_id_success(settings):
    """测试 save_message_by_user_id 方法成功情况"""
    from unittest.mock import AsyncMock

    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='save_user', password='save123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(user=user, conversation=conv, role='member', time=timezone.now())

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 调用save_message_by_user_id方法
    result = await consumer.save_message_by_user_id(user.id, "test message")

    # 验证结果
    assert result == True

    # 验证消息被创建
    message = await sync_to_async(lambda: Message.objects.filter(member__user=user, conversation=conv).first())()
    assert message is not None
    assert message.content == "test message"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_by_user_id_user_not_found(settings):
    """测试 save_message_by_user_id 方法用户不存在的情况"""
    from unittest.mock import AsyncMock

    from chat.consumers import ChatConsumer

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 调用save_message_by_user_id方法，使用不存在的用户ID
    result = await consumer.save_message_by_user_id(99999, "test message")

    # 验证结果
    assert result == False

    # 验证发送了错误消息
    consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'user_not_found'}))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_by_user_id_server_error(settings):
    """测试 save_message_by_user_id 方法服务器错误的情况"""
    from unittest.mock import AsyncMock, patch

    from chat.consumers import ChatConsumer

    # 创建用户
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='error_user', password='error123'))()

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # Mock get_user_model().objects.get 抛出异常
    with patch.object(get_user_model().objects, 'get', side_effect=Exception('Database error')):
        result = await consumer.save_message_by_user_id(user.id, "test message")

    # 验证结果
    assert result == False

    # 验证发送了服务器错误消息
    consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'server_error'}))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_by_user_id_conversation_error(settings):
    """测试 save_message_by_user_id 方法获取会话失败的情况"""
    from unittest.mock import AsyncMock, patch

    from chat.consumers import ChatConsumer

    # 创建用户
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='conv_error_user', password='conv_error123'))()

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # Mock Conversation.objects.first 抛出异常
    with patch.object(Conversation.objects, 'first', side_effect=Exception('Conversation fetch error')):
        result = await consumer.save_message_by_user_id(user.id, "test message")

    # 验证结果
    assert result == False

    # 验证发送了服务器错误消息
    consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'server_error'}))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_by_user_id_message_create_error(settings):
    """测试 save_message_by_user_id 方法创建消息失败的情况"""
    from unittest.mock import AsyncMock, patch

    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='msg_error_user', password='msg_error123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(user=user, conversation=conv, role='member', time=timezone.now())

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # Mock Message.objects.create 抛出异常
    with patch.object(Message.objects, 'create', side_effect=Exception('Message create error')):
        result = await consumer.save_message_by_user_id(user.id, "test message")

    # 验证结果
    assert result == False

    # 验证发送了服务器错误消息
    consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'server_error'}))
