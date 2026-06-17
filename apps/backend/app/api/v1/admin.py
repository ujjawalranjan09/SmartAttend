"""
Admin-only endpoints for feature flags and A/B testing management.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.core.deps import require_admin
from app.models.user import User
from app.core import feature_flags as ff
from app.core import ab_testing as ab

router = APIRouter(tags=["Admin"])


# ── Feature Flags ───────────────────────────────────────────────────────────


@router.get("/feature-flags")
async def list_flags(
    current_user: User = Depends(require_admin),
):
    """List all feature flags (admin only)."""
    institution_id = getattr(current_user, "institution_id", None)
    flags = await ff.list_feature_flags(institution_id)
    return {"flags": flags}


class FlagUpdateRequest(BaseModel):
    enabled: bool
    institution_id: Optional[str] = None


@router.put("/feature-flags/{flag_name}")
async def update_flag(
    flag_name: str,
    body: FlagUpdateRequest,
    current_user: User = Depends(require_admin),
):
    """Enable or disable a feature flag (admin only)."""
    inst_uuid = UUID(body.institution_id) if body.institution_id else None
    await ff.set_feature_flag(flag_name, body.enabled, inst_uuid)
    return {
        "flag": flag_name,
        "enabled": body.enabled,
        "scope": "institution" if inst_uuid else "global",
    }


# ── A/B Testing ─────────────────────────────────────────────────────────────


@router.get("/experiments/{name}/stats")
async def get_experiment_stats(
    name: str,
    current_user: User = Depends(require_admin),
):
    """Get A/B test statistics (admin only)."""
    stats = await ab.get_experiment_stats(name)
    return {"experiment": name, "stats": stats}
