import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from utils.assert_response import assert_error_response
from utils.jwt import generate_jwt_token

User = get_user_model()


@pytest.mark.django_db
def test_befriend_deactivated_user(client):
    """❌ 尝试与已注销用户建立好友关系"""
    # 创建普通用户和已注销用户
    active_user = User.objects.create_user(username="activeuser", password="123456")
    deactivated_user = User.objects.create_user(username="deactivateduser", password="123456")
    deactivated_user.is_active = False
    deactivated_user.save()

    # 尝试与已注销用户建立好友关系
    response = client.post(
        reverse("befriend", args=[deactivated_user.id]),
        HTTP_AUTHORIZATION=f"Bearer {generate_jwt_token('activeuser', active_user.id)}"
    )

    assert_error_response(response, 400, 4009, "Cannot befriend a deactivated user.")


@pytest.mark.django_db
def test_agree_deactivated_user_request(client):
    """❌ 尝试同意已注销用户的好友请求"""
    # 创建普通用户和已注销用户
    active_user = User.objects.create_user(username="activeuser", password="123456")
    deactivated_user = User.objects.create_user(username="deactivateduser", password="123456")
    deactivated_user.is_active = False
    deactivated_user.save()

    # 尝试同意已注销用户的好友请求
    response = client.post(
        reverse("agree", args=[deactivated_user.id]),
        HTTP_AUTHORIZATION=f"Bearer {generate_jwt_token('activeuser', active_user.id)}"
    )

    assert_error_response(response, 400, 4010, "Cannot establish friendship with deactivated users.")


@pytest.mark.django_db
def test_check_friendship_with_deactivated_user(client):
    """❌ 尝试检查与已注销用户的好友关系"""
    # 创建普通用户和已注销用户
    active_user = User.objects.create_user(username="activeuser", password="123456")
    deactivated_user = User.objects.create_user(username="deactivateduser", password="123456")
    deactivated_user.is_active = False
    deactivated_user.save()

    # 尝试检查与已注销用户的好友关系
    response = client.get(
        reverse("check_friendship", args=[deactivated_user.id]),
        HTTP_AUTHORIZATION=f"Bearer {generate_jwt_token('activeuser', active_user.id)}"
    )

    assert_error_response(response, 400, 4011, "Target user has been deactivated.")


@pytest.mark.django_db
def test_add_deactivated_user_to_group(client):
    """❌ 尝试将已注销用户添加到好友分组"""
    # 创建普通用户、已注销用户和好友分组
    active_user = User.objects.create_user(username="activeuser", password="123456")
    deactivated_user = User.objects.create_user(username="deactivateduser", password="123456")
    deactivated_user.is_active = False
    deactivated_user.save()

    # 创建好友分组
    from friend.models import FriendGroup
    group = FriendGroup.objects.create(name="Test Group", user=active_user)

    # 尝试将已注销用户添加到好友分组
    response = client.post(
        reverse("add_to_group"),
        data=json.dumps({"group_id": group.id, "friend_id": deactivated_user.id}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {generate_jwt_token('activeuser', active_user.id)}"
    )

    assert_error_response(response, 400, 4014, "Cannot add deactivated user to friend group.")
