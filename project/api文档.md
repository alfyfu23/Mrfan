# 前后端通信文档

此文档为详细版api文档

## 返回码一览

#### HTTP返回码
| 200 | OK                 |                               |
|-----|--------------------|-------------------------------|
| 201 | Created            | POST创建新数据                |
| 202 | Accepted           | 请求成功，但还未执行（用于异步） |
| 302 | Found              | 重定向                        |
| 400 | Bad Request        | 请求格式错误                  |
| 401 | Unauthorized       | 身份未认证                    |
| 403 | Forbidden          | 身份已认证，但没有权限         |
| 404 | Not Found          | 资源不存在                    |
| 405 | Method Not Allowed | 请求方法错误                  |

#### 业务返回码
- 0: 成功
- 登录&注册相关
    - 1001: 注册失败，用户名或密码缺失
    - 1002: 注册失败，用户名被占用
    - 1003: 登录失败，用户名不存在
    - 1004: 登录失败，密码错误
- 查询个人信息相关
    - 1101: JWT解析错误
    - 1102: 用户不存在
- 消息发送相关
    - 2001: 消息不合法
    - 2002: 身份验证失败
    - 2003: 聊天室不存在
    - 2004: 好友不存在
    - 2010: 进入会话时JWT token验证失败 / url格式错误（没有token或者c）
    - 2011: 会话不存在（用户试图加入不存在的会话时报错）
    - 2012: 无权进入会话（用户试图进入没有权限的会话时报错）
- 历史记录相关
    - 3001: 消息缺少Autorization
    - 3002: JWT Token认证失败
    - 3003: conversation不存在
    - 3004: 用户不属于此会话
- 好友相关
    - 4001: 身份验证失败
    - 4002: 试图添加重复的好友
    - 4003: 试图添加不存在的人为好友
    - 4004: 试图重复邀请
    - 4005: 试图同意不存在的好友申请
    - 4006: 试图添加自己为好友

- 好友相关
    - 4001: 身份验证失败
    - 4002: 试图添加重复的好友
    - 4003: 试图添加不存在的人为好友
    - 4004: 试图重复邀请
    - 4005: 试图同意不存在的好友申请
    - 4006: 试图添加自己为好友

- 其他内部错误
    - 9001: 找不到用户数据（在jwt验证成功时）（可能是数据库损坏导致）

# API文档与通信流程

## 登录 & 注册
### 注册
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant UDB as User Database

    F->>B: POST /register
    Note right of F: Body: {"username":"admin","password":"xxx"}
    B->>UDB: 查询用户名
    UDB-->>B: 返回用户数据
    alt 注册成功
        B-->>F: 200, {"jwt_token":"xxx","code":0}
        B-->>UDB: 创建用户
    else 用户名+密码的请求格式错误
        B-->>F: 400, {"code":1001, "info":"Invalid request. Username or password not found."}
    else 用户名已存在
        B-->>F: 400, {"code":1002, "info":"Username already exists"}
    end
```

### 登录
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant UDB as User Database

    F->>B: POST /login
    Note right of F: Body: {"username":"admin","password":"xxx"}
    B->>UDB: 查询用户
    UDB-->>B: 返回用户数据
    alt 登录成功
        B-->>F: 200, {"jwt_token":"xxx","code":0, "username":"xxx", "id":user_id}
    else 用户名+密码的请求格式错误
        B-->>F: 400, {"code":1001, "info":"Invalid request. Username or password not found."}    
    else 用户不存在
        B-->>F: 404, {"code":1003, "info":"Username does not exist"}
    else 密码错误
        B-->>F: 400, {"code":1004, "info":"Wrong password"}
    end
```

### 上传个人Profile
**TODO: 上传Avatar和Info**

## 好友 & 个人信息

注意，所有user在登录的时候，要主动向服务器请求好友信息，以备有任何变更、新的申请。

### 搜索指定人
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant FDB as Friendship Database
    
    F->>B: GET/friend/search/<username>
    Note right of F: Body: {"jwt_token": "xxx"}
    B-->>F: JWT令牌错误
    Note right of F: 400，{"code":4001, "info":"Invalid JWT Token"}
    B-->>F: 搜索：精确匹配与模糊匹配
    Note right of F: 200，{"code":0, "data":{ "fuzzy":[模糊id],"exact":[精确id] } }
