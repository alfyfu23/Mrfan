import json
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from utils.jwt import generate_jwt_token
from utils.assert_response import assert_error_response

User = get_user_model()


@pytest.mark.django_db
def test_login_deactivated_user(client):
    """❌ 尝试登录已注销的用户"""
    # 创建并注销用户
    user = User.objects.create_user(username="testuser", password="123456")
    user.is_active = False
    user.save()
    
    # 尝试登录已注销的用户
    response = client.post(reverse('login'), data=json.dumps({
        'username': 'testuser',
        'password': '123456'
    }), content_type='application/json')
    
    assert_error_response(response, 403, 1005, "User account has been deactivated.")


@pytest.mark.django_db
def test_register_with_deactivated_username(client):
    """✅ 使用已注销用户的用户名注册新用户"""
    # 创建并注销用户
    user = User.objects.create_user(username="olduser", password="123456")
    user.is_active = False
    user.save()
    
    # 使用相同的用户名注册新用户
    response = client.post(reverse('register'), data=json.dumps({
        'username': 'olduser',
        'password': 'newpassword123'
    }), content_type='application/json')
    
    data = response.json()
    assert response.status_code == 200
    assert data["code"] == 0
    assert "jwt_token" in data
    
    # 验证新用户已创建
    new_user = User.objects.filter(username="olduser", is_active=True).first()
    assert new_user is not None
    assert new_user.id != user.id  # 确保是不同的用户记录