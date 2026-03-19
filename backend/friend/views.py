from django.http import HttpRequest
from django.shortcuts import render
from utils.network import BAD_METHOD, request_failed, request_success
from utils.tools import get_jwt_token
from utils.jwt import parse_jwt_token
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db import transaction, IntegrityError
from django.utils import timezone
from chat.models import Conversation, Member
from .models import Friendship, Pending, FriendGroup
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json


def _notify_conversation_event(user_ids, event_name, conversation_id):
    """向相关用户广播会话事件，提示前端刷新。"""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    safe_ids = {uid for uid in user_ids if uid}
    if not safe_ids:
        return
    payload = {
        'type': 'conversation_event',
        'event': event_name,
        'conversation': conversation_id,
    }
    for uid in safe_ids:
        async_to_sync(channel_layer.group_send)(f'user_{uid}', payload)


def _ensure_private_conversation(user_a, user_b):
    """Ensure a private conversation exists (or is reactivated) between two friends."""
    conv = (Conversation.objects
            .filter(type="private", members__user=user_a)
            .filter(members__user=user_b)
            .first())
    created = False

    if conv:
        # Reactivate an existing conversation or missing memberships if they were soft-deleted.
        if not conv.is_active:
            conv.is_active = True
            conv.save(update_fields=["is_active"])
        for u in (user_a, user_b):
            member = Member.all_objects.filter(conversation=conv, user=u).first()
            if not member:
                Member.objects.create(
                    conversation=conv,
                    user=u,
                    nickname=u.username,
                    role="member",
                    time=timezone.now(),
                )
                created = True
            elif not member.is_active:
                member.is_active = True
                member.save(update_fields=["is_active"])
                created = True
        return conv, created

    current_time = timezone.now()
    try:
        with transaction.atomic():
            conv = Conversation.objects.create(name="", type="private")
            Member.objects.create(
                conversation=conv,
                user=user_a,
                nickname=user_a.username,
                role="member",
                time=current_time,
            )
            Member.objects.create(
                conversation=conv,
                user=user_b,
                nickname=user_b.username,
                role="member",
                time=current_time,
            )
            created = True
    except IntegrityError:
        # If another process created it concurrently, try to fetch again.
        conv = (Conversation.objects
                .filter(type="private", members__user=user_a)
                .filter(members__user=user_b)
                .first())

    return conv, created

