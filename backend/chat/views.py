import logging
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Count, F, Max, Q
from django.db.transaction import atomic
from django.http import HttpRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from friend.models import Friendship
from utils.jwt import parse_jwt_token
from utils.network import BAD_METHOD, request_failed, request_success
from utils.notify import notify_conversation_event
from utils.tools import get_jwt_token, load_body

from .models import Conversation, GroupAnnouncement, GroupInvitation, Member, Message, PinnedConversation
from .presence import is_online

logger = logging.getLogger(__name__)

# TODO: 去除csrf禁用


def _format_message_preview(msg):
    if msg.type == 'image':
        return "[图片]"
    if msg.type == 'video':
        return "[视频]"
    return msg.content or ""


def _get_active_user(user_id):
    """Fetch user and ensure the account is active."""
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    if not user:
        return None, request_failed(code=9001, info="User not found.", status_code=500)
    if not user.is_active:
        return None, request_failed(code=2013, info="User account is deactivated.", status_code=403)
    return user, None

def _find_private_between_v2(user1, user2):
    conv = (Conversation.objects
            .filter(type="private", members__user__in=[user1, user2])  # 至少包含这两人之一
            .annotate(num_members=Count('members__user', filter=Q(members__user__in=[user1, user2]), distinct=True))
            .filter(num_members=2)  # 确保两人都在会话中
            .first())
    return conv



@csrf_exempt
def history(req: HttpRequest):
    """获取会话的历史消息
    
    参数：
        c: conversation_id (会话ID)
    
    返回：
        messages: 消息列表，包含消息的详细信息
    """
    if req.method != "GET":
        return BAD_METHOD
    # 获取参数
    c = req.GET.get('c')
    logger.info(f"(history) request for conversation={c}")
    # 提取 jwt token
    try:
        jwt_token = get_jwt_token(req)
    except Exception:
        info = "Authorization failed."
        logger.info(info)
        return request_failed(
            code=3001,
            info=info,
            status_code=400
        )
    # 检查 jwt token
    user_id = parse_jwt_token(jwt_token)
    if not user_id:
        info = "Invalid JWT Token."
        logger.info(info)
        return request_failed(
            code=3002,
            info=info,
            status_code=403
        )
    # 查找user
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    # 查找 conversation
    conversation = Conversation.objects.filter(id=c).first()
    if not conversation:
        info = "Conversation not found."
        logger.info(info)
        return request_failed(
            code=3003,
            info=info,
            status_code=404
        )
    logger.info(f"(history) conversation found id={conversation.id} type={conversation.type}")
    # 验证 user 属于该 conversation
    member = Member.objects.filter(user=user, conversation=conversation).first()
    if not member:
        info = "User not authorized to join this conversation."
        logger.info(info)
        return request_failed(
            code=3004,
            info=info,
            status_code=403
        )
    # 可选过滤参数
    q = req.GET.get('q')  # 关键词
    sender = req.GET.get('sender')  # 发送者用户ID
    start = req.GET.get('start')  # ISO 时间起
    end = req.GET.get('end')      # ISO 时间止

    # 查找messages，根据新的模型结构
    messages = []
    qs = Message.objects.filter(conversation=conversation, valid=True).select_related('member__user', 'reply_to__member__user').order_by('time')
    if q:
        qs = qs.filter(content__icontains=q)
    if sender:
        qs = qs.filter(member__user_id=sender)
    if start:
        try:
            qs = qs.filter(time__gte=start)
        except Exception:
            pass
    if end:
        try:
            qs = qs.filter(time__lte=end)
        except Exception:
            pass

    for msg in qs:
        # 检查消息是否被当前用户删除
        if member in msg.delete_list.all():
            continue

        # 构建回复消息信息
        reply_to_message = None
        if msg.reply_to_id and msg.reply_to.valid:
            reply_sender = msg.reply_to.member.user
            reply_to_message = {
                'id': msg.reply_to.id,
                'sender': reply_sender.id,
                'nickname': msg.reply_to.member.nickname or getattr(reply_sender, 'display_username', reply_sender.username),
                'sender_nickname': msg.reply_to.member.nickname or getattr(reply_sender, 'display_username', reply_sender.username),
                'text': msg.reply_to.content,
                'type': msg.reply_to.type,
                'sender_username': getattr(reply_sender, 'display_username', reply_sender.username),
                'sender_is_active': reply_sender.is_active,
            }

        sender_user = msg.member.user
        messages.append({
            'id': msg.id,
            'sender_id': sender_user.id,
            'sender_username': getattr(sender_user, 'display_username', sender_user.username),
            'nickname': msg.member.nickname or getattr(sender_user, 'display_username', sender_user.username),  # 群昵称
            'sender_nickname': msg.member.nickname or getattr(sender_user, 'display_username', sender_user.username),  # 群昵称
            'sender_is_active': sender_user.is_active,
            'type': msg.type,
            'content': msg.content,
            'reply_to': msg.reply_to_id,
            'reply_to_message': reply_to_message,
            'time': msg.time.isoformat(),
            'is_edited': msg.is_edited,
            'is_read': member in msg.read_list.all(),
        })

    logger.info(f"(history) messages_count={len(messages)}")
    return request_success(data={
        'messages': messages
    })

