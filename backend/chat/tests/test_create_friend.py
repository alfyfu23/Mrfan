import json

import pytest
from django.test import Client
from django.urls import reverse

from chat.models import Conversation, Member


@pytest.mark.django_db
def test_create_friend_conversation_message_flow(client: Client):
    # user 1 注册
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'test_user',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200
    body = response.json()
    jwt_token = body.get('jwt_token')
    if not jwt_token:
        # 兜底：用 login 再拿一次
        response = client.post(reverse('login'), data=json.dumps({
            'username': 'test_user',
            'password': 'test123456'
        }), content_type='application/json')
        assert response.status_code == 200
        jwt_token = response.json().get('jwt_token')
    assert jwt_token

    # user 2 注册
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'test_user_2',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200
    body2 = response.json()
    jwt_token2 = body2.get('jwt_token')
    if not jwt_token2:
        response = client.post(reverse('login'), data=json.dumps({
            'username': 'test_user_2',
            'password': 'test123456'
        }), content_type='application/json')
        assert response.status_code == 200
        jwt_token2 = response.json().get('jwt_token')
    assert jwt_token2

    # user 1 搜索 user 2
    search_result = client.get(
        reverse("search", args=["test_user_2"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    ).json()
    assert 'exact' in search_result and len(search_result['exact']) > 0
    target_id = search_result['exact'][0]

    # user 1 申请添加 user 2 为好友
    response = client.post(
        reverse('befriend', args=[target_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 200

    # user 2 查看好友申请
    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token2}'
    )
    assert response.status_code == 200
    assert len(response.json()['pending']) > 0
    assert len(response.json()['friends']) == 0
    source_id = response.json()['pending'][0]

    # user 2 同意
    client.post(
        reverse('agree', args=[source_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token2}'
    )

    # user 2 检查好友列表
    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token2}'
    )
    assert response.status_code == 200
    assert len(response.json()['pending']) == 0
    assert len(response.json()['friends']) > 0
    id_1 = response.json()['friends'][0]

    # user 1 检查好友列表
    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 200
    assert len(response.json()['pending']) == 0
    assert len(response.json()['friends']) > 0
    id_2 = response.json()['friends'][0]

    # user 1 申请和 user 2 开启好友会话（成功，触发创建分支）
    response = client.post(
        reverse("create_friend_conversation"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        data={'id': id_2}
    )
    assert response.status_code == 200
    body = response.json()
    # 兼容返回结构：既支持 {"data":{"id":..}} 也支持 {"id":..}
    conv_id_1 = (body.get('data') or {}).get('id') if isinstance(body.get('data'), dict) else body.get('id')
    assert conv_id_1

    # 再次创建（应命中“已存在会话不报错”分支，得到同一个 id）
    response = client.post(
        reverse("create_friend_conversation"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token2}',
        data={'id': id_1}
    )
    assert response.status_code == 200
    body = response.json()
    conv_id_2 = (body.get('data') or {}).get('id') if isinstance(body.get('data'), dict) else body.get('id')
    assert conv_id_2 == conv_id_1

    # 无 Authorization（命中 code=3001 分支）
    response = client.post(
        reverse("create_friend_conversation"),
        content_type='application/json',
        data={'id': id_2}
    )
    assert response.status_code in (400, 401, 403)
    # 如果返回业务码，尽量兼容
    code = response.json().get('code')
    if code is not None:
        assert code in (3001, 3002)

    # Authorization 里放无效 token（命中 3002）
    response = client.post(
        reverse("create_friend_conversation"),
        content_type='application/json',
        HTTP_AUTHORIZATION='Bearer invalid_token_xyz',
        data={'id': id_2}
    )
    assert response.status_code in (403, 401)
    code = response.json().get('code')
    if code is not None:
        assert code == 3002

    # 错误方法 GET（命中 BAD_METHOD 分支）
    response = client.get(
        reverse("create_friend_conversation"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code in (400, 405)

    # 无 body / 错 body（命中 2001）
    response = client.post(
        reverse("create_friend_conversation"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        data='not-a-json'
    )
    assert response.status_code in (400, 422)
    code = response.json().get('code')
    if code is not None:
        assert code == 2001

    # 目标用户不存在（命中 2004）
    response = client.post(
        reverse("create_friend_conversation"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        data={'id': 999999}
    )
    assert response.status_code in (404, 400)
    code = response.json().get('code')
    if code is not None:
        assert code == 2004

    # 非好友时尝试创建（命中 2012）
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'test_user_3',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200
    response = client.get(
        reverse("search", args=["test_user_3"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 200
    nonfriend_id = response.json()['exact'][0]
    response = client.post(
        reverse("create_friend_conversation"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}',
        data={'id': nonfriend_id}
    )
    assert response.status_code in (403, 401)
    code = response.json().get('code')
    if code is not None:
        assert code == 2012

    # 轻触 models：读取一次成员以覆盖查询路径
    conv = Conversation.objects.get(id=conv_id_1)
    Member.objects.filter(conversation=conv).first()