@csrf_exempt  # 调试阶段禁用csrf
def befriend(req: HttpRequest, id:int):
    if req.method != "POST":
        return BAD_METHOD
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    if not user_id:
        return request_failed(
            code=4001,
            info="Invalid JWT Token",
            status_code=400
        )
    # 不能自己befriend自己
    if id == user_id:
        return request_failed(
            code=4006,
            info="Cannot befriend oneself.",
            status_code=400
        )
    # 检查两个用户是否都存在
    User = get_user_model()
    user_from = User.objects.filter(id=user_id).first()
    if not user_from:
        return request_failed(
            code=9001,
            info="User not found.",
            status_code=500
        )
    user_to = User.objects.filter(id=id).first()
    if not user_to:
        return request_failed(
            code=4003,
            info="User does not exist.",
            status_code=404
        )
    
    # 检查目标用户是否已注销
    if not user_to.is_active:
        return request_failed(
            code=4009,
            info="Cannot befriend a deactivated user.",
            status_code=400
        )
    # 检查是否已经是好友
    friendship_exists = Friendship.objects.filter(
        Q(user_a=user_from, user_b=user_to) | Q(user_a=user_to, user_b=user_from)
    ).exists()
    print(f"<Info> (befriend) friendship_exists={friendship_exists}")
    if friendship_exists:
        return request_failed(
            code=4002,
            info="Users are already friends.",
            status_code=400
        )
    # 检查是否已经发送了好友申请，对方尚未同意
    invited_exists = Pending.objects.filter(user_from=user_from, user_to=user_to).exists()
    print(f"<Info> (befriend) invited_exists={invited_exists}")
    if invited_exists:
        return request_failed(
            code=4004,
            info="Pending invitation already exists.",
            status_code=400
        )
    # 检查是否是: A已经给B发送了申请，现在B又给A发送申请
    rev_invited_exists = Pending.objects.filter(user_from=user_to, user_to=user_from).exists()
    print(f"<Info> (befriend) rev_invited_exists={rev_invited_exists}")
    if rev_invited_exists:
        # 对方已经邀请过我，直接在事务中创建 friendship 并删除双方 pending
        conv = None
        try:
            with transaction.atomic():
                friendship = Friendship(user_a=user_from, user_b=user_to)
                friendship.save()
                Pending.objects.filter(
                    Q(user_from=user_to, user_to=user_from) | Q(user_from=user_from, user_to=user_to)
                ).delete()
                conv, created = _ensure_private_conversation(user_from, user_to)
                # 如果会话是新创建的，通知双方用户
                if created and conv:
                    _notify_conversation_event([user_from.id, user_to.id], 'conversation_created', conv.id)
        except IntegrityError:
            # 可能并发创建 friendship，仍要删除 pending
            Pending.objects.filter(
                Q(user_from=user_to, user_to=user_from) | Q(user_from=user_from, user_to=user_to)
            ).delete()
            conv, created = _ensure_private_conversation(user_from, user_to)
            # 如果会话是新创建的，通知双方用户
            if created and conv:
                _notify_conversation_event([user_from.id, user_to.id], 'conversation_created', conv.id)
        return request_success(data={"conversation_id": conv.id if conv else None})
    # 创建Pending
    try:
        Pending.objects.create(user_from=user_from, user_to=user_to)
        print(f"<Info> (befriend) created pending from={user_from.id} to={user_to.id}")
    except IntegrityError:
        print(f"<Info> (befriend) failed to create pending from={user_from.id} to={user_to.id}")
        return request_failed(code=5001, info="Failed to create pending.", status_code=500)
    return request_success()

@csrf_exempt  # 调试阶段禁用csrf
def search(req: HttpRequest, username: str):
    if req.method != "GET":
        return BAD_METHOD
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    if not user_id:
        return request_failed(
            code=4001,
            info="Invalid JWT Token",
            status_code=400
        )
    # 搜索目标用户: 精确检索 & 模糊检索
    User = get_user_model()
    fuzzy = []
    exact = []
    if not username:
        return request_success(data={"fuzzy": fuzzy, "exact": exact})
    
    # 可以考虑加上一个数量限制
    # 仅返回活跃用户，避免在建群或加好友时出现已注销账号
    exact_qs = User.objects.filter(username=username, is_active=True).values_list('id', flat=True)
    fuzzy_qs = User.objects.filter(username__icontains=username, is_active=True).exclude(id__in=list(exact_qs))

    exact_count = exact_qs.count()
    fuzzy_count = fuzzy_qs.count()
    print(f"<Info> (search) exact_count={exact_count} fuzzy_count={fuzzy_count}")

    data = {
        "fuzzy": list(fuzzy_qs.values_list('id', flat=True)),
        "exact": list(exact_qs),
    }
    return request_success(data=data)

