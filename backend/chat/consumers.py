"""
WebSocket 消费者 (ChatConsumer)

这个模块负责通过 Django Channels 管理聊天 WebSocket 连接。
设计要点：
- 使用会话 (Conversation) 概念来统一处理私聊与群聊。
- 前端通过 query string 传入 token 与会话 id，例如：/ws/chat?token=xxx&c=123
- 只在 connect 阶段做鉴权与成员检查，所有 ORM 操作都使用 sync_to_async
    以避免在异步上下文中直接调用同步 ORM 导致 SynchronousOnlyOperation。

主要行为：
- connect: 解析 query string，验证 jwt，检查 conversation 与 membership，然后加入 channel group。
- receive: 校验消息格式、持久化消息、广播到组。
- chat_message: 将组消息发回 WebSocket 客户端。
- save_message: 在数据库中创建 Message 记录（在异步上下文中通过 sync_to_async 调用）。

注意：本文件只添加注释和说明，不改变已有逻辑。
"""

import json
import logging
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from utils.jwt import parse_jwt_token

from .models import Conversation, Member, Message
from .presence import mark_offline, mark_online

""" 这里我把 用户-用户 和 用户-群组 视为同一种，均使用"会话"来包装 """

class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket 消费者类。

    每个 WebSocket 连接对应一个 ChatConsumer 实例。实例属性：
    - conversation_id: 从 URL query string 提取的会话 id（字符串形式）
    - jwt_token: 用于鉴权的 jwt token
    - room_group_name: 用于 group_add/group_send 的 channel group 名称
    """

    logger = logging.getLogger(__name__)

    async def connect(self):
        """处理 websocket 连接建立。

        期望的 query 参数：
        - c: conversation id
        - token: JWT，用于鉴权

        步骤：
        1. 解析 query string，提取 c 与 token
        2. 验证 token（parse_jwt_token）得到 user_id
        3. 检查 conversation 是否存在并且 user 是否是成员
        4. 将 channel 加入 group 并 accept 连接

        如果任何一步失败，都会记录日志并关闭连接（带上错误码和 reason）。
        """
        # 解析 query string，parse_qs 返回列表值
        # 现在前端只会上传 token（不再带 c=conversation）
        try:
            query_string = self.scope.get('query_string', b'').decode()
            params = parse_qs(query_string)
            token_list = params.get('token') or []
            jwt_token = token_list[0] if token_list else None
        except Exception:
            self.logger.exception("Failed to parse query string for WS connect")
            await self.close(code=2010, reason="Invalid url params.")
            return

        if not jwt_token:
            self.logger.warning("Missing token in query string: token_present=%s", bool(jwt_token))
            await self.close(code=2010, reason="Invalid url params.")
            return

        self.jwt_token = jwt_token

        # 解析 token
        self.user_id = parse_jwt_token(self.jwt_token)
        if not self.user_id:
            self.logger.warning("Invalid JWT token for WS connect")
            await self.close(code=2010, reason="Invalid jwt token.")
            return

        # 检查用户是否已注销
        user = await sync_to_async(get_user_model().objects.filter(id=self.user_id).first)()
        if not user or not user.is_active:
            self.logger.warning(f"User {self.user_id} is deactivated or not found")
            await self.close(code=2011, reason="User deactivated.")
            return

        # 每个用户有一个全局 group，用于向该用户的所有连接广播消息
        self.room_group_name = f"user_{self.user_id}"

        try:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            await mark_online(self.user_id)
            self.logger.info(f"(connect) accepted connection user_id={self.user_id} room={self.room_group_name}")
        except Exception:
            self.logger.exception("Failed to add channel to group or accept websocket")
            try:
                await self.close()
            except Exception:
                pass
            return

    async def disconnect(self, close_code):
        """处理 websocket 断开连接。

        从 channel group 中移除该 channel。此方法应尽可能轻量，不抛出异常。
        """
        # 离开房间
        await self.channel_layer.group_discard(
            getattr(self, 'room_group_name', ''),
            self.channel_name
        )
        try:
            user_id = getattr(self, 'user_id', None)
            if user_id is not None:
                await mark_offline(user_id)
        except Exception:
            self.logger.exception("Failed to update presence on disconnect")
        self.logger.info(f"(disconnect) room={getattr(self, 'room_group_name', None)} close_code={close_code}")

    async def receive(self, text_data):
        """接收并处理来自客户端的消息。

        支持两种消息类型：
        1. 普通消息：
        {
            "type": "message",
            "conversation": 3,
            "message": {
                "content": "Hello"
            }
        }

        2. 已读状态更新：
        {
            "type": "read_receipt",
            "conversation": 3,
            "message_id": 123
        }

        流程：
        1. 解析 JSON，校验 type 和必要字段
        2. 根据消息类型调用相应处理方法
        3. 广播状态更新给会话中所有成员的用户组
        """
        try:
            data = json.loads(text_data)
        except Exception:
            self.logger.exception("Invalid JSON received from websocket")
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'invalid_json'}))
            return

        message_type = data.get('type')

        if message_type == 'message':
            await self.handle_message(data)
        elif message_type == 'read_receipt':
            await self.handle_read_receipt(data)
        elif message_type == 'edit_message':
            await self.handle_edit_message(data)
        elif message_type == 'recall_message':
            await self.handle_recall_message(data)
        else:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'invalid_message_type'}))
            return

    async def handle_message(self, data):
        """处理普通消息"""
        conversation_id = data.get('conversation')
        message_data = data.get('message', {})
        content = message_data.get('content')
        reply_to_id = message_data.get('reply_to')

        if not conversation_id or not content:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'missing_fields'}))
            return

        # 检查是否为私聊且用户是否仍为好友
        is_private = await self.is_private_conversation(int(conversation_id))
        if is_private:
            is_friend = await self.check_friendship_in_private_chat(self.user_id, int(conversation_id))
            if not is_friend:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'error': 'not_friends',
                    'message': '你们已经不是好友，无法发送消息'
                }))
                return

        # 保存消息并获取 message 对象
        created = await self.save_message_for_conversation(self.user_id, int(conversation_id), content, reply_to_id)
        if not created:
            return

        # created 是一个 dict 表示消息内容，包含 conversation 和 message
        # 将此消息广播给会话中的所有成员（他们监听 user_{id} 组）
        conversation_group_event = {
            'type': 'chat_message',
            'conversation': created['conversation'],
            'message': created['message']
        }

        # 广播到会话的每个成员的 user_{id} 组
        await self.broadcast_to_conversation_members(int(conversation_id), conversation_group_event)

    async def handle_read_receipt(self, data):
        """处理已读状态更新"""
        conversation_id = data.get('conversation')
        message_id = data.get('message_id')

        if not conversation_id or not message_id:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'missing_fields'}))
            return

        # 获取并更新消息的已读状态
        success = await self.update_message_read_status(self.user_id, int(conversation_id), int(message_id))
        if not success:
            return

        # 广播已读状态更新
        read_receipt_event = {
            'type': 'read_receipt_update',
            'conversation': conversation_id,
            'message_id': message_id,
            'user_id': self.user_id
        }

        # 广播到会话的每个成员的 user_{id} 组
        await self.broadcast_to_conversation_members(int(conversation_id), read_receipt_event)

    async def handle_edit_message(self, data):
        """处理消息编辑"""
        conversation_id = data.get('conversation')
        message_id = data.get('message_id')
        content = data.get('content')

        if not conversation_id or not message_id or content is None:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'missing_fields'}))
            return

        # 检查是否为私聊且用户是否仍为好友
        is_private = await self.is_private_conversation(int(conversation_id))
        if is_private:
            is_friend = await self.check_friendship_in_private_chat(self.user_id, int(conversation_id))
            if not is_friend:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'error': 'not_friends',
                    'message': '你们已经不是好友，无法编辑消息'
                }))
                return

        # 验证权限并更新消息
        success = await self.update_message_content(self.user_id, int(conversation_id), int(message_id), content)
        if not success:
            return

        # 广播消息编辑事件
        edit_event = {
            'type': 'message_edited',
            'conversation': conversation_id,
            'message_id': message_id,
            'content': content,
            'user_id': self.user_id
        }

        # 广播到会话的每个成员的 user_{id} 组
        await self.broadcast_to_conversation_members(int(conversation_id), edit_event)

    async def handle_recall_message(self, data):
        """处理消息撤回"""
        conversation_id = data.get('conversation')
        message_id = data.get('message_id')

        if not conversation_id or not message_id:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'missing_fields'}))
            return

        # 检查是否为私聊且用户是否仍为好友
        is_private = await self.is_private_conversation(int(conversation_id))
        if is_private:
            is_friend = await self.check_friendship_in_private_chat(self.user_id, int(conversation_id))
            if not is_friend:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'error': 'not_friends',
                    'message': '你们已经不是好友，无法撤回消息'
                }))
                return

        # 验证权限并撤回消息
        success = await self.recall_message(self.user_id, int(conversation_id), int(message_id))
        if not success:
            return

        # 广播消息撤回事件
        recall_event = {
            'type': 'message_recalled',
            'conversation': conversation_id,
            'message_id': message_id,
            'user_id': self.user_id
        }

        # 广播到会话的每个成员的 user_{id} 组
        await self.broadcast_to_conversation_members(int(conversation_id), recall_event)

    async def update_message_content(self, user_id, conversation_id, message_id, content):
        """更新消息内容"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            user = await sync_to_async(User.objects.get)(id=user_id)
            if not user.is_active:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'user_deactivated'}))
                return False
            conversation = await sync_to_async(Conversation.objects.get)(id=conversation_id)
            if not conversation.is_active:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'conversation_inactive'}))
                return False
            member = await sync_to_async(Member.objects.filter(user=user, conversation=conversation).first)()

            if not member:
                self.logger.warning(f"User {user_id} is not a member of conversation {conversation_id}")
                return False

            message = await sync_to_async(Message.objects.select_related('member').filter(id=message_id, conversation=conversation).first)()
            if not message:
                self.logger.warning(f"Message {message_id} not found in conversation {conversation_id}")
                return False

            if message.member.user_id != user_id:
                self.logger.warning(f"User {user_id} is not the author of message {message_id}")
                return False

            # 更新消息内容
            message.content = content
            message.is_edited = True
            await sync_to_async(message.save)()

            self.logger.info(f"User {user_id} edited message {message_id} in conversation {conversation_id}")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to update message: {e}")
            return False

    async def recall_message(self, user_id, conversation_id, message_id):
        """撤回消息"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            user = await sync_to_async(User.objects.get)(id=user_id)
            if not user.is_active:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'user_deactivated'}))
                return False
            conversation = await sync_to_async(Conversation.objects.get)(id=conversation_id)
            if not conversation.is_active:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'conversation_inactive'}))
                return False
            member = await sync_to_async(Member.objects.filter(user=user, conversation=conversation).first)()

            if not member:
                self.logger.warning(f"User {user_id} is not a member of conversation {conversation_id}")
                return False

            message = await sync_to_async(Message.objects.select_related('member').filter(id=message_id, conversation=conversation).first)()
            if not message:
                self.logger.warning(f"Message {message_id} not found in conversation {conversation_id}")
                return False

            if message.member.user_id != user_id:
                self.logger.warning(f"User {user_id} is not the author of message {message_id}")
                return False

            # 撤回消息
            message.valid = False
            message.content = f"{member.nickname or user.username}撤回了一条消息"
            await sync_to_async(message.save)()

            self.logger.info(f"User {user_id} recalled message {message_id} in conversation {conversation_id}")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to recall message: {e}")
            return False

    async def update_message_read_status(self, user_id, conversation_id, message_id):
        """更新消息的已读状态"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            user = await sync_to_async(User.objects.get)(id=user_id)
            if not user.is_active:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'user_deactivated'}))
                return False
            conversation = await sync_to_async(Conversation.objects.get)(id=conversation_id)
            member = await sync_to_async(Member.objects.filter(user=user, conversation=conversation).first)()

            if not member:
                self.logger.warning(f"User {user_id} is not a member of conversation {conversation_id}")
                return False

            message = await sync_to_async(Message.objects.filter(id=message_id, conversation=conversation).first)()
            if not message:
                self.logger.warning(f"Message {message_id} not found in conversation {conversation_id}")
                return False

            # 添加用户到已读列表
            await sync_to_async(message.read_list.add)(member)

            self.logger.info(f"User {user_id} marked message {message_id} as read in conversation {conversation_id}")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to update read status: {e}")
            return False

    async def broadcast_to_conversation_members(self, conversation_id, event):
        """向会话的所有成员广播事件"""
        # 在 sync_to_async 内一次性获取 user_id 列表，避免在异步上下文触发同步 ORM 调用
        try:
            user_ids = await sync_to_async(lambda: list(Conversation.objects.get(id=conversation_id).members.values_list('user_id', flat=True)))()
            for uid in user_ids:
                group_name = f'user_{uid}'
                # 根据事件类型设置正确的处理方法名
                event_type = event.get('type')
                if event_type == 'read_receipt_update':
                    # 对于已读回执，确保事件类型正确
                    await self.channel_layer.group_send(group_name, {
                        'type': 'read_receipt_update',
                        'conversation': event.get('conversation'),
                        'message_id': event.get('message_id'),
                        'user_id': event.get('user_id')
                    })
                elif event_type == 'message_edited':
                    # 对于消息编辑，确保事件类型正确
                    await self.channel_layer.group_send(group_name, {
                        'type': 'message_edited',
                        'conversation': event.get('conversation'),
                        'message_id': event.get('message_id'),
                        'content': event.get('content'),
                        'user_id': event.get('user_id')
                    })
                elif event_type == 'message_recalled':
                    # 对于消息撤回，确保事件类型正确
                    await self.channel_layer.group_send(group_name, {
                        'type': 'message_recalled',
                        'conversation': event.get('conversation'),
                        'message_id': event.get('message_id'),
                        'user_id': event.get('user_id')
                    })
                else:
                    # 对于其他事件类型，直接发送
                    await self.channel_layer.group_send(group_name, event)
        except Exception as e:
            self.logger.exception(f"Error broadcasting to conversation members: {e}")

    async def chat_message(self, event):
        """处理来自 channel group 的消息事件并发送给当前 WebSocket 客户端。

        事件格式示例：{'type': 'chat_message', 'sender': ..., 'message': ...}
        此处只是把消息序列化为 JSON 并发送到客户端。
        """
        # event contains 'conversation' and 'message' dict
        await self.send(text_data=json.dumps({
            'type': 'message',
            'conversation': event.get('conversation'),
            'message': event.get('message')
        }))

    async def read_receipt_update(self, event):
        """处理已读状态更新事件并发送给当前 WebSocket 客户端。

        事件格式：{'type': 'read_receipt_update', 'conversation': ..., 'message_id': ..., 'user_id': ...}
        """
        await self.send(text_data=json.dumps({
            'type': 'read_receipt_update',
            'conversation': event.get('conversation'),
            'message_id': event.get('message_id'),
            'user_id': event.get('user_id')
        }))

    async def message_edited(self, event):
        """处理消息编辑事件并发送给当前 WebSocket 客户端。

        事件格式：{'type': 'message_edited', 'conversation': ..., 'message_id': ..., 'content': ..., 'user_id': ...}
        """
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'conversation': event.get('conversation'),
            'message_id': event.get('message_id'),
            'content': event.get('content'),
            'user_id': event.get('user_id')
        }))

    async def message_recalled(self, event):
        """处理消息撤回事件并发送给当前 WebSocket 客户端。

        事件格式：{'type': 'message_recalled', 'conversation': ..., 'message_id': ..., 'user_id': ...}
        """
        await self.send(text_data=json.dumps({
            'type': 'message_recalled',
            'conversation': event.get('conversation'),
            'message_id': event.get('message_id'),
            'user_id': event.get('user_id')
        }))

    async def conversation_event(self, event):
        """广播会话相关事件（如新群聊创建），提示前端刷新。"""
        await self.send(text_data=json.dumps({
            'type': 'conversation_event',
            'event': event.get('event'),
            'conversation': event.get('conversation'),
        }))

    async def check_conversation_membership(self, user_id, conversation_id):
        """检查用户是否是会话成员"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            user = await sync_to_async(User.objects.get)(id=user_id)
            conversation = await sync_to_async(Conversation.objects.get)(id=conversation_id)
            member = await sync_to_async(Member.objects.filter(user=user, conversation=conversation).first)()

            return member is not None
        except Exception as e:
            self.logger.exception(f"Error checking conversation membership: {e}")
            return False

    async def is_private_conversation(self, conversation_id):
        """检查是否为私聊会话"""
        try:
            conversation = await sync_to_async(Conversation.objects.get)(id=conversation_id)
            return conversation.type == "private"
        except Exception as e:
            self.logger.exception(f"Error checking conversation type: {e}")
            return False

    async def check_friendship_in_private_chat(self, user_id, conversation_id):
        """检查私聊中的两个用户是否仍为好友关系"""
        try:
            from django.db.models import Q

            from friend.models import Friendship

            # 获取私聊会话的两个成员
            conversation = await sync_to_async(Conversation.objects.get)(id=conversation_id)
            members = await sync_to_async(list)(conversation.members.all().values_list('user_id', flat=True))

            if len(members) != 2:
                return False

            # 获取对方用户ID
            other_user_id = members[0] if members[1] == user_id else members[1]

            # 检查是否仍为好友（双向检查）
            return await sync_to_async(Friendship.objects.filter(
                Q(user_a_id=user_id, user_b_id=other_user_id) |
                Q(user_a_id=other_user_id, user_b_id=user_id)
            ).exists)()
        except Exception as e:
            self.logger.exception(f"Error checking friendship: {e}")
            return False
    async def save_message_by_user_id(self, user_id, message):
        """在数据库中创建 Message 对象。注意：该方法在异步上下文被调用，内部所有 ORM 操作都使用 sync_to_async 以避免触发 Django 的同步限制。"""
        try:
            user = await sync_to_async(get_user_model().objects.get)(id=user_id)
        except ObjectDoesNotExist:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'user_not_found'}))
            return False
        except Exception:
            self.logger.exception("Unexpected error fetching user %s", user_id)
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'server_error'}))
            return False

        try:
            # 该方法在旧实现中依赖 self.conversation_id，现在使用者会直接按 conversation id 调用新方法
            conversation = await sync_to_async(Conversation.objects.first)()
        except Exception:
            self.logger.exception("Unexpected error fetching conversation")
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'server_error'}))
            return False

        try:
            member = await sync_to_async(lambda: Member.objects.filter(user=user, conversation=conversation).first())()
            await sync_to_async(Message.objects.create)(
                conversation=conversation,
                member=member,
                content=message,
            )
            self.logger.info(f"(save_message) message_saved user_id={user_id} conv={getattr(conversation,'id',None)}")
        except Exception:
            self.logger.exception("Failed to create Message for conversation %s", getattr(self, 'conversation_id', None))
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'server_error'}))
            return False

        return True

    async def save_message_for_conversation(self, user_id: int, conversation_id: int, content: str, reply_to_id: int = None):
        """为指定会话保存消息并返回序列化结构。"""
        try:
            user = await sync_to_async(get_user_model().objects.get)(id=user_id)
        except ObjectDoesNotExist:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'user_not_found'}))
            return None
        if not user.is_active:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'user_deactivated'}))
            return None
        try:
            conversation = await sync_to_async(Conversation.objects.get)(id=conversation_id)
        except ObjectDoesNotExist:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'conversation_not_found'}))
            return None
        if not conversation.is_active:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'conversation_inactive'}))
            return None

        member = await sync_to_async(lambda: Member.objects.select_related('user').filter(user=user, conversation=conversation).first())()
        if not member:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'not_member'}))
            return None

        try:
            # 创建消息
            msg = await sync_to_async(Message.objects.create)(
                conversation=conversation,
                member=member,
                content=content,
                reply_to_id=reply_to_id
            )
            # 自动将发送者添加到已读列表
            await sync_to_async(msg.read_list.add)(member)

            # 重新获取消息，包含关联的reply_to数据
            msg = await sync_to_async(Message.objects.select_related('reply_to__member__user').get)(id=msg.id)
        except Exception:
            self.logger.exception("Failed to create message via websocket")
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'server_error'}))
            return None

        # 构建回复消息信息
        reply_to_message = None
        if msg.reply_to_id and msg.reply_to and msg.reply_to.valid:
            reply_to_message = {
                'id': msg.reply_to.id,
                'sender': msg.reply_to.member.user.id,
                'nickname': msg.reply_to.member.nickname,
                'sender_nickname': msg.reply_to.member.nickname,  # 添加群昵称
                'text': msg.reply_to.content,
                'type': msg.reply_to.type,
            }

        created = {
            'conversation': conversation.id,
            'message': {
                'id': msg.id,
                'sender': user_id,
                'nickname': member.nickname or member.user.username,  # 群昵称（默认用户名）
                'sender_nickname': member.nickname or member.user.username,  # 群昵称（默认用户名）
                'content': msg.content,
                'reply_to': msg.reply_to_id,
                'reply_to_message': reply_to_message,
                'time': msg.time.isoformat().replace('+00:00', 'Z') if getattr(msg, 'time', None) else None,
                'read_list': [user_id]  # 发送者自动已读
            }
        }
        return created

    async def _broadcast_presence_status(self, status: str):
        """将当前用户的在线状态广播给所有相关会话成员。"""
        try:
            conv_ids = await sync_to_async(list)(
                Member.objects
                .filter(user_id=self.user_id, conversation__is_active=True)
                .values_list('conversation_id', flat=True)
            )
            if not conv_ids:
                return
            user_ids = await sync_to_async(list)(
                Member.objects
                .filter(conversation_id__in=conv_ids, conversation__is_active=True)
                .values_list('user_id', flat=True)
                .distinct()
            )
            payload = {
                'type': 'presence',
                'user_id': self.user_id,
                'status': status
            }
            for uid in set(user_ids):
                await self.channel_layer.group_send(f'user_{uid}', payload)
        except Exception:
            self.logger.exception("Failed to broadcast presence status")

    async def presence(self, event):
        """向前端转发在线状态事件。"""
        try:
            await self.send(text_data=json.dumps(event))
        except Exception:
            self.logger.exception("Failed to send presence event")
