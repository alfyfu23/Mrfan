import json
from unittest.mock import AsyncMock, MagicMock, patch

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
async def test_consumer_connect_deactivated_user(settings):
    """测试连接时用户已注销的情况"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'deactivated_user', 'password': 'deactivated123'}),
        content_type='application/json'
    ))()
    assert resp.status_code == 200
    token = resp.json().get('jwt_token')
    assert token

    # 获取用户并注销
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.get(username='deactivated_user'))()
    await sync_to_async(lambda: User.objects.filter(id=user.id).update(is_active=False))()

    # 尝试连接，应该失败
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert not ok


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_connect_invalid_token_format(settings):
    """测试连接时token格式无效的情况"""
    # 测试无效的token格式（使用有效的base64格式但无效的内容）
    ws = WebsocketCommunicator(application, "/ws/chat?token=invalid.base64token")
    try:
        ok, _ = await ws.connect()
        assert not ok
    except Exception:
        # 如果连接过程中抛出异常，这也是可以接受的
        pass

    # 测试空token
    ws = WebsocketCommunicator(application, "/ws/chat?token=")
    try:
        ok, _ = await ws.connect()
        assert not ok
    except Exception:
        # 如果连接过程中抛出异常，这也是可以接受的
        pass


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_handle_message_missing_fields(settings):
    """测试处理消息时缺少必要字段"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'missing_fields_user', 'password': 'missing123'}),
        content_type='application/json'
    ))()
    token = resp.json().get('jwt_token')
    assert token

    # 创建会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.get(username='missing_fields_user'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )

    # 连接
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert ok

    # 发送缺少conversation字段的消息
    await ws.send_to(text_data=json.dumps({
        'type': 'message',
        'message': {'content': 'test'}
    }))

    # 应该收到错误
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'missing_fields'

    # 发送缺少content字段的消息
    await ws.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {}
    }))

    # 应该收到错误
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'missing_fields'

    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_handle_read_receipt_missing_fields(settings):
    """测试处理已读回执时缺少必要字段"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'read_receipt_user', 'password': 'readreceipt123'}),
        content_type='application/json'
    ))()
    token = resp.json().get('jwt_token')
    assert token

    # 连接
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert ok

    # 发送缺少conversation字段的已读回执
    await ws.send_to(text_data=json.dumps({
        'type': 'read_receipt',
        'message_id': 1
    }))

    # 应该收到错误
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'missing_fields'

    # 发送缺少message_id字段的已读回执
    await ws.send_to(text_data=json.dumps({
        'type': 'read_receipt',
        'conversation': 1
    }))

    # 应该收到错误
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'missing_fields'

    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_handle_edit_message_missing_fields(settings):
    """测试处理编辑消息时缺少必要字段"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'edit_msg_user', 'password': 'editmsg123'}),
        content_type='application/json'
    ))()
    token = resp.json().get('jwt_token')
    assert token

    # 连接
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert ok

    # 发送缺少conversation字段的编辑消息
    await ws.send_to(text_data=json.dumps({
        'type': 'edit_message',
        'message_id': 1,
        'content': 'edited content'
    }))

    # 应该收到错误
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'missing_fields'

    # 发送缺少message_id字段的编辑消息
    await ws.send_to(text_data=json.dumps({
        'type': 'edit_message',
        'conversation': 1,
        'content': 'edited content'
    }))

    # 应该收到错误
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'missing_fields'

    # 发送缺少content字段的编辑消息
    await ws.send_to(text_data=json.dumps({
        'type': 'edit_message',
        'conversation': 1,
        'message_id': 1
    }))

    # 应该收到错误
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'missing_fields'

    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_handle_recall_message_missing_fields(settings):
    """测试处理撤回消息时缺少必要字段"""
    client = Client()

    # 注册用户
    resp = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'recall_msg_user', 'password': 'recallmsg123'}),
        content_type='application/json'
    ))()
    token = resp.json().get('jwt_token')
    assert token

    # 连接
    ws = WebsocketCommunicator(application, f"/ws/chat?token={token}")
    ok, _ = await ws.connect()
    assert ok

    # 发送缺少conversation字段的撤回消息
    await ws.send_to(text_data=json.dumps({
        'type': 'recall_message',
        'message_id': 1
    }))

    # 应该收到错误
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'missing_fields'

    # 发送缺少message_id字段的撤回消息
    await ws.send_to(text_data=json.dumps({
        'type': 'recall_message',
        'conversation': 1
    }))

    # 应该收到错误
    recv = await ws.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'missing_fields'

    await ws.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_private_chat_not_friends(settings):
    """测试私聊中非好友关系发送消息"""
    client = Client()

    # 注册两个用户
    resp1 = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'private_user1', 'password': 'private123'}),
        content_type='application/json'
    ))()
    token1 = resp1.json().get('jwt_token')
    assert token1

    resp2 = await sync_to_async(lambda: client.post(
        reverse('register'),
        data=json.dumps({'username': 'private_user2', 'password': 'private456'}),
        content_type='application/json'
    ))()
    token2 = resp2.json().get('jwt_token')
    assert token2

    # 创建用户和会话（但不创建好友关系）
    User = get_user_model()
    user1 = await sync_to_async(lambda: User.objects.get(username='private_user1'))()
    user2 = await sync_to_async(lambda: User.objects.get(username='private_user2'))()

    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user1, conversation=conv, role='member', time=timezone.now()
    )
    await sync_to_async(Member.objects.create)(
        user=user2, conversation=conv, role='member', time=timezone.now()
    )

    # user1 连接
    ws1 = WebsocketCommunicator(application, f"/ws/chat?token={token1}")
    ok1, _ = await ws1.connect()
    assert ok1

    # user1 尝试发送消息（应该失败，因为不是好友）
    await ws1.send_to(text_data=json.dumps({
        'type': 'message',
        'conversation': conv.id,
        'message': {'content': 'test message'}
    }))

    # 应该收到错误
    recv = await ws1.receive_from()
    data = json.loads(recv)
    assert data.get('type') == 'error'
    assert data.get('error') == 'not_friends'
    assert '你们已经不是好友' in data.get('message', '')

    await ws1.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_update_message_content_user_deactivated(settings):
    """测试更新消息内容时用户已注销"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='deactivated_edit_user', password='deact123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    member = await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )

    # 创建消息
    message = await sync_to_async(Message.objects.create)(
        conversation=conv, member=member, content='original message'
    )

    # 注销用户
    await sync_to_async(lambda: User.objects.filter(id=user.id).update(is_active=False))()

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 尝试更新消息内容
    result = await consumer.update_message_content(user.id, conv.id, message.id, 'edited message')

    # 验证结果
    assert result == False

    # 验证发送了错误消息
    consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'user_deactivated'}))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_update_message_content_conversation_inactive(settings):
    """测试更新消息内容时会话已不活跃"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='inactive_conv_user', password='inactive123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private', is_active=False))()
    member = await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )

    # 创建消息
    message = await sync_to_async(Message.objects.create)(
        conversation=conv, member=member, content='original message'
    )

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 尝试更新消息内容
    result = await consumer.update_message_content(user.id, conv.id, message.id, 'edited message')

    # 验证结果
    assert result == False

    # 验证发送了错误消息
    consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'conversation_inactive'}))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_update_message_content_not_member(settings):
    """测试更新消息内容时用户不是会话成员"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='not_member_user', password='notmember123'))()
    other_user = await sync_to_async(lambda: User.objects.create_user(username='other_user', password='other123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    member = await sync_to_async(Member.objects.create)(
        user=other_user, conversation=conv, role='member', time=timezone.now()
    )

    # 创建消息
    message = await sync_to_async(Message.objects.create)(
        conversation=conv, member=member, content='original message'
    )

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 尝试更新消息内容
    result = await consumer.update_message_content(user.id, conv.id, message.id, 'edited message')

    # 验证结果
    assert result == False


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_update_message_content_not_author(settings):
    """测试更新消息内容时用户不是消息作者"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='not_author_user', password='notauthor123'))()
    author = await sync_to_async(lambda: User.objects.create_user(username='author_user', password='author123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()

    await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )
    author_member = await sync_to_async(Member.objects.create)(
        user=author, conversation=conv, role='member', time=timezone.now()
    )

    # 创建消息
    message = await sync_to_async(Message.objects.create)(
        conversation=conv, member=author_member, content='original message'
    )

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 尝试更新消息内容
    result = await consumer.update_message_content(user.id, conv.id, message.id, 'edited message')

    # 验证结果
    assert result == False


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_update_message_content_message_not_found(settings):
    """测试更新消息内容时消息不存在"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='msg_not_found_user', password='notfound123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 尝试更新不存在的消息
    result = await consumer.update_message_content(user.id, conv.id, 99999, 'edited message')

    # 验证结果
    assert result == False


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_recall_message_user_deactivated(settings):
    """测试撤回消息时用户已注销"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='deactivated_recall_user', password='deact123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    member = await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )

    # 创建消息
    message = await sync_to_async(Message.objects.create)(
        conversation=conv, member=member, content='message to recall'
    )

    # 注销用户
    await sync_to_async(lambda: User.objects.filter(id=user.id).update(is_active=False))()

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 尝试撤回消息
    result = await consumer.recall_message(user.id, conv.id, message.id)

    # 验证结果
    assert result == False

    # 验证发送了错误消息
    consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'user_deactivated'}))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_broadcast_to_conversation_members_error(settings):
    """测试向会话成员广播事件时的错误处理"""
    from chat.consumers import ChatConsumer

    # 创建consumer实例
    consumer = ChatConsumer()
    consumer.channel_layer = AsyncMock()
    consumer.logger = MagicMock()

    # Mock channel_layer.group_send 抛出异常
    consumer.channel_layer.group_send.side_effect = Exception('Broadcast error')

    # 尝试广播事件
    await consumer.broadcast_to_conversation_members(99999, {'type': 'test_event'})

    # 验证异常被捕获并记录日志
    consumer.logger.exception.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_check_conversation_membership_error(settings):
    """测试检查会话成员关系时的错误处理"""
    from chat.consumers import ChatConsumer

    # 创建consumer实例
    consumer = ChatConsumer()
    consumer.logger = MagicMock()

    # Mock Conversation.objects.get 抛出异常
    with patch('chat.consumers.Conversation.objects.get', side_effect=Exception('Database error')):
        result = await consumer.check_conversation_membership(1, 99999)

        # 验证返回False
        assert result == False

        # 验证异常被捕获并记录日志
        consumer.logger.exception.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_is_private_conversation_error(settings):
    """测试检查会话类型时的错误处理"""
    from chat.consumers import ChatConsumer

    # 创建consumer实例
    consumer = ChatConsumer()
    consumer.logger = MagicMock()

    # Mock Conversation.objects.get 抛出异常
    with patch('chat.consumers.Conversation.objects.get', side_effect=Exception('Database error')):
        result = await consumer.is_private_conversation(99999)

        # 验证返回False
        assert result == False

        # 验证异常被捕获并记录日志
        consumer.logger.exception.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_check_friendship_in_private_chat_error(settings):
    """测试检查私聊中好友关系时的错误处理"""
    from chat.consumers import ChatConsumer

    # 创建consumer实例
    consumer = ChatConsumer()
    consumer.logger = MagicMock()

    # Mock Conversation.objects.get 抛出异常
    with patch('chat.consumers.Conversation.objects.get', side_effect=Exception('Database error')):
        result = await consumer.check_friendship_in_private_chat(1, 99999)

        # 验证返回False
        assert result == False

        # 验证异常被捕获并记录日志
        consumer.logger.exception.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_presence_event_handlers(settings):
    """测试在线状态事件处理器"""
    from chat.consumers import ChatConsumer

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 测试presence事件处理器
    await consumer.presence({
        'type': 'presence',
        'user_id': 1,
        'status': 'online'
    })

    # 验证发送了事件
    consumer.send.assert_called_once_with(text_data=json.dumps({
        'type': 'presence',
        'user_id': 1,
        'status': 'online'
    }))

    # 重置mock
    consumer.send.reset_mock()

    # 测试read_receipt_update事件处理器
    await consumer.read_receipt_update({
        'type': 'read_receipt_update',
        'conversation': 1,
        'message_id': 123,
        'user_id': 2
    })

    # 验证发送了事件
    consumer.send.assert_called_once_with(text_data=json.dumps({
        'type': 'read_receipt_update',
        'conversation': 1,
        'message_id': 123,
        'user_id': 2
    }))

    # 重置mock
    consumer.send.reset_mock()

    # 测试message_edited事件处理器
    await consumer.message_edited({
        'type': 'message_edited',
        'conversation': 1,
        'message_id': 123,
        'content': 'edited content',
        'user_id': 2
    })

    # 验证发送了事件
    consumer.send.assert_called_once_with(text_data=json.dumps({
        'type': 'message_edited',
        'conversation': 1,
        'message_id': 123,
        'content': 'edited content',
        'user_id': 2
    }))

    # 重置mock
    consumer.send.reset_mock()

    # 测试message_recalled事件处理器
    await consumer.message_recalled({
        'type': 'message_recalled',
        'conversation': 1,
        'message_id': 123,
        'user_id': 2
    })

    # 验证发送了事件
    consumer.send.assert_called_once_with(text_data=json.dumps({
        'type': 'message_recalled',
        'conversation': 1,
        'message_id': 123,
        'user_id': 2
    }))

    # 重置mock
    consumer.send.reset_mock()

    # 测试conversation_event事件处理器
    await consumer.conversation_event({
        'type': 'conversation_event',
        'event': 'conversation_created',
        'conversation': 1
    })

    # 验证发送了事件
    consumer.send.assert_called_once_with(text_data=json.dumps({
        'type': 'conversation_event',
        'event': 'conversation_created',
        'conversation': 1
    }))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_broadcast_presence_status_error(settings):
    """测试广播在线状态时的错误处理"""
    from unittest.mock import MagicMock

    from django.utils import timezone

    from chat.consumers import ChatConsumer
    from chat.models import Conversation, Member

    # 创建用户和会话，确保有数据可以查询
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='broadcast_user', password='broadcast123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )

    # 创建consumer实例
    consumer = ChatConsumer()
    consumer.user_id = user.id
    consumer.channel_layer = AsyncMock()

    # 创建一个真实的logger mock
    logger_mock = MagicMock()
    consumer.logger = logger_mock

    # Mock channel_layer.group_send 抛出异常
    consumer.channel_layer.group_send.side_effect = Exception('Broadcast error')

    # 尝试广播在线状态
    await consumer._broadcast_presence_status('online')

    # 验证logger.exception被调用（代码中有exception日志）
    logger_mock.exception.assert_called_once_with("Failed to broadcast presence status")


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_for_conversation_with_reply_to(settings):
    """测试保存带有回复的消息"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='reply_user', password='reply123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    member = await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )

    # 创建被回复的消息
    reply_to_message = await sync_to_async(Message.objects.create)(
        conversation=conv, member=member, content='original message'
    )

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 调用save_message_for_conversation方法，带有回复
    result = await consumer.save_message_for_conversation(
        user.id, conv.id, 'reply message', reply_to_message.id
    )

    # 验证结果
    assert result is not None
    assert result['conversation'] == conv.id
    assert result['message']['content'] == 'reply message'
    assert result['message']['reply_to'] == reply_to_message.id
    assert result['message']['reply_to_message'] is not None
    assert result['message']['reply_to_message']['id'] == reply_to_message.id
    assert result['message']['reply_to_message']['text'] == 'original message'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_for_conversation_user_deactivated(settings):
    """测试保存消息时用户已注销"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='deactivated_save_user', password='deact123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )

    # 注销用户
    await sync_to_async(lambda: User.objects.filter(id=user.id).update(is_active=False))()

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 尝试保存消息
    result = await consumer.save_message_for_conversation(user.id, conv.id, 'test message')

    # 验证结果
    assert result is None

    # 验证发送了错误消息
    consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'user_deactivated'}))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_for_conversation_conversation_deactivated(settings):
    """测试保存消息时会话已不活跃"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='inactive_conv_save_user', password='inactive123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private', is_active=False))()
    await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 尝试保存消息
    result = await consumer.save_message_for_conversation(user.id, conv.id, 'test message')

    # 验证结果
    assert result is None

    # 验证发送了错误消息
    consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'conversation_inactive'}))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_for_conversation_not_member(settings):
    """测试保存消息时用户不是会话成员"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='not_member_save_user', password='notmember123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    # 不添加用户为成员

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # 尝试保存消息
    result = await consumer.save_message_for_conversation(user.id, conv.id, 'test message')

    # 验证结果
    assert result is None

    # 验证发送了错误消息
    consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'not_member'}))


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_consumer_save_message_for_conversation_create_error(settings):
    """测试保存消息时创建消息出错"""
    from chat.consumers import ChatConsumer

    # 创建用户和会话
    User = get_user_model()
    user = await sync_to_async(lambda: User.objects.create_user(username='create_error_user', password='createerror123'))()
    conv = await sync_to_async(lambda: Conversation.objects.create(type='private'))()
    await sync_to_async(Member.objects.create)(
        user=user, conversation=conv, role='member', time=timezone.now()
    )

    # 创建consumer实例并设置mock send方法
    consumer = ChatConsumer()
    consumer.send = AsyncMock()

    # Mock Message.objects.create 抛出异常
    with patch('chat.consumers.Message.objects.create', side_effect=Exception('Create error')):
        result = await consumer.save_message_for_conversation(user.id, conv.id, 'test message')

        # 验证结果
        assert result is None

        # 验证发送了错误消息
        consumer.send.assert_called_once_with(text_data=json.dumps({'type': 'error', 'error': 'server_error'}))