@csrf_exempt
def create_friend_conversation(req: HttpRequest):
    """创建好友私聊会话
    
    参数：
        id: 目标用户ID
    
    返回：
        id: 会话ID
    """
    if req.method != 'POST':
        return BAD_METHOD
    logger.info("(create_friend_conversation) called")
    # 身份验证
    try:
        jwt_token = get_jwt_token(req)
    except Exception:
        info = "Authorization failed."
        logger.info(info)
        return request_failed(
            code=3001,
            info=info,
            status_code=400
        )
    user_id = parse_jwt_token(jwt_token)
    if not user_id:
        info = "Invalid JWT Token."
        logger.info(info)
        return request_failed(
            code=3002,
            info=info,
            status_code=403
        )
    # 提取请求体
    try:
        data = load_body(req)
        target_id = data['id']
    except Exception:
        return request_failed(
            code=2001,
            info="Invalid request",
            status_code=400
        )
    # 检查用户是否存在
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    if not user:
        return request_failed(code=9001, info="User not found.", status_code=500)
    if not user.is_active:
        return request_failed(code=2013, info="User account is deactivated.", status_code=403)
    target = User.objects.filter(id=target_id).first()
    if not target:
        return request_failed(code=2004, info="Target user does not exist.", status_code=404)

    # 检查目标用户是否已注销
    if not target.is_active:
        return request_failed(code=2006, info="Cannot chat with deactivated user.", status_code=400)

    # 检查是否是好友
    friendship = Friendship.objects.filter(
        Q(user_a=user, user_b=target) | Q(user_a=target, user_b=user)
    ).first()
    logger.info(f"(create_friend_conversation) friendship_exists={bool(friendship)}")
    if not friendship:
        return request_failed(
            code=2012,
            info="Not authorized to create conversation.",
            status_code=403
        )
    # 检查会话是否已经存在
    conv = _find_private_between_v2(user, target)
    created_new = False
    if not conv:
        # 不存在则创建
        with atomic():
            conv = Conversation.objects.create(name="", type="private")
            current_time = timezone.now()
            # 创建两个 Member 记录
            Member.objects.create(
                conversation=conv,
                user=user,
                nickname=user.username,
                role="member",
                time=current_time
            )
            Member.objects.create(
                conversation=conv,
                user=target,
                nickname=target.username,
                role="member",
                time=current_time
            )
        logger.info(f"(create_friend_conversation) created_conv_id={conv.id}")
        created_new = True
    if created_new:
        notify_conversation_event([user.id, target.id], 'conversation_created', conv.id)
    return request_success(
        data={"id": conv.id}
    )

@csrf_exempt
def create_group(req: HttpRequest):
    """创建群聊
    body: {name: str, members: [user_id], avatar?: str}
    创建者为 owner，其余为 member
    """
    if req.method != 'POST':
        return BAD_METHOD

    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    creator, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp

    data = load_body(req) or {}
    name = data.get('name') or ''
    member_ids = data.get('members') or []
    avatar = data.get('avatar') or ''

    User = get_user_model()

    # 先检查是否包含已注销用户（存在但 is_active=False）
    if User.objects.filter(id__in=member_ids, is_active=False).exists():
        return request_failed(code=2005, info="Cannot add deactivated user to group.", status_code=400)

    # 仅保留存在且活跃的用户；忽略不存在的ID
    users = list(User.objects.filter(id__in=member_ids, is_active=True))

    with atomic():
        conv = Conversation.objects.create(name=name, type='group', avatar=avatar)
        now = timezone.now()
        Member.objects.create(conversation=conv, user=creator, nickname=creator.username, role='owner', time=now)
        for u in users:
            if u.id == creator.id:
                continue
            Member.objects.create(conversation=conv, user=u, nickname=u.username, role='member', time=now)

    member_ids = [creator.id] + [u.id for u in users if u.id != creator.id]
    notify_conversation_event(member_ids, 'conversation_created', conv.id)

    return request_success({'id': conv.id})

@csrf_exempt
def update_group_info(req: HttpRequest):
    """更新群信息：名称、头像"""
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    conv_id = data.get('id')
    name = data.get('name')
    avatar = data.get('avatar')
    conv = Conversation.objects.filter(id=conv_id, type='group').first()
    if not conv:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    if not conv.is_active:
        return request_failed(code=2012, info="Conversation is inactive.", status_code=403)
    # 只有管理员/群主可改
    role = Member.objects.filter(conversation=conv, user_id=user_id).values_list('role', flat=True).first()
    if role not in ['owner', 'admin']:
        return request_failed(code=2012, info="Not authorized.", status_code=403)
    if name is not None:
        conv.name = name
    if avatar is not None:
        conv.avatar = avatar
    conv.save()
    return request_success()

