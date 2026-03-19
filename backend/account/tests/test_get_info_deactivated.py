import json
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from utils.jwt import generate_jwt_token
from utils.assert_response import assert_error_response

User = get_user_model()


@pytest.mark.django_db
def test_get_info_deactivated_user(client):
    """✅ 获取已注销用户信息"""
    # 创建并注销用户
    user = User.objects.create_user(username="testuser", password="123456", info="original info")
    user.is_active = False
    user.save()
    
    # 获取已注销用户信息
    response = client.get(
        reverse("get_info") + f"?target={user.id}",
        HTTP_AUTHORIZATION=f"Bearer {generate_jwt_token('otheruser', 999)}"
    )
    
    data = response.json()
    assert response.status_code == 200
    assert data["code"] == 0
    assert data["username"] == "testuser"
    assert data["info"] == "此用户已注销"
    assert data["is_active"] is False
    assert data["avatar"] == ""


@pytest.mark.django_db
def test_get_self_info_deactivated_user(client):
    """❌ 已注销用户获取自己的信息"""
    # 创建并注销用户
    user = User.objects.create_user(username="testuser", password="123456", info="original info")
    user.is_active = False
    user.save()
    
    # 已注销用户尝试获取自己的信息
    response = client.get(
        reverse("get_info"),
        HTTP_AUTHORIZATION=f"Bearer {generate_jwt_token('testuser', user.id)}"
    )
    
    # 由于用户已注销，JWT应该仍然有效，但获取信息应该返回已注销状态
    data = response.json()
    assert response.status_code == 200
    assert data["code"] == 0
    assert data["username"] == "testuser"
    assert data["info"] == ""
    assert data["is_active"] is False