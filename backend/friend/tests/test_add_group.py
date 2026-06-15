import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from friend.models import FriendGroup, Friendship
from utils.assert_response import assert_error_response
from utils.jwt import generate_jwt_token

User = get_user_model()

@pytest.mark.django_db
def test_add_friend_to_group_invalid_jwt(client):
    """❌ 无效JWT"""
    User.objects.create_user(username="testuser", password="Password123")
    resp = client.post(
        reverse("add_to_group"),
        data=json.dumps({"group_id": 1, "friend_id": 2}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer invalidtoken"
    )
    assert_error_response(resp, 403, 4001, "Invalid JWT Token.")

@pytest.mark.django_db
def test_add_friend_to_group_missing_field(client):
    """❌ JWT格式错误（没有group_id或friend_id）"""
    user = User.objects.create_user(username="testuser", password="Password123")
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("add_to_group"),
        data=json.dumps({"group_id": 1}),  # Missing 'friend_id'
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 4001, "Invalid request (without group_id or friend_id)")

@pytest.mark.django_db
def test_add_friend_to_group_user_not_found(client):
    """❌ 用户不存在"""
    User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    token = generate_jwt_token(username="testusr", id=999)
    resp = client.post(
        reverse("add_to_group"),
        data=json.dumps({"group_id": 1, "friend_id": friend.id}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 404, 9001, "User not found.")


@pytest.mark.django_db
def test_add_friend_to_group_friend_not_found(client):
    """❌ 好友不存在"""
    user = User.objects.create_user(username="testuser", password="Password123")
    User.objects.create_user(username="friend", password="Password123")
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("add_to_group"),
        data=json.dumps({"group_id": 1, "friend_id": 999}),  # Friend doesn't exist
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 404, 4012, "Friend not found.")

@pytest.mark.django_db
def test_add_friend_to_group_not_friend(client):
    """❌ 用户与好友没有好友关系"""
    user = User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("add_to_group"),
        data=json.dumps({"group_id": 1, "friend_id": friend.id}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 4013, "Users are not friends.")

@pytest.mark.django_db
def test_add_friend_to_group_group_not_found(client):
    """❌ 分组不存在"""
    user = User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    Friendship.objects.create(user_a=user, user_b=friend) # 添加好友关系
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("add_to_group"),
        data=json.dumps({"group_id": 999, "friend_id": friend.id}),  # Group doesn't exist
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 404, 4014, "Group not found.")

@pytest.mark.django_db
def test_add_friend_to_group_already_in_group(client):
    """❌ 好友已在分组中"""
    user = User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    Friendship.objects.create(user_a=user, user_b=friend) # 添加好友关系
    group = FriendGroup.objects.create(name="Group1", user=user)
    group.add_friend(friend=friend)
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("add_to_group"),
        data=json.dumps({"group_id": group.id, "friend_id": friend.id}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 4015, "Friend already in a group.")

@pytest.mark.django_db
def test_add_friend_to_group_success(client):
    """✅ 成功添加好友到分组"""
    user = User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    Friendship.objects.create(user_a=user, user_b=friend) # 添加好友关系
    group = FriendGroup.objects.create(name="Group1", user=user)
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("add_to_group"),
        data=json.dumps({"group_id": group.id, "friend_id": friend.id}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
