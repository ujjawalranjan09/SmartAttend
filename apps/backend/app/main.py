from contextlib import asynccontextmanager
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.errors import AppError, app_error_handler, general_error_handler
from app.core.logging import RequestIDMiddleware, setup_logging
from app.core.audit import setup_audit_listeners
from app.core.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestBodySizeMiddleware,
)
from app.core.profiling import ProfilingMiddleware
from app.api.v1 import (
    alerts,
    auth,
    attendance,
    departments,
    sessions,
    students,
    faculty,
    analytics,
    reports,
    notifications,
    institutions,
    courses,
    timetable,
    push,
    faces,
    admin as admin_api,
    student_profile,
    daily_plan,
    display,
)
from app.websocket.handlers import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    if settings.sentry_dsn:
        try:
            sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
        except Exception as e:  # BadDsn or other config errors shouldn't crash the app
            print(f"WARNING: Sentry init failed ({e}); continuing without Sentry.", flush=True)
    setup_audit_listeners()
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

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, general_error_handler)

# CORS
# In production, allow either a configured frontend origin (FRONTEND_URL env var),
# the smartattend.in domain, or any *.onrender.com static site (for hosted deploys).
#
# NOTE: CORSMiddleware is added LAST so it is the OUTERMOST middleware. Starlette
# runs middleware in reverse-add order (last added = outermost). If CORS were
# innermost (added first), any 500 raised by an outer middleware/handler would
# be returned WITHOUT CORS headers, so the browser would block it and mask the
# real error behind a generic CORS failure. Adding it last ensures error
# responses still carry Access-Control-Allow-Origin.
_prod_origins = ["https://app.smartattend.in"]
if getattr(settings, "frontend_url", ""):
    _prod_origins.append(settings.frontend_url.rstrip("/"))

# Request ID tracking
app.add_middleware(RequestIDMiddleware)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request body size limits
app.add_middleware(RequestBodySizeMiddleware)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# GZip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Profiling (development only)
app.add_middleware(ProfilingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    if settings.app_env == "development"
    else _prod_origins,
    allow_origin_regex=r"^https://[a-z0-9-]+\.onrender\.com$"
    if settings.app_env != "development"
    else None,
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
app.include_router(
    notifications.router, prefix="/api/v1/notifications", tags=["Notifications"]
)
app.include_router(
    institutions.router, prefix="/api/v1/institutions", tags=["Institutions"]
)
app.include_router(courses.router, prefix="/api/v1/courses", tags=["Courses"])
app.include_router(
    departments.router, prefix="/api/v1/departments", tags=["Departments"]
)
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(timetable.router, prefix="/api/v1/timetable", tags=["Timetable"])
app.include_router(push.router, prefix="/api/v1/push", tags=["Push Notifications"])
app.include_router(faces.router, prefix="/api/v1/faces", tags=["Face Enrollment"])
app.include_router(admin_api.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(
    student_profile.router, prefix="/api/v1/students", tags=["Student Profile"]
)
app.include_router(daily_plan.router, prefix="/api/v1/students", tags=["Daily Plan"])
app.include_router(display.router, prefix="/api/v1", tags=["Display"])

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
        from app.core.redis import get_redis

        r = await get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
        checks["status"] = "degraded"
    # ML service check
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.ml_service_url}/health")
            checks["ml_service"] = "ok" if resp.status_code == 200 else "error"
    except Exception:
        checks["ml_service"] = "unavailable"
    status_code = 200 if checks["status"] == "ok" else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(content=checks, status_code=status_code)