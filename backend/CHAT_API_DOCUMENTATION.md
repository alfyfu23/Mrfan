# Chat API 文档

## 概述

聊天模块提供了完整的即时通讯功能，包括私聊、群聊、消息发送、已读状态、消息删除等功能。

## 认证

所有 API 请求都需要在 HTTP Header 中包含 JWT Token：
```
Authorization: Bearer <jwt_token>
```

## WebSocket 连接

### 连接地址
```
ws://your-domain/ws/chat?token=<jwt_token>&c=<conversation_id>
```

### 连接参数
- `token`: JWT Token（用于身份验证）
- `c`: Conversation ID（会话ID）

### 发送消息格式
```json
{
    "message": "消息内容",
    "type": "text"  // 可选：text/image/emoji，默认为 text
}
```

### 接收消息格式
```json
{
    "sender": "发送者用户名",
    "message": "消息内容",
    "msg_type": "text"
}
```

### 错误消息格式
```json
{
    "type": "error",
    "error": "错误类型"
}
```

可能的错误类型：
- `invalid_json`: JSON 格式错误
- `missing_fields`: 缺少必要字段
- `user_not_found`: 用户不存在
- `conversation_not_found`: 会话不存在
- `member_not_found`: 成员关系不存在
- `server_error`: 服务器错误

---

## REST API 接口

### 1. 获取会话历史消息

**URL**: `/chat/history`  
**方法**: `GET`  
**参数**:
- `c`: conversation_id（会话ID）

**响应**:
```json
{
    "code": 0,
    "info": "Succeed",
    "data": {
        "messages": [
            {
                "id": 100,
                "sender_id": 1,
                "sender_username": "张三",
                "sender_nickname": "小张",
                "type": "text",
                "content": "你好",
                "time": "2025-10-18T08:00:00Z",
                "is_edited": false,
                "is_read": true
            },
            {
                "id": 101,
                "sender_id": 2,
                "sender_username": "李四",
                "sender_nickname": "小李",
                "type": "image",
                "content": "https://example.com/image.jpg",
                "time": "2025-10-18T08:05:00Z",
                "is_edited": false,
                "is_read": false
            },
            {
                "id": 102,
                "sender_id": 1,
                "sender_username": "张三",
                "sender_nickname": "小张",
                "type": "emoji",
                "content": "😊",
                "time": "2025-10-18T08:10:00Z",
                "is_edited": false,
                "is_read": true
            }
        ]
    }
}
```

**说明**:
- 只返回有效且未被当前用户删除的消息
- `is_read` 表示当前用户是否已读该消息
- 消息按时间升序排列

---

### 2. 创建好友私聊会话

**URL**: `/chat/create/friend`  
**方法**: `POST`  
**请求体**:
```json
{
    "id": 2  // 对方用户ID
}
```

**响应**:
```json
{
    "code": 0,
    "info": "Succeed",
    "data": {
        "id": 123  // 会话ID
    }
}
```

**说明**:
- 只有好友关系才能创建私聊会话
- 如果会话已存在，返回现有会话ID
- 会话类型自动设置为 `private`

---

### 3. 获取会话列表

**URL**: `/chat/conversations`  
**方法**: `GET`  
**参数**: 无

**响应**:
```json
{
    "code": 0,
    "info": "Succeed",
    "data": {
        "conversations": [
            {
                "id": 1,
                "name": "MrFan",  // 群聊名称或好友用户名
                "avatar": "https://example.com/avatar.jpg",
                "type": "group",  // private 或 group
                "last_message": {
                    "type": "text",
                    "content": "最后一条消息内容",
                    "time": "2025-10-18T10:00:00Z",
                    "sender": "李四"
                },
                "unread_count": 5,  // 未读消息数
                "mute": false,  // 是否静音
                "pinned": true,  // 是否置顶
                "my_nickname": "小张",  // 我在该会话中的昵称
                "my_role": "member"  // 我的角色：member 或 admin
            },
            {
                "id": 2,
                "name": "李四",
                "avatar": "",
                "type": "private",
                "last_message": {
                    "type": "emoji",
                    "content": "👍",
                    "time": "2025-10-18T09:00:00Z",
                    "sender": "李四"
                },
                "unread_count": 0,
                "mute": false,
                "pinned": false,
                "my_nickname": "张三",
                "my_role": "member"
            }
        ]
    }
}
```

**说明**:
- 返回当前用户参与的所有会话
- 按最后查看时间倒序排列
- 私聊会话的名称和头像自动显示为对方信息

---

### 4. 标记消息为已读

**URL**: `/chat/mark-read`  
**方法**: `POST`  
**请求体**:
```json
{
    "c": 1,  // conversation_id
    "message_ids": [100, 101, 102]  // 可选，不传则标记所有未读消息
}
```

**响应**:
```json
{
    "code": 0,
    "info": "Succeed",
    "data": {
        "marked_count": 3  // 标记的消息数量
    }
}
```

**说明**:
- 将指定消息或所有未读消息标记为已读
- 同时更新用户的最后查看时间
- 不会标记自己发送的消息

---

### 5. 删除消息

**URL**: `/chat/delete-message`  
**方法**: `POST`  
**请求体**:
```json
{
    "message_id": 100
}
```

**响应**:
```json
{
    "code": 0,
    "info": "Succeed",
    "data": {
        "success": true
    }
}
```

**说明**:
- 软删除，只对当前用户隐藏该消息
- 其他用户仍可看到该消息
- 删除后无法恢复

---

### 6. 更新会话成员设置

