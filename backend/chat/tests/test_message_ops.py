import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from chat.models import Conversation, Member, Message


@pytest.mark.django_db
def test_mark_read_and_edit_recall(client: Client):
    User = get_user_model()
    u1 = User.objects.create_user(username='u1', password='p@ssw0rd1')
    u2 = User.objects.create_user(username='u2', password='p@ssw0rd2')

    # 登录u1
    resp = client.post(reverse('login'), data=json.dumps({'username':'u1','password':'p@ssw0rd1'}), content_type='application/json')
    assert resp.status_code == 200
    token1 = resp.json().get('jwt_token')

    # 登录u2
    resp = client.post(reverse('login'), data=json.dumps({'username':'u2','password':'p@ssw0rd2'}), content_type='application/json')
    assert resp.status_code == 200
    token2 = resp.json().get('jwt_token')

    # 创建私聊会话
    conv = Conversation.objects.create(type='private')
    m1 = Member.objects.create(conversation=conv, user=u1, nickname='u1', role='member')
    Member.objects.create(conversation=conv, user=u2, nickname='u2', role='member')

    # u1 发一条消息
    msg = Message.objects.create(conversation=conv, member=m1, content='hello')

    # u2 标记已读
    resp = client.post(reverse('mark_read'), data=json.dumps({'conversation': conv.id, 'up_to_id': msg.id}), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token2}')
    assert resp.status_code == 200
    msg.refresh_from_db()

    # u1 编辑消息
    resp = client.post(reverse('edit_message'), data=json.dumps({'id': msg.id, 'content': 'hello edited'}), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token1}')
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.is_edited is True
    assert msg.content == 'hello edited'

    # u1 撤回消息
    resp = client.post(reverse('recall_message'), data=json.dumps({'id': msg.id}), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token1}')
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.valid is False
    assert 'u1撤回了一条消息' in msg.content
