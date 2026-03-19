import json
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from utils.jwt import generate_jwt_token
from utils.assert_response import assert_error_response
from django.contrib.auth.hashers import check_password

User = get_user_model()


@pytest.mark.django_db
def test_delete_account_bad_method(client):
    """❌ 不使用POST方法"""
    resp = client.get(reverse("delete_account"))
    assert_error_response(resp, 405, -3, "Bad method.")


@pytest.mark.django_db
def test_delete_account_jwt_invalid(client):
    """❌ JWT无效"""
    user = User.objects.create_user(username="testuser", password="123456")
    resp = client.post(
        reverse("delete_account"),
        data=json.dumps({"password": "123456"}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer invalidtoken"
    )
    assert_error_response(resp, 403, 1301, "Invalid JWT Token.")


@pytest.mark.django_db
def test_delete_account_user_not_exist(client):
    """❌ 用户不存在"""
    token = generate_jwt_token("testuser", 9999)
    resp = client.post(
        reverse("delete_account"),
        data=json.dumps({"password": "123456"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 404, 1302, "User does not exist.")


@pytest.mark.django_db
def test_delete_account_missing_password(client):
    """❌ 请求体缺少 password"""
    user = User.objects.create_user(username="testuser", password="123456")
    token = generate_jwt_token("testuser", user.id)
    # body为空
    resp = client.post(
        reverse("delete_account"),
        data=json.dumps({}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 1303, "Missing password in request body.")


@pytest.mark.django_db
def test_delete_account_wrong_password(client):
    """❌ 密码错误"""
    user = User.objects.create_user(username="testuser", password="123456")
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("delete_account"),
        data=json.dumps({"password": "wrongpass"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 403, 1304, "Password incorrect.")


@pytest.mark.django_db
def test_delete_account_success(client):
    """✅ 成功注销用户（软删除）"""
    user = User.objects.create_user(username="testuser", password="123456", email="test@example.com", info="some info")
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("delete_account"),
        data=json.dumps({"password": "123456"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    
    # 确认用户仍然存在，但状态已变更
    user.refresh_from_db()
    assert user.is_active is False
    assert user.email == ""
    assert user.info == ""
    assert user.avatar == ""
    assert not user.has_usable_password()


@pytest.mark.django_db
def test_register_after_deletion(client):
    """✅ 注销后可以使用相同用户名注册新用户"""
    # 创建用户
    user = User.objects.create_user(username="testuser", password="123456", email="test@example.com", info="some info")
    
    # 注销用户
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("delete_account"),
        data=json.dumps({"password": "123456"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    
    # 使用相同用户名注册新用户
    resp = client.post(
        reverse("register"),
        data=json.dumps({"username": "testuser", "password": "newpassword123"}),
        content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "jwt_token" in data
    
    # 验证新用户已创建
    new_user = User.objects.filter(username="testuser", is_active=True).first()
    assert new_user is not None
    assert new_user.id != user.id  # 确保是不同的用户记录


@pytest.mark.django_db
def test_login_after_deletion(client):
    """❌ 注销后无法使用原账户登录"""
    # 创建用户
    user = User.objects.create_user(username="testuser", password="123456")
    
    # 注销用户
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("delete_account"),
        data=json.dumps({"password": "123456"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    
    # 尝试使用原账户登录
    resp = client.post(
        reverse("login"),
        data=json.dumps({"username": "testuser", "password": "123456"}),
        content_type="application/json"
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["code"] == 1005
    assert "deactivated" in data["info"].lower()