**URL**: `/chat/member/settings`  
**方法**: `POST`  
**请求体**:
```json
{
    "c": 1,  // conversation_id
    "mute": true,  // 可选，是否静音
    "pinned": false,  // 可选，是否置顶
    "nickname": "新昵称"  // 可选，我在该会话中的昵称
}
```

**响应**:
```json
{
    "code": 0,
    "info": "Succeed",
    "data": {
        "success": true,
        "updated_fields": ["mute", "nickname"]
    }
}
```

**说明**:
- 可以单独或同时更新多个设置
- 只影响当前用户在该会话中的设置
- 昵称只在该会话中显示

---

## 消息类型说明

### 1. 文本消息 (text)
```json
{
    "type": "text",
    "content": "这是一条文本消息"
}
```

### 2. 图片消息 (image)
```json
{
    "type": "image",
    "content": "https://example.com/images/photo.jpg"
}
```
- `content` 字段存储图片的完整 URL
- 图片大小、缩略图等由前端处理

### 3. 表情消息 (emoji)
```json
{
    "type": "emoji",
    "content": "😊"
}
```
- `content` 字段存储 Unicode 表情符号
- 前端可以放大显示或特殊渲染

### 4. 视频消息 (video) - 预留
```json
{
    "type": "video",
    "content": "https://example.com/videos/video.mp4"
}
```

### 5. 音频消息 (audio) - 预留
```json
{
    "type": "audio",
    "content": "https://example.com/audios/voice.mp3"
}
```

---

## 错误码说明

| 错误码 | 说明 | HTTP状态码 |
|--------|------|-----------|
| 2001 | 请求参数错误 | 400 |
| 2004 | 目标用户不存在 | 404 |
| 2010 | WebSocket 参数错误 | - |
| 2011 | WebSocket 会话不存在 | - |
| 2012 | 未授权访问会话 | 403 |
| 3001 | 认证失败 | 400 |
| 3002 | JWT Token 无效 | 403 |
| 3003 | 会话不存在 | 404 |
| 3004 | 无权访问该会话 | 403 |
| 3005 | 消息不存在 | 404 |
| 9001 | 用户不存在 | 500 |

---

## 数据模型说明

### Conversation (会话)
- `id`: 会话ID
- `name`: 会话名称（群聊名称，私聊为空）
- `type`: 会话类型（private/group）
- `created_at`: 创建时间
- `avatar`: 会话头像URL

### Member (会话成员)
- `conversation`: 所属会话
- `user`: 用户
- `nickname`: 在该会话中的昵称
- `mute`: 是否静音
- `pinned`: 是否置顶
- `time`: 最后查看时间
- `role`: 角色（member/admin）

### Message (消息)
- `conversation`: 所属会话
- `member`: 发送者（Member 对象）
- `type`: 消息类型（text/image/emoji/video/audio）
- `content`: 消息内容
- `time`: 发送时间
- `is_edited`: 是否已编辑
- `valid`: 是否有效
- `read_list`: 已读成员列表（多对多）
- `delete_list`: 删除成员列表（多对多）

---

## 使用示例

### 1. 创建私聊并发送消息

```javascript
// 1. 创建会话
const createResponse = await fetch('/chat/create/friend', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ id: 2 })
});
const { data } = await createResponse.json();
const conversationId = data.id;

// 2. 建立 WebSocket 连接
const ws = new WebSocket(`ws://localhost:8000/ws/chat?token=${token}&c=${conversationId}`);

// 3. 发送文本消息
ws.send(JSON.stringify({
    message: "你好！",
    type: "text"
}));

// 4. 发送图片消息
ws.send(JSON.stringify({
    message: "https://example.com/photo.jpg",
    type: "image"
}));

// 5. 接收消息
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`${data.sender}: ${data.message} [${data.msg_type}]`);
};
```

### 2. 获取会话列表并显示未读数

```javascript
const response = await fetch('/chat/conversations', {
    headers: {
        'Authorization': 'Bearer ' + token
    }
});
const { data } = await response.json();

data.conversations.forEach(conv => {
    console.log(`${conv.name}: ${conv.unread_count} 条未读消息`);
    if (conv.last_message) {
        console.log(`最后消息: ${conv.last_message.content}`);
    }
});
```

### 3. 标记所有消息为已读

```javascript
await fetch('/chat/mark-read', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        c: conversationId
        // 不传 message_ids 则标记所有未读消息
    })
});
```

### 4. 会话设置（静音、置顶）

```javascript
// 置顶并静音某个会话
await fetch('/chat/member/settings', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        c: conversationId,
        pinned: true,
        mute: true
    })
});
```

---

## 注意事项

1. **WebSocket 连接管理**
   - 每个会话需要单独的 WebSocket 连接
   - 建议在进入聊天页面时建立连接，离开时关闭
   - 断线后需要重新连接

2. **消息已读状态**
   - 打开会话时应调用 `mark-read` 接口
   - WebSocket 消息不会自动标记为已读
   - 已读状态是针对每个用户的

3. **消息删除**
   - 删除是软删除，只对当前用户隐藏
   - 删除后该消息在历史记录中不会返回
   - 无法删除他人的消息，只能隐藏

4. **图片和表情**
   - 图片需要先上传获取 URL，再发送消息
   - 表情可以直接发送 Unicode 字符
   - 图片处理（压缩、缩略图）由前端负责

5. **性能优化**
   - 历史消息建议分页加载
   - 会话列表可以缓存，定期刷新
   - WebSocket 消息建议防抖处理

---

## 数据库迁移

在使用新的 models 之前，需要执行数据库迁移：

```bash
# 生成迁移文件
python manage.py makemigrations chat

# 应用迁移
python manage.py migrate chat

# 加载测试数据（可选）
python manage.py loaddata chat/fixtures/initial_data.json
```
