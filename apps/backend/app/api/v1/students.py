from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.services.user_service import UserService

router = APIRouter()


@router.get("/{student_id}")
async def get_student(student_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = UserService(db)
    user = await svc.get_by_id(student_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student not found")
    return {"id": str(user.id), "name": user.full_name, "email": user.email, "roll": user.roll_number}
