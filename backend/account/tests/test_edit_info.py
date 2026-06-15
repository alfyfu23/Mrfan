import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from utils.assert_response import assert_error_response
from utils.jwt import generate_jwt_token

User = get_user_model()

@pytest.mark.django_db
def test_bad_method(client):
    """❌ 不使用POST方法"""
    resp = client.get(reverse("edit_info"))
    assert_error_response(resp, 405, -3, "Bad method.")

@pytest.mark.django_db
def test_edit_info_jwt_invalid(client):
    """❌ JWT无效"""
    User.objects.create_user(username="testuser", password="123456")
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field": "username", "value": "newuser", "password":""}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer invalidtoken"
    )
    assert_error_response(resp, 403, 1201, "Invalid JWT Token.")

@pytest.mark.django_db
def test_edit_info_user_not_exist(client):
    """❌ 用户不存在"""
    token = generate_jwt_token("testuser", 9999)
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field": "username", "value": "newuser", "password":""}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 404, 1202, "User does not exist.")

@pytest.mark.django_db
def test_edit_info_request_body_missing_fields(client):
    """❌ 请求体缺少字段"""
    user = User.objects.create_user(username="testuser", password="123456")
    token = generate_jwt_token("testuser", user.id)

    # 缺少 password
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field":"username", "value":"newuser"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 1203, "Invalid request body.")

    # 缺少 value
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field":"username", "password":""}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 1203, "Invalid request body.")

    # 缺少 field
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"password":"", "value":"newuser"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 1203, "Invalid request body.")

@pytest.mark.django_db
def test_edit_info_invalid_field(client):
    """❌ 错误的field"""
    user = User.objects.create_user(username="testuser", password="123456")
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field": "nonexistent_field", "value": "abc", "password":""}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 400, 1204, "Invalid field value.")

@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value",
    [
        ("username", "newuser"),
        ("avatar", "http://example.com/avatar.png"),
        ("info", "New info text."),
    ],
)
def test_edit_info_normal_field_success(client, field, value):
    """✅ 修改普通字段(username/avatar/info)"""
    user = User.objects.create_user(username="testuser", password="123456")
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field": field, "value": value, 'password': ""}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    updated_user = User.objects.get(id=user.id)
    assert getattr(updated_user, field) == value

@pytest.mark.django_db
def test_edit_info_password_wrong(client):
    """❌ 修改密码时原密码错误"""
    user = User.objects.create_user(username="testuser", password="123456")
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field": "password", "password": "wrongpass", "value": "newpass123"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 403, 1205, "Password incorrect.")

@pytest.mark.django_db
def test_edit_info_password_success(client):
    """✅ 修改密码成功"""
    user = User.objects.create_user(username="testuser", password="123456")
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field": "password", "password": "123456", "value": "newpass123"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    updated_user = User.objects.get(id=user.id)
    assert updated_user.check_password("newpass123")

@pytest.mark.django_db
def test_edit_info_email_wrong_password(client):
    """❌ 修改邮箱时原密码错误"""
    user = User.objects.create_user(username="testuser", password="123456", email="old@example.com")
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field": "email", "password": "wrongpass", "value": "new@example.com"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 403, 1205, "Password incorrect.")

@pytest.mark.django_db
def test_edit_info_email_success(client):
    """✅ 修改邮箱成功"""
    user = User.objects.create_user(username="testuser", password="123456", email="old@example.com")
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field": "email", "password": "123456", "value": "new@example.com"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    updated_user = User.objects.get(id=user.id)
    assert updated_user.email == "new@example.com"

@pytest.mark.django_db
def test_edit_info_phone_wrong_password(client):
    """❌ 修改手机号时原密码错误"""
    user = User.objects.create_user(username="testuser", password="123456", phone="12345678901")
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field": "phone", "password": "wrongpass", "value": "19876543210"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert_error_response(resp, 403, 1205, "Password incorrect.")

@pytest.mark.django_db
def test_edit_info_phone_success(client):
    """✅ 修改手机号成功"""
    user = User.objects.create_user(username="testuser", password="123456", phone="12345678901")
    token = generate_jwt_token("testuser", user.id)
    resp = client.post(
        reverse("edit_info"),
        data=json.dumps({"field": "phone", "password": "123456", "value": "19876543210"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    updated_user = User.objects.get(id=user.id)
    assert updated_user.phone == "19876543210"
