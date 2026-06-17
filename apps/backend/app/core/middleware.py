import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.security import decode_token
from app.core.config import settings as _settings

_IS_PRODUCTION = _settings.app_env == "production"


# Endpoint group → (limit, window_seconds)
RATE_LIMITS = {
    "auth": (10, 60),
    "attendance": (5, 60),
    "write": (30, 60),
    "read": (60, 60),
}

# Login/refresh are excluded in development — repeated attempts during testing
# otherwise hit the auth bucket and block sign-in with HTTP 429.
AUTH_LOGIN_PATHS = {"/api/v1/auth/login", "/api/v1/auth/refresh"}

# URL path prefix → endpoint group
ENDPOINT_GROUPS = {
    "/api/v1/auth": "auth",
    "/api/v1/attendance": "attendance",
    "/api/v1/sessions": "write",
}

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Body size limits per endpoint (in bytes)
BODY_SIZE_LIMITS = {
    "default": 1 * 1024 * 1024,  # 1 MB
    "/api/v1/faces/enroll": 10 * 1024 * 1024,  # 10 MB
    "/api/v1/courses": 10 * 1024 * 1024,  # 10 MB (for CSV uploads)
}


def _get_endpoint_group(path: str, method: str) -> str:
    """Map a request path + method to an endpoint group."""
    for prefix, group in ENDPOINT_GROUPS.items():
        if path.startswith(prefix):
            return group
    if method in WRITE_METHODS:
        return "write"
    return "read"


def _get_body_size_limit(path: str) -> int:
    """Get the maximum body size for a given path."""
    for prefix, limit in BODY_SIZE_LIMITS.items():
        if path.startswith(prefix):
            return limit
    return BODY_SIZE_LIMITS["default"]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-user rate limiting using Redis INCR with TTL."""

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        if path in ("/health", "/metrics", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        if not _IS_PRODUCTION and path in AUTH_LOGIN_PATHS:
            return await call_next(request)

        method = request.method.upper()
        group = _get_endpoint_group(path, method)
        limits = RATE_LIMITS if _IS_PRODUCTION else {
            **RATE_LIMITS,
            "auth": (60, 60),
        }
        limit, window = limits[group]

        # Extract user_id from JWT, fallback to client IP
        user_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ", 1)[1]
                payload = decode_token(token)
                if payload.get("type") == "access":
                    user_id = payload.get("sub")
            except (ValueError, Exception):
                pass

        if user_id:
            key = f"rate_limit:{user_id}:{group}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            key = f"rate_limit:ip:{client_ip}:{group}"

        try:
            from app.core.redis import get_redis

            r = await get_redis()
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            results = await pipe.execute()

            count = results[0]
            if count > limit:
                retry_after = window
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={"Retry-After": str(retry_after)},
                )
        except Exception:
            pass

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable):
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # CSP — allow CDN scripts and styles, camera for QR/face
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://api.fontshare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://api.fontshare.com; "
            "connect-src 'self' ws: wss:; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:;"
        )

        # Permissions
        response.headers["Permissions-Policy"] = (
            "camera=(self), geolocation=(self), microphone=()"
        )

        # HSTS only in production
        if _IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


class RequestBodySizeMiddleware(BaseHTTPMiddleware):
    """Limit request body size per endpoint."""

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        if path in ("/health", "/metrics", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            limit = _get_body_size_limit(path)
            if size > limit:
                limit_mb = limit / (1024 * 1024)
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request body too large. Maximum is {limit_mb:.0f} MB."
                    },
                )

        return await call_next(request)