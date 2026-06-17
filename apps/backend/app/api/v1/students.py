from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.core.deps import require_faculty, require_admin, get_current_user
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse, BulkCreateRequest, BulkCreateResponse
from app.services.user_service import UserService
from app.services.analytics_service import AnalyticsService
from app.services.attendance_service import AttendanceService

router = APIRouter()


@router.get("/", response_model=UserListResponse)
async def list_students(
    department_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_faculty),
):
    svc = UserService(db)
    users, total = await svc.get_all(
        institution_id=current_user.institution_id,
        role=UserRole.STUDENT,
        department_id=department_id,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
    )
    return UserListResponse(
        total=total, page=page, page_size=page_size,
        items=[UserResponse.model_validate(u) for u in users],
    )


@router.post("/", response_model=UserResponse, status_code=201)
async def create_student(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    if body.role != UserRole.STUDENT:
        raise HTTPException(status_code=400, detail="Role must be student")
    svc = UserService(db)
    existing = await svc.get_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = await svc.create(body)
    return UserResponse.model_validate(user)


@router.post("/bulk", response_model=BulkCreateResponse, status_code=201)
async def bulk_create_students(
    body: BulkCreateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    """Bulk enrol students (e.g. import from CSV). Max 200 per request."""
    svc = UserService(db)
    result = await svc.bulk_create(body.users)
    return BulkCreateResponse(**result)


@router.get("/{student_id}", response_model=UserResponse)
async def get_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.STUDENT and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Cannot view another student's profile")
    svc = UserService(db)
    user = await svc.get_by_id(student_id)
    if not user or user.role != UserRole.STUDENT:
        raise HTTPException(status_code=404, detail="Student not found")
    return UserResponse.model_validate(user)


@router.put("/{student_id}", response_model=UserResponse)
async def update_student(
    student_id: UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.HOD, UserRole.FACULTY) \
            and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    svc = UserService(db)
    user = await svc.update(student_id, body)
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
    return UserResponse.model_validate(user)


@router.delete("/{student_id}", status_code=204)
async def deactivate_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    svc = UserService(db)
    ok = await svc.deactivate(student_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Student not found")


@router.get("/{student_id}/attendance")
async def get_student_attendance(
    student_id: UUID,
    course_id: Optional[UUID] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full attendance history for a student with optional course/date filters."""
    if current_user.role == UserRole.STUDENT and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Cannot view another student's attendance")
    svc = AnalyticsService(db)
    return await svc.get_student_analytics(
        student_id=student_id,
        course_id=course_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/{student_id}/alerts")
async def get_student_alerts(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return active low-attendance / proxy alerts for a student."""
    if current_user.role == UserRole.STUDENT and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Permission denied")
    from app.models.alert import Alert
    from sqlalchemy import select
    result = await db.execute(
        select(Alert).where(
            Alert.student_id == student_id,
            Alert.resolved == False,
        ).order_by(Alert.created_at.desc())
    )
    alerts = result.scalars().all()
    return [{"id": str(a.id), "type": a.alert_type, "message": a.message,
             "created_at": a.created_at.isoformat()} for a in alerts]
