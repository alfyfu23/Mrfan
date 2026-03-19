import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from chat.models import Conversation, Member, Message, GroupAnnouncement, PinnedConversation, GroupInvitation


@pytest.mark.django_db
class TestConversationModel(TestCase):
    """测试Conversation模型的各项功能"""
    
    def test_conversation_creation_private(self):
        """测试创建私聊会话"""
        conv = Conversation.objects.create(type='private')
        
        assert conv.type == 'private'
        assert conv.name == ''
        assert conv.is_active == True
        assert conv.created_at is not None
        assert str(conv) == f"conversation_{conv.id} (private)"
    
    def test_conversation_creation_group(self):
        """测试创建群聊会话"""
        conv = Conversation.objects.create(
            type='group',
            name='Test Group',
            avatar='http://example.com/avatar.jpg'
        )
        
        assert conv.type == 'group'
        assert conv.name == 'Test Group'
        assert conv.avatar == 'http://example.com/avatar.jpg'
        assert conv.is_active == True
        assert conv.created_at is not None
        assert str(conv) == f"conversation_{conv.id} (Test Group)"
    
    def test_conversation_with_blank_name(self):
        """测试空白名称的会话字符串表示"""
        conv = Conversation.objects.create(type='group', name='')
        
        assert str(conv) == f"conversation_{conv.id} (group)"


