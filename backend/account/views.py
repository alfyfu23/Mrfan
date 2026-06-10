from django.http import HttpRequest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from account.models import validate_username, validate_password_strength
from utils.network import BAD_METHOD, request_failed, request_success
from utils.jwt import generate_jwt_token, parse_jwt_token
from utils.tools import get_jwt_token
from django.contrib.auth import authenticate 
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password
from django.db import transaction
import json 
import logging

logger = logging.getLogger(__name__)

# 开发阶段临时禁用 CSRF；生产请开启并配置跨域

# 初始化用户类
User = get_user_model()
USER_NOT_FOUND_INFO = "User does not exist."


def _generate_deactivated_username(user_id: int) -> str:
    """Build a unique placeholder username for deactivated accounts.

    Keep it short (<30 chars) and retry if an unexpected collision occurs.
    """
    base = f"deactivated_{user_id}"
    candidate = base[:30]
    suffix = 0
    while User.objects.filter(username=candidate).exclude(id=user_id).exists():
        suffix += 1
        candidate = f"{base}_{suffix}"[:30]
    return candidate
    
@csrf_exempt  # 调试阶段禁用csrf
def register(req: HttpRequest):
    # 方法不对
    if req.method != 'POST':
        return BAD_METHOD

    # ---- 解析请求 ----
    try:
        data = json.loads(req.body)  # 解析 JSON
        username = data["username"]
        password = data["password"]
    except Exception:
        return request_failed(code=1001, info="Invalid request. Username or password not found.", status_code=400)

    # ---- 用户名是否存在 ----
    # 检查是否有活跃用户使用此用户名
    if User.objects.filter(username=username, is_active=True).exists():
        return request_failed(code=1002, info="Username already exists.", status_code=400)

    # 如果存在已注销用户，保留其记录但释放用户名以便重用
    deactivated_user = User.objects.filter(username=username, is_active=False).first()
    if deactivated_user:
        with transaction.atomic():
            if not deactivated_user.deactivated_username:
                deactivated_user.deactivated_username = deactivated_user.username
            deactivated_user.username = _generate_deactivated_username(deactivated_user.id)
            deactivated_user.save(update_fields=["deactivated_username", "username"])

    # ---- 验证用户名格式 ----
    try:
        validate_username(username)
    except ValidationError:
        return request_failed(code=1005, info="Username format invalid.", status_code=400)

    # ---- 验证密码强度 ----
    try:
        validate_password_strength(password)
    except ValidationError:
        return request_failed(code=1006, info="Password format invalid.", status_code=400)

    # ---- 创建用户 ----
    user = User(username=username)
    user.set_password(password)
    user.save()

    # 返回
    jwt_token = generate_jwt_token(username=username, id=user.id)
    return request_success(data={'jwt_token': jwt_token, 'code': 0})
    
@csrf_exempt # 调试阶段禁用csrf
def login(req: HttpRequest):
    if req.method != 'POST':
        return BAD_METHOD
    try:
        data = json.loads(req.body)  # 解析 JSON
        username = data["username"]
        password = data["password"]
    except Exception:
        info = "Invalid request. Username or password not found."
        logger.info(info)
        return request_failed(
            code=1001,
            info=info,
            status_code=400
        )
    try:
        user = User.objects.filter(username=username).first()
        # 如果当前用户名不存在，尝试匹配已注销账号的旧用户名
        if not user:
            user = User.objects.filter(deactivated_username=username, is_active=False).first()
        if not user:
            info = "Username does not exist."
            logger.info(info)
            return request_failed(
                code=1003,
                info=info,
                status_code=404
            )
        # 检查用户是否已注销
        if not user.is_active:
            info = "User account has been deactivated."
            logger.info(info)
            return request_failed(
                code=1005,
                info=info,
                status_code=403
            )
    except Exception:
        info = "Username does not exist."
        logger.info(info)
        return request_failed(
            code=1003,
            info=info,
            status_code=404
        )
    
    user = authenticate(username=username, password=password)
    if user is not None:
        # 验证成功，签发jwt token
        jwt_token = generate_jwt_token(username=username, id=user.id)
        return request_success(data={
            'jwt_token': jwt_token,
            "username": username,
            "id": user.id
        })
    else:
        # 验证失败
        info = "Wrong password."
        logger.info(info)
        return request_failed(
            code=1004,
            info=info,
            status_code=400
        )

