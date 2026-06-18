# Deployment Guide

## Quick Start (Docker Compose)

```bash
# Clone repository
git clone https://github.com/ujjawalranjan09/SmartAttend.git
cd SmartAttend

# Copy environment file
cp .env.example .env
# Edit .env with your secrets

# Start all services (builds images, runs migrations automatically)
docker compose up --build -d

# Check all services are healthy
curl http://localhost:8000/health
curl http://localhost:8001/health
```

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 5173 | React 19 + Vite 6 SPA |
| Backend API | 8000 | FastAPI backend |
| ML Service | 8001 | Face/Anomaly/Forecast |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache & pub/sub |
| Celery Worker | - | Async task processing |
| Celery Beat | - | Scheduled task runner |
| Flower | 5555 | Celery monitoring |

## Environment Variables

See [`.env.example`](../.env.example) at the repo root for the full template.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | JWT signing key (32+ chars) |
| `DATABASE_URL` | Yes | - | PostgreSQL async URL |
| `REDIS_URL` | Yes | - | Redis connection URL |
| `CELERY_BROKER_URL` | Yes | - | Celery broker (Redis DB 1) |
| `CELERY_RESULT_BACKEND` | Yes | - | Celery results (Redis DB 2) |
| `ML_SERVICE_URL` | No | http://localhost:8001 | ML service endpoint |
| `APP_ENV` | No | development | Environment |
| `QR_TOKEN_TTL_SECONDS` | No | 30 | QR code expiration time |
| `SENTRY_DSN` | No | - | Error tracking |
| `SMTP_HOST` | No | smtp.gmail.com | Email server |
| `SMTP_USER` | No | - | SMTP username |
| `SMTP_PASSWORD` | No | - | SMTP password |
| `OPENROUTER_API_KEY` | No | - | LLM API key (AI suggestions) |
| `OPENROUTER_MODEL` | No | google/gemma-4-26b-a4b-it:free | LLM model |

## Deployment Options

### Option 0: Vercel (Free Tier — Frontend Only)

Best for deploying the React frontend quickly. The backend runs on a separate host.

**Frontend on Vercel:**
1. Push repo to GitHub
2. Import into [vercel.com](https://vercel.com)
3. Set env var: `BACKEND_URL` = your backend URL (e.g. `https://smartattend-api.onrender.com`)
4. Deploy

**Backend on Render (free tier):**
1. Create PostgreSQL + Redis on Render
2. Create Web Service → `apps/backend/`:
   - Build: `pip install -r requirements.txt && alembic upgrade head`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Create Worker Service for Celery:
   - Start: `celery -A app.tasks.celery_app.celery_app worker --loglevel=info -Q default,ml,ml_scoring,reports,notifications`

**Vercel free tier limitations:**
- No WebSockets (live session feed unavailable)
- No persistent processes (Celery can't run here)
- 10s function timeout
- API proxy uses `api/index.py` (stdlib-only, forwards to your backend)

**How it works:** `vercel.json` rewrites `/api/v1/*` to a serverless Python function that proxies requests to `BACKEND_URL`. The frontend reads `VITE_API_BASE` (defaults to `/api/v1`).

### Option 1: Docker Compose (Recommended for Staging)

```bash
docker compose up --build -d
```

Migrations run automatically on API startup. No manual `alembic upgrade head` needed.

### Option 2: Render

1. Create a PostgreSQL instance on Render
2. Create a Redis instance on Render
3. Create a Web Service for the backend:
   - Build Command: `pip install -r requirements.txt && alembic upgrade head`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Create a separate Web Service for Celery worker:
   - Start Command: `celery -A app.tasks.celery_app.celery_app worker --loglevel=info -Q default,ml,ml_scoring,reports,notifications`
5. Create a separate Web Service for Celery beat:
   - Start Command: `celery -A app.tasks.celery_app.celery_app beat --loglevel=info`
6. Create a Static Site for the frontend (`npm run build`)
7. Set environment variables in Render dashboard

### Option 3: AWS ECS

1. Build Docker images and push to ECR:
   ```bash
   docker build -t smartattend-api ./apps/backend
   docker build -t smartattend-ml ./apps/ml-service
   ```
2. Create ECS task definitions for each service
3. Set up RDS PostgreSQL and ElastiCache Redis
4. Configure ALB with SSL termination

## Database Migrations

```bash
# Run migrations (automatic with Docker, manual for local)
cd apps/backend
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback
alembic downgrade -1
```

## Backup & Restore

### Database Backup
```bash
# Manual backup
docker compose exec db pg_dump -U smartattend smartattend > backup_$(date +%Y%m%d).sql

# Restore
cat backup.sql | docker compose exec -T db psql -U smartattend
```

### Redis Backup
Redis AOF persistence is enabled by default. Backup files are in `redis_data/` volume.

## Monitoring

- **Health Check:** `GET /health` — returns DB, Redis, ML service status
- **Metrics:** `GET /metrics` — Prometheus metrics
- **Celery:** Flower UI at `http://localhost:5555`
- **API Docs:** Swagger at `http://localhost:8000/docs`, ReDoc at `/redoc`

## Scaling

### Horizontal Scaling
- Backend: Add more uvicorn workers: `--workers 4`
- WebSocket: Redis pub/sub handles multi-worker delivery
- Celery: Add more worker instances for higher throughput

### Vertical Scaling
- Increase PostgreSQL connection pool: `DATABASE_POOL_SIZE=20`
- Increase Celery concurrency: `--concurrency=8`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to database" | Check DATABASE_URL, ensure PostgreSQL is running |
| "Redis connection refused" | Check REDIS_URL, ensure Redis is running |
| "ML service unavailable" | Check ML_SERVICE_URL, ensure ml service is running |
| "Face embedding fails" | Check InsightFace model download, GPU/CPU setup |
| "429 Rate limit exceeded" | Wait or adjust RATE_LIMITS in middleware.py |