@pytest.mark.django_db
class TestMemberModel(TestCase):
    """测试Member模型的各项功能"""
    
    def test_member_creation_with_nickname(self):
        """测试创建带昵称的成员"""
        User = get_user_model()
        user = User.objects.create_user(username='testuser', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        member = Member.objects.create(
            user=user,
            conversation=conv,
            nickname='Test Nickname',
            role='member',
            time=timezone.now()
        )
        
        assert member.user == user
        assert member.conversation == conv
        assert member.nickname == 'Test Nickname'
        assert member.role == 'member'
        assert member.is_active == True
        assert str(member) == f"user {user.username} in conversation_{conv.id} (member)"
    
    def test_member_creation_without_nickname(self):
        """测试创建不带昵称的成员（应该自动使用用户名）"""
        User = get_user_model()
        user = User.objects.create_user(username='testuser2', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        member = Member.objects.create(
            user=user,
            conversation=conv,
            role='member',
            time=timezone.now()
        )
        
        # 验证昵称自动设置为用户名
        assert member.nickname == 'testuser2'
        assert str(member) == f"user {user.username} in conversation_{conv.id} (member)"
    
    def test_member_soft_delete(self):
        """测试成员软删除"""
        User = get_user_model()
        user = User.objects.create_user(username='testuser3', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
    
        member = Member.objects.create(
            user=user,
            conversation=conv,
            role='member',
            time=timezone.now()
        )
    
        # 验证成员是活跃的
        assert member.is_active == True
    
        # 软删除成员
        member.delete()
    
        # 验证成员不再活跃，但记录仍然存在
        member.refresh_from_db()
        assert member.is_active == False
    
        # 验证默认管理器不返回非活跃成员
        assert member not in conv.members.all()
    
        # 验证all_objects管理器返回所有成员
        assert member in Member.all_objects.all()
    
    def test_member_double_soft_delete(self):
        """测试重复软删除成员"""
        User = get_user_model()
        user = User.objects.create_user(username='testuser4', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        member = Member.objects.create(
            user=user,
            conversation=conv,
            role='member',
            time=timezone.now()
        )
        
        # 第一次软删除
        member.delete()
        member.refresh_from_db()
        assert member.is_active == False
        
        # 第二次软删除（应该不会出错）
        member.delete()
        member.refresh_from_db()
        assert member.is_active == False
    
    def test_member_roles(self):
        """测试成员的不同角色"""
        User = get_user_model()
        user1 = User.objects.create_user(username='owner', password='test123')
        user2 = User.objects.create_user(username='admin', password='test123')
        user3 = User.objects.create_user(username='member', password='test123')
        
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        owner = Member.objects.create(
            user=user1, conversation=conv, role='owner', time=timezone.now()
        )
        admin = Member.objects.create(
            user=user2, conversation=conv, role='admin', time=timezone.now()
        )
        member = Member.objects.create(
            user=user3, conversation=conv, role='member', time=timezone.now()
        )
        
        assert owner.role == 'owner'
        assert admin.role == 'admin'
        assert member.role == 'member'
        
        assert str(owner) == f"user {user1.username} in conversation_{conv.id} (owner)"
        assert str(admin) == f"user {user2.username} in conversation_{conv.id} (admin)"
        assert str(member) == f"user {user3.username} in conversation_{conv.id} (member)"


@pytest.mark.django_db
class TestMessageModel(TestCase):
    """测试Message模型的各项功能"""
    
    def test_message_creation_text(self):
        """测试创建文本消息"""
        User = get_user_model()
        user = User.objects.create_user(username='testuser', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member = Member.objects.create(
            user=user, conversation=conv, role='member', time=timezone.now()
        )
        
        message = Message.objects.create(
            conversation=conv,
            member=member,
            type='text',
            content='Hello, world!'
        )
        
        assert message.conversation == conv
        assert message.member == member
        assert message.type == 'text'
        assert message.content == 'Hello, world!'
        assert message.is_edited == False
        assert message.valid == True
        assert message.time is not None
        assert str(message) == f"[text] from {user.username} to conversation_{conv.id} at {message.time}: Hello, world!"
    
    def test_message_creation_image(self):
        """测试创建图片消息"""
        User = get_user_model()
        user = User.objects.create_user(username='testuser2', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member = Member.objects.create(
            user=user, conversation=conv, role='member', time=timezone.now()
        )
        
        message = Message.objects.create(
            conversation=conv,
            member=member,
            type='image',
            content='http://example.com/image.jpg'
        )
        
        assert message.type == 'image'
        assert message.content == 'http://example.com/image.jpg'
        assert str(message) == f"[image] from {user.username} to conversation_{conv.id} at {message.time}: http://example.com/image.jpg"
    
    def test_message_with_reply(self):
        """测试带有回复的消息"""
        User = get_user_model()
        user = User.objects.create_user(username='testuser3', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member = Member.objects.create(
            user=user, conversation=conv, role='member', time=timezone.now()
        )
    
        # 创建原始消息
        original = Message.objects.create(
            conversation=conv,
            member=member,
            type='text',
            content='Original message'
        )
    
        # 创建回复消息
        reply = Message.objects.create(
            conversation=conv,
            member=member,
            type='text',
            content='Reply message',
            reply_to=original
        )
    
        assert reply.reply_to == original
        # 验证回复关系 - 注意replies是related_name，应该通过original访问
        assert reply in original.replies.all()
    
    def test_message_long_content_truncation(self):
        """测试长内容在字符串表示中的截断"""
        User = get_user_model()
        user = User.objects.create_user(username='testuser4', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member = Member.objects.create(
            user=user, conversation=conv, role='member', time=timezone.now()
        )
    
        # 创建长内容消息
        long_content = 'A' * 100
        message = Message.objects.create(
            conversation=conv,
            member=member,
            type='text',
            content=long_content
        )
    
        # 验证字符串表示被截断为前30个字符
        message_str = str(message)
        assert 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' in message_str  # 前30个A
        assert len(message_str.split(': ')[-1]) == 30  # 验证截断长度为30
        assert '...' in message_str or message_str.endswith('A' * 30)
    
    def test_message_types(self):
        """测试不同类型的消息"""
        User = get_user_model()
        user = User.objects.create_user(username='testuser5', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member = Member.objects.create(
            user=user, conversation=conv, role='member', time=timezone.now()
        )
        
        # 创建不同类型的消息
        text_msg = Message.objects.create(
            conversation=conv, member=member, type='text', content='Text'
        )
        image_msg = Message.objects.create(
            conversation=conv, member=member, type='image', content='Image URL'
        )
        emoji_msg = Message.objects.create(
            conversation=conv, member=member, type='emoji', content='😊'
        )
        video_msg = Message.objects.create(
            conversation=conv, member=member, type='video', content='Video URL'
        )
        audio_msg = Message.objects.create(
            conversation=conv, member=member, type='audio', content='Audio URL'
        )
        
        assert text_msg.type == 'text'
        assert image_msg.type == 'image'
        assert emoji_msg.type == 'emoji'
        assert video_msg.type == 'video'
        assert audio_msg.type == 'audio'
        
        assert '[text]' in str(text_msg)
        assert '[image]' in str(image_msg)
        assert '[emoji]' in str(emoji_msg)
        assert '[video]' in str(video_msg)
        assert '[audio]' in str(audio_msg)
    
    def test_message_read_list(self):
        """测试消息的已读列表"""
        User = get_user_model()
        user1 = User.objects.create_user(username='reader1', password='test123')
        user2 = User.objects.create_user(username='reader2', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member1 = Member.objects.create(
            user=user1, conversation=conv, role='member', time=timezone.now()
        )
        member2 = Member.objects.create(
            user=user2, conversation=conv, role='member', time=timezone.now()
        )
        
        message = Message.objects.create(
            conversation=conv,
            member=member1,
            type='text',
            content='Test message'
        )
        
        # 验证初始已读列表为空
        assert message.read_list.count() == 0
        
        # 添加到已读列表
        message.read_list.add(member1)
        message.read_list.add(member2)
        
        # 验证已读列表
        assert message.read_list.count() == 2
        assert member1 in message.read_list.all()
        assert member2 in message.read_list.all()
    
    def test_message_delete_list(self):
        """测试消息的删除列表"""
        User = get_user_model()
        user1 = User.objects.create_user(username='deleter1', password='test123')
        user2 = User.objects.create_user(username='deleter2', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member1 = Member.objects.create(
            user=user1, conversation=conv, role='member', time=timezone.now()
        )
        member2 = Member.objects.create(
            user=user2, conversation=conv, role='member', time=timezone.now()
        )
        
        message = Message.objects.create(
            conversation=conv,
            member=member1,
            type='text',
            content='Test message'
        )
        
        # 验证初始删除列表为空
        assert message.delete_list.count() == 0
        
        # 添加到删除列表
        message.delete_list.add(member1)
        message.delete_list.add(member2)
        
        # 验证删除列表
        assert message.delete_list.count() == 2
        assert member1 in message.delete_list.all()
        assert member2 in message.delete_list.all()


@pytest.mark.django_db
class TestGroupAnnouncementModel(TestCase):
    """测试GroupAnnouncement模型的各项功能"""
    
    def test_announcement_creation(self):
        """测试创建群公告"""
        User = get_user_model()
        user = User.objects.create_user(username='announcer', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member = Member.objects.create(
            user=user, conversation=conv, role='owner', time=timezone.now()
        )
        
        announcement = GroupAnnouncement.objects.create(
            conversation=conv,
            author=member,
            content='This is a group announcement'
        )
        
        assert announcement.conversation == conv
        assert announcement.author == member
        assert announcement.content == 'This is a group announcement'
        assert announcement.created_at is not None
        assert str(announcement) == f"Announcement in conversation_{conv.id} at {announcement.created_at}"
    
    def test_announcement_without_author(self):
        """测试没有作者的群公告"""
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        announcement = GroupAnnouncement.objects.create(
            conversation=conv,
            author=None,
            content='System announcement'
        )
        
        assert announcement.author is None
        assert str(announcement) == f"Announcement in conversation_{conv.id} at {announcement.created_at}"
    
    def test_multiple_announcements(self):
        """测试多个群公告"""
        User = get_user_model()
        user = User.objects.create_user(username='announcer2', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member = Member.objects.create(
            user=user, conversation=conv, role='owner', time=timezone.now()
        )
        
        # 创建多个公告
        ann1 = GroupAnnouncement.objects.create(
            conversation=conv, author=member, content='First announcement'
        )
        ann2 = GroupAnnouncement.objects.create(
            conversation=conv, author=member, content='Second announcement'
        )
        ann3 = GroupAnnouncement.objects.create(
            conversation=conv, author=member, content='Third announcement'
        )
        
        # 验证所有公告都被创建
        announcements = GroupAnnouncement.objects.filter(conversation=conv)
        assert announcements.count() == 3
        
        # 验证按时间排序
        ordered_announcements = list(announcements.order_by('created_at'))
        assert ordered_announcements[0] == ann1
        assert ordered_announcements[1] == ann2
        assert ordered_announcements[2] == ann3


@pytest.mark.django_db
class TestPinnedConversationModel(TestCase):
    """测试PinnedConversation模型的各项功能"""
    
    def test_pinned_conversation_creation(self):
        """测试创建置顶会话"""
        User = get_user_model()
        user = User.objects.create_user(username='pinner', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        pinned = PinnedConversation.objects.create(
            user=user,
            conversation=conv,
            pin_order=1
        )
        
        assert pinned.user == user
        assert pinned.conversation == conv
        assert pinned.pin_order == 1
        assert pinned.created_at is not None
        assert str(pinned) == f"user {user.username} pinned conversation_{conv.id} at order 1"
    
    def test_multiple_pinned_conversations(self):
        """测试多个置顶会话"""
        User = get_user_model()
        user = User.objects.create_user(username='pinner2', password='test123')
        
        # 创建多个会话
        conv1 = Conversation.objects.create(type='group', name='Group 1')
        conv2 = Conversation.objects.create(type='group', name='Group 2')
        conv3 = Conversation.objects.create(type='group', name='Group 3')
        
        # 创建多个置顶会话
        pin1 = PinnedConversation.objects.create(
            user=user, conversation=conv1, pin_order=3
        )
        pin2 = PinnedConversation.objects.create(
            user=user, conversation=conv2, pin_order=1
        )
        pin3 = PinnedConversation.objects.create(
            user=user, conversation=conv3, pin_order=2
        )
        
        # 验证按pin_order排序
        ordered_pins = list(PinnedConversation.objects.filter(user=user))
        assert ordered_pins[0] == pin2
        assert ordered_pins[1] == pin3
        assert ordered_pins[2] == pin1
    
    def test_unique_constraint(self):
        """测试唯一性约束"""
        User = get_user_model()
        user = User.objects.create_user(username='pinner3', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        # 创建第一个置顶会话
        PinnedConversation.objects.create(
            user=user, conversation=conv, pin_order=1
        )
        
        # 尝试创建第二个相同的置顶会话，应该失败
        with transaction.atomic():
            with pytest.raises(Exception):  # 可能是IntegrityError或其他异常
                PinnedConversation.objects.create(
                    user=user, conversation=conv, pin_order=2
                )


@pytest.mark.django_db
class TestGroupInvitationModel(TestCase):
    """测试GroupInvitation模型的各项功能"""
    
    def test_invitation_creation(self):
        """测试创建群聊邀请"""
        User = get_user_model()
        inviter = User.objects.create_user(username='inviter', password='test123')
        invitee = User.objects.create_user(username='invitee', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        invitation = GroupInvitation.objects.create(
            conversation=conv,
            inviter=inviter,
            invitee=invitee,
            message='Please join our group'
        )
        
        assert invitation.conversation == conv
        assert invitation.inviter == inviter
        assert invitation.invitee == invitee
        assert invitation.status == 'pending'
        assert invitation.message == 'Please join our group'
        assert invitation.created_at is not None
        assert invitation.updated_at is not None
        assert str(invitation) == f"Invitation from {inviter.username} to {invitee.username} for conversation_{conv.id} (pending)"
    
    def test_invitation_status_transitions(self):
        """测试邀请状态转换"""
        User = get_user_model()
        inviter = User.objects.create_user(username='inviter2', password='test123')
        invitee = User.objects.create_user(username='invitee2', password='test123')
        reviewer = User.objects.create_user(username='reviewer', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        invitation = GroupInvitation.objects.create(
            conversation=conv,
            inviter=inviter,
            invitee=invitee,
            message='Please join our group'
        )
        
        # 初始状态为pending
        assert invitation.status == 'pending'
        assert invitation.reviewer is None
        assert invitation.review_time is None
        assert invitation.review_comment == ''
        
        # 批准邀请
        invitation.status = 'approved'
        invitation.reviewer = reviewer
        invitation.review_time = timezone.now()
        invitation.review_comment = 'Welcome to the group'
        invitation.save()
        
        # 验证状态已更新
        invitation.refresh_from_db()
        assert invitation.status == 'approved'
        assert invitation.reviewer == reviewer
        assert invitation.review_time is not None
        assert invitation.review_comment == 'Welcome to the group'
        assert 'approved' in str(invitation)
    
    def test_invitation_unique_constraint(self):
        """测试邀请的唯一性约束"""
        User = get_user_model()
        inviter = User.objects.create_user(username='inviter3', password='test123')
        invitee = User.objects.create_user(username='invitee3', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        # 创建第一个邀请
        GroupInvitation.objects.create(
            conversation=conv,
            inviter=inviter,
            invitee=invitee,
            message='First invitation'
        )
        
        # 尝试创建第二个相同的邀请，应该失败
        with transaction.atomic():
            with pytest.raises(Exception):  # 可能是IntegrityError或其他异常
                GroupInvitation.objects.create(
                    conversation=conv,
                    inviter=inviter,
                    invitee=invitee,
                    message='Second invitation'
                )
    
    def test_multiple_invitations_different_users(self):
        """测试不同用户的邀请"""
        User = get_user_model()
        inviter = User.objects.create_user(username='inviter4', password='test123')
        invitee1 = User.objects.create_user(username='invitee4a', password='test123')
        invitee2 = User.objects.create_user(username='invitee4b', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        # 创建多个邀请
        inv1 = GroupInvitation.objects.create(
            conversation=conv, inviter=inviter, invitee=invitee1, status='pending'
        )
        inv2 = GroupInvitation.objects.create(
            conversation=conv, inviter=inviter, invitee=invitee2, status='approved'
        )
        
        # 验证可以创建不同用户的邀请
        assert GroupInvitation.objects.filter(conversation=conv).count() == 2
        
        # 验证状态
        assert inv1.status == 'pending'
        assert inv2.status == 'approved'
    
    def test_invitation_all_statuses(self):
        """测试所有邀请状态"""
        User = get_user_model()
        inviter = User.objects.create_user(username='inviter5', password='test123')
        invitee = User.objects.create_user(username='invitee5', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        # 创建不同状态的邀请
        pending = GroupInvitation.objects.create(
            conversation=conv, inviter=inviter, invitee=invitee, status='pending'
        )
        approved = GroupInvitation.objects.create(
            conversation=conv, inviter=inviter, 
            invitee=User.objects.create_user(username='invitee5a', password='test123'), 
            status='approved'
        )
        rejected = GroupInvitation.objects.create(
            conversation=conv, inviter=inviter, 
            invitee=User.objects.create_user(username='invitee5b', password='test123'), 
            status='rejected'
        )
        expired = GroupInvitation.objects.create(
            conversation=conv, inviter=inviter, 
            invitee=User.objects.create_user(username='invitee5c', password='test123'), 
            status='expired'
        )
        
        # 验证所有状态
        assert pending.status == 'pending'
        assert approved.status == 'approved'
        assert rejected.status == 'rejected'
        assert expired.status == 'expired'
        
        # 验证字符串表示
        assert 'pending' in str(pending)
        assert 'approved' in str(approved)
        assert 'rejected' in str(rejected)
        assert 'expired' in str(expired)


@pytest.mark.django_db
class TestModelRelationships(TestCase):
    """测试模型之间的关系"""
    
    def test_conversation_member_relationship(self):
        """测试会话与成员的关系"""
        User = get_user_model()
        user1 = User.objects.create_user(username='member1', password='test123')
        user2 = User.objects.create_user(username='member2', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        member1 = Member.objects.create(
            user=user1, conversation=conv, role='member', time=timezone.now()
        )
        member2 = Member.objects.create(
            user=user2, conversation=conv, role='member', time=timezone.now()
        )
        
        # 验证会话可以访问其成员
        members = list(conv.members.all())
        assert len(members) == 2
        assert member1 in members
        assert member2 in members
        
        # 验证成员可以访问其会话
        assert member1.conversation == conv
        assert member2.conversation == conv
    
    def test_conversation_message_relationship(self):
        """测试会话与消息的关系"""
        User = get_user_model()
        user = User.objects.create_user(username='sender', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member = Member.objects.create(
            user=user, conversation=conv, role='member', time=timezone.now()
        )
        
        msg1 = Message.objects.create(
            conversation=conv, member=member, type='text', content='Message 1'
        )
        msg2 = Message.objects.create(
            conversation=conv, member=member, type='text', content='Message 2'
        )
        
        # 验证会话可以访问其消息
        messages = list(conv.messages.all())
        assert len(messages) == 2
        assert msg1 in messages
        assert msg2 in messages
        
        # 验证消息可以访问其会话
        assert msg1.conversation == conv
        assert msg2.conversation == conv
    
    def test_conversation_announcement_relationship(self):
        """测试会话与公告的关系"""
        User = get_user_model()
        user = User.objects.create_user(username='announcer3', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        member = Member.objects.create(
            user=user, conversation=conv, role='owner', time=timezone.now()
        )
        
        ann1 = GroupAnnouncement.objects.create(
            conversation=conv, author=member, content='Announcement 1'
        )
        ann2 = GroupAnnouncement.objects.create(
            conversation=conv, author=member, content='Announcement 2'
        )
        
        # 验证会话可以访问其公告
        announcements = list(conv.announcements.all())
        assert len(announcements) == 2
        assert ann1 in announcements
        assert ann2 in announcements
        
        # 验证公告可以访问其会话
        assert ann1.conversation == conv
        assert ann2.conversation == conv
    
    def test_user_pinned_conversation_relationship(self):
        """测试用户与置顶会话的关系"""
        User = get_user_model()
        user = User.objects.create_user(username='pinner4', password='test123')
        
        conv1 = Conversation.objects.create(type='group', name='Group 1')
        conv2 = Conversation.objects.create(type='group', name='Group 2')
        
        pin1 = PinnedConversation.objects.create(
            user=user, conversation=conv1, pin_order=1
        )
        pin2 = PinnedConversation.objects.create(
            user=user, conversation=conv2, pin_order=2
        )
        
        # 验证用户可以访问其置顶会话
        pins = list(user.pinned_conversations.all())
        assert len(pins) == 2
        assert pin1 in pins
        assert pin2 in pins
        
        # 验证置顶会话可以访问其用户
        assert pin1.user == user
        assert pin2.user == user
    
    def test_conversation_invitation_relationship(self):
        """测试会话与邀请的关系"""
        User = get_user_model()
        inviter = User.objects.create_user(username='inviter6', password='test123')
        invitee1 = User.objects.create_user(username='invitee6a', password='test123')
        invitee2 = User.objects.create_user(username='invitee6b', password='test123')
        conv = Conversation.objects.create(type='group', name='Test Group')
        
        inv1 = GroupInvitation.objects.create(
            conversation=conv, inviter=inviter, invitee=invitee1
        )
        inv2 = GroupInvitation.objects.create(
            conversation=conv, inviter=inviter, invitee=invitee2
        )
        
        # 验证会话可以访问其邀请
        invitations = list(conv.invitations.all())
        assert len(invitations) == 2
        assert inv1 in invitations
        assert inv2 in invitations
        
        # 验证邀请可以访问其会话
        assert inv1.conversation == conv
        assert inv2.conversation == conv