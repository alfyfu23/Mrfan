import json
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from utils.assert_response import assert_error_response
User = get_user_model()

@pytest.mark.django_db
def test_register_success(client):
    """✅ 正常注册"""
    resp = client.post(
        reverse("register"),
        data=json.dumps({"username": "user001", "password": "abc12345"}),
        content_type="application/json",
    )
    data = resp.json()
    assert resp.status_code == 200
    assert data["code"] == 0
    assert "jwt_token" in data
    assert User.objects.filter(username="user001").exists()

@pytest.mark.django_db
def test_bad_method(client):
    """❌ 不使用POST方法"""
    resp = client.get(reverse("register"))
    assert_error_response(resp, 405, -3, "Bad method.")
    

@pytest.mark.django_db
def test_register_invalid_body(client):
    """❌ JSON 解析失败或字段缺失"""
    # 空 body
    resp = client.post(reverse("register"), data="", content_type="application/json")
    assert_error_response(resp, 400, 1001, "Invalid request. Username or password not found.")

    # 缺少字段
    resp = client.post(
        reverse("register"),
        data=json.dumps({"username": "onlyname"}),
        content_type="application/json",
    )
    assert_error_response(resp, 400, 1001, "Invalid request. Username or password not found.")


@pytest.mark.django_db
def test_register_duplicate_username(client):
    """❌ 用户名重复"""
    User.objects.create_user(username="dup_user", password="abc12345")
    resp = client.post(
        reverse("register"),
        data=json.dumps({"username": "dup_user", "password": "abc12345"}),
        content_type="application/json",
    )
    assert_error_response(resp, 400, 1002, "Username already exists.")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "username",
    [
        "bad@name",    # 特殊字符
        "a" * 50,      # 太长
        "",            # 太短
        ".startdot",   # 以点开头
        "_startunder", # 以下划线开头
        "enddot.",     # 以点结尾
        "endunder_"    # 以下划线结尾
    ],
)
def test_register_invalid_username_format(client, username):
    """❌ 用户名格式不合法"""
    resp = client.post(
        reverse("register"),
        data=json.dumps({"username": username, "password": "abc12345"}),
        content_type="application/json",
    )
    assert_error_response(resp, 400, 1005, "Username format invalid.")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "password",
    [
        "abc",        # 太短
        "a" * 129,    # 太长
        "12345678",   # 没有字母
        "abcdefgh",   # 没有数字
        "abc 1234",   # 含空格
    ],
)
def test_register_invalid_password_format(client, password):
    """❌ 密码格式不合法"""
    resp = client.post(
        reverse("register"),
        data=json.dumps({"username": "user_test", "password": password}),
        content_type="application/json",
    )
    assert_error_response(resp, 400, 1006, "Password format invalid.")
