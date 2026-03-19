import json
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from utils.assert_response import assert_error_response

User = get_user_model()


@pytest.mark.django_db
def test_bad_method(client):
    """❌ 不使用POST方法"""
    resp = client.get(reverse("login"))
    assert_error_response(resp, 405, -3, "Bad method.")
    
@pytest.mark.django_db
def test_login_invalid_body(client):
    """❌ JSON 解析失败或字段缺失"""
    # 空 body
    resp = client.post(reverse("login"), data="", content_type="application/json")
    assert_error_response(resp, 400, 1001, "Invalid request. Username or password not found.")

    # 缺少字段
    resp = client.post(
        reverse("login"),
        data=json.dumps({"username": "onlyname"}),
        content_type="application/json",
    )
    assert_error_response(resp, 400, 1001, "Invalid request. Username or password not found.")


@pytest.mark.django_db
def test_login_user_not_found(client):
    """❌ 用户名不存在"""
    # 注册一个正常用户
    client.post(reverse('register'), data=json.dumps({
        'username': 'test_user',
        'password': 'test123456'
    }), content_type='application/json')

    # 尝试用不存在的用户名登录
    response = client.post(reverse('login'), data=json.dumps({
        'username': 'test_ser',  # 拼写错误
        'password': 'test12345'
    }), content_type='application/json')

    assert_error_response(response, 404, 1003, "Username does not exist.")


@pytest.mark.django_db
def test_login_wrong_password(client):
    """❌ 密码错误"""
    # 注册一个正常用户
    client.post(reverse('register'), data=json.dumps({
        'username': 'test_user',
        'password': 'test123456'
    }), content_type='application/json')

    # 用错误密码登录
    response = client.post(reverse('login'), data=json.dumps({
        'username': 'test_user',
        'password': 'wrongpwd'
    }), content_type='application/json')

    assert_error_response(response, 400, 1004, "Wrong password.")


@pytest.mark.django_db
def test_login_success(client):
    """✅ 正确登录"""
    # 注册一个用户
    register_resp = client.post(reverse('register'), data=json.dumps({
        'username': 'test_user',
        'password': 'test123456'
    }), content_type='application/json')
    assert register_resp.status_code == 200

    # 使用正确的用户名密码登录
    response = client.post(reverse('login'), data=json.dumps({
        'username': 'test_user',
        'password': 'test123456'
    }), content_type='application/json')

    data = response.json()
    assert response.status_code == 200
    assert data["code"] == 0
    assert data["username"] == 'test_user'
    assert "jwt_token" in data
    # 验证用户确实存在数据库中
    assert User.objects.filter(username='test_user').exists()