@csrf_exempt
def group_info(req: HttpRequest):
    """查询群聊信息：名称、头像、最新公告、成员列表与当前用户角色
    GET id: conv_id
    返回：{id, name, avatar, role, announcement, members: [{id, nickname, avatar}]}
    """
    if req.method != 'GET':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    conv_id = req.GET.get('id')
    conv = Conversation.objects.filter(id=conv_id, type='group').first()
    if not conv:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    me = Member.objects.filter(conversation=conv, user_id=user_id).first()
    if not me:
        return request_failed(code=3004, info="Member not found.", status_code=404)
    last_announce = conv.announcements.order_by('-created_at').first()
    members_qs = conv.members.select_related('user')
    members = [{
        'id': m.user_id,
        'nickname': m.nickname,
        'avatar': getattr(m.user, 'avatar', ''),
        'role': m.role,
        'is_active': m.user.is_active,
        'display_username': getattr(m.user, 'display_username', m.user.username),
    } for m in members_qs]
    active_members_count = sum(1 for m in members_qs if m.user.is_active)
    return request_success({
        'id': conv.id,
        'name': conv.name or '',
        'avatar': conv.avatar or '',
        'role': me.role,
        'announcement': (last_announce.content if last_announce else ''),
        'is_active': conv.is_active,
        'active_members_count': active_members_count,
        'members': members,
    })

