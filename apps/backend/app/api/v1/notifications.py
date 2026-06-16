from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationResponse, NotificationListResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NotificationService(db)
    items, total, unread_count = await svc.list_for_user(
        user_id=current_user.id, page=page, page_size=page_size,
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
        unread_count=unread_count,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NotificationService(db)
    updated = await svc.mark_read(
        notification_id=notification_id, user_id=current_user.id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
    from sqlalchemy import select
    from app.models.notification import Notification
    result = await db.execute(
        select(Notification).where(Notification.id == str(notification_id))
    )
    notification = result.scalar_one()
    return NotificationResponse.model_validate(notification)