@csrf_exempt  # 调试阶段禁用csrf
def agree(req: HttpRequest, id: int):
    if req.method != "POST":
        return BAD_METHOD
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    if not user_id:
        return request_failed(
            code=4001,
            info="Invalid JWT Token",
            status_code=400
        )
    # 检查两个用户是否都存在
    User = get_user_model()
    user_from = User.objects.filter(id=id).first()
    if not user_from:
        return request_failed(
            code=4003,
            info="User does not exist.",
            status_code=404
        )
    user_to = User.objects.filter(id=user_id).first()
    if not user_to:
        return request_failed(
            code=9001,
            info="User not found.",
            status_code=500
        )
    # 检查用户是否已注销
    if not user_from.is_active or not user_to.is_active:
        return request_failed(
            code=4010,
            info="Cannot establish friendship with deactivated users.",
            status_code=400
        )
    
    # 检查是否确实有Pending invitation
    pending_exists = Pending.objects.filter(user_from=user_from, user_to=user_to).exists()
    print(f"<Info> (agree) pending_exists={pending_exists}")
    if not pending_exists:
        return request_failed(
            code=4005,
            info="Pending invitation does not exist.",
            status_code=400
        )
    # 添加好友并删除Pending
    try:
        with transaction.atomic():
            friendship = Friendship(user_a=user_from, user_b=user_to)
            friendship.save()  # 必须显式调用save来规范顺序
            Pending.objects.filter(Q(user_from=user_from, user_to=user_to)|Q(user_from=user_to, user_to=user_from)).delete()
            conv, created = _ensure_private_conversation(user_from, user_to)
            # 如果会话是新创建的，通知双方用户
            if created and conv:
                _notify_conversation_event([user_from.id, user_to.id], 'conversation_created', conv.id)
    except IntegrityError:
        # 如果已经存在（并发创建），仍应删除 pending 并返回成功/已存在
        Pending.objects.filter(Q(user_from=user_from, user_to=user_to)|Q(user_from=user_to, user_to=user_from)).delete()
        print(f"<Info> (agree) integrity error when creating friendship for {user_from.id} & {user_to.id}")
        return request_failed(code=4002, info="Users are already friends.", status_code=400)
    return request_success(data={"conversation_id": conv.id if conv else None})

@csrf_exempt  # 调试阶段禁用csrf
def disagree(req: HttpRequest, id: int):
    if req.method != "POST":
        return BAD_METHOD
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    if not user_id:
        return request_failed(
            code=4001,
            info="Invalid JWT Token",
            status_code=400
        )
    # 检查两个用户是否都存在
    User = get_user_model()
    user_from = User.objects.filter(id=id).first()
    if not user_from:
        return request_failed(
            code=4003,
            info="User does not exist.",
            status_code=404
        )
    user_to = User.objects.filter(id=user_id).first()
    if not user_to:
        return request_failed(
            code=9001,
            info="User not found.",
            status_code=500
        )
    
    # 检查用户是否已注销
    if not user_from.is_active or not user_to.is_active:
        return request_failed(
            code=4012,
            info="Cannot handle friend request with deactivated users.",
            status_code=400
        )
    # 检查是否确实有Pending invitation
    pending_exists = Pending.objects.filter(user_from=user_from, user_to=user_to).exists()
    print(f"<Info> (disagree) pending_exists={pending_exists}")
    if not pending_exists:
        return request_failed(
            code=4005,
            info="Pending invitation does not exist.",
            status_code=400
        )
    # 删除Pending
    Pending.objects.filter(user_from=user_from, user_to=user_to).delete()
    return request_success()

@csrf_exempt  # 调试阶段禁用csrf
def delete_friend(req: HttpRequest, id: int):
    if req.method != "POST":
        return BAD_METHOD
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    if not user_id:
        return request_failed(
            code=4001,
            info="Invalid JWT Token",
            status_code=400
        )
    # 检查两个用户是否都存在
    User = get_user_model()
    user_a = User.objects.filter(id=user_id).first()
    if not user_a:
        return request_failed(
            code=9001,
            info="User not found.",
            status_code=500
        )
    user_b = User.objects.filter(id=id).first()
    if not user_b:
        return request_failed(
            code=4003,
            info="User does not exist.",
            status_code=404
        )
    
    # 检查用户是否已注销
    if not user_a.is_active or not user_b.is_active:
        return request_failed(
            code=4013,
            info="Cannot delete friendship with deactivated users.",
            status_code=400
        )
    # 删除好友关系
    deleted, _ = Friendship.objects.filter(
        Q(user_a=user_a, user_b=user_b) | Q(user_a=user_b, user_b=user_a)
    ).delete()
    if deleted == 0:
        return request_failed(
            code=4007,
            info="Friendship does not exist.",
            status_code=400
        )
    # 友情关系已删除：同时把对方从双方的好友分组中移除，避免出现已删除好友仍在分组里的情况
    try:
        # 从 user_a 的所有分组中移除 user_b
        for fg in FriendGroup.objects.filter(user=user_a, friends__id=user_b.id):
            fg.friends.remove(user_b)
        # 从 user_b 的所有分组中移除 user_a
        for fg in FriendGroup.objects.filter(user=user_b, friends__id=user_a.id):
            fg.friends.remove(user_a)
    except Exception as e:
        # 移除分组成员失败不影响删除好友的主流程，但记录错误
        print(f"<Warning> failed to cleanup FriendGroup entries after deleting friendship: {e}")

    return request_success()
    
