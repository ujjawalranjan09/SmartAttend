from contextlib import asynccontextmanager
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.api.v1 import auth, attendance, sessions, students, faculty, analytics, reports
from app.websocket.handlers import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
    yield
    # Shutdown — clean up connections if needed


app = FastAPI(
    title="SmartAttend API",
    description="AI-Augmented Student Attendance Monitoring & Analytics Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else ["https://app.smartattend.in"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# API Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["Sessions"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])
app.include_router(students.router, prefix="/api/v1/students", tags=["Students"])
app.include_router(faculty.router, prefix="/api/v1/faculty", tags=["Faculty"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])

# WebSocket
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])


@app.get("/health", tags=["Health"])
async def health_check():
    checks = {"status": "ok", "service": settings.app_name, "env": settings.app_env}
    # DB check
    try:
        import sqlalchemy as sa
        from app.core.database import async_engine
        async with async_engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        checks["status"] = "degraded"
    # Redis check
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
        checks["status"] = "degraded"
    status_code = 200 if checks["status"] == "ok" else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(content=checks, status_code=status_code)
