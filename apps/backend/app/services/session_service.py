from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.session import ClassSession, SessionStatus
from app.schemas.session import SessionCreate


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start(self, data: SessionCreate) -> ClassSession:
        session = ClassSession(
            course_id=data.course_id,
            faculty_id=data.faculty_id,
            timetable_slot_id=data.timetable_slot_id,
            is_online=data.is_online,
            meeting_url=data.meeting_url,
            qr_rotation_interval_sec=data.qr_rotation_interval_sec,
            date=datetime.utcnow(),
            started_at=datetime.utcnow(),
            status=SessionStatus.ACTIVE,
        )
        self.db.add(session)
        await self.db.commit()
        return session

    async def end(self, session_id: UUID) -> None:
        result = await self.db.execute(
            select(ClassSession).where(ClassSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.status = SessionStatus.ENDED
            session.ended_at = datetime.utcnow()
            await self.db.commit()

    async def get(self, session_id: UUID) -> ClassSession | None:
        result = await self.db.execute(
            select(ClassSession).where(ClassSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_faculty(self, faculty_id: UUID) -> list[ClassSession]:
        result = await self.db.execute(
            select(ClassSession).where(ClassSession.faculty_id == faculty_id)
        )
        return result.scalars().all()
