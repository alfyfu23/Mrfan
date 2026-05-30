<div align="center">

# MrFan IM

A full-stack instant messaging application with real-time communication, group management, and social features.

**[English](#overview) | [中文](#项目简介)**

</div>

---

## Overview

MrFan IM is a modern instant messaging system built with a decoupled frontend-backend architecture. It supports private and group chats, friend management, real-time messaging via WebSocket, and rich message operations (read receipts, editing, recall, deletion).

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15 · React 19 · TypeScript · pnpm |
| **Backend** | Django 5 · Django Channels · Daphne (ASGI) |
| **Database** | SQLite (development) |
| **Real-time** | WebSocket (Django Channels) |
| **Auth** | Custom JWT (HMAC-SHA256) |
| **Deployment** | Docker · Docker Compose |

### Architecture

```
┌─────────────────┐     HTTP REST      ┌─────────────────┐
│                 │ ◄──────────────► │                 │
│   Next.js SPA   │                   │   Django API    │
│   (React 19)    │                   │   (ASGI/Daphne) │
│                 │ ◄──────────────► │                 │
└─────────────────┘    WebSocket      └────────┬────────┘
                                                │
                                         ┌──────▼──────┐
                                         │   SQLite    │
                                         └─────────────┘
```

### Key Features

- **User System** — Registration, login, profile editing, account deactivation (soft-delete)
- **Friend System** — Search, request, accept/reject, unfriend, friend groups
- **Private & Group Chat** — Create conversations, group management with roles (owner/admin/member)
- **Rich Messaging** — Text, image, emoji messages with read receipts, editing, recall, and deletion
- **Group Management** — Announcements, nicknames, member invitation, role assignment, ownership transfer
- **Real-time** — WebSocket-based instant message delivery with online presence tracking

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 22+ & pnpm
- Docker (optional)

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your own secret keys
```

### 2. Start Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize database
python manage.py makemigrations account friend chat
python manage.py migrate

# Start ASGI server
daphne -b 0.0.0.0 -p 8000 im.asgi:application
```

### 3. Start Frontend

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

Visit http://localhost:3000

### Docker Compose (Alternative)

```bash
docker compose up --build
```

### Testing

**Backend:**

```bash
cd backend
bash test.sh
```

**Frontend:**

```bash
cd frontend
pnpm test
pnpm test:coverage
```

## Repository Structure

```
mrfan/
├── backend/              # Django + Channels backend
│   ├── account/          # User auth & profile
│   ├── chat/             # Messaging, conversations, groups, WebSocket
│   ├── friend/           # Friend relationships & groups
│   ├── im/               # Django project settings & ASGI config
│   └── utils/            # JWT, networking, constants
├── frontend/             # Next.js frontend
│   └── src/
│       ├── app/          # Next.js App Router pages
│       ├── components/   # React UI components
│       ├── context/      # React Context (auth, WebSocket state)
│       ├── types/        # TypeScript type definitions
│       └── utils/        # API helpers, validators
└── docker-compose.yml
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 项目简介

MrFan 即时通讯系统是一个前后端分离的全栈即时通讯应用，支持私聊/群聊、好友管理、实时 WebSocket 通信以及丰富的消息操作（已读、编辑、撤回、删除）。

### 技术亮点

- 基于 Django Channels + WebSocket 的实时双向通信
- 自实现 JWT（HMAC-SHA256）认证机制
- 消息已读回执、撤回、编辑等多状态管理
- 用户注销、消息删除、群解散等软删除设计
- Docker 容器化部署

### 核心功能

- **用户系统** — 注册、登录、信息编辑、账号注销（软删除）
- **好友系统** — 搜索、申请、同意/拒绝、删除、好友分组
- **私聊与群聊** — 会话创建、群角色管理（群主/管理员/成员）
- **富消息** — 文本/图片/表情，支持已读、编辑、撤回、删除
- **群组管理** — 群公告、群昵称、成员邀请、角色设置、群主转让
- **实时通信** — WebSocket 即时消息推送与在线状态追踪

### 快速开始

```bash
# 配置环境变量
cp .env.example .env

# 启动后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations account friend chat
python manage.py migrate
daphne -b 0.0.0.0 -p 8000 im.asgi:application

# 启动前端
cd frontend
corepack enable && pnpm install && pnpm dev
```

访问 http://localhost:3000

### 许可证

本项目基于 MIT 许可证开源，详见 [LICENSE](LICENSE) 文件。
