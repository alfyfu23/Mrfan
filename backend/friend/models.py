from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q, F

class Friendship(models.Model):
    """记录两个用户之间的好友关系（无方向，A-B 与 B-A 视为同一条记录）"""
    user_a = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='friendships_a',
        db_index=True
    )
    user_b = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='friendships_b',
        db_index=True
    ) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # 防止 self-friend
            models.CheckConstraint(condition=~Q(user_a=F('user_b')), name='friendship_no_self'),
            # 确保 (user_a, user_b) 唯一（需在 save 中把顺序规范化）
            models.UniqueConstraint(fields=['user_a', 'user_b'], name='unique_friendship'),
        ]

    def save(self, *args, **kwargs):
        if self.user_a_id and self.user_b_id:
            if self.user_a_id == self.user_b_id:
                raise ValueError("A user cannot befriend themselves.")
            if self.user_a_id > self.user_b_id:
                self.user_a, self.user_b = self.user_b, self.user_a
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user_a} ↔ {self.user_b}"
    
class Pending(models.Model):
    user_from = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="user_from",
        db_index=True
    )
    user_to = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="user_to",
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user_from} → {self.user_to}"
    
class FriendGroup(models.Model):
    User = get_user_model()
    name = models.CharField(max_length=100)  # 分组名称
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_groups')  # 属于哪个用户
    friends = models.ManyToManyField(User)  # 直接指向用户

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    def add_friend(self, friend):
        """将好友添加到分组"""
        # 检查是否是好友
        if not Friendship.objects.filter(
            Q(user_a=self.user, user_b=friend) | Q(user_a=friend, user_b=self.user)
        ).exists():
            raise ValueError("User and friend are not friends.")
        
        # 检查好友是否已经在该分组
        if self.friends.filter(id=friend.id).exists():
            raise ValueError("Friend already in group.")
        
        # 添加好友到分组
        self.friends.add(friend)

    def remove_friend(self, friend):
        """从分组中移除好友"""
        # 检查是否是好友
        if not Friendship.objects.filter(
            Q(user_a=self.user, user_b=friend) | Q(user_a=friend, user_b=self.user)
        ).exists():
            raise ValueError("User and friend are not friends.")
        
        # 检查好友是否不在该分组
        if not self.friends.filter(id=friend.id).exists():
            raise ValueError("Friend not in this group.")
        
        self.friends.remove(friend)