@csrf_exempt # 调试阶段禁用csrf       
def get_info(req: HttpRequest):
    if req.method != 'GET':
        return BAD_METHOD

    # ---- 解析并验证 JWT ----
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(
            code=1101,
            info="Invalid JWT token.",
            status_code=403
        )

    # ---- 获取目标用户 ID ----
    target_id = req.GET.get('target')
    if not target_id:
        target_id = user_id

    # ---- 检查用户是否存在 ----
    User = get_user_model()
    user = User.objects.filter(id=target_id).first()
    if not user:
        return request_failed(code=1102, info=USER_NOT_FOUND_INFO, status_code=404)

    # ---- 判断是否本人 ----
    is_self = str(user_id) == str(target_id)

    # ---- 构造返回数据 ----
    display_name = user.display_username if hasattr(user, "display_username") else user.username
    if is_self:
        # 对于已注销用户获取自己的信息，显示已注销状态
        if not user.is_active:
            data = {
                "username": display_name,
                "avatar": "",
                "email": "",
                "phone": "",
                "info": "",
                "is_active": False
            }
        else:
            data = {
                "username": display_name,
                "avatar": user.avatar,
                "email": getattr(user, "email", ""),
                "phone": getattr(user, "phone", ""),
                "info": getattr(user, "info", ""),
                "is_active": user.is_active
            }
    else:
        # 对于已注销用户，显示特殊状态
        if not user.is_active:
            data = {
                "username": display_name,
                "avatar": "",
                "info": "此用户已注销",
                "is_active": False
            }
        else:
            data = {
                "username": display_name,
                "avatar": user.avatar,
                "info": getattr(user, "info", ""),
                "is_active": user.is_active
            }

    return request_success(data)

@csrf_exempt # 调试阶段禁用csrf
def edit_info(req: HttpRequest):
    """修改个人信息"""
    if req.method != 'POST':
        return BAD_METHOD

    # ---- 解析 JWT ----
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(
            code=1201,
            info="Invalid JWT Token.",
            status_code=403
        )

    # ---- 查询用户 ----
    user = User.objects.filter(id=user_id).first()
    if not user:
        return request_failed(code=1202, info=USER_NOT_FOUND_INFO, status_code=404)

    # ---- 解析请求体 ----
    try:
        data = json.loads(req.body)
    except Exception:
        return request_failed(code=1203, info="Invalid request body.", status_code=400)

    field = data.get("field")
    value = data.get("value")
    password = data.get("password")  # 原密码（仅敏感字段修改时使用，可为空）
    if field is None or value is None or password is None:
        return request_failed(code=1203, info="Invalid request body.", status_code=400)

    # ---- 区分普通字段和敏感字段 ----
    sensitive_fields = ["password", "email", "phone"]
    normal_fields = ["username", "avatar", "info"]

    # --- 修改普通字段 ---
    if field in normal_fields:
        setattr(user, field, value)
        user.save()
        return request_success(data={"code": 0})

    # --- 修改敏感字段 ---
    elif field in sensitive_fields:
        # 验证原密码是否正确
        if not password or not check_password(password, user.password):
            return request_failed(
                code=1205,
                info="Password incorrect.",
                status_code=403
            )

        # 更新对应字段
        if field == "password":
            # 验证新密码强度
            try:
                validate_password_strength(value)
            except ValidationError as e:
                return request_failed(
                    code=1206,
                    info=f"Password format invalid: {str(e)}",
                    status_code=400
                )
            user.set_password(value)
        else:
            setattr(user, field, value)
        user.save()
        return request_success(data={"code": 0})

    # --- 其他非法字段 ---
    else:
        return request_failed(
            code=1204,
            info="Invalid field value.",
            status_code=400
        )

@csrf_exempt
def delete_account(req: HttpRequest):
    """注销用户账号"""
    if req.method != "POST":
        return BAD_METHOD

    # ---- 解析 JWT ----
    user_id = parse_jwt_token(get_jwt_token(req))
    if not user_id:
        return request_failed(code=1301, info="Invalid JWT Token.", status_code=403)

    # ---- 查询用户 ----
    user = User.objects.filter(id=user_id).first()
    if not user:
        return request_failed(code=1302, info=USER_NOT_FOUND_INFO, status_code=404)

    # ---- 解析请求体 ----
    try:
        data = json.loads(req.body)
        password = data["password"]
    except Exception:
        return request_failed(code=1303, info="Missing password in request body.", status_code=400)

    # ---- 校验密码 ----
    if not password or not check_password(password, user.password):
        return request_failed(code=1304, info="Password incorrect.", status_code=403)

    # ---- 软删除用户账号 ----
    original_username = user.username
    user.is_active = False
    user.deactivated_username = user.deactivated_username or original_username
    user.username = _generate_deactivated_username(user.id)
    user.set_unusable_password()
    user.email = ""
    user.phone = ""
    user.info = ""
    user.avatar = ""
    user.save()

    # ---- 如果用户是群主，自动将群标记为不可用（保留消息记录） ----
    try:
        from chat.models import Member
        from chat.views import _notify_conversation_event

        owner_memberships = (
            Member.objects
            .filter(user=user, role='owner', conversation__type='group', conversation__is_active=True)
            .select_related('conversation')
        )
        for owner_member in owner_memberships:
            conv = owner_member.conversation
            conv.is_active = False
            conv.save(update_fields=["is_active"])
            member_ids = list(conv.members.values_list('user_id', flat=True))
            _notify_conversation_event(member_ids, 'group_disbanded', conv.id)
    except Exception as e:
        # 不阻断注销流程，但记录异常便于排查
        logger.warning(f"failed to mark owned groups inactive for user {user.id}: {e}")

    return request_success()