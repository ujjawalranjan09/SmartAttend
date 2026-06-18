from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin, get_current_user
from app.models.batch import Batch, BatchSchedule
from app.models.user import User, UserRole
from app.schemas.batch import (
    BatchCreate,
    BatchUpdate,
    BatchResponse,
    BatchListResponse,
    BatchScheduleCreate,
    BatchScheduleUpdate,
    BatchScheduleResponse,
    BatchScheduleListResponse,
    BatchMemberIds,
)

router = APIRouter()


# ── Batch CRUD ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=BatchResponse, status_code=201)
async def create_batch(
    body: BatchCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    dup = await db.execute(
        select(Batch).where(
            Batch.institution_id == body.institution_id,
            Batch.code == body.code,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Batch code already exists within this institution",
        )

    batch = Batch(
        institution_id=body.institution_id,
        department_id=body.department_id,
        name=body.name,
        code=body.code,
        academic_year=body.academic_year,
        semester=body.semester,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return BatchResponse.model_validate(batch)


@router.get("/", response_model=BatchListResponse)
async def list_batches(
    institution_id: UUID | None = Query(None),
    department_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    count_q = select(func.count()).select_from(Batch)
    data_q = select(Batch).order_by(Batch.name)

    if institution_id is not None:
        count_q = count_q.where(Batch.institution_id == institution_id)
        data_q = data_q.where(Batch.institution_id == institution_id)
    if department_id is not None:
        count_q = count_q.where(Batch.department_id == department_id)
        data_q = data_q.where(Batch.department_id == department_id)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(data_q)
    items = result.scalars().all()

    return BatchListResponse(
        items=[BatchResponse.model_validate(b) for b in items],
        total=total,
    )


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return BatchResponse.model_validate(batch)


@router.put("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    body: BatchUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    updates = body.model_dump(exclude_none=True)

    if "code" in updates and updates["code"] != batch.code:
        dup = await db.execute(
            select(Batch).where(
                Batch.institution_id == batch.institution_id,
                Batch.code == updates["code"],
                Batch.id != batch_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="Batch code already exists within this institution",
            )

    for field, value in updates.items():
        setattr(batch, field, value)

    await db.commit()
    await db.refresh(batch)
    return BatchResponse.model_validate(batch)


@router.delete("/{batch_id}", status_code=204)
async def delete_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    # Unlink members first (users.batch_id is nullable) to avoid FK surprises.
    await db.execute(
        update(User).where(User.batch_id == batch_id).values(batch_id=None)
    )
    await db.delete(batch)
    await db.commit()


# ── Weekly schedule (batch + teacher + subject + time) ─────────────────────────

@router.get("/{batch_id}/schedule", response_model=BatchScheduleListResponse)
async def list_batch_schedule(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BatchSchedule)
        .where(BatchSchedule.batch_id == batch_id)
        .order_by(BatchSchedule.day_of_week, BatchSchedule.start_time)
    )
    items = result.scalars().all()
    return BatchScheduleListResponse(
        items=[BatchScheduleResponse.model_validate(s) for s in items],
        total=len(items),
    )


@router.post("/{batch_id}/schedule", response_model=BatchScheduleResponse, status_code=201)
async def create_batch_schedule(
    batch_id: UUID,
    body: BatchScheduleCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    if body.batch_id != batch_id:
        raise HTTPException(status_code=400, detail="batch_id mismatch")

    batch = (
        await db.execute(select(Batch).where(Batch.id == batch_id))
    ).scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    if body.start_time >= body.end_time:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")
    if not (0 <= body.day_of_week <= 6):
        raise HTTPException(status_code=400, detail="day_of_week must be 0..6 (Mon..Sun)")

    # Prevent double-booking the same batch at the same day/time.
    clash = (
        await db.execute(
            select(BatchSchedule).where(
                BatchSchedule.batch_id == batch_id,
                BatchSchedule.day_of_week == body.day_of_week,
                BatchSchedule.start_time == body.start_time,
            )
        )
    ).scalar_one_or_none()
    if clash:
        raise HTTPException(
            status_code=409,
            detail="Batch already has a class at this day/time",
        )

    slot = BatchSchedule(
        institution_id=batch.institution_id,
        batch_id=batch_id,
        faculty_id=body.faculty_id,
        subject_id=body.subject_id,
        day_of_week=body.day_of_week,
        start_time=body.start_time,
        end_time=body.end_time,
        room=body.room,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return BatchScheduleResponse.model_validate(slot)


@router.put("/{batch_id}/schedule/{slot_id}", response_model=BatchScheduleResponse)
async def update_batch_schedule(
    batch_id: UUID,
    slot_id: UUID,
    body: BatchScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(BatchSchedule).where(
            BatchSchedule.id == slot_id,
            BatchSchedule.batch_id == batch_id,
        )
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Schedule slot not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(slot, field, value)

    await db.commit()
    await db.refresh(slot)
    return BatchScheduleResponse.model_validate(slot)


@router.delete("/{batch_id}/schedule/{slot_id}", status_code=204)
async def delete_batch_schedule(
    batch_id: UUID,
    slot_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(BatchSchedule).where(
            BatchSchedule.id == slot_id,
            BatchSchedule.batch_id == batch_id,
        )
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Schedule slot not found")
    await db.delete(slot)
    await db.commit()


# ── Members (students in a batch) ──────────────────────────────────────────────

@router.get("/{batch_id}/members")
async def list_batch_members(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    batch = (
        await db.execute(select(Batch).where(Batch.id == batch_id))
    ).scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    result = await db.execute(
        select(User).where(User.batch_id == batch_id).order_by(User.full_name)
    )
    students = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "full_name": s.full_name,
            "roll_number": s.roll_number,
            "email": s.email,
            "is_active": s.is_active,
        }
        for s in students
    ]


@router.post("/{batch_id}/members")
async def set_batch_members(
    batch_id: UUID,
    body: BatchMemberIds,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    """Assign the given student ids to this batch, removing any others.

    Replaces membership: students not in body.user_ids lose this batch.
    """
    batch = (
        await db.execute(select(Batch).where(Batch.id == batch_id))
    ).scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Clear existing members of this batch, then assign the new set.
    await db.execute(
        update(User).where(User.batch_id == batch_id).values(batch_id=None)
    )
    if body.user_ids:
        await db.execute(
            update(User)
            .where(User.id.in_(body.user_ids), User.role == UserRole.STUDENT)
            .values(batch_id=batch_id)
        )
    await db.commit()
    return {"batch_id": str(batch_id), "assigned": len(body.user_ids)}
