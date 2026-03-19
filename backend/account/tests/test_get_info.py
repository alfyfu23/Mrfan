import json
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from utils.jwt import generate_jwt_token
from utils.assert_response import assert_error_response


@pytest.fixture
def register_user(client):
    """注册一个测试用户并返回 (user, jwt_token)"""
    resp = client.post(
        reverse('register'),
        data=json.dumps({'username': 'test_user', 'password': 'test123456'}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    token = resp.json()['jwt_token']
    user = get_user_model().objects.get(username='test_user')
    return user, token

@pytest.mark.django_db
def test_bad_method(client):
    """❌ 不使用GET方法"""
    resp = client.post(reverse("get_info"))
    assert_error_response(resp, 405, -3, "Bad method.")


@pytest.mark.django_db
def test_info_invalid_jwt(client: Client):
    """❌ 无效 JWT：应返回 403, code=1101"""
    resp = client.get(
        reverse('get_info'),
        HTTP_AUTHORIZATION='Bearer invalid.token',
        content_type='application/json'
    )
    assert_error_response(resp, 403, 1101, "Invalid JWT token.")
    

@pytest.mark.django_db
def test_get_info_user_not_exist(client: Client):
    """❌ 用户不存在：应返回 404, code=1102"""
    fake_token = generate_jwt_token(username='ghost', id=9999)
    resp = client.get(
        reverse('get_info') + '?target=9999',
        HTTP_AUTHORIZATION=f'Bearer {fake_token}',
        content_type='application/json'
    )
    assert_error_response(resp, 404, 1102, "User does not exist.")


@pytest.mark.django_db
def test_get_info_self_success(client: Client, register_user):
    """✅ 正常获取本人信息"""
    user, token = register_user
    resp = client.get(
        reverse('get_info'),
        HTTP_AUTHORIZATION=f'Bearer {token}',
        content_type='application/json'
    )
    data = resp.json()
    assert resp.status_code == 200
    assert data["code"] == 0
    assert data["username"] == user.username
    assert "avatar" in data
    assert "info" in data


@pytest.mark.django_db
def test_get_info_other_user_basic_only(client: Client, register_user):
    """✅ 查看他人信息：仅返回基本信息"""
    user, token = register_user

    # 创建另一个用户
    other = get_user_model().objects.create_user(
        username='friend',
        password='friend12345'
    )

    # 用第一个用户的 token 请求第二个用户的信息
    resp = client.get(
        reverse('get_info') + f'?target={other.id}',
        HTTP_AUTHORIZATION=f'Bearer {token}',
        content_type='application/json'
    )
    data = resp.json()
    assert resp.status_code == 200
    assert data["code"] == 0
    assert data["username"] == "friend"
    # 他人信息不应包含敏感字段
    assert "email" not in data
    assert "phone" not in data
