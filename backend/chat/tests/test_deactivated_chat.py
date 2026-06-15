import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from friend.models import Friendship
from utils.assert_response import assert_error_response
from utils.jwt import generate_jwt_token

User = get_user_model()

@pytest.mark.django_db
def test_create_group_with_deactivated_user(client):
    """❌ 尝试创建包含已注销用户的群聊"""
    creator = User.objects.create_user(username="creator", password="123456")
    user1 = User.objects.create_user(username="user1", password="123456")
    deactivated_user = User.objects.create_user(username="deactivated", password="123456")
    deactivated_user.is_active = False
    deactivated_user.save()

    token = generate_jwt_token("creator", creator.id)

    # 尝试创建群聊，包含已注销用户
    resp = client.post(
        reverse("create_group"),
        data=json.dumps({
            "name": "Test Group",
            "members": [user1.id, deactivated_user.id]
        }),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )

    # 应该失败，或者成功但不包含已注销用户？
    # 通常应该报错，或者忽略已注销用户。
    # 假设应该报错，因为请求包含了无效用户。
    # 如果后端只是忽略，那么 assert 会不同。
    # 让我们先假设应该报错。
    assert_error_response(resp, 400, 2005, "Cannot add deactivated user to group.")

@pytest.mark.django_db
def test_create_friend_conversation_with_deactivated_user(client):
    """❌ 尝试与已注销好友创建会话"""
    user = User.objects.create_user(username="user", password="123456")
    friend = User.objects.create_user(username="friend", password="123456")

    # 先建立好友关系
    Friendship.objects.create(user_a=user, user_b=friend)

    # 好友注销
    friend.is_active = False
    friend.save()

    token = generate_jwt_token("user", user.id)

    # 尝试创建会话
    resp = client.post(
        reverse("create_friend_conversation"),
        data=json.dumps({"id": friend.id}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )

    assert_error_response(resp, 400, 2006, "Cannot chat with deactivated user.")
