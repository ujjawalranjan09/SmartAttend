# Deployment Guide

## Quick Start (Docker Compose)

```bash
# Clone repository
git clone https://github.com/ujjawalranjan09/SmartAttend.git
cd SmartAttend

# Copy environment file
cp .env.example .env
# Edit .env with your secrets

# Start all services
docker-compose up --build -d

# Run database migrations
docker-compose exec api alembic upgrade head

# Check all services are healthy
curl http://localhost:8000/health
curl http://localhost:8001/health
```

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 8080 | Vanilla JS SPA |
| Backend API | 8000 | FastAPI backend |
| ML Service | 8001 | Face/Anomaly/Forecast |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache & pub/sub |
| Celery Worker | - | Async task processing |
| Flower | 5555 | Celery monitoring |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | JWT signing key (32+ chars) |
| `DATABASE_URL` | Yes | - | PostgreSQL async URL |
| `REDIS_URL` | Yes | - | Redis connection URL |
| `ML_SERVICE_URL` | No | http://localhost:8001 | ML service endpoint |
| `APP_ENV` | No | development | Environment |
| `SENTRY_DSN` | No | - | Error tracking |
| `SMTP_HOST` | No | smtp.gmail.com | Email server |
| `SMTP_USER` | No | - | SMTP username |
| `SMTP_PASSWORD` | No | - | SMTP password |
| `VAPID_PUBLIC_KEY` | No | - | Web Push public key |
| `VAPID_PRIVATE_KEY` | No | - | Web Push private key |

## Deployment Options

### Option 1: Docker Compose (Recommended for Staging)

```bash
# Production compose
docker-compose -f docker-compose.yml -f infra/docker-compose.prod.yml up -d
```

### Option 2: Render

1. Create a PostgreSQL instance on Render
2. Create a Redis instance on Render
3. Create a Web Service for the backend:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Create a Web Service for the frontend (static site)
5. Set environment variables in Render dashboard

### Option 3: AWS ECS

1. Build Docker images and push to ECR:
   ```bash
   docker build -t smartattend-api ./apps/backend
   docker build -t smartattend-ml ./apps/ml-service
   docker build -t smartattend-frontend ./apps/frontend
   ```
2. Create ECS task definitions for each service
3. Set up RDS PostgreSQL and ElastiCache Redis
4. Configure ALB with SSL termination

## Database Migrations

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Rollback
docker-compose exec api alembic downgrade -1
```

## Backup & Restore

### Database Backup
```bash
# Automatic backup (runs daily via Celery Beat)
docker-compose exec db pg_dump -U smartattend smartattend > backup_$(date +%Y%m%d).sql

# Restore
cat backup.sql | docker-compose exec -T db psql -U smartattend
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