@csrf_exempt
def set_group_nickname(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    conv_id = data.get('id')
    nickname = data.get('nickname')
    m = Member.objects.filter(conversation_id=conv_id, user_id=user_id).first()
    if not m:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    if not m.conversation.is_active:
        return request_failed(code=2012, info="Conversation is inactive.", status_code=403)
    m.nickname = nickname or m.nickname
    m.save()
    return request_success()

@csrf_exempt
def set_member_role(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    conv_id = data.get('id')
    target_id = data.get('user_id')
    role = data.get('role')  # admin/member
    conv = Conversation.objects.filter(id=conv_id, type='group').first()
    if not conv:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    if not conv.is_active:
        return request_failed(code=2012, info="Conversation is inactive.", status_code=403)
    actor_role = Member.objects.filter(conversation=conv, user_id=user_id).values_list('role', flat=True).first()
    if actor_role != 'owner':
        return request_failed(code=2012, info="Only owner can set admin.", status_code=403)
    target_member = Member.objects.filter(conversation=conv, user_id=target_id).first()
    if not target_member:
        return request_failed(code=3004, info="Target not in conversation.", status_code=404)
    if not target_member.user.is_active:
        return request_failed(code=2005, info="Cannot set role for deactivated user.", status_code=400)
    if role not in ['admin', 'member']:
        return request_failed(code=2001, info="Invalid role.", status_code=400)
    target_member.role = role
    target_member.save()
    member_ids = list(conv.members.values_list('user_id', flat=True))
    notify_conversation_event(member_ids, 'conversation_event', conv_id)
    return request_success()

@csrf_exempt
def transfer_owner(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    conv_id = data.get('id')
    to_user = data.get('to')
    conv = Conversation.objects.filter(id=conv_id, type='group').first()
    if not conv:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    if not conv.is_active:
        return request_failed(code=2012, info="Conversation is inactive.", status_code=403)
    cur = Member.objects.filter(conversation=conv, user_id=user_id).first()
    if not cur or cur.role != 'owner':
        return request_failed(code=2012, info="Only owner can transfer.", status_code=403)
    nxt = Member.objects.filter(conversation=conv, user_id=to_user).first()
    if not nxt:
        return request_failed(code=3004, info="Target not in conversation.", status_code=404)
    if not nxt.user.is_active:
        return request_failed(code=2005, info="Cannot transfer to deactivated user.", status_code=400)
    cur.role = 'member'
    nxt.role = 'owner'
    cur.save(); nxt.save()
    member_ids = list(conv.members.values_list('user_id', flat=True))
    notify_conversation_event(member_ids, 'conversation_event', conv_id)
    return request_success()

@csrf_exempt
def announce(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    conv_id = data.get('id')
    content = data.get('content')
    conv = Conversation.objects.filter(id=conv_id, type='group').first()
    if not conv:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    if not conv.is_active:
        return request_failed(code=2012, info="Conversation is inactive.", status_code=403)
    m = Member.objects.filter(conversation=conv, user_id=user_id).first()
    if not m or m.role not in ['owner', 'admin']:
        return request_failed(code=2012, info="Not authorized.", status_code=403)
    GroupAnnouncement.objects.create(conversation=conv, author=m, content=content)
    return request_success()

@csrf_exempt
def get_announcements(req: HttpRequest):
    """获取群聊历史公告
    GET id: conv_id
    GET limit: 可选，限制返回数量
    GET offset: 可选，分页偏移量
    返回：{announcements: [{id, content, author_id, author_name, author_nickname, created_at}]}
    """
    if req.method != 'GET':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    conv_id = req.GET.get('id')
    limit = req.GET.get('limit')
    offset = req.GET.get('offset')
    conv = Conversation.objects.filter(id=conv_id, type='group').first()
    if not conv:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    # 验证用户是否是群成员
    member = Member.objects.filter(conversation=conv, user_id=user_id).first()
    if not member:
        return request_failed(code=3004, info="Not a member of this group.", status_code=403)

    # 获取公告列表，按时间倒序排列
    announcements_qs = conv.announcements.select_related('author__user').order_by('-created_at')

    # 处理分页
    if offset:
        try:
            offset_val = int(offset)
            if offset_val > 0:
                announcements_qs = announcements_qs[offset_val:]
        except ValueError:
            pass

    if limit:
        try:
            limit_val = int(limit)
            if limit_val > 0:
                announcements_qs = announcements_qs[:limit_val]
        except ValueError:
            pass

    announcements = []
    for announce in announcements_qs:
        announcements.append({
            'id': announce.id,
            'content': announce.content,
            'author_id': announce.author.user.id if announce.author else None,
            'author_name': (announce.author.nickname or announce.author.user.username) if announce.author else '系统',
            'author_nickname': (announce.author.nickname or announce.author.user.username) if announce.author else '',
            'created_at': announce.created_at.isoformat(),
        })

    return request_success({
        'announcements': announcements
    })

@csrf_exempt
def remove_member(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    conv_id = data.get('id')
    target_id = data.get('user_id')
    conv = Conversation.objects.filter(id=conv_id, type='group').first()
    if not conv:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    actor = Member.objects.filter(conversation=conv, user_id=user_id).first()
    target = Member.objects.filter(conversation=conv, user_id=target_id).first()
    if not actor or not target:
        return request_failed(code=3004, info="Member not found.", status_code=404)

    # 权限检查：只有群主和管理员能移除成员
    if actor.role not in ['owner', 'admin']:
        return request_failed(code=2012, info="Not authorized to remove members.", status_code=403)

    # 管理员不能移除管理员或群主
    if actor.role == 'admin' and target.role in ['admin', 'owner']:
        return request_failed(code=2012, info="Admin cannot remove owner/admin.", status_code=403)

    # 群主不能移除自己
    if actor.role == 'owner' and target.role == 'owner':
        return request_failed(code=2012, info="Owner cannot remove self as owner.", status_code=403)

    target.delete()
    return request_success()

@csrf_exempt
def exit_group(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    conv_id = data.get('id')
    m = Member.objects.filter(conversation_id=conv_id, user_id=user_id).first()
    if not m:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    if m.role == 'owner':
        return request_failed(code=2012, info="Owner must transfer ownership before exit.", status_code=403)
    m.delete()
    return request_success()

@csrf_exempt
def disband_group(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    conv_id = data.get('id')
    conv = Conversation.objects.filter(id=conv_id, type='group').first()
    if not conv:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    member = Member.objects.filter(conversation=conv, user_id=user_id).first()
    if not member or member.role != 'owner':
        return request_failed(code=2012, info="Only owner can disband group.", status_code=403)

    # 只标记群聊不可用，保留消息和成员记录供查看历史
    with atomic():
        member_ids = list(conv.members.values_list('user_id', flat=True))
        conv.is_active = False
        conv.save(update_fields=["is_active"])
        # 失效所有未处理的群邀请，避免解散后仍能加入
        GroupInvitation.objects.filter(conversation=conv, status='pending').update(
            status='expired',
            review_time=timezone.now(),
            review_comment='Group disbanded'
        )

    notify_conversation_event(member_ids, 'group_disbanded', conv_id)
    return request_success()

@csrf_exempt
def mark_read(req: HttpRequest):
    """将会话消息标记为已读
    body: {conversation: id, up_to_id?: message_id}
    """
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    conv_id = data.get('conversation')
    up_to_id = data.get('up_to_id')
    member = Member.objects.filter(conversation_id=conv_id, user_id=user_id).first()  # 这里原本是user_id=user.id
    if not member:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    qs = Message.objects.filter(conversation_id=conv_id, valid=True).exclude(delete_list=member)
    if up_to_id:
        qs = qs.filter(id__lte=up_to_id)
    # 批量添加到已读列表，提高性能
    messages_to_mark = list(qs)
    for msg in messages_to_mark:
        msg.read_list.add(member)
    logger.info(f"(mark_read) marked {len(messages_to_mark)} messages as read for user={user_id} conv={conv_id} up_to={up_to_id}")
    return request_success()

@csrf_exempt
def edit_message(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    msg_id = data.get('id')
    content = data.get('content')
    msg = Message.objects.filter(id=msg_id).select_related('member__user', 'conversation').first()
    if not msg:
        return request_failed(code=4001, info="Message not found.", status_code=404)
    if not msg.member.user.is_active:
        return request_failed(code=2013, info="User account is deactivated.", status_code=403)
    if not msg.conversation.is_active:
        return request_failed(code=2012, info="Conversation is inactive.", status_code=403)
    if msg.member.user_id != user_id:
        return request_failed(code=2012, info="Not allowed.", status_code=403)
    msg.content = content or msg.content
    msg.is_edited = True
    msg.save()
    return request_success()

@csrf_exempt
def recall_message(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    msg_id = data.get('id')
    msg = Message.objects.filter(id=msg_id).select_related('member__user', 'conversation').first()
    if not msg:
        return request_failed(code=4001, info="Message not found.", status_code=404)
    if not msg.member.user.is_active:
        return request_failed(code=2013, info="User account is deactivated.", status_code=403)
    if not msg.conversation.is_active:
        return request_failed(code=2012, info="Conversation is inactive.", status_code=403)
    if msg.member.user_id != user_id:
        return request_failed(code=2012, info="Not allowed.", status_code=403)
    msg.valid = False
    # 获取用户名来显示撤回提示
    username = msg.member.user.username
    msg.content = f"{username}撤回了一条消息"
    msg.save()
    return request_success()

@csrf_exempt
def delete_message(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    data = load_body(req) or {}
    msg_id = data.get('id')
    msg = Message.objects.filter(id=msg_id).select_related('conversation').first()
    if not msg:
        return request_failed(code=4001, info="Message not found.", status_code=404)
    member = Member.objects.filter(conversation=msg.conversation, user_id=user_id).first()
    if not member:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    msg.delete_list.add(member)
    return request_success()

@csrf_exempt
def set_mute_pin(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    data = load_body(req) or {}
    conv_id = data.get('id')
    mute = data.get('mute')
    pinned = data.get('pinned')
    m = Member.objects.filter(conversation_id=conv_id, user_id=user_id).first()
    if not m:
        return request_failed(code=3003, info="Conversation not found.", status_code=404)
    if mute is not None:
        m.mute = bool(mute)
    if pinned is not None:
        m.pinned = bool(pinned)
    m.save()
    return request_success()

@csrf_exempt
def upload(req: HttpRequest):
    """简单的文件上传接口，返回可访问URL
    form-data: file, type(optional): image/file
    """
    if req.method != 'POST':
        return BAD_METHOD
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp
    f = req.FILES.get('file')
    if not f:
        return request_failed(code=2001, info='No file uploaded.', status_code=400)
    # 存储到 media/uploads/
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    # 使用时间戳+UUID重命名以防止同名覆盖与枚举
    original_name = Path(f.name).name
    ext = Path(original_name).suffix
    unique_stem = f"{timezone.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex}"
    safe_name = f"{unique_stem}{ext}"
    filename = default_storage.save(os.path.join('uploads', safe_name), ContentFile(f.read()))
    url = settings.MEDIA_URL + filename
    return request_success({'url': url})

@csrf_exempt
def home(req: HttpRequest):
    """
    用户登录完成后返回主界面显示需要的信息
    """
    if req.method != 'GET':
        return BAD_METHOD

    # ---- JWT 解析 ----
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=5001, info="Invalid JWT Token.", status_code=403)

    # ---- 获取用户 ----
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp

    # ---- 获取该用户参与的会话 ----
    members = Member.objects.filter(user=user).select_related('conversation')
    if not members.exists():
        return request_success({"conversations": []})

    # 获取用户的置顶会话列表，用于后续排序
    pinned_conversations = PinnedConversation.objects.filter(
        user=user
    ).order_by('pin_order')
    pinned_conv_dict = {pc.conversation_id: pc.pin_order for pc in pinned_conversations}

    conversations_list = []

    for member in members:
        conv = member.conversation
        if not conv.is_active:
            continue

        # ---- 会话成员 ----
        members_qs = conv.members.select_related('user')
        members_data = [
            {
                "id": m.user.id,
                "nickname": m.nickname,
                "display_username": getattr(m.user, 'display_username', m.user.username),
                "avatar": getattr(m.user, "avatar", ""),
                "is_active": m.user.is_active,
                "is_online": is_online(m.user.id)
            }
            for m in members_qs
        ]

        # ---- 消息（排除删除的） ----
        msgs_qs = (
            Message.objects.filter(conversation=conv)
            .exclude(delete_list=member)
            .order_by('-time')[:100]
            .prefetch_related('read_list', 'delete_list', 'member__user', 'reply_to__member__user')
        )

        msgs_data = []
        for msg in reversed(msgs_qs):
            # 构建回复消息信息
            reply_to_message = None
            if msg.reply_to_id and msg.reply_to.valid:
                reply_to_message = {
                    'id': msg.reply_to.id,
                    'sender': msg.reply_to.member.user.id,
                    'sender_username': getattr(msg.reply_to.member.user, 'display_username', msg.reply_to.member.user.username),
                    'nickname': msg.reply_to.member.nickname,
                    'text': msg.reply_to.content,
                    'type': msg.reply_to.type,
                }

            msgs_data.append({
                "id": msg.id,
                "sender": msg.member.user.id,
                "sender_username": getattr(msg.member.user, 'display_username', msg.member.user.username),
                "nickname": getattr(msg.member.user, 'display_username', msg.member.user.username),  # 保持向后兼容
                "sender_nickname": msg.member.nickname,  # 群昵称
                "sender_is_active": msg.member.user.is_active,
                "content": msg.content,
                "content_preview": _format_message_preview(msg),
                "type": msg.type,
                "reply_to": msg.reply_to_id,
                "reply_to_message": reply_to_message,
                "time": msg.time.isoformat(),
                "is_edited": msg.is_edited,
                "valid": msg.valid,
                # 返回用户ID列表，便于前端直接映射到昵称
                "read_list": [m.user_id for m in msg.read_list.all()],
                "is_deleted": member in msg.delete_list.all(),
                "is_read": member in msg.read_list.all(),
            })

        # ---- 未读消息统计 ----
        unread_count = (
            Message.objects.filter(conversation=conv, valid=True)
            .exclude(delete_list=member)
            .exclude(read_list=member)
            .count()
        )

        # ---- 会话显示名 ----
        display_name = conv.name or ""
        if not display_name and conv.type == 'private':
            # 私聊：展示对方昵称
            other = next((m for m in members_qs if m.user_id != user.id), None)
            if other:
                display_name = other.nickname or getattr(other.user, 'display_username', other.user.username) or ''

        # ---- 会话头像 ----
        display_avatar = conv.avatar or ""
        if not display_avatar and conv.type == 'private':
            other2 = next((m for m in members_qs if m.user_id != user.id), None)
            if other2:
                display_avatar = getattr(other2.user, 'avatar', '') or ''

        # 获取置顶顺序，如果未置顶则为0
        pin_order = pinned_conv_dict.get(conv.id, 0)

        last_message_preview = _format_message_preview(msgs_qs[0]) if msgs_qs else ""

        conversations_list.append({
            "id": conv.id,
            "type": conv.type,
            "is_group": conv.type == 'group',
            "name": display_name,
            "avatar": display_avatar,
            "unread_count": unread_count,
            "muted": member.mute,
            "pinned": member.pinned,
            "pin_order": pin_order,  # 添加置顶顺序
            "members": members_data,
            "messages": msgs_data,
            "is_active": conv.is_active,
            "last_message_preview": last_message_preview,
        })

    # 按置顶状态排序：置顶的会话在前，并按pin_order排序；非置顶的会话在后
    conversations_list.sort(key=lambda x: (not x["pinned"], x["pin_order"]))

    return request_success({"conversations": conversations_list})

@csrf_exempt
def pin_conversation(req: HttpRequest):
    """置顶会话
    body: {id: conversation_id}
    """
    if req.method != 'POST':
        return BAD_METHOD

    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp

    data = load_body(req) or {}
    conv_id = data.get('id')

    if not conv_id:
        return request_failed(code=2001, info="Missing conversation ID.", status_code=400)

    # 检查会话是否存在且用户是成员
    member = Member.objects.filter(conversation_id=conv_id, user_id=user_id).first()
    if not member:
        return request_failed(code=3003, info="Conversation not found or user not a member.", status_code=404)
    conv = Conversation.objects.get(id=conv_id)

    # 检查是否已经置顶
    existing_pin = PinnedConversation.objects.filter(user=user, conversation=conv).first()
    if existing_pin:
        return request_failed(code=3005, info="Conversation already pinned.", status_code=400)

    # 获取当前最大的置顶顺序
    max_order = PinnedConversation.objects.filter(user=user).aggregate(
        max_order=Max('pin_order')
    )['max_order'] or 0

    # 创建置顶记录
    with atomic():
        PinnedConversation.objects.create(
            user=user,
            conversation=conv,
            pin_order=max_order + 1
        )

        # 同时更新Member表中的pinned字段，保持兼容性
        member.pinned = True
        member.save()

    logger.info(f"(pin_conversation) user={user_id} pinned conversation={conv_id}")
    return request_success()

@csrf_exempt
def unpin_conversation(req: HttpRequest):
    """取消置顶会话
    body: {id: conversation_id}
    """
    if req.method != 'POST':
        return BAD_METHOD

    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp

    data = load_body(req) or {}
    conv_id = data.get('id')

    if not conv_id:
        return request_failed(code=2001, info="Missing conversation ID.", status_code=400)

    # 检查会话是否存在且用户是成员
    member = Member.objects.filter(conversation_id=conv_id, user_id=user_id).first()
    if not member:
        return request_failed(code=3003, info="Conversation not found or user not a member.", status_code=404)
    conv = Conversation.objects.get(id=conv_id)

    # 删除置顶记录
    with atomic():
        # 获取要删除的置顶记录的顺序
        pinned_conv = PinnedConversation.objects.filter(user=user, conversation=conv).first()
        if not pinned_conv:
            return request_failed(code=3006, info="Conversation not pinned.", status_code=400)

        removed_order = pinned_conv.pin_order
        pinned_conv.delete()

        # 更新其他置顶会话的顺序，确保连续
        PinnedConversation.objects.filter(
            user=user,
            pin_order__gt=removed_order
        ).update(pin_order=F('pin_order') - 1)

        # 同时更新Member表中的pinned字段，保持兼容性
        member.pinned = False
        member.save()

    logger.info(f"(unpin_conversation) user={user_id} unpinned conversation={conv_id}")
    return request_success()

@csrf_exempt
def get_pinned_conversations(req: HttpRequest):
    """获取用户的置顶会话列表
    返回：{pinned: [conversation_id]}
    """
    if req.method != 'GET':
        return BAD_METHOD

    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)
    user, err_resp = _get_active_user(user_id)
    if err_resp:
        return err_resp

    # 获取置顶会话列表，按置顶顺序排序
    pinned_convs = PinnedConversation.objects.filter(
        user=user
    ).order_by('pin_order').values_list('conversation_id', flat=True)

    pinned_list = list(pinned_convs)

    logger.info(f"(get_pinned_conversations) user={user_id} pinned_count={len(pinned_list)}")
    return request_success(data={"pinned": pinned_list})

# 群成员邀请功能相关API
@csrf_exempt
def invite_to_group(req: HttpRequest):
    """邀请好友加入群聊
    body: {group_id: int, friend_id: int, message?: str}
    返回: {id: invitation_id}
    """
    if req.method != 'POST':
        return BAD_METHOD

    # 身份验证
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)

    # 解析请求体
    data = load_body(req) or {}
    group_id = data.get('group_id')
    friend_id = data.get('friend_id')
    message = data.get('message', '')

    if not group_id or not friend_id:
        return request_failed(code=2001, info="Missing group_id or friend_id.", status_code=400)

    User = get_user_model()

    # 检查用户是否存在
    inviter = User.objects.filter(id=user_id).first()
    if not inviter:
        return request_failed(code=9001, info="User not found.", status_code=404)

    # 检查好友是否存在
    invitee = User.objects.filter(id=friend_id).first()
    if not invitee:
        return request_failed(code=2004, info="Friend not found.", status_code=404)

    # 检查群聊是否存在
    conversation = Conversation.objects.filter(id=group_id, type='group').first()
    if not conversation:
        return request_failed(code=3003, info="Group not found.", status_code=404)
    if not conversation.is_active:
        return request_failed(code=2012, info="Conversation is inactive.", status_code=403)

    # 检查邀请者是否是群成员
    inviter_member = Member.objects.filter(conversation=conversation, user=inviter).first()
    if not inviter_member:
        return request_failed(code=3004, info="You are not a member of this group.", status_code=403)

    # 检查被邀请者是否已经是群成员
    if Member.objects.filter(conversation=conversation, user=invitee).exists():
        return request_failed(code=3005, info="User is already a member of this group.", status_code=400)

    # 检查是否已经是好友
    friendship = Friendship.objects.filter(
        Q(user_a=inviter, user_b=invitee) | Q(user_a=invitee, user_b=inviter)
    ).first()
    if not friendship:
        return request_failed(code=3006, info="You can only invite your friends.", status_code=403)

    # 检查是否已经有邀请记录（任何状态）
    existing_invitation = GroupInvitation.objects.filter(
        conversation=conversation,
        invitee=invitee
    ).first()

    if existing_invitation:
        # 如果已有待处理的邀请，则返回错误
        if existing_invitation.status == 'pending':
            return request_failed(code=3007, info="There is already a pending invitation for this user.", status_code=400)
        # 如果已有非待处理的邀请（已拒绝/已通过/已过期），则直接覆盖现有记录
        else:
            invitation = existing_invitation
            invitation.inviter = inviter  # 更新邀请者，可能是不同的人邀请
            invitation.message = message  # 更新邀请消息
            invitation.status = 'pending'  # 重置为待处理
            invitation.reviewer = None  # 清除审核信息
            invitation.review_time = None
            invitation.review_comment = ''
            invitation.save()
    else:
        # 创建新的邀请记录
        invitation = GroupInvitation.objects.create(
            conversation=conversation,
            inviter=inviter,
            invitee=invitee,
            message=message
        )

    logger.info(f"(invite_to_group) user={user_id} invited friend={friend_id} to group={group_id}")

    # 通知群主和管理员有新的邀请待审核
    admin_members = Member.objects.filter(
        conversation=conversation,
        role__in=['owner', 'admin']
    ).exclude(user=inviter)  # 排除邀请者自己

    admin_ids = [m.user_id for m in admin_members]
    if admin_ids:
        notify_conversation_event(admin_ids, 'group_invitation_pending', group_id)

    return request_success({'id': invitation.id})

@csrf_exempt
def list_group_invitations(req: HttpRequest):
    """获取群聊的邀请列表
    GET group_id: 群聊ID
    GET status: 可选，过滤状态 (pending/approved/rejected/expired)
    返回: {invitations: [{id, inviter_id, inviter_name, inviter_nickname, invitee_id, invitee_name, invitee_nickname, status, created_at, message, reviewer_id, reviewer_name, reviewer_nickname, review_time, review_comment}]}
    """
    if req.method != 'GET':
        return BAD_METHOD

    # 身份验证
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)

    # 获取参数
    group_id = req.GET.get('group_id')
    status = req.GET.get('status')

    if not group_id:
        return request_failed(code=2001, info="Missing group_id.", status_code=400)

    # 检查群聊是否存在
    conversation = Conversation.objects.filter(id=group_id, type='group').first()
    if not conversation:
        return request_failed(code=3003, info="Group not found.", status_code=404)

    # 检查用户是否是群成员
    member = Member.objects.filter(conversation=conversation, user_id=user_id).first()
    if not member:
        return request_failed(code=3004, info="You are not a member of this group.", status_code=403)

    # 只有群主和管理员可以查看邀请列表
    if member.role not in ['owner', 'admin']:
        return request_failed(code=3008, info="Only owner and admin can view invitations.", status_code=403)

    # 查询邀请列表
    invitations_qs = GroupInvitation.objects.filter(conversation=conversation)
    if status:
        invitations_qs = invitations_qs.filter(status=status)

    # 按创建时间倒序排列
    invitations_qs = invitations_qs.order_by('-created_at')

    invitations = []
    for inv in invitations_qs:
        reviewer_name = ''
        reviewer_nickname = ''
        if inv.reviewer:
            # 获取审核人在群中的昵称
            reviewer_member = Member.objects.filter(conversation=conversation, user=inv.reviewer).first()
            reviewer_nickname = reviewer_member.nickname if reviewer_member else ''
            reviewer_name = reviewer_nickname or inv.reviewer.username

        # 获取邀请人在群中的昵称
        inviter_member = Member.objects.filter(conversation=conversation, user=inv.inviter).first()
        inviter_nickname = inviter_member.nickname if inviter_member else ''
        inviter_name = inviter_nickname or inv.inviter.username

        # 获取被邀请人在群中的昵称（如果已加入群）
        invitee_member = Member.objects.filter(conversation=conversation, user=inv.invitee).first()
        invitee_nickname = invitee_member.nickname if invitee_member else ''
        invitee_name = invitee_nickname or inv.invitee.username

        invitations.append({
            'id': inv.id,
            'inviter_id': inv.inviter.id,
            'inviter_name': inviter_name,
            'inviter_nickname': inviter_nickname,
            'invitee_id': inv.invitee.id,
            'invitee_name': invitee_name,
            'invitee_nickname': invitee_nickname,
            'status': inv.status,
            'created_at': inv.created_at.isoformat(),
            'message': inv.message,
            'reviewer_id': inv.reviewer.id if inv.reviewer else None,
            'reviewer_name': reviewer_name,
            'reviewer_nickname': reviewer_nickname,
            'review_time': inv.review_time.isoformat() if inv.review_time else None,
            'review_comment': inv.review_comment,
        })

    return request_success({'invitations': invitations})

@csrf_exempt
def review_group_invitation(req: HttpRequest):
    """审核群聊邀请
    body: {invitation_id: int, action: str, comment?: str}
    action: "approve" 或 "reject"
    返回: {}
    """
    if req.method != 'POST':
        return BAD_METHOD

    # 身份验证
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)

    # 解析请求体
    data = load_body(req) or {}
    invitation_id = data.get('invitation_id')
    action = data.get('action')
    comment = data.get('comment', '')

    if not invitation_id or not action:
        return request_failed(code=2001, info="Missing invitation_id or action.", status_code=400)

    if action not in ['approve', 'reject']:
        return request_failed(code=2001, info="Invalid action. Must be 'approve' or 'reject'.", status_code=400)

    User = get_user_model()
    reviewer = User.objects.filter(id=user_id).first()
    if not reviewer:
        return request_failed(code=9001, info="User not found.", status_code=404)

    # 查找邀请记录
    invitation = GroupInvitation.objects.filter(id=invitation_id).first()
    if not invitation:
        return request_failed(code=3009, info="Invitation not found.", status_code=404)
    if not invitation.conversation.is_active:
        return request_failed(code=2012, info="Conversation is inactive.", status_code=403)

    # 检查邀请状态是否为待处理
    if invitation.status != 'pending':
        return request_failed(code=3010, info="Invitation has already been processed.", status_code=400)

    # 检查审核者是否是群主或管理员
    reviewer_member = Member.objects.filter(
        conversation=invitation.conversation,
        user=reviewer,
        role__in=['owner', 'admin']
    ).first()
    if not reviewer_member:
        return request_failed(code=3008, info="Only owner and admin can review invitations.", status_code=403)

    # 更新邀请状态
    with atomic():
        if action == 'approve':
            invitation.status = 'approved'
            # 将被邀请者添加到群聊中
            Member.objects.create(
                conversation=invitation.conversation,
                user=invitation.invitee,
                nickname=invitation.invitee.username,
                role='member',
                time=timezone.now()
            )

            # 通知被邀请者已加入群聊
            notify_conversation_event([invitation.invitee.id], 'conversation_created', invitation.conversation.id)

            # 通知群成员有新成员加入
            member_ids = list(invitation.conversation.members.values_list('user_id', flat=True))
            notify_conversation_event(member_ids, 'group_member_joined', invitation.conversation.id)

        else:  # reject
            invitation.status = 'rejected'

        invitation.reviewer = reviewer
        invitation.review_time = timezone.now()
        invitation.review_comment = comment
        invitation.save()

    logger.info(f"(review_group_invitation) user={user_id} {action}d invitation={invitation_id}")

    return request_success()

@csrf_exempt
def get_user_invitations(req: HttpRequest):
    """获取用户收到的群聊邀请列表
    GET status: 可选，过滤状态 (pending/approved/rejected/expired)
    返回: {invitations: [{id, group_id, group_name, inviter_id, inviter_name, status, created_at, message}]}
    """
    if req.method != 'GET':
        return BAD_METHOD

    # 身份验证
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=3002, info="Invalid JWT Token.", status_code=403)

    # 获取参数
    status = req.GET.get('status')

    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    if not user:
        return request_failed(code=9001, info="User not found.", status_code=404)

    # 查询用户收到的邀请列表
    invitations_qs = GroupInvitation.objects.filter(invitee=user, conversation__is_active=True)
    if status:
        invitations_qs = invitations_qs.filter(status=status)

    # 按创建时间倒序排列
    invitations_qs = invitations_qs.order_by('-created_at')

    invitations = []
    for inv in invitations_qs:
        inviter_member = Member.objects.filter(conversation=inv.conversation, user=inv.inviter).first()
        inviter_nickname = inviter_member.nickname if inviter_member else ''
        reviewer_name = None
        reviewer_nickname = None
        if inv.reviewer:
            reviewer_member = Member.objects.filter(conversation=inv.conversation, user=inv.reviewer).first()
            reviewer_nickname = reviewer_member.nickname if reviewer_member else ''
            reviewer_name = reviewer_nickname or inv.reviewer.username

        invitations.append({
            'id': inv.id,
            'group_id': inv.conversation.id,
            'group_name': inv.conversation.name or f"群聊 {inv.conversation.id}",
            'inviter_id': inv.inviter.id,
            'inviter_name': inviter_nickname or inv.inviter.username,
            'inviter_nickname': inviter_nickname,
            'reviewer_id': inv.reviewer.id if inv.reviewer else None,
            'reviewer_name': reviewer_name,
            'reviewer_nickname': reviewer_nickname,
            'status': inv.status,
            'created_at': inv.created_at.isoformat(),
            'message': inv.message,
        })

    return request_success({'invitations': invitations})
