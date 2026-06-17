import uuid
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.notification import Notification


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: UUID | str,
        title: str,
        body: str,
        type: str,
        link: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            type=type,
            link=link,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def list_for_user(
        self,
        user_id: UUID | str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int, int]:
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        base = select(Notification).where(Notification.user_id == user_id)

        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar() or 0

        unread_result = await self.db.execute(
            select(func.count()).select_from(
                base.where(Notification.is_read == False).subquery()
            )
        )
        unread_count = unread_result.scalar() or 0

        q = base.order_by(Notification.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        items = result.scalars().all()

        return items, total, unread_count

    async def mark_read(self, notification_id: UUID | str, user_id: UUID | str) -> bool:
        if isinstance(notification_id, str):
            notification_id = uuid.UUID(notification_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True)
        )
        await self.db.commit()
        return result.rowcount > 0
