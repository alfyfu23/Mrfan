import json

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_add_friend_flow(client: Client):
    # JWT Error
    response = client.post(
        reverse('befriend', args=[123456]),
        content_type='application/json'
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4001

    # user 1 注册
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'test_user',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200

    jwt_token = response.json()['jwt_token']

    # user 2 注册

    response = client.post(reverse('register'), data=json.dumps({
        'username': 'test_user_2',
        'password': 'test123456'
    }), content_type='application/json')

    jwt_token2 = response.json()['jwt_token']


    # user 1 搜索 user 2

    search_result = client.get(
        reverse("search", args=["test_user_2"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    ).json()

    assert 'exact' in search_result and len(search_result['exact']) > 0

    target_id = search_result['exact'][0]

    # user 1 申请添加 use 2 为好友

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

    # user 1 检查好友列表

    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )

    assert response.status_code == 200
    assert len(response.json()['pending']) == 0
    assert len(response.json()['friends']) > 0

    response = client.post(reverse('register'), data=json.dumps({
        'username': 'test_user_3',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200
    jwt_token3 = response.json()['jwt_token']

    # 获取 user 1 / user 3 的 id
    search_user1 = client.get(
        reverse("search", args=["test_user"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    ).json()
    assert len(search_user1['exact']) > 0
    user1_id = search_user1['exact'][0]

    search_user3 = client.get(
        reverse("search", args=["test_user_3"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    ).json()
    assert len(search_user3['exact']) > 0
    user3_id = search_user3['exact'][0]

    # 3 通过 1（应报错：没有 pending）
    response = client.post(
        reverse('agree', args=[user1_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token3}'
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4005

    # 1 搜 1
    response = client.get(
        reverse("search", args=["test_user"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 200
    assert user1_id in response.json()['exact']

    # 1 加 1（应报错：不能加自己）
    response = client.post(
        reverse('befriend', args=[user1_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4006

    # 1 搜 4（不存在）
    response = client.get(
        reverse("search", args=["test_user_4"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 200
    assert len(response.json()['exact']) == 0
    assert len(response.json()['fuzzy']) == 0

    # 1 加 4（应报错：用户不存在）
    non_exist_user_id = 999999
    response = client.post(
        reverse('befriend', args=[non_exist_user_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 404
    assert response.json().get('code') == 4003
    response = client.get(
        reverse("search", args=["test_user"]),
        content_type='application/json'  # 不带 Authorization
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4001

    # 为了构造 URL 参数，先用已登录的 user 1 拿到其 id
    search_user1_for_url = client.get(
        reverse("search", args=["test_user"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    ).json()
    assert len(search_user1_for_url['exact']) > 0
    user1_id_for_url = search_user1_for_url['exact'][0]

    # 4 加 1（未注册 & 无 JWT，应报错：Invalid JWT Token）
    response = client.post(
        reverse('befriend', args=[user1_id_for_url]),
        content_type='application/json'  # 不带 Authorization
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4001

    # 1 搜 2
    response = client.get(
        reverse("search", args=["test_user_2"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 200
    assert len(response.json()['exact']) > 0
    user2_id = response.json()['exact'][0]

    # 1 加 2（应报错：已是好友）
    response = client.post(
        reverse('befriend', args=[user2_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4002

    # 1 搜 3
    response = client.get(
        reverse("search", args=["test_user_3"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 200
    assert len(response.json()['exact']) > 0
    user3_id_again = response.json()['exact'][0]

    # 1 加 3（成功：创建 pending）
    response = client.post(
        reverse('befriend', args=[user3_id_again]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 200

    # 1 再次加 3（应报错：pending 已存在）
    response = client.post(
        reverse('befriend', args=[user3_id_again]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4004

    # 3 搜 1
    response = client.get(
        reverse("search", args=["test_user"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token3}'
    )
    assert response.status_code == 200
    assert len(response.json()['exact']) > 0
    user1_id_for_3 = response.json()['exact'][0]

    # 3 加 1（成功：对向申请存在，应自动成为好友并清理 pending）
    response = client.post(
        reverse('befriend', args=[user1_id_for_3]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token3}'
    )
    assert response.status_code == 200

    # 1 检查好友列表（包含 2、3，无 pending）
    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token}'
    )
    assert response.status_code == 200
    friends_1 = response.json()['friends']
    pending_1 = response.json()['pending']
    assert user2_id in friends_1
    assert user3_id in friends_1
    assert user3_id not in pending_1

    # 3 检查好友列表（包含 1，无 pending）
    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt_token3}'
    )
    assert response.status_code == 200
    friends_3 = response.json()['friends']
    pending_3 = response.json()['pending']
    assert user1_id in friends_3
    assert user1_id not in pending_3

@pytest.mark.django_db
def test_disagree_flow(client: Client):
    # 无 JWT
    response = client.post(
        reverse('disagree', args=[123456]),
        content_type='application/json'
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4001

    # user1 注册
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'u1',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200
    jwt1 = response.json()['jwt_token']

    # user2 注册
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'u2',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200
    jwt2 = response.json()['jwt_token']

    # user1 获取 user2 的 id
    response = client.get(
        reverse("search", args=["u2"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt1}'
    )
    assert response.status_code == 200
    assert 'exact' in response.json() and len(response.json()['exact']) > 0
    u2_id = response.json()['exact'][0]

    # user1 获取自己的 id（用于后面方向校验）
    response = client.get(
        reverse("search", args=["u1"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt1}'
    )
    assert response.status_code == 200
    assert 'exact' in response.json() and len(response.json()['exact']) > 0
    u1_id = response.json()['exact'][0]

    # user1 -> user2 申请好友（创建 pending）
    response = client.post(
        reverse('befriend', args=[u2_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt1}'
    )
    assert response.status_code == 200

    # user2 查看 pending
    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt2}'
    )
    assert response.status_code == 200
    assert u1_id in response.json()['pending']
    assert u1_id not in response.json()['friends']

    # user2 拒绝（成功）
    response = client.post(
        reverse('disagree', args=[u1_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt2}'
    )
    assert response.status_code == 200

    # 拒绝后检查：无 pending、不是好友
    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt2}'
    )
    assert response.status_code == 200
    assert u1_id not in response.json()['pending']
    assert u1_id not in response.json()['friends']

    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt1}'
    )
    assert response.status_code == 200
    assert u2_id not in response.json()['pending']
    assert u2_id not in response.json()['friends']

    # 重复拒绝（pending 不存在）
    response = client.post(
        reverse('disagree', args=[u1_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt2}'
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4005

    # 方向错误：申请方自己拒绝
    response = client.post(
        reverse('befriend', args=[u2_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt1}'
    )
    assert response.status_code == 200

    response = client.post(
        reverse('disagree', args=[u2_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt1}'
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4005

    # 目标不存在
    response = client.post(
        reverse('disagree', args=[999999]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwt2}'
    )
    assert response.status_code == 404
    assert response.json().get('code') == 4003


@pytest.mark.django_db
def test_delete_friend_flow(client: Client):
    # 无 JWT
    response = client.post(
        reverse('delete_friend', args=[123456]),
        content_type='application/json'
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4001

    # 注册 userA
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'userA',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200
    jwtA = response.json()['jwt_token']

    # 注册 userB
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'userB',
        'password': 'test123456'
    }), content_type='application/json')
    assert response.status_code == 200
    jwtB = response.json()['jwt_token']

    # 获取彼此 id
    response = client.get(
        reverse("search", args=["userA"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtA}'
    )
    assert response.status_code == 200
    userA_id = response.json()['exact'][0]

    response = client.get(
        reverse("search", args=["userB"]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtA}'
    )
    assert response.status_code == 200
    userB_id = response.json()['exact'][0]

    # A -> B 申请，B 同意（成为好友）
    response = client.post(
        reverse('befriend', args=[userB_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtA}'
    )
    assert response.status_code == 200

    response = client.post(
        reverse('agree', args=[userA_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtB}'
    )
    assert response.status_code == 200

    # 成为好友后的列表检查
    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtA}'
    )
    assert response.status_code == 200
    assert userB_id in response.json()['friends']

    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtB}'
    )
    assert response.status_code == 200
    assert userA_id in response.json()['friends']

    # A 删除与 B 的好友关系（成功）
    response = client.post(
        reverse('delete_friend', args=[userB_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtA}'
    )
    assert response.status_code == 200

    # 删除后双方都不再是好友
    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtA}'
    )
    assert response.status_code == 200
    assert userB_id not in response.json()['friends']

    response = client.get(
        reverse("list_friends"),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtB}'
    )
    assert response.status_code == 200
    assert userA_id not in response.json()['friends']

    # 重复删除（关系不存在）
    response = client.post(
        reverse('delete_friend', args=[userB_id]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtA}'
    )
    assert response.status_code == 400
    assert response.json().get('code') == 4007

    # 目标不存在
    response = client.post(
        reverse('delete_friend', args=[999999]),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {jwtA}'
    )
    assert response.status_code == 404
    assert response.json().get('code') == 4003
