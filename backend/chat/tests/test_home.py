import json
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from utils.jwt import generate_jwt_token
from utils.assert_response import assert_error_response
from chat.models import Conversation, Member, Message


@pytest.fixture
def create_user():
    """创建测试用户"""
    User = get_user_model()
    return User.objects.create_user(username="alice", password="test123")


@pytest.fixture
def auth_client(client, create_user):
    """返回带 JWT 的客户端"""
    token = generate_jwt_token(create_user.username, create_user.id)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client, create_user, token


@pytest.mark.django_db
def test_bad_method(client):
    """❌ 不使用GET方法"""
    resp = client.post(reverse("home"))
    assert_error_response(resp, 405, -3, "Bad method.")


@pytest.mark.django_db
def test_invalid_jwt(client):
    """❌ JWT 无效"""
    client.defaults['HTTP_AUTHORIZATION'] = "Bearer invalid.token"
    resp = client.get(reverse("home"))
    assert_error_response(resp, 403, 5001, "Invalid JWT Token.")

@pytest.mark.django_db
def test_user_not_found(client):
    """❌ 用户不存在"""
    fake_user_id = 999
    token = generate_jwt_token('alice', fake_user_id)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    resp = client.get(reverse("home"))
    assert_error_response(resp, 500, 9001, "User not found.")


@pytest.mark.django_db
def test_user_has_no_conversation(auth_client):
    """✅ 用户存在但无会话"""
    client, user, _ = auth_client
    resp = client.get(reverse("home"))

    assert resp.status_code == 200
    data = resp.json()
    assert "conversations" in data
    assert data["conversations"] == []


@pytest.mark.django_db
def test_user_with_conversation_and_messages(auth_client):
    """✅ 用户有会话、成员、消息"""
    client, user, _ = auth_client

    # 创建群聊
    conv = Conversation.objects.create(
        name="测试群聊",
        type="group",
        avatar="https://cdn.example.com/group.jpg"
    )

    # 当前用户是成员
    member_alice = Member.objects.create(
        conversation=conv, user=user, nickname="Alice",
        mute=False, pinned=True, time=timezone.now(), role="member"
    )

    # 另一个用户
    User = get_user_model()
    bob = User.objects.create_user(username="bob", password="123")
    member_bob = Member.objects.create(
        conversation=conv, user=bob, nickname="Bob",
        mute=False, pinned=False, time=timezone.now(), role="member"
    )

    # 创建两条消息
    msg1 = Message.objects.create(
        conversation=conv, member=member_bob, content="你好 Alice！"
    )
    msg2 = Message.objects.create(
        conversation=conv, member=member_alice, content="你好 Bob！"
    )

    # 模拟已读
    msg1.read_list.add(member_alice)
    msg2.read_list.add(member_bob)

    # 请求接口
    resp = client.get(reverse("home"))
    assert resp.status_code == 200

    data = resp.json()
    assert "conversations" in data
    convs = data["conversations"]
    assert len(convs) == 1

    c = convs[0]
    # ---- 验证会话字段 ----
    assert c["id"] == conv.id
    assert c["name"] == "测试群聊"
    assert c["avatar"] == "https://cdn.example.com/group.jpg"
    assert c["muted"] is False
    assert c["pinned"] is True

    # ---- 验证成员信息 ----
    members = c["members"]
    assert isinstance(members, list)
    names = {m["nickname"] for m in members}
    assert names == {"Alice", "Bob"}

    # ---- 验证消息结构 ----
    messages = c["messages"]
    assert len(messages) == 2
    first_msg = messages[0]
    assert "id" in first_msg
    assert "sender" in first_msg
    assert "content" in first_msg
    assert "time" in first_msg
    assert "read_list" in first_msg
    assert "is_deleted" in first_msg

    # ---- 验证未读统计字段存在 ----
    assert "unread_count" in c
    assert isinstance(c["unread_count"], int)
