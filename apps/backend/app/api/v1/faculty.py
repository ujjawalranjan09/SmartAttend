from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.services.session_service import SessionService

router = APIRouter()


@router.get("/{faculty_id}/sessions")
async def get_faculty_sessions(faculty_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = SessionService(db)
    sessions = await svc.get_by_faculty(faculty_id)
    return sessions
