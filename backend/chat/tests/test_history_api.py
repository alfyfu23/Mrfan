import json
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from chat.models import Conversation, Member, Message

@pytest.mark.django_db
def test_history_api_posts_and_returns(client):
    User = get_user_model()

    # user 1 注册
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'test_user',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200
    jwt_token = response.json().get('jwt_token')
    if not jwt_token:
        jwt_token = client.post(
            reverse('login'),
            data=json.dumps({'username': 'test_user', 'password': 'test123456'}),
            content_type='application/json'
        ).json().get('jwt_token')
    assert jwt_token

    # user 2 注册
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'test_user_2',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200
    jwt_token2 = response.json().get('jwt_token')
    if not jwt_token2:
        jwt_token2 = client.post(
            reverse('login'),
            data=json.dumps({'username': 'test_user_2', 'password': 'test123456'}),
            content_type='application/json'
        ).json().get('jwt_token')
    assert jwt_token2

    # user 1 搜索 user 2
    r = client.get(
        reverse("search", args=["test_user_2"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert r.status_code == 200
    target_id = r.json()['exact'][0]

    # user 1 申请
    r = client.post(
        reverse('befriend', args=[target_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert r.status_code == 200

    # user 2 同意
    r = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token2}'
    )
    assert r.status_code == 200
    source_id = r.json()['pending'][0]
    client.post(
        reverse('agree', args=[source_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token2}'
    )

    # 获取 friend id
    r = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert r.status_code == 200
    id_2 = r.json()['friends'][0]

    # 创建私聊会话
    r = client.post(
        reverse("create_friend_conversation"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        data={'id': id_2}
    )
    assert r.status_code == 200
    body = r.json()
    conv_id = (body.get('data') or {}).get('id') if isinstance(body.get('data'), dict) else body.get('id')
    assert conv_id

    # 写两条消息（新版模型）
    conv = Conversation.objects.get(id=conv_id)
    u1 = User.objects.get(username='test_user')
    u2 = User.objects.get(username='test_user_2')
    m1 = Member.objects.get(conversation=conv, user=u1)
    m2 = Member.objects.get(conversation=conv, user=u2)

    Message.objects.create(conversation=conv, member=m1, type='text', content='hello')
    Message.objects.create(conversation=conv, member=m2, type='text', content='world')

    # 成功读取 history
    history_url = reverse('history') + f'?c={conv_id}'
    r = client.get(history_url, HTTP_AUTHORIZATION=f'Bearer {jwt_token}')
    assert r.status_code == 200
    body = r.json()
    container = body.get('data') if isinstance(body, dict) else None
    msgs = None
    if isinstance(container, dict) and 'messages' in container:
        msgs = container['messages']
    elif 'messages' in body:
        msgs = body['messages']
    assert isinstance(msgs, list) and len(msgs) >= 2

    # 错误方法
    r = client.post(reverse('history'), HTTP_AUTHORIZATION=f'Bearer {jwt_token}')
    assert r.status_code in (400, 405)

    # 无 Authorization
    r = client.get(reverse('history') + f'?c={conv_id}')
    assert r.status_code in (400, 401, 403)

    # 无效 token
    r = client.get(reverse('history') + f'?c={conv_id}', HTTP_AUTHORIZATION='Bearer invalid')
    assert r.status_code in (401, 403)

    # 用户被删除
    User.objects.filter(id=u1.id).delete()
    r = client.get(reverse('history') + f'?c={conv_id}', HTTP_AUTHORIZATION=f'Bearer {jwt_token}')
    assert r.status_code in (500, 401, 403)

    # 会话不存在
    r = client.get(reverse('history') + f'?c=999999', HTTP_AUTHORIZATION=f'Bearer {jwt_token2}')
    assert r.status_code in (404, 400)

    # 非成员访问
    conv2 = Conversation.objects.create(name='', type='private')
    r = client.get(reverse('history') + f'?c={conv2.id}', HTTP_AUTHORIZATION=f'Bearer {jwt_token2}')
    assert r.status_code in (403, 401)
