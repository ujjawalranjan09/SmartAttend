from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.push_subscription import PushSubscription

router = APIRouter()


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


@router.get("/vapid-public-key")
async def vapid_public_key():
    """Return the VAPID public key for browser Push API subscription."""
    if not settings.vapid_public_key:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"public_key": settings.vapid_public_key}


@router.post("/subscribe")
async def subscribe(
    body: PushSubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Store a Web Push subscription for the current user."""
    # Remove existing subscription for this endpoint (upsert behavior)
    await db.execute(
        delete(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )

    sub = PushSubscription(
        user_id=current_user.id,
        endpoint=body.endpoint,
        p256dh=body.p256dh,
        auth=body.auth,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return {"detail": "Subscription stored", "id": str(sub.id)}


@router.post("/unsubscribe")
async def unsubscribe(
    body: PushUnsubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a Web Push subscription by endpoint."""
    result = await db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == body.endpoint,
            PushSubscription.user_id == current_user.id,
        )
    )
    await db.commit()
    return {"detail": "Subscription removed", "deleted": result.rowcount > 0}