@csrf_exempt  # 调试阶段禁用csrf
def list_friends(req: HttpRequest):
    if req.method != "GET":
        return BAD_METHOD
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    if not user_id:
        return request_failed(
            code=4001,
            info="Invalid JWT Token",
            status_code=400
        )
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    friends = Friendship.objects.filter(
        Q(user_a=user) | Q(user_b=user)
    )
    friend_ids = [
        f.user_b.id if f.user_a == user else f.user_a.id
        for f in friends
    ]
    pendings = Pending.objects.filter(user_to=user)
    pending_ids = [
        p.user_from.id for p in pendings
    ]
    print(f"<Info> (list_friends) friends_count={friends.count()} pending_count={pendings.count()}")
    return request_success({
        "friends": friend_ids,
        "pending": pending_ids
    })


@csrf_exempt
def create_friend_group(req: HttpRequest):
    """创建好友分组 for current user
    body: {name: str}
    返回: {id: group_id}
    """
    if req.method != 'POST':
        return BAD_METHOD
    
    # 提取 JWT Token 并解析
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
     
    # 校验 JWT Token 是否有效
    if not user_id:
        return request_failed(code=4001, info='Invalid JWT Token.', status_code=403)
    
    # 查询用户是否存在
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    if not user:
        return request_failed(code=9001, info='User not found.', status_code=404)

    # 解析请求体
    try:
        body = json.loads(req.body.decode('utf-8') or '{}')
    except Exception:
        body = {}

    # 检查组名是否为空
    name = body.get('name')
    if not name:
        return request_failed(code=4010, info='Group name cannot be empty.', status_code=400)

    # 查询同名分组是否已存在
    existing_group = FriendGroup.objects.filter(user=user, name=name).first()
    if existing_group:
        return request_failed(code=4011, info='Group name already exists.', status_code=400)

    # 创建新分组
    fg = FriendGroup.objects.create(name=name, user=user)

    return request_success({'id': fg.id})

@csrf_exempt
def list_groups(req: HttpRequest):
    """返回当前用户的好友分组及其成员(返回成员为 user_id 列表)
    GET /friend/group/list
    """
    if req.method != 'GET':
        return BAD_METHOD
    
    # 提取 JWT Token 并解析
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    
    # 校验 JWT Token 是否有效
    if not user_id:
        return request_failed(code=4001, info='Invalid JWT Token.', status_code=403)
    
    # 查询用户是否存在
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    if not user:
        return request_failed(code=9001, info='User not found.', status_code=404)

    # 查询用户的所有分组
    groups = FriendGroup.objects.filter(user=user).prefetch_related('friends')

    # 组装返回的数据为结构化数组：
    # { groups: [ {id, name, members: [user_id,...]}, ... ] }
    groups_list = []
    grouped_users = set()  # 用于存储已经分配到分组中的用户ID
    for g in groups:
        member_user_ids = []
        for fr in g.friends.all():
            other_id = fr.id
            member_user_ids.append(other_id)
            grouped_users.add(other_id)
        groups_list.append({"id": g.id, "name": g.name, "members": member_user_ids})

    # 查询所有好友，找出未分组的好友
    friendships = Friendship.objects.filter(Q(user_a=user) | Q(user_b=user))
    ungrouped_friends = []
    for fr in friendships:
        other_id = fr.user_b.id if fr.user_a_id == user.id else fr.user_a.id
        if other_id not in grouped_users:
            ungrouped_friends.append(other_id)

    # 把未分组放到列表末尾，id 使用 0 表示系统生成的未分组组
    groups_list.append({"id": 0, "name": "未分组", "members": ungrouped_friends})

    return request_success({"groups": groups_list})


