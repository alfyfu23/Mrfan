import json
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from chat.models import Conversation, Member


@pytest.mark.django_db
def test_create_group_and_roles(client: Client):
    User = get_user_model()
    owner = User.objects.create_user(username='owner', password='p@ssw0rd1')
    u2 = User.objects.create_user(username='u2', password='p@ssw0rd2')

    # 登录owner
    resp = client.post(reverse('login'), data=json.dumps({'username':'owner','password':'p@ssw0rd1'}), content_type='application/json')
    assert resp.status_code == 200
    token = resp.json().get('jwt_token')

    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({'name': 'my group', 'members':[u2.id]}), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    assert group_id

    conv = Conversation.objects.get(id=group_id)
    assert conv.type == 'group'
    roles = set(Member.objects.filter(conversation=conv).values_list('role', flat=True))
    assert 'owner' in roles and 'member' in roles
