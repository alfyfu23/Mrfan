# MrFan 即时通讯系统

一个前后端分离的即时通讯系统课程项目，包含用户管理、好友关系、私聊/群聊、消息状态、群管理等功能。

## 仓库结构

```text
mrfan/
├── backend/      # Django + Channels 后端
└── frontend/     # Next.js 前端
```

## 技术栈

- 后端：Django 5 + Channels + Daphne + SQLite
- 前端：Next.js 15 + React 19 + TypeScript + pnpm
- 通信：HTTP REST + WebSocket

## 核心功能

- 用户注册、登录、信息编辑、账号注销
- 好友搜索、申请、同意/拒绝、删除、分组
- 私聊与群聊会话管理
- 文本/图片/表情等消息发送
- 消息已读、编辑、撤回、删除
- 群公告、群昵称、成员邀请、管理员设置、群主转让

## 快速开始

### 1. 启动后端（本地）

推荐 Python 3.11。

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 初始化数据库
python manage.py makemigrations
python manage.py migrate

# 运行 ASGI 服务（本地开发建议使用 8000 端口）
daphne -b 0.0.0.0 -p 8000 im.asgi:application
```

可选：使用项目脚本（会自动迁移并启动）

```bash
cd backend
bash start.sh
```

说明：`start.sh` 默认监听 80 端口，某些环境下可能需要更高权限。

### 2. 启动前端（本地）

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

默认访问：<http://localhost:3000>

## 前后端联调说明

当前前端代码默认请求线上后端域名 `backend-mrfan.app.secoder.net`（见 `frontend/src/constant/strings.tsx`），并广泛使用 `https://` 与 `wss://`。

如果你要完整联调本地后端，需要统一调整前端请求地址与协议（例如改为本地 host，并将 `https/wss` 改为 `http/ws`）。

## Docker 运行（可选）

### 后端

```bash
cd backend
docker build -t mrfan-backend .
docker run --rm -p 8000:80 mrfan-backend
```

### 前端

```bash
cd frontend
docker build -t mrfan-frontend .
docker run --rm -p 3000:80 mrfan-frontend
```

## 测试

### 后端

```bash
cd backend
bash test.sh
```

输出：

- `backend/xunit-reports/xunit-result.xml`
- `backend/coverage-reports/coverage.xml`

### 前端

```bash
cd frontend
pnpm test
pnpm test:coverage
```

## 文档索引

- 后端 API 文档：`backend/CHAT_API_DOCUMENTATION.md`
- 后端说明：`backend/README.md`
- 前端说明：`frontend/README.md`
- 项目需求与交付文档：`project/`

## 备注

- 后端数据库默认位于 `backend/data/db.sqlite3`
- 用户上传媒体文件默认位于 `backend/media/`
- 开发阶段 CORS 配置较宽松，仅适合开发与测试环境
