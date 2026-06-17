import json
import asyncio
from typing import Callable, Optional

import redis.asyncio as redis
from app.core.config import settings

_redis_client: redis.Redis | None = None
_pubsub_tasks: dict[str, asyncio.Task] = {}


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def redis_publish(channel: str, message: dict) -> None:
    """Publish a JSON message to a Redis channel."""
    r = await get_redis()
    await r.publish(channel, json.dumps(message))


async def redis_subscribe(channel: str, callback: Callable[[dict], None]) -> None:
    """Subscribe to a Redis channel and invoke callback for each message.

    Runs in a background task. Stores reference so it can be cancelled.
    """
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)

    async def _listener():
        try:
            async for raw in pubsub.listen():
                if raw["type"] == "message":
                    try:
                        data = json.loads(raw["data"])
                    except (json.JSONDecodeError, TypeError):
                        data = raw["data"]
                    callback(data)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    task = asyncio.create_task(_listener())
    _pubsub_tasks[channel] = task


async def redis_unsubscribe(channel: str) -> None:
    """Cancel a subscription listener for a channel."""
    task = _pubsub_tasks.pop(channel, None)
    if task and not task.done():
        task.cancel()


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


# ── Generic caching ────────────────────────────────────────────────────────


async def cache_get(key: str) -> Optional[str]:
    """Get a cached value by key."""
    r = await get_redis()
    return await r.get(key)


async def cache_set(key: str, value: str, ttl_seconds: int = 300) -> None:
    """Set a cached value with TTL (default 5 minutes)."""
    r = await get_redis()
    await r.setex(key, ttl_seconds, value)


async def cache_delete(key: str) -> None:
    """Delete a cached value by key."""
    r = await get_redis()
    await r.delete(key)


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a glob pattern (e.g., 'analytics:student:*')."""
    r = await get_redis()
    cursor = 0
    while True:
        cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            await r.delete(*keys)
        if cursor == 0:
            break


# ── Token blacklisting ─────────────────────────────────────────────────────


async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Store a token JTI in Redis with TTL matching token expiry."""
    r = await get_redis()
    await r.setex(f"blacklist:{jti}", ttl_seconds, "1")


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a token JTI is blacklisted."""
    r = await get_redis()
    return await r.exists(f"blacklist:{jti}") > 0
