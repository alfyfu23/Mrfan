import re

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


# ---- 用户名验证函数 ----
def validate_username(username: str):
    """基础用户名格式检测"""
    if not 1 <= len(username) <= 30:
        raise ValidationError("Username length must be 1–30 characters.")
    if not re.match(r'^[A-Za-z0-9._\u4e00-\u9fa5]+$', username):
        raise ValidationError("Username can only contain letters, digits, underscores, dots, and Chinese characters.")
    if username[0] in "._" or username[-1] in "._":
        raise ValidationError("Username cannot start or end with a dot or underscore.")
    return username



# ---- 密码验证函数 ----
def validate_password_strength(password: str):
    """基础强度检测"""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if len(password) > 128:
        raise ValidationError("Password must be shorter than 128 characters.")
    if not re.search(r'[A-Za-z]', password):
        raise ValidationError("Password must contain at least one letter.")
    if not re.search(r'\d', password):
        raise ValidationError("Password must contain at least one digit.")
    if re.search(r'\s', password):
        raise ValidationError("Password cannot contain spaces.")
    return password


# ---- 手机号验证器 ----
phone_validator = RegexValidator(
    regex=r'^1[3-9]\d{9}$',
    message="Phone number must be a valid 11-digit Chinese mainland number."
)


class User(AbstractUser):
    username = models.CharField(
        max_length=30,
        unique=True,
        help_text="1–30 characters, letters/digits/._ only, cannot start or end with . or _"
    )

    email = models.EmailField(
        blank=True,
        null=True,
        help_text="User email address (optional)"
    )

    phone = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        validators=[phone_validator],
        help_text="User phone number (optional)"
    )

    avatar = models.URLField(
        blank=True,
        null=True,
        help_text="User avatar image URL"
    )

    info = models.TextField(
        max_length=1000,
        blank=True,
        help_text="Personal introduction or profile text"
    )

    # Preserve the original username when the account is deactivated so that
    # existing references (friends, messages) can still display the former name
    # after the active username is freed for reuse.
    deactivated_username = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="Former username kept for display after deactivation"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

    @property
    def display_username(self) -> str:
        """Return the name that should be shown to others."""
        if not self.is_active and self.deactivated_username:
            return self.deactivated_username
        return self.username
