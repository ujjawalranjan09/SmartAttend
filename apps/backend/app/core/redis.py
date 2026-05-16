import redis.asyncio as redis
from app.core.config import settings

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def store_qr_token(session_id: str, token: str, ttl: int = None) -> None:
    r = await get_redis()
    ttl = ttl or settings.qr_token_ttl_seconds
    await r.setex(f"qr:{session_id}", ttl, token)


async def validate_qr_token(session_id: str, token: str) -> bool:
    r = await get_redis()
    stored = await r.get(f"qr:{session_id}")
    return stored == token


async def invalidate_qr_token(session_id: str) -> None:
    r = await get_redis()
    await r.delete(f"qr:{session_id}")


async def rate_limit_check(key: str, limit: int, window_seconds: int) -> bool:
    """Returns True if request is within rate limit."""
    r = await get_redis()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = await pipe.execute()
    return results[0] <= limit