```

### 申请添加好友
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant FDB as Friendship Database
    
    F->>B: POST/friend/add/<id>
    Note right of F: Body: {"jwt_token": "xxx"}
    B-->>F: JWT令牌错误
    Note right of F: 400，{"code":4001, "info":"Invalid JWT Token"}
    B-->>F: 不能添加自己为好友
    Note right of F: 400, {"code":4006, "info":"Cannot befriend oneself."}
    par
        B-->>F: 申请人不存在
        B-->>FDB: 可能为数据库损坏，内部报错
    end
    Note right of F: 500, {"code":9001, "info":"User not found."}
    B-->>F: 添加人不存在
    Note right of F: 404, {"code":4003, "info":"User does not exist."}
    B-->>F: 已经是好友，不能再添加
    Note right of F: 400, {"code":4002, "info":"Users are already friends."}
    B-->>F: 已经发送过好友申请
    Note right of F: 400, {"code":4004, "info":"Pending invitation already exists."}
    B-->>F: 互相发送申请，自动变为好友
    Note right of F: 200，{"code":0}
    B-->>F: 询问被申请方
    F->>B: 对方回复
    alt 对方拒绝--还未撰写本部分
        F->>B: 对方: NO
        B-->>F: 告知申请被拒绝
    else 对方同意
        F->>B: POST/friend/agree/<id>
        Note right of F: Body: {"jwt_token": "xxx"}
        B-->>F: JWT令牌错误
        Note right of F: 400，{"code":4001, "info":"Invalid JWT Token"}
        par
            B-->>F: 申请人不存在
            B-->>FDB: 可能为数据库损坏，内部报错
        end
        Note right of F: 500, {"code":9001, "info":"User not found."}
        B-->>F: 添加人不存在
        Note right of F: 404, {"code":4003, "info":"User does not exist."}
        B-->>F: 不存在好友申请
        Note right of F: 400，{"code":4005, "info":"Pending invitation does not exist."}
        B-->>F: 已经是好友，无法通过申请
        Note right of F: 400，{"code":4002, "info":"Users are already friends"}
        F->>B: 对方: YES
        B->>FDB: 记录好友关系
        B-->>F: 告知申请被同意，并更新两人的好友信息
    end
```

### 同意好友申请
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant FDB as Friendship Database
    
    F->>B: POST /friend/agree?id=x
    Note right of F: Body: {"jwt_toekn": "xxx"}
    
    B-->>FDB: 试图同意Pending
    FDB->>B: Pending结果
    alt 操作失败
        B-->>F: 告知申请被拒绝
    else 对方同意
        F->>B: 对方: YES
        B->>FDB: 记录好友关系
        B-->>F: 告知申请被同意，并更新两人的好友信息
    end
```

### 获得好友列表
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant FDB as Friendship Database
    
    F->>B: GET/friend/list
    Note right of F: Body: {"jwt_token": "xxx"}
    B-->>F: JWT令牌错误
    Note right of F: 400，{"code":4001, "info":"Invalid JWT Token"}
    B->>FDB: 查询好友列表
    FDB->>B: 查询结果 
    B->>F: 好友列表
    Note right of F: 200, {"code":0, "data": {"friends": ["id1", "id2"], "pending": ["id3", "id4"] } } 
```

### 请求个人信息
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant UDB as User Database
    
    F->>B: GET /account/info
    Note right of F: Body: {"jwt_token": "xxx"}
    B->>UDB: 查询个人信息
    B->>F: JWT令牌解析错误
    Note right of F: 403, {"code":1101, "info":Invalid JWT Token}
    B->>F: 用户不存在
    Note right of F: 404, {"code":1102, "info":User does not exist.}
    UDB->>B: 查询结果 
    B->>F: 个人信息
    Note right of F: {name: xxx, avatar: url, info: ...}
```

## 消息

### 请求创建好友会话
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant MDB as Message Database
    participant FDB as Friend Database

    F->>B: GET /message/friend
    Note right of F: Body: {"jwt_token": xx, "to": 对方id}
    B-->>FDB: 验证好友身份
    FDB-->>B: 验证结果
    alt 验证成功
        B-->>MDB: 请求创建会话
        MDB-->>B: 创建成功
        B->>F: 200, {'code': 400, "data": {"id": 会话id}}
    else 验证失败
        B->>F: 403
    end
```

### 请求创建群组会话
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant MDB as Message Database
    participant FDB as Friend Database

    F->>B: GET /message/friend
    Note right of F: Body: {"jwt_token": xx, "to": 对方id}
    B-->>FDB: 验证好友身份
    FDB-->>B: 验证结果
    alt 验证成功
        B-->>MDB: 请求创建会话
        MDB-->>B: 创建成功
        B->>F: 200, {'code': 400, "data": {"id": 会话id}}
    else 验证失败
        B->>F: 403
    end
```

### 请求消息记录
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant MDB as Message Database

    F->>B: GET /message/history?c=xxx （c用于指定会话的id）
    Note right of F: Body: {'jwt_token': xx}
    alt 验证成功
        B-->>MDB: 请求历史消息记录
        MDB-->>B: 返回历史消息记录
        B->>F: 200, {'code': 0, 'data': 历史数据}
    else 提取JWT失败
        B->>F: 400, {'code': 3001, 'info': 'Authorization failed.'}
    else 无效JWT
        B->>F: 403, {'code': 3002, 'info': 'Invalid JWT Token.'}
    else 找不到User
        B->>F: 500, {'code': 9001, 'info': 'User not found.'} 
    
    else 身份验证失败,user不属于conversation
        B->>F: 403, {'code': 3004, 'info': 'User not authorized to join this conversation.'}
    else room不存在
        B->>F: 404, {'code': 3003, 'info': 'Conversation not found.'}
    end
```

