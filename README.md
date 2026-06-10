<div align="center">

# MrFan IM

A full-stack instant messaging application.

**[English](#tech-stack) | [中文](#技术栈)**

</div>

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 · React 19 · TypeScript · pnpm |
| Backend | Django 5 · Django Channels · Daphne |
| Database | SQLite (dev) |
| Real-time | WebSocket |
| Auth | Custom JWT (HMAC-SHA256) |
| Deployment | Docker · Docker Compose |

## Features

- User registration, login, profile editing, account deactivation
- Friend search, requests, accept/reject, unfriend, friend groups
- Private and group chat with role management (owner/admin/member)
- Rich messages: text, image, emoji with read receipts, edit, recall, delete
- Group management: announcements, nicknames, invite, role assignment, ownership transfer
- Real-time WebSocket delivery with online presence tracking

## Quick Start

### Docker Compose (Recommended)

```bash
cp .env.example .env
docker compose up --build
```

Visit http://localhost:3000

### Manual Setup

Prerequisites: Python 3.11+, Node.js 22+, pnpm

```bash
cp .env.example .env

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations account friend chat
python manage.py migrate
daphne -b 0.0.0.0 -p 8000 im.asgi:application

# Frontend (new terminal)
cd frontend
corepack enable && pnpm install && pnpm dev
```

### Testing

```bash
# Backend
cd backend && bash test.sh

# Frontend
cd frontend && pnpm test
```

## Project Structure

```
mrfan/
├── backend/
│   ├── account/      # User auth & profile
│   ├── chat/         # Messaging, conversations, WebSocket
│   ├── friend/       # Friend relationships & groups
│   ├── im/           # Django settings & ASGI config
│   └── utils/        # JWT, networking, constants
├── frontend/
│   └── src/
│       ├── app/          # Next.js App Router pages
│       ├── components/   # React UI components
│       ├── context/      # React Context (auth, WebSocket)
│       ├── types/        # TypeScript type definitions
│       └── utils/        # API helpers, validators
└── docker-compose.yml
```

## License

MIT — see [LICENSE](LICENSE).

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 15 · React 19 · TypeScript · pnpm |
| 后端 | Django 5 · Django Channels · Daphne |
| 数据库 | SQLite（开发） |
| 实时通信 | WebSocket |
| 认证 | 自实现 JWT（HMAC-SHA256） |
| 部署 | Docker · Docker Compose |

## 核心功能

- 用户注册、登录、信息编辑、账号注销
- 好友搜索、申请、同意/拒绝、删除、好友分组
- 私聊与群聊，群角色管理（群主/管理员/成员）
- 富消息：文本/图片/表情，支持已读、编辑、撤回、删除
- 群组管理：公告、昵称、邀请、角色设置、群主转让
- WebSocket 实时推送与在线状态追踪

## 快速开始

### Docker Compose（推荐）

```bash
cp .env.example .env
docker compose up --build
```

访问 http://localhost:3000

### 手动启动

前置条件：Python 3.11+、Node.js 22+、pnpm

```bash
cp .env.example .env

# 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations account friend chat
python manage.py migrate
daphne -b 0.0.0.0 -p 8000 im.asgi:application

# 前端（新终端）
cd frontend
corepack enable && pnpm install && pnpm dev
```

### 测试

```bash
# 后端
cd backend && bash test.sh

# 前端
cd frontend && pnpm test
```

## 项目结构

```
mrfan/
├── backend/
│   ├── account/      # 用户认证与资料
│   ├── chat/         # 消息、会话、WebSocket
│   ├── friend/       # 好友关系与分组
│   ├── im/           # Django 配置与 ASGI
│   └── utils/        # JWT、网络工具、常量
├── frontend/
│   └── src/
│       ├── app/          # Next.js 页面路由
│       ├── components/   # React UI 组件
│       ├── context/      # React Context（认证、WebSocket）
│       ├── types/        # TypeScript 类型定义
│       └── utils/        # API 辅助、校验器
└── docker-compose.yml
```

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
