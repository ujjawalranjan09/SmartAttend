from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import (
    get_current_user,
    get_user_institution_id,
    require_faculty,
)
from app.models.alert import Alert
from app.models.user import User, UserRole
from app.schemas.alert import AlertResponse, AlertListResponse

router = APIRouter()


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    is_resolved: bool | None = Query(None),
    alert_type: str | None = Query(None),
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    institution_id: UUID | None = Depends(get_user_institution_id),
):
    from app.models.user import User as UserModel

    query = select(Alert)

    if current_user.role == UserRole.STUDENT:
        query = query.where(Alert.student_id == current_user.id)
    elif institution_id is not None:
        query = query.where(Alert.institution_id == institution_id)

    if is_resolved is not None:
        query = query.where(Alert.is_resolved == is_resolved)
    if alert_type is not None:
        query = query.where(Alert.alert_type == alert_type)
    if severity is not None:
        query = query.where(Alert.severity == severity)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Alert.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    alerts = result.scalars().all()

    student_ids = {a.student_id for a in alerts if a.student_id}
    course_ids = {a.course_id for a in alerts if a.course_id}

    student_names: dict[UUID, str] = {}
    if student_ids:
        students_result = await db.execute(
            select(UserModel.id, UserModel.full_name).where(
                UserModel.id.in_(student_ids)
            )
        )
        student_names = {row.id: row.full_name for row in students_result.all()}

    course_names: dict[UUID, str] = {}
    if course_ids:
        from app.models.course import Course

        courses_result = await db.execute(
            select(Course.id, Course.name).where(Course.id.in_(course_ids))
        )
        course_names = {row.id: row.name for row in courses_result.all()}

    items = []
    for a in alerts:
        resp = AlertResponse.model_validate(a)
        resp.student_name = student_names.get(a.student_id)
        resp.course_name = course_names.get(a.course_id)
        items.append(resp)

    return AlertListResponse(items=items, total=total)


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if current_user.role == UserRole.STUDENT and alert.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Alert not found")

    student_name = None
    course_name = None

    if alert.student_id:
        from app.models.user import User as UserModel

        student_result = await db.execute(
            select(UserModel.full_name).where(UserModel.id == alert.student_id)
        )
        row = student_result.scalar_one_or_none()
        if row:
            student_name = row

    if alert.course_id:
        from app.models.course import Course

        course_result = await db.execute(
            select(Course.name).where(Course.id == alert.course_id)
        )
        row = course_result.scalar_one_or_none()
        if row:
            course_name = row

    resp = AlertResponse.model_validate(alert)
    resp.student_name = student_name
    resp.course_name = course_name
    return resp


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_faculty),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.is_resolved:
        raise HTTPException(status_code=400, detail="Alert is already resolved")

    alert.is_resolved = True
    alert.resolved_by_id = current_user.id
    alert.resolved_at = datetime.utcnow()
    await db.commit()
    await db.refresh(alert)

    return AlertResponse.model_validate(alert)