@csrf_exempt
def add_to_group(req: HttpRequest):
    """POST body: {group_id: int, friend_id: int} 把已是好友的 friend_id 加入分组"""
    if req.method != 'POST':
        return BAD_METHOD
    
    # 提取 JWT Token 并解析
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    
    # 校验 JWT Token 是否有效
    if not user_id:
        return request_failed(code=4001, info='Invalid JWT Token.', status_code=403)
    
    # 解析请求体
    try:
        import json
        body = json.loads(req.body.decode('utf-8') or '{}')
    except Exception:
        body = {}

    # 获取 group_id 和 friend_id
    group_id = body.get('group_id')
    friend_id = body.get('friend_id')

    # 如果 group_id 或 friend_id 缺失，返回格式错误
    if not group_id or not friend_id:
        return request_failed(code=4001, info='Invalid request (without group_id or friend_id)', status_code=400)

    # 查询当前用户和好友
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    friend = User.objects.filter(id=friend_id).first()

    # 检查用户是否存在
    if not user:
        return request_failed(code=9001, info='User not found.', status_code=404)
    # 检查好友是否存在
    if not friend:
        return request_failed(code=4012, info='Friend not found.', status_code=404)
    
    # 检查好友是否已注销
    if not friend.is_active:
        return request_failed(code=4014, info='Cannot add deactivated user to friend group.', status_code=400)

    # 确保用户和好友之间是好友关系
    fr = Friendship.objects.filter(Q(user_a=user, user_b=friend) | Q(user_a=friend, user_b=user)).first()
    if not fr:
        return request_failed(code=4013, info='Users are not friends.', status_code=400)

    # 查询分组是否存在
    group = FriendGroup.objects.filter(id=group_id, user=user).first()
    if not group:
        return request_failed(code=4014, info='Group not found.', status_code=404)

    # 检查好友是否已经在该分组内
    if friend in group.friends.all():
        return request_failed(code=4015, info='Friend already in a group.', status_code=400)

    # 将好友添加到分组,这里已经检查过好友关系和是否已经在分组里，理论上肯定不会报错，只是为了保险
    try:
        group.add_friend(friend=friend)
    except Exception as e:
        return request_failed(code=9001, info=str(e), status_code=400)

    return request_success()



@csrf_exempt
def remove_from_group(req: HttpRequest):
    """POST body: {group_id, friend_id} 从分组移除某好友"""
    if req.method != 'POST':
        return BAD_METHOD
    
    # 提取 JWT Token 并解析
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    
    # 校验 JWT Token 是否有效
    if not user_id:
        return request_failed(code=4001, info='Invalid JWT Token.', status_code=403)
    
    # 解析请求体
    try:
        import json
        body = json.loads(req.body.decode('utf-8') or '{}')
    except Exception:
        body = {}

    # 获取 group_id 和 friend_id
    group_id = body.get('group_id')
    friend_id = body.get('friend_id')

    # 如果 group_id 或 friend_id 缺失，返回格式错误
    if not group_id or not friend_id:
        return request_failed(code=4001, info='Invalid request (without group_id or friend_id)', status_code=400)

    # 查询当前用户和好友
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    friend = User.objects.filter(id=friend_id).first()

    # 检查用户是否存在
    if not user:
        return request_failed(code=9001, info='User not found.', status_code=404)
    # 检查好友是否存在
    if not friend:
        return request_failed(code=4012, info='Friend not found.', status_code=404)

    # 确保用户和好友之间是好友关系
    fr = Friendship.objects.filter(Q(user_a=user, user_b=friend) | Q(user_a=friend, user_b=user)).first()
    if not fr:
        return request_failed(code=4013, info='Users are not friends.', status_code=400)

    # 查询分组是否存在
    group = FriendGroup.objects.filter(id=group_id, user=user).first()
    if not group:
        return request_failed(code=4014, info='Group not found.', status_code=404)

    # 检查好友是否不在该分组内
    if not group.friends.filter(id=friend.id).exists():
        return request_failed(code=4015, info='Friend not in the group.', status_code=400)

    # 将好友移除,这里已经检查过好友关系和是否不在该分组里，理论上肯定不会报错，只是为了保险
    try:
        group.remove_friend(friend=friend)
    except Exception as e:
        return request_failed(code=9001, info=str(e), status_code=400)

    return request_success()

