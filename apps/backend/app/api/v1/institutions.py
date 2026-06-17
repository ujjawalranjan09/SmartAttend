import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import require_admin, get_current_user
from app.models.user import User
from app.models.institution import Institution, Department
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionUpdate,
    InstitutionResponse,
    InstitutionListResponse,
)
from app.schemas.department import DepartmentResponse

router = APIRouter()


@router.get("/", response_model=InstitutionListResponse)
async def list_institutions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    count_q = select(func.count()).select_from(Institution)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Institution)
        .order_by(Institution.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    items = result.scalars().all()

    return InstitutionListResponse(
        items=[InstitutionResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=InstitutionResponse, status_code=201)
async def create_institution(
    body: InstitutionCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    existing = await db.execute(
        select(Institution).where(Institution.short_name == body.short_name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Short name already exists")

    inst = Institution(
        name=body.name,
        short_name=body.short_name,
        city=body.city,
        state=body.state,
        country=body.country,
    )
    db.add(inst)
    await db.commit()
    await db.refresh(inst)
    return InstitutionResponse.model_validate(inst)


@router.get("/{institution_id}", response_model=InstitutionResponse)
async def get_institution(
    institution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    return InstitutionResponse.model_validate(inst)


@router.put("/{institution_id}", response_model=InstitutionResponse)
async def update_institution(
    institution_id: uuid.UUID,
    body: InstitutionUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(inst, field, value)

    await db.commit()
    await db.refresh(inst)
    return InstitutionResponse.model_validate(inst)


@router.get("/{institution_id}/departments", response_model=list[DepartmentResponse])
async def list_institution_departments(
    institution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    inst_result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    if not inst_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Institution not found")

    result = await db.execute(
        select(Department)
        .where(Department.institution_id == institution_id)
        .order_by(Department.name)
    )
    return [DepartmentResponse.model_validate(d) for d in result.scalars().all()]
