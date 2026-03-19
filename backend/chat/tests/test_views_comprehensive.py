import json
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from chat.models import Conversation, Member, Message, GroupAnnouncement
from django.utils import timezone


@pytest.mark.django_db
def test_update_group_info(client: Client):
    """测试更新群信息"""
    User = get_user_model()
    owner = User.objects.create_user(username='group_owner', password='pass123')
    member = User.objects.create_user(username='group_member', password='pass456')
    
    # 登录
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'group_owner', 'password': 'pass123'
    }), content_type='application/json')
    token = resp.json().get('jwt_token')
    assert token
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Test Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    assert group_id
    
    # 更新群名称
    resp = client.post(reverse('update_group_info'), data=json.dumps({
        'id': group_id,
        'name': 'Updated Group Name'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证更新
    conv = Conversation.objects.get(id=group_id)
    assert conv.name == 'Updated Group Name'


@pytest.mark.django_db
def test_update_group_info_not_authorized(client: Client):
    """测试非管理员/群主无法更新群信息"""
    User = get_user_model()
    owner = User.objects.create_user(username='owner2', password='pass123')
    member = User.objects.create_user(username='member2', password='pass456')
    
    # 登录 owner
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'owner2', 'password': 'pass123'
    }), content_type='application/json')
    owner_token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Test Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # 登录 member
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'member2', 'password': 'pass456'
    }), content_type='application/json')
    member_token = resp.json().get('jwt_token')
    
    # member 尝试更新群信息
    resp = client.post(reverse('update_group_info'), data=json.dumps({
        'id': group_id,
        'name': 'Hacked Name'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {member_token}')
    assert resp.status_code == 403
    assert resp.json().get('code') == 2012


@pytest.mark.django_db
def test_group_info(client: Client):
    """测试获取群信息"""
    User = get_user_model()
    owner = User.objects.create_user(username='info_owner', password='pass123')
    member = User.objects.create_user(username='info_member', password='pass456')
    
    # 登录
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'info_owner', 'password': 'pass123'
    }), content_type='application/json')
    token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Info Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # 获取群信息
    resp = client.get(
        reverse('group_info') + f'?id={group_id}',
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('code') == 0
    assert data.get('name') == 'Info Group'
    assert data.get('role') == 'owner'
    assert 'members' in data
    members = data.get('members', [])
    assert len(members) == 2
    # 检查 is_active 字段
    for m in members:
        assert 'is_active' in m
        assert m['is_active'] is True


@pytest.mark.django_db
def test_set_group_nickname(client: Client):
    """测试设置群昵称"""
    User = get_user_model()
    owner = User.objects.create_user(username='nick_owner', password='pass123')
    member = User.objects.create_user(username='nick_member', password='pass456')
    
    # 登录 owner
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'nick_owner', 'password': 'pass123'
    }), content_type='application/json')
    owner_token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Nick Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # 登录 member
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'nick_member', 'password': 'pass456'
    }), content_type='application/json')
    member_token = resp.json().get('jwt_token')
    
    # 设置群昵称
    resp = client.post(reverse('set_group_nickname'), data=json.dumps({
        'id': group_id,
        'nickname': 'My Group Nickname'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {member_token}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证
    member_obj = Member.objects.get(user=member, conversation_id=group_id)
    assert member_obj.nickname == 'My Group Nickname'


@pytest.mark.django_db
def test_set_member_role(client: Client):
    """测试设置成员角色"""
    User = get_user_model()
    owner = User.objects.create_user(username='role_owner', password='pass123')
    member = User.objects.create_user(username='role_member', password='pass456')
    
    # 登录 owner
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'role_owner', 'password': 'pass123'
    }), content_type='application/json')
    owner_token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Role Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # 设置成员为管理员
    resp = client.post(reverse('set_member_role'), data=json.dumps({
        'id': group_id,
        'user_id': member.id,
        'role': 'admin'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证
    member_obj = Member.objects.get(user=member, conversation_id=group_id)
    assert member_obj.role == 'admin'


@pytest.mark.django_db
def test_set_member_role_only_owner(client: Client):
    """测试只有群主可以设置管理员"""
    User = get_user_model()
    owner = User.objects.create_user(username='only_owner', password='pass123')
    admin = User.objects.create_user(username='only_admin', password='pass456')
    member = User.objects.create_user(username='only_member', password='pass789')
    
    # 登录 owner
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'only_owner', 'password': 'pass123'
    }), content_type='application/json')
    owner_token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Only Owner Group',
        'members': [admin.id, member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # 先设置 admin 为管理员
    resp = client.post(reverse('set_member_role'), data=json.dumps({
        'id': group_id,
        'user_id': admin.id,
        'role': 'admin'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    assert resp.status_code == 200
    
    # 登录 admin
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'only_admin', 'password': 'pass456'
    }), content_type='application/json')
    admin_token = resp.json().get('jwt_token')
    
    # admin 尝试设置角色（应该失败）
    resp = client.post(reverse('set_member_role'), data=json.dumps({
        'id': group_id,
        'user_id': member.id,
        'role': 'admin'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {admin_token}')
    assert resp.status_code == 403
    assert resp.json().get('code') == 2012


@pytest.mark.django_db
def test_transfer_owner(client: Client):
    """测试转移群主"""
    User = get_user_model()
    owner = User.objects.create_user(username='transfer_owner', password='pass123')
    new_owner = User.objects.create_user(username='transfer_new', password='pass456')
    
    # 登录 owner
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'transfer_owner', 'password': 'pass123'
    }), content_type='application/json')
    owner_token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Transfer Group',
        'members': [new_owner.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # 转移群主
    resp = client.post(reverse('transfer_owner'), data=json.dumps({
        'id': group_id,
        'to': new_owner.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证
    old_owner = Member.objects.get(user=owner, conversation_id=group_id)
    new_owner_obj = Member.objects.get(user=new_owner, conversation_id=group_id)
    assert old_owner.role == 'member'  # 转让群主后，原群主变成普通成员
    assert new_owner_obj.role == 'owner'


@pytest.mark.django_db
def test_history_bad_method(client: Client):
    """测试历史消息API的错误方法"""
    resp = client.post(reverse('history'))
    assert resp.status_code == 405


@pytest.mark.django_db
def test_history_no_auth(client: Client):
    """测试历史消息API无认证"""
    resp = client.get(reverse('history'))
    assert resp.status_code == 403
    assert resp.json().get('code') == 3002


@pytest.mark.django_db
def test_history_invalid_token(client: Client):
    """测试历史消息API无效token"""
    resp = client.get(reverse('history'), HTTP_AUTHORIZATION='Bearer invalid.token')
    assert resp.status_code == 403
    assert resp.json().get('code') == 3002


@pytest.mark.django_db
def test_history_user_not_found(client: Client):
    """测试历史消息API用户不存在"""
    # 使用一个不存在的用户ID创建token
    from utils.jwt import generate_jwt_token
    invalid_token = generate_jwt_token('nonexistent', 99999)
    resp = client.get(reverse('history'), HTTP_AUTHORIZATION=f'Bearer {invalid_token}')
    assert resp.status_code == 500
    assert resp.json().get('code') == 9001


@pytest.mark.django_db
def test_history_conversation_not_found(client: Client):
    """测试历史消息API会话不存在"""
    User = get_user_model()
    user = User.objects.create_user(username='history_user', password='pass123')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('history_user', user.id)

    resp = client.get(reverse('history'), {'c': '99999'}, HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 404
    assert resp.json().get('code') == 3003


@pytest.mark.django_db
def test_history_not_member(client: Client):
    """测试历史消息API非成员访问"""
    User = get_user_model()
    user1 = User.objects.create_user(username='history_user1', password='pass123')
    user2 = User.objects.create_user(username='history_user2', password='pass456')

    from utils.jwt import generate_jwt_token
    token1 = generate_jwt_token('history_user1', user1.id)
    token2 = generate_jwt_token('history_user2', user2.id)

    # 创建会话，只包含user1
    conv = Conversation.objects.create(type='private')
    Member.objects.create(user=user1, conversation=conv, role='member', time=timezone.now())

    # user2尝试访问
    resp = client.get(reverse('history'), {'c': conv.id}, HTTP_AUTHORIZATION=f'Bearer {token2}')
    assert resp.status_code == 403
    assert resp.json().get('code') == 3004


@pytest.mark.django_db
def test_history_with_filters(client: Client):
    """测试历史消息API的过滤功能"""
    User = get_user_model()
    user1 = User.objects.create_user(username='filter_user1', password='pass123')
    user2 = User.objects.create_user(username='filter_user2', password='pass456')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('filter_user1', user1.id)

    # 创建会话
    conv = Conversation.objects.create(type='private')
    Member.objects.create(user=user1, conversation=conv, role='member', time=timezone.now())
    Member.objects.create(user=user2, conversation=conv, role='member', time=timezone.now())

    # 创建消息
    member1 = Member.objects.get(user=user1, conversation=conv)
    member2 = Member.objects.get(user=user2, conversation=conv)
    Message.objects.create(conversation=conv, member=member1, content='test message 1', time=timezone.now(), valid=True)
    Message.objects.create(conversation=conv, member=member2, content='special keyword', time=timezone.now(), valid=True)

    # 先检查所有消息
    resp = client.get(reverse('history'), {'c': conv.id}, HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200
    response_data = resp.json()
    all_messages = response_data.get('messages', [])
    assert len(all_messages) == 2

    # 测试关键词过滤 - user1应该能看到所有消息，包括自己的和别人的
    resp = client.get(reverse('history'), {'c': conv.id, 'q': 'special'}, HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200
    response_data = resp.json()
    messages = response_data.get('messages', [])
    # user1 发送的消息不包含 'special'，user2 的消息包含 'special'
    assert len(messages) == 1
    assert 'special' in messages[0]['content']

    # 测试发送者过滤
    resp = client.get(reverse('history'), {'c': conv.id, 'sender': user1.id}, HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200
    response_data = resp.json()
    messages = response_data.get('messages', [])
    assert len(messages) == 1
    assert messages[0]['sender_id'] == user1.id


@pytest.mark.django_db
def test_create_friend_conversation_bad_method(client: Client):
    """测试创建好友会话的错误方法"""
    resp = client.get(reverse('create_friend_conversation'))
    assert resp.status_code == 405


@pytest.mark.django_db
def test_create_friend_conversation_no_auth(client: Client):
    """测试创建好友会话无认证"""
    resp = client.post(reverse('create_friend_conversation'))
    assert resp.status_code == 403
    assert resp.json().get('code') == 3002


@pytest.mark.django_db
def test_create_friend_conversation_invalid_token(client: Client):
    """测试创建好友会话无效token"""
    resp = client.post(reverse('create_friend_conversation'), HTTP_AUTHORIZATION='Bearer invalid.token')
    assert resp.status_code == 403
    assert resp.json().get('code') == 3002


@pytest.mark.django_db
def test_create_friend_conversation_not_friends(client: Client):
    """测试创建好友会话非好友关系"""
    User = get_user_model()
    user1 = User.objects.create_user(username='conv_user1', password='pass123')
    user2 = User.objects.create_user(username='conv_user2', password='pass456')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('conv_user1', user1.id)

    resp = client.post(reverse('create_friend_conversation'), data=json.dumps({
        'id': user2.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 403
    assert resp.json().get('code') == 2012


@pytest.mark.django_db
def test_create_group_bad_method(client: Client):
    """测试创建群聊的错误方法"""
    resp = client.get(reverse('create_group'))
    assert resp.status_code == 405


@pytest.mark.django_db
def test_create_group_invalid_members(client: Client):
    """测试创建群聊包含无效成员"""
    User = get_user_model()
    user = User.objects.create_user(username='group_creator', password='pass123')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('group_creator', user.id)

    # 包含不存在的用户ID
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Test Group',
        'members': [99999]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    # 应该成功创建，但无效成员会被跳过
    assert resp.status_code == 200
    assert resp.json().get('code') == 0


@pytest.mark.django_db
def test_update_group_info_bad_method(client: Client):
    """测试更新群信息的错误方法"""
    resp = client.get(reverse('update_group_info'))
    assert resp.status_code == 405


@pytest.mark.django_db
def test_update_group_info_conversation_not_found(client: Client):
    """测试更新群信息时会话不存在"""
    User = get_user_model()
    user = User.objects.create_user(username='update_user', password='pass123')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('update_user', user.id)

    resp = client.post(reverse('update_group_info'), data=json.dumps({
        'id': 99999,
        'name': 'New Name'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 404
    assert resp.json().get('code') == 3003


@pytest.mark.django_db
def test_set_member_role_invalid_role(client: Client):
    """测试设置成员角色时的无效角色"""
    User = get_user_model()
    owner = User.objects.create_user(username='role_owner', password='pass123')
    member = User.objects.create_user(username='role_member', password='pass456')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('role_owner', owner.id)

    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Role Test Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    group_id = resp.json().get('id')

    # 尝试设置无效角色
    resp = client.post(reverse('set_member_role'), data=json.dumps({
        'id': group_id,
        'user_id': member.id,
        'role': 'invalid_role'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 400
    assert resp.json().get('code') == 2001


@pytest.mark.django_db
def test_transfer_owner_not_owner(client: Client):
    """测试转让群主时操作者不是群主"""
    User = get_user_model()
    owner = User.objects.create_user(username='transfer_test_owner', password='pass123')
    member = User.objects.create_user(username='transfer_test_member', password='pass456')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('transfer_test_member', member.id)  # 使用成员的token

    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Transfer Test Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {generate_jwt_token("transfer_test_owner", owner.id)}')
    group_id = resp.json().get('id')

    # 成员尝试转让群主
    resp = client.post(reverse('transfer_owner'), data=json.dumps({
        'id': group_id,
        'to': member.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 403
    assert resp.json().get('code') == 2012


@pytest.mark.django_db
def test_transfer_owner_target_not_member(client: Client):
    """测试转让群主时目标用户不在群聊中"""
    User = get_user_model()
    owner = User.objects.create_user(username='transfer_owner2', password='pass123')
    outsider = User.objects.create_user(username='transfer_outsider', password='pass456')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('transfer_owner2', owner.id)

    # 创建群聊（不包含outsider）
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Transfer Test Group 2',
        'members': []
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    group_id = resp.json().get('id')

    # 尝试转让给不在群聊中的用户
    resp = client.post(reverse('transfer_owner'), data=json.dumps({
        'id': group_id,
        'to': outsider.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 404
    assert resp.json().get('code') == 3004


@pytest.mark.django_db
def test_remove_member_not_authorized(client: Client):
    """测试移除成员时的权限检查"""
    User = get_user_model()
    owner = User.objects.create_user(username='remove_owner', password='pass123')
    member1 = User.objects.create_user(username='remove_member1', password='pass456')
    member2 = User.objects.create_user(username='remove_member2', password='pass789')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('remove_member1', member1.id)  # 使用普通成员的token

    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Remove Test Group',
        'members': [member1.id, member2.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {generate_jwt_token("remove_owner", owner.id)}')
    group_id = resp.json().get('id')

    # 普通成员尝试移除另一个成员
    resp = client.post(reverse('remove_member'), data=json.dumps({
        'id': group_id,
        'user_id': member2.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_disband_group_not_owner(client: Client):
    """测试解散群聊时操作者不是群主"""
    User = get_user_model()
    owner = User.objects.create_user(username='disband_owner', password='pass123')
    member = User.objects.create_user(username='disband_member', password='pass456')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('disband_member', member.id)  # 使用成员的token

    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Disband Test Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {generate_jwt_token("disband_owner", owner.id)}')
    group_id = resp.json().get('id')

    # 成员尝试解散群聊
    resp = client.post(reverse('disband_group'), data=json.dumps({
        'id': group_id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 403
    assert resp.json().get('code') == 2012


@pytest.mark.django_db
def test_disband_group_hides_and_blocks_invite(client: Client):
    """解散后不会再出现在home，并且阻止继续邀请"""
    User = get_user_model()
    owner = User.objects.create_user(username='disband_owner2', password='pass123')
    member = User.objects.create_user(username='disband_member2', password='pass456')
    new_friend = User.objects.create_user(username='disband_friend', password='pass789')

    from utils.jwt import generate_jwt_token
    owner_token = generate_jwt_token('disband_owner2', owner.id)

    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Disband Visible Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id')

    # 解散群聊
    resp = client.post(reverse('disband_group'), data=json.dumps({
        'id': group_id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0

    # home 中不会再返回已解散的群聊
    resp = client.get(reverse('home'), HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    assert resp.status_code == 200
    assert resp.json().get('conversations') == []

    # 继续邀请成员会被禁止
    resp = client.post(reverse('invite_to_group'), data=json.dumps({
        'group_id': group_id,
        'friend_id': new_friend.id,
        'message': 'join us'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    assert resp.status_code == 403
    assert resp.json().get('code') == 2012


@pytest.mark.django_db
def test_set_group_nickname_not_member(client: Client):
    """测试设置群昵称时用户不在群聊中"""
    User = get_user_model()
    user1 = User.objects.create_user(username='nickname_user1', password='pass123')
    user2 = User.objects.create_user(username='nickname_user2', password='pass456')

    from utils.jwt import generate_jwt_token
    token1 = generate_jwt_token('nickname_user1', user1.id)
    token2 = generate_jwt_token('nickname_user2', user2.id)

    # 创建群聊，只包含user1
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Nickname Test Group',
        'members': []
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token1}')
    group_id = resp.json().get('id')

    # user2（不在群聊中）尝试设置昵称
    resp = client.post(reverse('set_group_nickname'), data=json.dumps({
        'id': group_id,
        'nickname': 'New Nickname'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token2}')
    assert resp.status_code == 404
    assert resp.json().get('code') == 3003


@pytest.mark.django_db
def test_announce(client: Client):
    """测试设置群公告"""
    User = get_user_model()
    owner = User.objects.create_user(username='announce_owner', password='pass123')
    member = User.objects.create_user(username='announce_member', password='pass456')
    
    # 登录 owner
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'announce_owner', 'password': 'pass123'
    }), content_type='application/json')
    owner_token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Announce Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # 设置公告
    resp = client.post(reverse('announce'), data=json.dumps({
        'id': group_id,
        'content': 'This is a test announcement'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证
    announcement = GroupAnnouncement.objects.filter(conversation_id=group_id).order_by('-created_at').first()
    assert announcement is not None
    assert announcement.content == 'This is a test announcement'


@pytest.mark.django_db
def test_announce_not_authorized(client: Client):
    """测试非管理员/群主无法设置公告"""
    User = get_user_model()
    owner = User.objects.create_user(username='announce_no_owner', password='pass123')
    member = User.objects.create_user(username='announce_no_member', password='pass456')
    
    # 登录 owner
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'announce_no_owner', 'password': 'pass123'
    }), content_type='application/json')
    owner_token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'No Announce Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # 登录 member
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'announce_no_member', 'password': 'pass456'
    }), content_type='application/json')
    member_token = resp.json().get('jwt_token')
    
    # member 尝试设置公告（应该失败）
    resp = client.post(reverse('announce'), data=json.dumps({
        'id': group_id,
        'content': 'Hacked announcement'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {member_token}')
    assert resp.status_code == 403
    assert resp.json().get('code') == 2012


@pytest.mark.django_db
def test_remove_member(client: Client):
    """测试移除成员"""
    User = get_user_model()
    owner = User.objects.create_user(username='remove_owner', password='pass123')
    member = User.objects.create_user(username='remove_member', password='pass456')
    
    # 登录 owner
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'remove_owner', 'password': 'pass123'
    }), content_type='application/json')
    owner_token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Remove Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # 验证成员存在
    assert Member.objects.filter(user=member, conversation_id=group_id).exists()
    
    # 移除成员
    resp = client.post(reverse('remove_member'), data=json.dumps({
        'id': group_id,
        'user_id': member.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证成员已被移除
    assert not Member.objects.filter(user=member, conversation_id=group_id).exists()


@pytest.mark.django_db
def test_exit_group(client: Client):
    """测试退出群聊"""
    User = get_user_model()
    owner = User.objects.create_user(username='exit_owner', password='pass123')
    member = User.objects.create_user(username='exit_member', password='pass456')
    
    # 登录 owner
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'exit_owner', 'password': 'pass123'
    }), content_type='application/json')
    owner_token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Exit Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # 登录 member
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'exit_member', 'password': 'pass456'
    }), content_type='application/json')
    member_token = resp.json().get('jwt_token')
    
    # member 退出群聊
    resp = client.post(reverse('exit_group'), data=json.dumps({
        'id': group_id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {member_token}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证成员已退出
    assert not Member.objects.filter(user=member, conversation_id=group_id).exists()


@pytest.mark.django_db
def test_exit_group_owner_cannot_exit(client: Client):
    """测试群主不能直接退出"""
    User = get_user_model()
    owner = User.objects.create_user(username='exit_owner2', password='pass123')
    member = User.objects.create_user(username='exit_member2', password='pass456')
    
    # 登录 owner
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'exit_owner2', 'password': 'pass123'
    }), content_type='application/json')
    owner_token = resp.json().get('jwt_token')
    
    # 创建群聊
    resp = client.post(reverse('create_group'), data=json.dumps({
        'name': 'Exit Owner Group',
        'members': [member.id]
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    group_id = resp.json().get('id') or (resp.json().get('data') or {}).get('id')
    
    # owner 尝试退出（应该失败）
    resp = client.post(reverse('exit_group'), data=json.dumps({
        'id': group_id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {owner_token}')
    assert resp.status_code == 403
    assert resp.json().get('code') == 2012


@pytest.mark.django_db
def test_mark_read(client: Client):
    """测试标记消息为已读"""
    User = get_user_model()
    user1 = User.objects.create_user(username='read_user1', password='pass123')
    user2 = User.objects.create_user(username='read_user2', password='pass456')
    
    # 登录 user1
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'read_user1', 'password': 'pass123'
    }), content_type='application/json')
    token1 = resp.json().get('jwt_token')
    
    # 创建会话
    conv = Conversation.objects.create(type='private')
    member1 = Member.objects.create(user=user1, conversation=conv, role='member', time=timezone.now())
    member2 = Member.objects.create(user=user2, conversation=conv, role='member', time=timezone.now())
    
    # 创建消息
    msg = Message.objects.create(conversation=conv, member=member2, content='Test message')
    
    # 标记为已读
    resp = client.post(reverse('mark_read'), data=json.dumps({
        'conversation': conv.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token1}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证消息已被标记为已读
    assert member1 in msg.read_list.all()


@pytest.mark.django_db
def test_edit_message(client: Client):
    """测试编辑消息"""
    User = get_user_model()
    user1 = User.objects.create_user(username='edit_user1', password='pass123')
    user2 = User.objects.create_user(username='edit_user2', password='pass456')
    
    # 登录 user1
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'edit_user1', 'password': 'pass123'
    }), content_type='application/json')
    token1 = resp.json().get('jwt_token')
    
    # 创建会话和消息
    conv = Conversation.objects.create(type='private')
    member1 = Member.objects.create(user=user1, conversation=conv, role='member', time=timezone.now())
    msg = Message.objects.create(conversation=conv, member=member1, content='Original message')
    
    # 编辑消息
    resp = client.post(reverse('edit_message'), data=json.dumps({
        'id': msg.id,
        'content': 'Edited message'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token1}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证
    msg.refresh_from_db()
    assert msg.content == 'Edited message'
    assert msg.is_edited is True


@pytest.mark.django_db
def test_edit_message_not_owner(client: Client):
    """测试非消息发送者无法编辑消息"""
    User = get_user_model()
    user1 = User.objects.create_user(username='edit_no_user1', password='pass123')
    user2 = User.objects.create_user(username='edit_no_user2', password='pass456')
    
    # 登录 user1
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'edit_no_user1', 'password': 'pass123'
    }), content_type='application/json')
    token1 = resp.json().get('jwt_token')
    
    # 登录 user2
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'edit_no_user2', 'password': 'pass456'
    }), content_type='application/json')
    token2 = resp.json().get('jwt_token')
    
    # 创建会话和消息（user1 发送）
    conv = Conversation.objects.create(type='private')
    member1 = Member.objects.create(user=user1, conversation=conv, role='member', time=timezone.now())
    msg = Message.objects.create(conversation=conv, member=member1, content='Original message')
    
    # user2 尝试编辑 user1 的消息（应该失败）
    resp = client.post(reverse('edit_message'), data=json.dumps({
        'id': msg.id,
        'content': 'Hacked message'
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token2}')
    assert resp.status_code == 403
    assert resp.json().get('code') == 2012


@pytest.mark.django_db
def test_recall_message(client: Client):
    """测试撤回消息"""
    User = get_user_model()
    user1 = User.objects.create_user(username='recall_user1', password='pass123')
    
    # 登录 user1
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'recall_user1', 'password': 'pass123'
    }), content_type='application/json')
    token1 = resp.json().get('jwt_token')
    
    # 创建会话和消息
    conv = Conversation.objects.create(type='private')
    member1 = Member.objects.create(user=user1, conversation=conv, role='member', time=timezone.now())
    msg = Message.objects.create(conversation=conv, member=member1, content='Message to recall')
    
    # 撤回消息
    resp = client.post(reverse('recall_message'), data=json.dumps({
        'id': msg.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token1}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证
    msg.refresh_from_db()
    assert msg.valid is False
    assert 'recall_user1撤回了一条消息' in msg.content


@pytest.mark.django_db
def test_delete_message(client: Client):
    """测试删除消息"""
    User = get_user_model()
    user1 = User.objects.create_user(username='delete_user1', password='pass123')
    user2 = User.objects.create_user(username='delete_user2', password='pass456')
    
    # 登录 user1
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'delete_user1', 'password': 'pass123'
    }), content_type='application/json')
    token1 = resp.json().get('jwt_token')
    
    # 创建会话和消息
    conv = Conversation.objects.create(type='private')
    member1 = Member.objects.create(user=user1, conversation=conv, role='member', time=timezone.now())
    member2 = Member.objects.create(user=user2, conversation=conv, role='member', time=timezone.now())
    msg = Message.objects.create(conversation=conv, member=member1, content='Message to delete')
    
    # 删除消息
    resp = client.post(reverse('delete_message'), data=json.dumps({
        'id': msg.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token1}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证消息在 user1 的删除列表中
    assert member1 in msg.delete_list.all()


@pytest.mark.django_db
def test_set_mute_pin(client: Client):
    """测试设置静音和置顶"""
    User = get_user_model()
    user1 = User.objects.create_user(username='mute_user1', password='pass123')
    
    # 登录 user1
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'mute_user1', 'password': 'pass123'
    }), content_type='application/json')
    token1 = resp.json().get('jwt_token')
    
    # 创建会话
    conv = Conversation.objects.create(type='private')
    member1 = Member.objects.create(user=user1, conversation=conv, role='member', time=timezone.now())
    
    # 设置静音和置顶
    resp = client.post(reverse('set_mute_pin'), data=json.dumps({
        'id': conv.id,
        'mute': True,
        'pinned': True
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token1}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0
    
    # 验证
    member1.refresh_from_db()
    assert member1.mute is True
    assert member1.pinned is True


@pytest.mark.django_db
def test_upload(client: Client):
    """测试文件上传"""
    User = get_user_model()
    user1 = User.objects.create_user(username='upload_user1', password='pass123')
    
    # 登录 user1
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'upload_user1', 'password': 'pass123'
    }), content_type='application/json')
    token1 = resp.json().get('jwt_token')
    
    # 创建测试文件
    from io import BytesIO
    test_file = BytesIO(b'test file content')
    test_file.name = 'test.txt'
    
    # 上传文件
    resp = client.post(
        reverse('upload'),
        {'file': test_file},
        HTTP_AUTHORIZATION=f'Bearer {token1}'
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('code') == 0
    assert 'url' in data


@pytest.mark.django_db
def test_upload_no_file(client: Client):
    """测试上传时没有文件"""
    User = get_user_model()
    user1 = User.objects.create_user(username='upload_no_user1', password='pass123')
    
    # 登录 user1
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'upload_no_user1', 'password': 'pass123'
    }), content_type='application/json')
    token1 = resp.json().get('jwt_token')
    
    # 尝试上传但没有文件
    resp = client.post(
        reverse('upload'),
        {},
        HTTP_AUTHORIZATION=f'Bearer {token1}'
    )
    assert resp.status_code == 400
    assert resp.json().get('code') == 2001


@pytest.mark.django_db
def test_history_bad_method(client: Client):
    """测试 history API 的错误方法"""
    User = get_user_model()
    user1 = User.objects.create_user(username='history_bad_user', password='pass123')
    
    # 登录
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'history_bad_user', 'password': 'pass123'
    }), content_type='application/json')
    token1 = resp.json().get('jwt_token')
    
    # 使用 POST 方法（应该是 GET）
    resp = client.post(
        reverse('history') + '?c=1',
        HTTP_AUTHORIZATION=f'Bearer {token1}'
    )
    assert resp.status_code == 405


@pytest.mark.django_db
def test_history_no_conversation(client: Client):
    """测试 history API 会话不存在"""
    User = get_user_model()
    user1 = User.objects.create_user(username='history_no_user', password='pass123')
    
    # 登录
    resp = client.post(reverse('login'), data=json.dumps({
        'username': 'history_no_user', 'password': 'pass123'
    }), content_type='application/json')
    token1 = resp.json().get('jwt_token')
    
    # 查询不存在的会话
    resp = client.get(
        reverse('history') + '?c=99999',
        HTTP_AUTHORIZATION=f'Bearer {token1}'
    )
    assert resp.status_code == 404
    assert resp.json().get('code') == 3003


@pytest.mark.django_db
def test_pin_conversation_success(client: Client):
    """测试置顶会话成功"""
    User = get_user_model()
    user = User.objects.create_user(username='pin_user', password='pass123')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('pin_user', user.id)

    # 创建会话
    conv = Conversation.objects.create(type='private')
    Member.objects.create(user=user, conversation=conv, role='member', time=timezone.now())

    # 置顶会话
    resp = client.post(reverse('pin_conversation'), data=json.dumps({
        'id': conv.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0

    # 验证置顶记录已创建
    from chat.models import PinnedConversation
    pinned = PinnedConversation.objects.filter(user=user, conversation=conv).first()
    assert pinned is not None
    assert pinned.pin_order == 1

    # 验证Member的pinned字段也更新了
    member = Member.objects.get(user=user, conversation=conv)
    assert member.pinned == True


@pytest.mark.django_db
def test_pin_conversation_bad_method(client: Client):
    """测试置顶会话错误的HTTP方法"""
    resp = client.get(reverse('pin_conversation'))
    assert resp.status_code == 405


@pytest.mark.django_db
def test_pin_conversation_no_auth(client: Client):
    """测试置顶会话无认证"""
    resp = client.post(reverse('pin_conversation'))
    assert resp.status_code == 403
    assert resp.json().get('code') == 3002


@pytest.mark.django_db
def test_pin_conversation_missing_id(client: Client):
    """测试置顶会话缺少会话ID"""
    User = get_user_model()
    user = User.objects.create_user(username='pin_user2', password='pass123')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('pin_user2', user.id)

    resp = client.post(reverse('pin_conversation'), data=json.dumps({}),
                       content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 400
    assert resp.json().get('code') == 2001


@pytest.mark.django_db
def test_pin_conversation_not_member(client: Client):
    """测试置顶不存在的会话"""
    User = get_user_model()
    user = User.objects.create_user(username='pin_user3', password='pass123')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('pin_user3', user.id)

    resp = client.post(reverse('pin_conversation'), data=json.dumps({
        'id': 99999
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 404
    assert resp.json().get('code') == 3003


@pytest.mark.django_db
def test_pin_conversation_already_pinned(client: Client):
    """测试重复置顶会话"""
    User = get_user_model()
    user = User.objects.create_user(username='pin_user4', password='pass123')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('pin_user4', user.id)

    # 创建会话
    conv = Conversation.objects.create(type='private')
    Member.objects.create(user=user, conversation=conv, role='member', time=timezone.now())

    # 第一次置顶
    resp = client.post(reverse('pin_conversation'), data=json.dumps({
        'id': conv.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200

    # 第二次置顶（应该失败）
    resp = client.post(reverse('pin_conversation'), data=json.dumps({
        'id': conv.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 400
    assert resp.json().get('code') == 3005


@pytest.mark.django_db
def test_unpin_conversation_success(client: Client):
    """测试取消置顶会话成功"""
    User = get_user_model()
    user = User.objects.create_user(username='unpin_user', password='pass123')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('unpin_user', user.id)

    # 创建会话并置顶
    conv = Conversation.objects.create(type='private')
    member = Member.objects.create(user=user, conversation=conv, role='member', time=timezone.now())

    from chat.models import PinnedConversation
    PinnedConversation.objects.create(user=user, conversation=conv, pin_order=1)
    member.pinned = True
    member.save()

    # 取消置顶
    resp = client.post(reverse('unpin_conversation'), data=json.dumps({
        'id': conv.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200
    assert resp.json().get('code') == 0

    # 验证置顶记录已删除
    pinned = PinnedConversation.objects.filter(user=user, conversation=conv).first()
    assert pinned is None

    # 验证Member的pinned字段也更新了
    member.refresh_from_db()
    assert member.pinned == False


@pytest.mark.django_db
def test_unpin_conversation_not_pinned(client: Client):
    """测试取消未置顶的会话"""
    User = get_user_model()
    user = User.objects.create_user(username='unpin_user2', password='pass123')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('unpin_user2', user.id)

    # 创建会话（未置顶）
    conv = Conversation.objects.create(type='private')
    Member.objects.create(user=user, conversation=conv, role='member', time=timezone.now())

    # 尝试取消置顶
    resp = client.post(reverse('unpin_conversation'), data=json.dumps({
        'id': conv.id
    }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 400
    assert resp.json().get('code') == 3006


@pytest.mark.django_db
def test_get_pinned_conversations_success(client: Client):
    """测试获取置顶会话列表成功"""
    User = get_user_model()
    user = User.objects.create_user(username='get_pinned_user', password='pass123')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('get_pinned_user', user.id)

    # 创建多个会话并置顶
    conv1 = Conversation.objects.create(type='private')
    conv2 = Conversation.objects.create(type='private')
    Member.objects.create(user=user, conversation=conv1, role='member', time=timezone.now())
    Member.objects.create(user=user, conversation=conv2, role='member', time=timezone.now())

    from chat.models import PinnedConversation
    PinnedConversation.objects.create(user=user, conversation=conv1, pin_order=1)
    PinnedConversation.objects.create(user=user, conversation=conv2, pin_order=2)

    # 获取置顶列表
    resp = client.get(reverse('get_pinned_conversations'), HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('code') == 0
    pinned_list = data.get('pinned', [])
    assert len(pinned_list) == 2
    assert conv1.id in pinned_list
    assert conv2.id in pinned_list


@pytest.mark.django_db
def test_get_pinned_conversations_bad_method(client: Client):
    """测试获取置顶会话列表错误的HTTP方法"""
    resp = client.post(reverse('get_pinned_conversations'))
    assert resp.status_code == 405


@pytest.mark.django_db
def test_home_with_pinned_conversations(client: Client):
    """测试home接口返回的会话按置顶顺序排序"""
    User = get_user_model()
    user = User.objects.create_user(username='home_pinned_user', password='pass123')
    other_user = User.objects.create_user(username='home_other_user', password='pass456')

    from utils.jwt import generate_jwt_token
    token = generate_jwt_token('home_pinned_user', user.id)

    # 创建多个私人会话（每个会话需要两个成员）
    conv1 = Conversation.objects.create(type='private')  # 置顶的会话
    conv2 = Conversation.objects.create(type='private')  # 未置顶的会话
    conv3 = Conversation.objects.create(type='private')  # 置顶的会话

    # 添加成员 - 每个私人会话需要两个成员
    Member.objects.create(user=user, conversation=conv1, role='member', time=timezone.now(), pinned=True)
    Member.objects.create(user=user, conversation=conv2, role='member', time=timezone.now(), pinned=False)
    Member.objects.create(user=user, conversation=conv3, role='member', time=timezone.now(), pinned=True)
    Member.objects.create(user=other_user, conversation=conv1, role='member', time=timezone.now())
    Member.objects.create(user=other_user, conversation=conv2, role='member', time=timezone.now())
    Member.objects.create(user=other_user, conversation=conv3, role='member', time=timezone.now())

    # 置顶会话
    from chat.models import PinnedConversation
    PinnedConversation.objects.create(user=user, conversation=conv1, pin_order=2)  # 置顶顺序2
    PinnedConversation.objects.create(user=user, conversation=conv3, pin_order=1)  # 置顶顺序1

    # 为每个会话添加一条消息，确保会话会被显示
    Message.objects.create(conversation=conv1, member=Member.objects.get(user=user, conversation=conv1), content="Message in conv1")
    Message.objects.create(conversation=conv2, member=Member.objects.get(user=user, conversation=conv2), content="Message in conv2")
    Message.objects.create(conversation=conv3, member=Member.objects.get(user=user, conversation=conv3), content="Message in conv3")

    # 获取home数据
    resp = client.get(reverse('home'), HTTP_AUTHORIZATION=f'Bearer {token}')
    assert resp.status_code == 200
    full_resp = resp.json()
    print(f"Full response: {full_resp}")
    # home视图直接返回conversations在根级别，不像其他视图那样包装在data中
    conversations = full_resp.get('conversations', [])
    print(f"Conversations: {len(conversations)}")
    for conv in conversations:
        print(f"Conv {conv['id']}: pinned={conv.get('pinned')}, pin_order={conv.get('pin_order')}")

    # 验证排序：置顶的会话在前，按pin_order排序，然后是未置顶的会话
    assert len(conversations) == 3

    # 第一个应该是conv3（pin_order=1）
    assert conversations[0]['id'] == conv3.id
    assert conversations[0]['pinned'] == True
    assert conversations[0]['pin_order'] == 1

    # 第二个应该是conv1（pin_order=2）
    assert conversations[1]['id'] == conv1.id
    assert conversations[1]['pinned'] == True
    assert conversations[1]['pin_order'] == 2

    # 第三个应该是conv2（未置顶）
    assert conversations[2]['id'] == conv2.id
    assert conversations[2]['pinned'] == False

