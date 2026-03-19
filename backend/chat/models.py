from django.db import models
from django.contrib.auth import get_user_model

# 模块级获取 User 模型，避免类属性命名混淆
User = get_user_model()


class ActiveMemberManager(models.Manager):
    """Default manager that only returns active memberships."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Conversation(models.Model):
    name = models.CharField(max_length=50, blank=True)  # 群聊昵称，私聊可为空
    type = models.CharField(max_length=10, choices=[
        ("private", "Private"), ("group", "Group")
    ])
    is_active = models.BooleanField(default=True)  # 标记会话是否可继续发送消息（群解散后置为 False）
    created_at = models.DateTimeField(auto_now_add=True)
    avatar = models.URLField(max_length=150, blank=True)

    def __str__(self):
        return f"conversation_{self.id} ({self.name or self.type})"


class Member(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='members')
    nickname = models.CharField(max_length=30, blank=True)  # 用户的昵称
    mute = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    time = models.DateTimeField(blank=True, null=True)  # 上一次关闭时间
    role = models.CharField(max_length=10, choices=[("member", "Member"), ("admin", "Admin"), ("owner", "Owner")])  # member,admin,owner三种角色
    is_active = models.BooleanField(default=True)

    # Default manager hides inactive (soft-deleted) memberships; all_objects keeps raw access.
    objects = ActiveMemberManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = 'all_objects'
        default_manager_name = 'objects'
    
    def save(self, *args, **kwargs):
        if not self.nickname:  # 如果没填 nickname，就自动使用 user 的名字
            self.nickname = self.user.username
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete: mark membership inactive without removing messages."""
        if not self.is_active:
            return
        self.is_active = False
        self.save(update_fields=['is_active'])

    def __str__(self):
        return f"user {self.user.username} in conversation_{self.conversation.id} ({self.role})"


class PinnedConversation(models.Model):
    """用户置顶会话模型，用于管理置顶顺序"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pinned_conversations')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='pinned_by_users')
    pin_order = models.PositiveIntegerField(default=0)  # 置顶顺序，数字越小越靠前
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'conversation')  # 确保每个用户对每个会话只能置顶一次
        ordering = ['pin_order', 'created_at']  # 默认按置顶顺序排序
    
    def __str__(self):
        return f"user {self.user.username} pinned conversation_{self.conversation.id} at order {self.pin_order}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='messages')
    type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),           # 文本消息
            ('image', 'Image'),         # 图片消息
            ('emoji', 'Emoji'),         # 表情消息
            ('video', 'Video'),         # 视频消息（预留）
            ('audio', 'Audio'),         # 音频消息（预留）
        ],
        default='text',
        help_text='消息类型：文本、图片、文件等'
    )
    content = models.TextField(blank=True, help_text='消息内容。文本消息存文本，图片/文件消息存URL')
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies', help_text='被回复的消息')
    time = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)
    valid = models.BooleanField(default=True)
    read_list = models.ManyToManyField(Member, related_name='read_messages', blank=True)
    delete_list = models.ManyToManyField(Member, related_name='deleted_messages', blank=True)


    def __str__(self):
        sender_name = self.member.user.username if self.member_id else "unknown"
        preview = (self.content or '')[:30]
        return f"[{self.type}] from {sender_name} to conversation_{self.conversation.id} at {self.time}: {preview}"


class GroupAnnouncement(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='announcements')
    author = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Announcement in conversation_{self.conversation_id} at {self.created_at}"


class GroupInvitation(models.Model):
    """群聊邀请模型，记录群成员邀请好友加入群聊的申请"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),    # 待审核
        ('approved', 'Approved'),  # 已通过
        ('rejected', 'Rejected'),  # 已拒绝
        ('expired', 'Expired'),    # 已过期
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='invitations')
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')  # 邀请人
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')  # 被邀请人
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, help_text='邀请附言')  # 邀请附言
    
    # 审核相关字段
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_invitations')  # 审核人
    review_time = models.DateTimeField(null=True, blank=True)  # 审核时间
    review_comment = models.TextField(blank=True, help_text='审核意见')  # 审核意见
    
    class Meta:
        unique_together = ('conversation', 'invitee')  # 确保每个群聊对每个用户的邀请是唯一的
        
    def __str__(self):
        return f"Invitation from {self.inviter.username} to {self.invitee.username} for conversation_{self.conversation.id} ({self.status})"