@csrf_exempt
def rename_group(req: HttpRequest):
    """POST body: {group_id, name} 重命名分组"""
    if req.method != 'POST':
        return BAD_METHOD
    
    # 提取 JWT Token 并解析
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    
    # 校验 JWT Token 是否有效
    if not user_id:
        return request_failed(code=4001, info='Invalid JWT Token.', status_code=403)
    
    # 解析请求体
    try:
        import json
        body = json.loads(req.body.decode('utf-8') or '{}')
    except Exception:
        body = {}

    # 获取 group_id 和 name
    group_id = body.get('group_id')
    name = body.get('name')

    # 检查请求参数是否有效
    if not group_id or name is None:
        return request_failed(code=4001, info='Invalid request (without group_id or name)', status_code=400)

    # 查询当前用户
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()

    # 检查用户是否存在
    if not user:
        return request_failed(code=9001, info='User not found.', status_code=404)

    # 查询分组是否存在
    group = FriendGroup.objects.filter(id=group_id, user=user).first()
    if not group:
        return request_failed(code=4016, info='Group not found.', status_code=404)

    # 修改分组名称
    group.name = name
    group.save()

    return request_success()


@csrf_exempt
def delete_group(req: HttpRequest):
    """POST body: {group_id} 删除指定分组"""
    if req.method != 'POST':
        return BAD_METHOD
    
    # 提取 JWT Token 并解析
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    
    # 校验 JWT Token 是否有效
    if not user_id:
        return request_failed(code=4001, info='Invalid JWT Token.', status_code=403)
    
    # 解析请求体
    try:
        import json
        body = json.loads(req.body.decode('utf-8') or '{}')
    except Exception:
        body = {}

    # 获取 group_id
    group_id = body.get('group_id')

    # 检查请求参数是否有效
    if not group_id:
        return request_failed(code=4001, info='Invalid request (without group_id)', status_code=400)

    # 查询当前用户
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()

    # 检查用户是否存在
    if not user:
        return request_failed(code=9001, info='User not found.', status_code=404)

    # 查询分组是否存在
    group = FriendGroup.objects.filter(id=group_id, user=user).first()
    if not group:
        return request_failed(code=4017, info='Group not found.', status_code=404)

    # 删除分组
    group.delete()

    return request_success()

@csrf_exempt  # 调试阶段禁用csrf
def check_friendship(req: HttpRequest, id: int):
    """检查与指定用户是否为好友关系"""
    if req.method != "GET":
        return BAD_METHOD
    jwt_token = get_jwt_token(req)
    user_id = parse_jwt_token(jwt_token)
    if not user_id:
        return request_failed(
            code=4001,
            info="Invalid JWT Token",
            status_code=400
        )
    # 不能自己检查自己
    if id == user_id:
        return request_failed(
            code=4006,
            info="Cannot check friendship with oneself.",
            status_code=400
        )
    # 检查两个用户是否都存在
    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    if not user:
        return request_failed(
            code=9001,
            info="User not found.",
            status_code=500
        )
    target = User.objects.filter(id=id).first()
    if not target:
        return request_failed(
            code=4003,
            info="Target user does not exist.",
            status_code=404
        )
    
    # 检查目标用户是否已注销
    if not target.is_active:
        return request_failed(
            code=4011,
            info="Target user has been deactivated.",
            status_code=400
        )
    # 检查是否是好友
    friendship_exists = Friendship.objects.filter(
        Q(user_a=user, user_b=target) | Q(user_a=target, user_b=user)
    ).exists()
    print(f"<Info> (check_friendship) friendship_exists={friendship_exists}")
    if friendship_exists:
        return request_success()
    else:
        return request_failed(
            code=4008,
            info="Users are not friends.",
            status_code=400
        )