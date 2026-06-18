from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin, get_current_user
from app.models.subject import Subject
from app.models.user import User
from app.schemas.subject import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    SubjectListResponse,
)

router = APIRouter()


@router.post("/", response_model=SubjectResponse, status_code=201)
async def create_subject(
    body: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    dup = await db.execute(
        select(Subject).where(
            Subject.institution_id == body.institution_id,
            Subject.code == body.code,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Subject code already exists within this institution",
        )

    subject = Subject(
        institution_id=body.institution_id,
        department_id=body.department_id,
        name=body.name,
        code=body.code,
    )
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return SubjectResponse.model_validate(subject)


@router.get("/", response_model=SubjectListResponse)
async def list_subjects(
    institution_id: UUID | None = Query(None),
    department_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    count_q = select(func.count()).select_from(Subject)
    data_q = select(Subject).order_by(Subject.name)

    if institution_id is not None:
        count_q = count_q.where(Subject.institution_id == institution_id)
        data_q = data_q.where(Subject.institution_id == institution_id)
    if department_id is not None:
        count_q = count_q.where(Subject.department_id == department_id)
        data_q = data_q.where(Subject.department_id == department_id)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(data_q)
    items = result.scalars().all()

    return SubjectListResponse(
        items=[SubjectResponse.model_validate(s) for s in items],
        total=total,
    )


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return SubjectResponse.model_validate(subject)


@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: UUID,
    body: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    updates = body.model_dump(exclude_none=True)

    if "code" in updates and updates["code"] != subject.code:
        dup = await db.execute(
            select(Subject).where(
                Subject.institution_id == subject.institution_id,
                Subject.code == updates["code"],
                Subject.id != subject_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="Subject code already exists within this institution",
            )

    for field, value in updates.items():
        setattr(subject, field, value)

    await db.commit()
    await db.refresh(subject)
    return SubjectResponse.model_validate(subject)


@router.delete("/{subject_id}", status_code=204)
async def delete_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    # Hard delete; FK columns referencing subjects are nullable, so removal is safe.
    await db.delete(subject)
    await db.commit()
