import json
import pytest
from friend.models import FriendGroup
from django.urls import reverse
from django.contrib.auth import get_user_model
from utils.jwt import generate_jwt_token
from utils.assert_response import assert_error_response
User = get_user_model()

@pytest.mark.django_db
def test_create_friend_group_bad_method(client):
    """❌ 使用不支持的 GET 方法"""
    resp = client.get(reverse("create_friend_group"))
    assert_error_response(resp, 405, -3, "Bad method.")

@pytest.mark.django_db
def test_create_friend_group_invalid_jwt(client):
    """❌ JWT无效"""
    user = User.objects.create_user(username="testuser", password="test123456")
    resp = client.post(
        reverse("create_friend_group"),
        data=json.dumps({"name": "New Group"}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer invalidtoken"
    )
    assert_error_response(resp, 403, 4001, "Invalid JWT Token.")

@pytest.mark.django_db
def test_create_friend_group_user_not_found(client):
    """❌ 用户不存在"""
    # 模拟一个无效的JWT token
    invalid_token = generate_jwt_token(username="testusr", id=9999)  # 假设9999是不存在的用户ID
    resp = client.post(
        reverse("create_friend_group"),
        data=json.dumps({"name": "New Group"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {invalid_token}"
    )
    assert_error_response(resp, 404, 9001, "User not found.")

@pytest.mark.django_db
def test_create_friend_group_name_empty(client):
    """❌ 创建分组时组名为空"""
    user = User.objects.create_user(username="testuser", password="test123456")
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("create_friend_group"),
        data=json.dumps({"name": ""}),  # 组名为空
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 4010, "Group name cannot be empty.")

@pytest.mark.django_db
def test_create_friend_group_name_exists(client):
    """❌ 创建分组时同名分组已存在"""
    user = User.objects.create_user(username="testuser", password="test123456")
    token = generate_jwt_token(username="testuser", id=user.id)
    
    # 创建一个分组
    FriendGroup.objects.create(name="Existing Group", user=user)
    
    resp = client.post(
        reverse("create_friend_group"),
        data=json.dumps({"name": "Existing Group"}),  # 已存在的组名
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 4011, "Group name already exists.")

@pytest.mark.django_db
def test_create_friend_group_success(client):
    """✅ 成功创建分组"""
    user = User.objects.create_user(username="testuser", password="test123456")
    token = generate_jwt_token(username="testuser", id=user.id)
    
    resp = client.post(
        reverse("create_friend_group"),
        data=json.dumps({"name": "New Group"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    
    response_data = resp.json()
    assert response_data.get("code") == 0, f"Expected 'code' to be 0, but got {response_data.get('code')}"
    assert "id" in response_data
    group_id = response_data["id"]
    
    # 验证分组是否被创建
    group = FriendGroup.objects.get(id=group_id)
    assert group.name == "New Group"
    assert group.user == user
