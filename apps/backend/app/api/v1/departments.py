from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin, get_current_user
from app.models.institution import Department
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentListResponse,
)

router = APIRouter()


@router.post("/", response_model=DepartmentResponse, status_code=201)
async def create_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Department).where(
            Department.institution_id == body.institution_id,
            Department.code == body.code,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Department code already exists within this institution",
        )

    dept = Department(
        institution_id=body.institution_id,
        name=body.name,
        code=body.code,
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return DepartmentResponse.model_validate(dept)


@router.get("/", response_model=DepartmentListResponse)
async def list_departments(
    institution_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    count_q = select(func.count()).select_from(Department)
    data_q = select(Department).order_by(Department.name)

    if institution_id is not None:
        count_q = count_q.where(Department.institution_id == institution_id)
        data_q = data_q.where(Department.institution_id == institution_id)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(data_q)
    items = result.scalars().all()

    return DepartmentListResponse(
        items=[DepartmentResponse.model_validate(d) for d in items],
        total=total,
    )


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Department).where(Department.id == department_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return DepartmentResponse.model_validate(dept)


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: UUID,
    body: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    result = await db.execute(select(Department).where(Department.id == department_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    updates = body.model_dump(exclude_none=True)

    if "code" in updates:
        dup = await db.execute(
            select(Department).where(
                Department.institution_id == dept.institution_id,
                Department.code == updates["code"],
                Department.id != department_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="Department code already exists within this institution",
            )

    for field, value in updates.items():
        setattr(dept, field, value)

    await db.commit()
    await db.refresh(dept)
    return DepartmentResponse.model_validate(dept)
