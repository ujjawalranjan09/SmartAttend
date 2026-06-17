from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_faculty, require_admin
from app.models.user import User
from app.schemas.timetable import (
    SlotCreate,
    SlotUpdate,
    SlotResponse,
    WeeklyViewResponse,
)
from app.services.timetable_service import TimetableService

router = APIRouter()


@router.post("/slots", response_model=SlotResponse, status_code=201)
async def create_slot(
    body: SlotCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    svc = TimetableService(db)
    slot = await svc.create_slot(body)
    await db.commit()
    return SlotResponse.model_validate(slot)


@router.get("/slots")
async def list_slots(
    course_id: UUID | None = Query(None),
    department_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    svc = TimetableService(db)
    slots = await svc.list_slots(course_id=course_id, department_id=department_id)
    return [SlotResponse.model_validate(s) for s in slots]


@router.put("/slots/{slot_id}", response_model=SlotResponse)
async def update_slot(
    slot_id: UUID,
    body: SlotUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    svc = TimetableService(db)
    slot = await svc.update_slot(slot_id, body)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    await db.commit()
    return SlotResponse.model_validate(slot)


@router.delete("/slots/{slot_id}")
async def delete_slot(
    slot_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    svc = TimetableService(db)
    deleted = await svc.delete_slot(slot_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Slot not found")
    await db.commit()
    return {"deleted": True}


@router.post("/generate")
async def generate_sessions(
    week_start: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_faculty),
):
    svc = TimetableService(db)
    count = await svc.generate_sessions_for_week(
        week_start, institution_id=current_user.institution_id
    )
    await db.commit()
    return {"sessions_created": count}


@router.get("/weekly", response_model=WeeklyViewResponse)
async def get_weekly_view(
    institution_id: UUID = Query(...),
    week_start: date = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    svc = TimetableService(db)
    data = await svc.get_weekly_view(institution_id, week_start)
    return WeeklyViewResponse(**data)
