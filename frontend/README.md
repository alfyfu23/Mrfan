# Frontend

Next.js 15 + React 19 + TypeScript frontend for the MrFan IM system.

## Setup

```bash
corepack enable
pnpm install
pnpm dev
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_BACKEND_URL` | Backend host (e.g. `localhost:8000`) | `localhost:8000` |

## Scripts

| Command | Description |
|---------|-------------|
| `pnpm dev` | Start development server |
| `pnpm build` | Production build |
| `pnpm start` | Start production server |
| `pnpm lint` | Run ESLint |
| `pnpm test` | Run tests |
| `pnpm test:coverage` | Run tests with coverage |
