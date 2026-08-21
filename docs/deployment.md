# NutriQ Deployment & DevOps Runbook

## Deployment Architecture

- **Frontend Hosting**: Vercel / Netlify / Cloudflare Pages.
- **Backend API Hosting**: Render / Railway / AWS ECS / Google Cloud Run.
- **Managed Database**: PostgreSQL (v15+) with SSL enabled.

## Environment Separation
- **Development**: SQLite (`sqlite+aiosqlite:///./nutriq.db`) / Local PostgreSQL.
- **Staging**: Managed PostgreSQL on Render/Railway with automated PR review deploys.
- **Production**: High-availability PostgreSQL cluster with automated daily snapshots.

## Production Environment Variables (`.env`)
```bash
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/nutriq_prod
JWT_SECRET=production-crypto-random-256-bit-key
ANTHROPIC_API_KEY=sk-ant-api03-...
SENTRY_DSN=https://...
FCM_CONFIG={"type": "service_account", ...}
BILLING_PROVIDER_KEY=sk_live_...
SAFE_MIN_CALORIES=1200
AI_DAILY_LIMIT_FREE=15
AI_DAILY_LIMIT_PREMIUM=200
```

## Running with Docker Compose
```bash
docker-compose up --build -d
```
