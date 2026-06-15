import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from chat.models import Conversation, GroupInvitation, Member
from friend.models import Friendship


@pytest.fixture
def setup_group_invitation_test():
    """设置群邀请测试所需的数据"""
    User = get_user_model()

    # 创建用户
    owner = User.objects.create_user(username='owner', password='p@ssw0rd1')
    admin = User.objects.create_user(username='admin', password='p@ssw0rd2')
    member = User.objects.create_user(username='member', password='p@ssw0rd3')
    inviter = User.objects.create_user(username='inviter', password='p@ssw0rd4')
    invitee = User.objects.create_user(username='invitee', password='p@ssw0rd5')
    non_friend = User.objects.create_user(username='non_friend', password='p@ssw0rd6')

    # 创建好友关系
    Friendship.objects.create(user_a=inviter, user_b=invitee)

    # 创建群聊
    conv = Conversation.objects.create(name='test_group', type='group')

    # 添加群成员
    Member.objects.create(conversation=conv, user=owner, nickname='owner', role='owner')
    Member.objects.create(conversation=conv, user=admin, nickname='admin', role='admin')
    Member.objects.create(conversation=conv, user=member, nickname='member', role='member')
    Member.objects.create(conversation=conv, user=inviter, nickname='inviter', role='member')

    return {
        'owner': owner,
        'admin': admin,
        'member': member,
        'inviter': inviter,
        'invitee': invitee,
        'non_friend': non_friend,
        'conv': conv
    }


def get_auth_token(client: Client, username: str, password: str):
    """获取用户的认证令牌"""
    resp = client.post(reverse('login'),
                      data=json.dumps({'username': username, 'password': password}),
                      content_type='application/json')
    assert resp.status_code == 200
    return resp.json().get('jwt_token')


