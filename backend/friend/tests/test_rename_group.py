import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from friend.models import FriendGroup
from utils.assert_response import assert_error_response
from utils.jwt import generate_jwt_token

User = get_user_model()

@pytest.mark.django_db
def test_rename_group_invalid_jwt(client):
    """❌ 无效JWT"""
    User.objects.create_user(username="testuser", password="Password123")
    resp = client.post(
        reverse("rename_group"),
        data=json.dumps({"group_id": 1, "name": "New Group Name"}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer invalidtoken"
    )
    assert_error_response(resp, 403, 4001, "Invalid JWT Token.")

@pytest.mark.django_db
def test_rename_group_missing_field(client):
    """❌ JWT格式错误（没有group_id或name）"""
    user = User.objects.create_user(username="testuser", password="Password123")
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("rename_group"),
        data=json.dumps({"group_id": 1}),  # Missing 'name'
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 4001, "Invalid request (without group_id or name)")

@pytest.mark.django_db
def test_rename_group_user_not_found(client):
    """❌ 用户不存在"""
    User.objects.create_user(username="testuser", password="Password123")
    token = generate_jwt_token(username="testser", id=9999)
    resp = client.post(
        reverse("rename_group"),
        data=json.dumps({"group_id": 1, "name": "New Group Name"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 404, 9001, "User not found.")

@pytest.mark.django_db
def test_rename_group_group_not_found(client):
    """❌ 分组不存在"""
    user = User.objects.create_user(username="testuser", password="Password123")
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("rename_group"),
        data=json.dumps({"group_id": 999, "name": "New Group Name"}),  # Group doesn't exist
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 404, 4016, "Group not found.")

@pytest.mark.django_db
def test_rename_group_success(client):
    """✅ 成功重命名分组"""
    user = User.objects.create_user(username="testuser", password="Password123")
    group = FriendGroup.objects.create(name="Old Group Name", user=user)
    token = generate_jwt_token(username="testuser", id=user.id)
    resp = client.post(
        reverse("rename_group"),
        data=json.dumps({"group_id": group.id, "name": "New Group Name"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    # Verify the group name has been updated
    group.refresh_from_db()
    assert group.name == "New Group Name"
