"""
Simple A/B testing framework using Redis.
Assigns users deterministically to experiment variants.
"""
import hashlib
import json
import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


def _get_variant_key(experiment_name: str, user_id: UUID) -> int:
    """
    Deterministically assign user to variant 0 (control) or 1 (treatment).
    Uses SHA-256 hash of experiment_name + user_id.
    """
    hash_input = f"{experiment_name}:{user_id}".encode()
    digest = hashlib.sha256(hash_input).hexdigest()
    return int(digest[:8], 16) % 2


async def get_variant(
    experiment_name: str, user_id: UUID
) -> str:
    """
    Get the assigned variant for a user in an experiment.
    Returns "control" or "treatment".
    Ensures consistency via Redis cache.
    """
    from app.core.redis import get_redis

    r = await get_redis()
    cache_key = f"abtest:{experiment_name}:user:{user_id}"

    # Check cached assignment
    cached = await r.get(cache_key)
    if cached == "control":
        return "control"
    elif cached == "treatment":
        return "treatment"

    # Deterministic assignment
    variant = "treatment" if _get_variant_key(experiment_name, user_id) == 1 else "control"
    # Cache for 30 days (experiments are long-running)
    await r.setex(cache_key, 86400 * 30, variant)
    return variant


async def track_event(
    experiment_name: str, user_id: UUID, event_name: str
) -> None:
    """
    Track an event in an experiment.
    Increments a Redis counter for the experiment + variant + event.
    """
    from app.core.redis import get_redis

    r = await get_redis()
    variant = await get_variant(experiment_name, user_id)
    key = f"abtest:{experiment_name}:{variant}:{event_name}"
    await r.incr(key)
    # Expire after 90 days
    await r.expire(key, 86400 * 90)


async def get_experiment_stats(experiment_name: str) -> dict:
    """
    Get statistics for an experiment.
    Returns event counts for both variants.
    """
    from app.core.redis import get_redis

    r = await get_redis()
    stats = {}

    for variant in ["control", "treatment"]:
        cursor = 0
        variant_events = {}
        while True:
            cursor, keys = await r.scan(
                cursor=cursor,
                match=f"abtest:{experiment_name}:{variant}:*",
                count=100,
            )
            for key in keys:
                event_name = key.split(f":{variant}:")[1]
                count = await r.get(key)
                variant_events[event_name] = int(count) if count else 0
            if cursor == 0:
                break
        stats[variant] = variant_events

    return stats