### 请求创建好友会话
```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant MDB as Message Database
    participant FDB as Friend Database

    F->>B: POST /chat/create/friend
    Note right of F: Body: {"jwt_token": xx, "id": 对方id}
    B-->>FDB: 验证好友身份
    FDB-->>B: 验证结果
    alt 验证成功
        B-->>MDB: 请求创建会话
        MDB-->>B: 创建成功
        B->>F: 200, {'code': 0, "data": {"id": 会话id}}
    else 提取JWT失败
        B->>F: 400, {'code': 3001, 'info': 'Authorization failed.'}
    else 无效JWT
        B->>F: 403, {'code': 3002, 'info': 'Invalid JWT Token.'}
    else 请求体格式错误
        B->>F: 400, {'code': 2001, 'info': 'Invalid request'}
    else 找不到User
        B->>F: 500, {'code': 9001, 'info': 'User not found.'}
    else 不是好友
        B->>F: 403, {'code': 2012, 'info': 'Not authorized to create conversation.'}
    end
```

### 发送消息

使用websocket实现

```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant UDB as User Database
    participant CDB as Conversation Database
    participant MDB as Message Database

    F->>B: WebSocket connection request
    Note right of F: Query params: ?token=xxx&c=123
    B->>B: 解析 token 和 c 参数
    alt token 或 c 无效
        B-->>F: Close connection, code=2010, reason="Invalid url params."
    else token 验证失败
        B-->>F: Close connection, code=2010, reason="Invalid jwt token."
    else 会话不存在
        B-->>F: Close connection, code=2011, reason="Invalid conversation id."
    else 用户不是该会话成员
        B-->>F: Close connection, code=2012, reason="Not authorized to join conversation."
    else 成功加入会话
        B->>CDB: 查询 conversation 是否存在
        CDB-->>B: 返回 conversation 数据
        B->>MDB: 加入 channel group 并接受连接
        B-->>F: Accept connection, room_group_name="chat_123"
    end

    F->>B: Send message to backend
    Note right of F: Message format: {"message": "Hello!"} 
    B->>B: 校验消息格式
    B->>MDB: save_message(sender, message)
    alt 消息保存失败
        B-->>F: Send error: {"type": "error", "error": "server_error"}
    else 消息保存成功
        B->>MDB: 创建 Message 记录
        MDB-->>B: Return message data
        B->>CDB: 广播消息给所有成员
        CDB-->>B: Message broadcasted
        B->>F: Send message to frontend: {"message": "Hello!"} 
    end

    F->>B: WebSocket disconnect request
    B->>CDB: 从 channel group 移除
    CDB-->>B: Remove from group
    B-->>F: WebSocket disconnected
```

发送的具体消息json为
```json
payload: {
    "message": "..."
}
```
注意这里的url用于发送图片

#### 发送消息全过程示意图
```
┌──────────────────────────────────────────────────────┐
│                 用户A打开聊天界面                     │
└──────────────────────────────────────────────────────┘
             │
  [1] 前端 fetch 历史消息（HTTP）
             │
  向后端 /message/history 请求历史消息
             │
  后端从数据库 Message 取出 → 返回 JSON
             │
  前端渲染聊天记录（完成历史加载）
             │
┌────────────────────────────────────────────┐
│ [2] 前端通过 WebSocket 连接后端 /ws/chat/    │
└────────────────────────────────────────────┘
             │
后端 consumer 建立一个 WebSocket 连接对象（scope.user = A）
             │
后端将 A 加入对应的房间组 (Group)
  └── 比如: conversation_3  (一个群/私聊)
             │
┌────────────────────────────────────────────┐
│ [3] 用户 A 发送一条新消息                     │
└────────────────────────────────────────────┘
             │
前端 WebSocket send({
    "type": "chat.message",
    "conversation_id": 3,
    "content": "Hello!"
})
             │
后端 consumer 接收到消息
  ├── 保存到数据库 Message
  └── 将消息广播到该 conversation 的 group
             │
[其他成员（如用户 B）的 consumer] 收到 group 消息
             │
前端 B 的 WebSocket onmessage() 回调触发
  └── 新消息出现在聊天窗口
             │
┌────────────────────────────────────────────┐
│ [4] 用户离开聊天界面                          │
└────────────────────────────────────────────┘
             │
前端执行 websocket.close()
             │
后端 consumer 的 disconnect() 被调用
  └── 将用户从 group 移除
             │
连接关闭，结束。
```

### 接收消息
接收格式为
```json
{
    "sender": "xxx",
    "text": "......"
}
```


## 其他隐藏API

### 上传图片

前端上传一张图片到后端，后端返回url