@pytest.mark.django_db
def test_invite_friend_to_group_success(client: Client, setup_group_invitation_test):
    """测试成功邀请好友加入群聊"""
    data = setup_group_invitation_test
    inviter_token = get_auth_token(client, 'inviter', 'p@ssw0rd4')

    # 邀请好友加入群聊
    resp = client.post(
        reverse('invite_to_group'),
        data=json.dumps({
            'group_id': data['conv'].id,
            'friend_id': data['invitee'].id,
            'message': '请加入我们的群聊'
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {inviter_token}'
    )

    assert resp.status_code == 200
    invitation_id = resp.json().get('id')
    assert invitation_id

    # 验证邀请记录已创建
    invitation = GroupInvitation.objects.get(id=invitation_id)
    assert invitation.conversation == data['conv']
    assert invitation.inviter == data['inviter']
    assert invitation.invitee == data['invitee']
    assert invitation.status == 'pending'
    assert invitation.message == '请加入我们的群聊'


@pytest.mark.django_db
def test_invite_non_friend_to_group_fail(client: Client, setup_group_invitation_test):
    """测试邀请非好友加入群聊失败"""
    data = setup_group_invitation_test
    inviter_token = get_auth_token(client, 'inviter', 'p@ssw0rd4')

    # 尝试邀请非好友加入群聊
    resp = client.post(
        reverse('invite_to_group'),
        data=json.dumps({
            'group_id': data['conv'].id,
            'friend_id': data['non_friend'].id,
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {inviter_token}'
    )

    assert resp.status_code == 403
    assert 'You can only invite your friends' in resp.json().get('info', '')


@pytest.mark.django_db
def test_invite_existing_member_fail(client: Client, setup_group_invitation_test):
    """测试邀请已经是群成员的用户失败"""
    data = setup_group_invitation_test
    inviter_token = get_auth_token(client, 'inviter', 'p@ssw0rd4')

    # 尝试邀请已经是群成员的用户
    resp = client.post(
        reverse('invite_to_group'),
        data=json.dumps({
            'group_id': data['conv'].id,
            'friend_id': data['member'].id,
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {inviter_token}'
    )

    assert resp.status_code == 400
    assert 'already a member of this group' in resp.json().get('info', '')


@pytest.mark.django_db
def test_invite_duplicate_invitation_fail(client: Client, setup_group_invitation_test):
    """测试重复邀请同一用户失败"""
    data = setup_group_invitation_test
    inviter_token = get_auth_token(client, 'inviter', 'p@ssw0rd4')

    # 创建第一个邀请
    GroupInvitation.objects.create(
        conversation=data['conv'],
        inviter=data['member'],
        invitee=data['invitee'],
        status='pending'
    )

    # 尝试创建第二个相同的邀请
    resp = client.post(
        reverse('invite_to_group'),
        data=json.dumps({
            'group_id': data['conv'].id,
            'friend_id': data['invitee'].id,
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {inviter_token}'
    )

    assert resp.status_code == 400
    assert 'already a pending invitation' in resp.json().get('info', '')


@pytest.mark.django_db
def test_list_group_invitations_success(client: Client, setup_group_invitation_test):
    """测试成功获取群聊邀请列表"""
    data = setup_group_invitation_test
    admin_token = get_auth_token(client, 'admin', 'p@ssw0rd2')

    # 创建一些邀请
    inv1 = GroupInvitation.objects.create(
        conversation=data['conv'],
        inviter=data['member'],
        invitee=data['invitee'],
        status='pending',
        message='邀请1'
    )

    # 创建第二个群聊用于第二个邀请
    conv2 = Conversation.objects.create(name='test_group2', type='group')
    Member.objects.create(conversation=conv2, user=data['owner'], nickname='owner', role='owner')
    Member.objects.create(conversation=conv2, user=data['admin'], nickname='admin', role='admin')

    GroupInvitation.objects.create(
        conversation=conv2,
        inviter=data['member'],
        invitee=data['non_friend'],
        status='approved',
        reviewer=data['admin'],
        review_comment='已批准'
    )

    # 获取邀请列表
    resp = client.get(
        reverse('list_group_invitations'),
        data={'group_id': data['conv'].id},
        HTTP_AUTHORIZATION=f'Bearer {admin_token}'
    )

    assert resp.status_code == 200
    invitations = resp.json().get('invitations', [])
    assert len(invitations) == 1

    # 验证邀请详情
    invitation_ids = {inv['id'] for inv in invitations}
    assert inv1.id in invitation_ids
    # inv2不在当前群聊的邀请列表中，所以不检查


@pytest.mark.django_db
def test_list_group_invitations_unauthorized(client: Client, setup_group_invitation_test):
    """测试普通成员无法获取群聊邀请列表"""
    data = setup_group_invitation_test
    member_token = get_auth_token(client, 'member', 'p@ssw0rd3')

    # 尝试获取邀请列表
    resp = client.get(
        reverse('list_group_invitations'),
        data={'group_id': data['conv'].id},
        HTTP_AUTHORIZATION=f'Bearer {member_token}'
    )

    assert resp.status_code == 403
    assert 'Only owner and admin' in resp.json().get('info', '')


@pytest.mark.django_db
def test_approve_group_invitation_success(client: Client, setup_group_invitation_test):
    """测试成功批准群聊邀请"""
    data = setup_group_invitation_test
    admin_token = get_auth_token(client, 'admin', 'p@ssw0rd2')

    # 创建邀请
    invitation = GroupInvitation.objects.create(
        conversation=data['conv'],
        inviter=data['member'],
        invitee=data['invitee'],
        status='pending',
        message='请加入'
    )

    # 批准邀请
    resp = client.post(
        reverse('review_group_invitation'),
        data=json.dumps({
            'invitation_id': invitation.id,
            'action': 'approve',
            'comment': '欢迎加入'
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {admin_token}'
    )

    assert resp.status_code == 200

    # 验证邀请状态已更新
    invitation.refresh_from_db()
    assert invitation.status == 'approved'
    assert invitation.reviewer == data['admin']
    assert invitation.review_comment == '欢迎加入'

    # 验证用户已被添加到群聊
    member = Member.objects.filter(conversation=data['conv'], user=data['invitee']).first()
    assert member is not None
    assert member.role == 'member'


@pytest.mark.django_db
def test_reject_group_invitation_success(client: Client, setup_group_invitation_test):
    """测试成功拒绝群聊邀请"""
    data = setup_group_invitation_test
    admin_token = get_auth_token(client, 'admin', 'p@ssw0rd2')

    # 创建邀请
    invitation = GroupInvitation.objects.create(
        conversation=data['conv'],
        inviter=data['member'],
        invitee=data['invitee'],
        status='pending',
        message='请加入'
    )

    # 拒绝邀请
    resp = client.post(
        reverse('review_group_invitation'),
        data=json.dumps({
            'invitation_id': invitation.id,
            'action': 'reject',
            'comment': '暂时不需要'
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {admin_token}'
    )

    assert resp.status_code == 200

    # 验证邀请状态已更新
    invitation.refresh_from_db()
    assert invitation.status == 'rejected'
    assert invitation.reviewer == data['admin']
    assert invitation.review_comment == '暂时不需要'

    # 验证用户未被添加到群聊
    member = Member.objects.filter(conversation=data['conv'], user=data['invitee']).first()
    assert member is None


@pytest.mark.django_db
def test_review_group_invitation_unauthorized(client: Client, setup_group_invitation_test):
    """测试普通成员无法审核群聊邀请"""
    data = setup_group_invitation_test
    member_token = get_auth_token(client, 'member', 'p@ssw0rd3')

    # 创建邀请
    invitation = GroupInvitation.objects.create(
        conversation=data['conv'],
        inviter=data['member'],
        invitee=data['invitee'],
        status='pending'
    )

    # 尝试审核邀请
    resp = client.post(
        reverse('review_group_invitation'),
        data=json.dumps({
            'invitation_id': invitation.id,
            'action': 'approve'
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {member_token}'
    )

    assert resp.status_code == 403
    assert 'Only owner and admin' in resp.json().get('info', '')


@pytest.mark.django_db
def test_get_user_invitations_success(client: Client, setup_group_invitation_test):
    """测试成功获取用户收到的邀请列表"""
    data = setup_group_invitation_test
    invitee_token = get_auth_token(client, 'invitee', 'p@ssw0rd5')

    # 创建一些邀请
    inv1 = GroupInvitation.objects.create(
        conversation=data['conv'],
        inviter=data['member'],
        invitee=data['invitee'],
        status='pending',
        message='邀请1'
    )

    # 创建第二个群聊用于第二个邀请
    conv2 = Conversation.objects.create(name='test_group2', type='group')
    Member.objects.create(conversation=conv2, user=data['owner'], nickname='owner', role='owner')
    Member.objects.create(conversation=conv2, user=data['admin'], nickname='admin', role='admin')

    inv2 = GroupInvitation.objects.create(
        conversation=conv2,
        inviter=data['admin'],
        invitee=data['invitee'],
        status='rejected',
        reviewer=data['owner'],
        review_comment='已拒绝'
    )

    # 获取用户收到的邀请列表
    resp = client.get(
        reverse('get_user_invitations'),
        HTTP_AUTHORIZATION=f'Bearer {invitee_token}'
    )

    assert resp.status_code == 200
    invitations = resp.json().get('invitations', [])
    assert len(invitations) == 2

    # 验证邀请详情
    invitation_ids = {inv['id'] for inv in invitations}
    assert inv1.id in invitation_ids
    assert inv2.id in invitation_ids


@pytest.mark.django_db
def test_get_user_invitations_with_filter(client: Client, setup_group_invitation_test):
    """测试按状态过滤用户收到的邀请列表"""
    data = setup_group_invitation_test
    invitee_token = get_auth_token(client, 'invitee', 'p@ssw0rd5')

    # 创建一些邀请
    inv1 = GroupInvitation.objects.create(
        conversation=data['conv'],
        inviter=data['member'],
        invitee=data['invitee'],
        status='pending',
        message='邀请1'
    )

    # 创建第二个群聊用于第二个邀请
    conv2 = Conversation.objects.create(name='test_group2', type='group')
    Member.objects.create(conversation=conv2, user=data['owner'], nickname='owner', role='owner')
    Member.objects.create(conversation=conv2, user=data['admin'], nickname='admin', role='admin')

    GroupInvitation.objects.create(
        conversation=conv2,
        inviter=data['admin'],
        invitee=data['invitee'],
        status='rejected',
        reviewer=data['owner'],
        review_comment='已拒绝'
    )

    # 获取待处理的邀请列表
    resp = client.get(
        reverse('get_user_invitations'),
        data={'status': 'pending'},
        HTTP_AUTHORIZATION=f'Bearer {invitee_token}'
    )

    assert resp.status_code == 200
    invitations = resp.json().get('invitations', [])
    assert len(invitations) == 1

    # 验证只返回待处理的邀请
    assert invitations[0]['id'] == inv1.id
    assert invitations[0]['status'] == 'pending'


@pytest.mark.django_db
def test_review_already_processed_invitation_fail(client: Client, setup_group_invitation_test):
    """测试审核已处理的邀请失败"""
    data = setup_group_invitation_test
    admin_token = get_auth_token(client, 'admin', 'p@ssw0rd2')

    # 创建已处理的邀请
    invitation = GroupInvitation.objects.create(
        conversation=data['conv'],
        inviter=data['member'],
        invitee=data['invitee'],
        status='approved',
        reviewer=data['owner']
    )

    # 尝试再次审核
    resp = client.post(
        reverse('review_group_invitation'),
        data=json.dumps({
            'invitation_id': invitation.id,
            'action': 'reject'
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {admin_token}'
    )

    assert resp.status_code == 400
    assert 'already been processed' in resp.json().get('info', '')


@pytest.mark.django_db
def test_invite_with_invalid_parameters_fail(client: Client, setup_group_invitation_test):
    """测试使用无效参数邀请失败"""
    data = setup_group_invitation_test
    inviter_token = get_auth_token(client, 'inviter', 'p@ssw0rd4')

    # 测试缺少group_id
    resp = client.post(
        reverse('invite_to_group'),
        data=json.dumps({
            'friend_id': data['invitee'].id,
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {inviter_token}'
    )
    assert resp.status_code == 400
    assert 'Missing group_id or friend_id' in resp.json().get('info', '')

    # 测试缺少friend_id
    resp = client.post(
        reverse('invite_to_group'),
        data=json.dumps({
            'group_id': data['conv'].id,
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {inviter_token}'
    )
    assert resp.status_code == 400
    assert 'Missing group_id or friend_id' in resp.json().get('info', '')


@pytest.mark.django_db
def test_review_with_invalid_parameters_fail(client: Client, setup_group_invitation_test):
    """测试使用无效参数审核邀请失败"""
    data = setup_group_invitation_test
    admin_token = get_auth_token(client, 'admin', 'p@ssw0rd2')

    # 创建邀请
    invitation = GroupInvitation.objects.create(
        conversation=data['conv'],
        inviter=data['member'],
        invitee=data['invitee'],
        status='pending'
    )

    # 测试缺少invitation_id
    resp = client.post(
        reverse('review_group_invitation'),
        data=json.dumps({
            'action': 'approve'
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {admin_token}'
    )
    assert resp.status_code == 400
    assert 'Missing invitation_id or action' in resp.json().get('info', '')

    # 测试缺少action
    resp = client.post(
        reverse('review_group_invitation'),
        data=json.dumps({
            'invitation_id': invitation.id
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {admin_token}'
    )
    assert resp.status_code == 400
    assert 'Missing invitation_id or action' in resp.json().get('info', '')

    # 测试无效的action
    resp = client.post(
        reverse('review_group_invitation'),
        data=json.dumps({
            'invitation_id': invitation.id,
            'action': 'invalid'
        }),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {admin_token}'
    )
    assert resp.status_code == 400
    assert 'Must be \'approve\' or \'reject\'' in resp.json().get('info', '')
