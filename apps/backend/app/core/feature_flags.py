"""
Feature flag system using Redis.
Supports global flags and per-institution overrides.
"""
import json
import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

FLAG_PREFIX = "feature_flag:"
FLAG_DEFAULT_TTL = 86400 * 7  # 7 days


async def is_feature_enabled(
    flag_name: str, institution_id: Optional[UUID] = None
) -> bool:
    """
    Check if a feature flag is enabled.

    Priority:
    1. Per-institution override (if institution_id provided)
    2. Global flag value
    3. Default: False
    """
    from app.core.redis import get_redis

    r = await get_redis()

    # Check per-institution first
    if institution_id:
        inst_key = f"{FLAG_PREFIX}{flag_name}:inst:{institution_id}"
        inst_val = await r.get(inst_key)
        if inst_val is not None:
            return inst_val == "1"

    # Check global flag
    global_key = f"{FLAG_PREFIX}{flag_name}"
    global_val = await r.get(global_key)
    if global_val is not None:
        return global_val == "1"

    return False


async def set_feature_flag(
    flag_name: str,
    enabled: bool,
    institution_id: Optional[UUID] = None,
    ttl: Optional[int] = None,
) -> None:
    """Set a feature flag (global or per-institution)."""
    from app.core.redis import get_redis

    r = await get_redis()
    ttl = ttl or FLAG_DEFAULT_TTL

    if institution_id:
        key = f"{FLAG_PREFIX}{flag_name}:inst:{institution_id}"
    else:
        key = f"{FLAG_PREFIX}{flag_name}"

    await r.setex(key, ttl, "1" if enabled else "0")
    logger.info(
        f"Feature flag '{flag_name}' set to {enabled}"
        + (f" for institution {institution_id}" if institution_id else " (global)")
    )


async def list_feature_flags(institution_id: Optional[UUID] = None) -> list[dict]:
    """List all feature flags and their states."""
    from app.core.redis import get_redis

    r = await get_redis()
    flags = []

    cursor = 0
    seen = set()

    # Scan for global flags
    while True:
        cursor, keys = await r.scan(cursor=cursor, match=f"{FLAG_PREFIX}*", count=100)
        for key in keys:
            # Skip per-institution keys
            if ":inst:" in key:
                continue
            flag_name = key.replace(FLAG_PREFIX, "")
            if flag_name in seen:
                continue
            seen.add(flag_name)
            val = await r.get(key)
            flags.append(
                {
                    "name": flag_name,
                    "enabled": val == "1",
                    "scope": "global",
                }
            )
        if cursor == 0:
            break

    # Scan for institution-specific overrides
    if institution_id:
        cursor = 0
        while True:
            cursor, keys = await r.scan(
                cursor=cursor, match=f"{FLAG_PREFIX}*inst:{institution_id}", count=100
            )
            for key in keys:
                flag_name = key.replace(FLAG_PREFIX, "").split(":inst:")[0]
                val = await r.get(key)
                # Update or add institution-specific entry
                existing = next((f for f in flags if f["name"] == flag_name), None)
                if existing:
                    existing["enabled"] = val == "1"
                    existing["scope"] = "institution"
                else:
                    flags.append(
                        {
                            "name": flag_name,
                            "enabled": val == "1",
                            "scope": "institution",
                        }
                    )
            if cursor == 0:
                break

    return flags