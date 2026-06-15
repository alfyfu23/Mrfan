import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from friend.models import FriendGroup, Friendship
from utils.assert_response import assert_error_response
from utils.jwt import generate_jwt_token

User = get_user_model()

@pytest.mark.django_db
def test_list_groups_bad_method(client):
    """❌ 使用不支持的 POST 方法"""
    resp = client.post(reverse("list_groups"))
    assert_error_response(resp, 405, -3, "Bad method.")

@pytest.mark.django_db
def test_list_groups_invalid_jwt(client):
    """❌ JWT无效"""
    User.objects.create_user(username="testuser", password="test123456")
    resp = client.get(
        reverse("list_groups"),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer invalidtoken"
    )
    assert_error_response(resp, 403, 4001, "Invalid JWT Token.")

@pytest.mark.django_db
def test_list_groups_user_not_found(client):
    """❌ 用户不存在"""
    # 模拟一个无效的JWT token
    invalid_token = generate_jwt_token(username="testuser", id=9999)  # 假设9999是不存在的用户ID
    resp = client.get(
        reverse("list_groups"),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {invalid_token}"
    )
    assert_error_response(resp, 404, 9001, "User not found.")

@pytest.mark.django_db
def test_list_groups_success(client):
    """✅ 成功列出好友分组"""
    user = User.objects.create_user(username="testuser", password="test123456")
    token = generate_jwt_token(username="testuser", id=user.id)

    # 创建一些分组
    group1 = FriendGroup.objects.create(name="Group 1", user=user)
    group2 = FriendGroup.objects.create(name="Group 2", user=user)

    # 添加好友到分组
    friend1 = User.objects.create_user(username="friend1", password="password1")
    friend2 = User.objects.create_user(username="friend2", password="password2")

    group1.friends.add(friend1)
    group2.friends.add(friend2)

    # 未分组的好友
    friend3 = User.objects.create_user(username="friend3", password="password3")
    Friendship.objects.create(user_a=user, user_b=friend3)

    # 获取好友分组列表
    resp = client.get(
        reverse("list_groups"),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )

    response_data = resp.json()

    # 验证分组列表数据
    assert response_data.get("code") == 0, f"Expected 'code' to be 0, but got {response_data.get('code')}"

    # 检查返回的分组名
    assert "Group 1" in [group['name'] for group in response_data['groups']]
    assert "Group 2" in [group['name'] for group in response_data['groups']]
    assert "未分组" in [group['name'] for group in response_data['groups']]

    # 验证成员ID是否正确
    group1_data = next(group for group in response_data['groups'] if group['name'] == "Group 1")
    group2_data = next(group for group in response_data['groups'] if group['name'] == "Group 2")
    ungrouped_data = next(group for group in response_data['groups'] if group['name'] == "未分组")

    # 验证好友1、2是否在正确的分组中
    assert friend1.id in group1_data['members']
    assert friend2.id in group2_data['members']
    # 验证未分组的好友是否在未分组中
    assert friend3.id in ungrouped_data['members']
