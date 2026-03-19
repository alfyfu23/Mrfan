import json
import pytest
from friend.models import FriendGroup,Friendship
from django.urls import reverse
from django.contrib.auth import get_user_model
from utils.jwt import generate_jwt_token
from utils.assert_response import assert_error_response

User = get_user_model()

@pytest.mark.django_db
def test_remove_friend_from_group_invalid_jwt(client):
    """❌ 无效JWT"""
    user = User.objects.create_user(username="testuser", password="Password123")
    resp = client.post(
        reverse("remove_from_group"),
        data=json.dumps({"group_id": 1, "friend_id": 2}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer invalidtoken"
    )
    assert_error_response(resp, 403, 4001, "Invalid JWT Token.")

@pytest.mark.django_db
def test_remove_friend_from_group_missing_field(client):
    """❌ JWT格式错误（没有group_id或friend_id）"""
    user = User.objects.create_user(username="testuser", password="Password123")
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("remove_from_group"),
        data=json.dumps({"group_id": 1}),  # Missing 'friend_id'
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 4001, "Invalid request (without group_id or friend_id)")

@pytest.mark.django_db
def test_remove_friend_from_group_user_not_found(client):
    """❌ 用户不存在"""
    user = User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    Friendship.objects.create(user_a=user, user_b=friend) # 添加好友关系
    token = generate_jwt_token(username="testser", id=9999)
    resp = client.post(
        reverse("remove_from_group"),
        data=json.dumps({"group_id": 1, "friend_id": friend.id}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 404, 9001, "User not found.")
    
@pytest.mark.django_db
def test_remove_friend_from_group_user_not_found(client):
    """❌ 好友不存在"""
    user = User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    Friendship.objects.create(user_a=user, user_b=friend) # 添加好友关系
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("remove_from_group"),
        data=json.dumps({"group_id": 1, "friend_id": 999}),  # Friend doesn't exist
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 404, 4012, "Friend not found.")

@pytest.mark.django_db
def test_remove_friend_from_group_not_friend(client):
    """❌ 用户与好友没有好友关系"""
    user = User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("remove_from_group"),
        data=json.dumps({"group_id": 1, "friend_id": friend.id}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 4013, "Users are not friends.")

@pytest.mark.django_db
def test_remove_friend_from_group_group_not_found(client):
    """❌ 分组不存在"""
    user = User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    Friendship.objects.create(user_a=user, user_b=friend) # 添加好友关系
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("remove_from_group"),
        data=json.dumps({"group_id": 999, "friend_id": friend.id}),  # Group doesn't exist
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 404, 4014, "Group not found.")

@pytest.mark.django_db
def test_remove_friend_from_group_friend_not_in_group(client):
    """❌ 好友不在分组中"""
    user = User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    Friendship.objects.create(user_a=user, user_b=friend) # 添加好友关系
    group = FriendGroup.objects.create(name="Group1", user=user)
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("remove_from_group"),
        data=json.dumps({"group_id": group.id, "friend_id": friend.id}),  # Friend not in group
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 4015, "Friend not in the group.")

@pytest.mark.django_db
def test_remove_friend_from_group_success(client):
    """✅ 成功从分组移除好友"""
    user = User.objects.create_user(username="testuser", password="Password123")
    friend = User.objects.create_user(username="friend", password="Password123")
    Friendship.objects.create(user_a=user, user_b=friend) # 添加好友关系
    group = FriendGroup.objects.create(name="Group1", user=user)
    group.friends.add(friend)  # Add friend to group
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("remove_from_group"),
        data=json.dumps({"group_id": group.id, "friend_id": friend.id}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
