# Frontend 前端


## 预计的项目结构
```
frontend/
├── public/                   # 静态资源
│   └── icons/
│       └── favicon.ico
├── src/
│   ├── app/                  # Next.js App Router 页面入口
│   │   ├── layout.tsx
│   │   ├── page.tsx          # 首页（登录或聊天页）
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── chat/
│   │   │   ├── page.tsx      # 聊天主界面
│   │   │   ├── layout.tsx    # 聊天模块通用布局
│   │   │   └── [id]/page.tsx # 单个聊天会话
│   │   └── api/
│   │       ├── auth/
│   │       │   ├── register/route.ts
│   │       │   └── login/route.ts
│   │       ├── messages/
│   │       │   └── route.ts
│   │       └── users/
│   │           └── route.ts
│   ├── components/            # 可复用的 UI 组件
│   │   ├── ChatInput.tsx
│   │   ├── MessageList.tsx
│   │   ├── UserAvatar.tsx
│   │   ├── Sidebar.tsx
│   │   └── Navbar.tsx
│   ├── store/                 # 全局状态（Zustand/Redux）
│   │   └── userStore.ts
│   ├── lib/                   # 工具 & 底层逻辑
│   │   ├── db.ts              # 数据库连接（Prisma/Drizzle）
│   │   ├── auth.ts            # 用户鉴权逻辑
│   │   ├── socket.ts          # WebSocket 客户端封装
│   │   └── utils.ts           # 工具函数
│   ├── types/                 # 类型定义
│   │   ├── message.ts
│   │   └── user.ts
│   └── styles/
│       └── globals.css
├── tests/                     # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── .env.local                 # 环境变量
├── next.config.ts
├── package.json
└── tsconfig.json
```