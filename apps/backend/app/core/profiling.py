"""
Performance profiling middleware for development use.
When ?profile=true is added to a request, profiling output is returned.
"""
import time
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


class ProfilingMiddleware(BaseHTTPMiddleware):
    """
    Profile request handling time and query counts.
    Only enabled in development mode.
    Use ?profile=true query parameter to profile a specific request.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Only profile in development
        if settings.app_env != "development":
            return await call_next(request)

        # Check if profiling is requested
        profile = request.query_params.get("profile", "").lower()
        if profile not in ("true", "1", "yes"):
            return await call_next(request)

        # Profile the request
        start_time = time.perf_counter()
        import cProfile, io, pstats

        profiler = cProfile.Profile()
        profiler.enable()

        response = await call_next(request)

        profiler.disable()
        elapsed = time.perf_counter() - start_time

        # Capture profiling stats
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats("cumtime")
        ps.print_stats(30)  # Top 30 functions by cumulative time

        profiling_output = s.getvalue()

        # Return profiling data
        return JSONResponse(
            content={
                "elapsed_seconds": round(elapsed, 4),
                "profiling": profiling_output,
                "path": str(request.url.path),
                "method": request.method,
            }
        )