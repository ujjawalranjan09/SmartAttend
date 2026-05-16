from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.core.deps import require_faculty, require_student, get_current_user
from app.models.user import User, UserRole
from app.schemas.analytics import StudentAnalyticsResponse, CourseAnalyticsResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/student/{student_id}", response_model=StudentAnalyticsResponse)
async def student_analytics(
    student_id: UUID,
    course_id: Optional[UUID] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.STUDENT and current_user.id != student_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Cannot view another student's analytics")
    svc = AnalyticsService(db)
    return await svc.get_student_analytics(
        student_id=student_id,
        course_id=course_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/course/{course_id}", response_model=CourseAnalyticsResponse)
async def course_analytics(
    course_id: UUID,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    svc = AnalyticsService(db)
    return await svc.get_course_analytics(
        course_id=course_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/institution/{institution_id}/at-risk")
async def institution_at_risk(
    institution_id: UUID,
    threshold_pct: float = Query(75.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    """Return all students below the attendance threshold for this institution."""
    svc = AnalyticsService(db)
    at_risk = await svc.get_at_risk_students(
        institution_id=institution_id,
        threshold_pct=threshold_pct,
    )
    return {"institution_id": str(institution_id), "threshold_pct": threshold_pct,
            "count": len(at_risk), "students": [s.model_dump() for s in at_risk]}


@router.get("/institution/{institution_id}/summary")
async def institution_summary(
    institution_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    """High-level KPIs for the admin/HOD dashboard."""
    from sqlalchemy import select, func
    from app.models.user import User as UserModel
    from app.models.session import ClassSession
    from app.models.attendance import AttendanceRecord, AttendanceStatus

    student_count = (await db.execute(
        select(func.count(UserModel.id)).where(
            UserModel.institution_id == institution_id,
            UserModel.role == UserRole.STUDENT,
            UserModel.is_active == True,
        )
    )).scalar() or 0

    sessions_today = (await db.execute(
        select(func.count(ClassSession.id)).where(
            ClassSession.status == "active",
        )
    )).scalar() or 0

    present_today = (await db.execute(
        select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.status == AttendanceStatus.PRESENT,
        )
    )).scalar() or 0

    proxy_alerts = (await db.execute(
        select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.status == AttendanceStatus.PROXY_SUSPECTED,
        )
    )).scalar() or 0

    svc = AnalyticsService(db)
    at_risk = await svc.get_at_risk_students(institution_id)

    return {
        "institution_id": str(institution_id),
        "total_students": student_count,
        "active_sessions_now": sessions_today,
        "students_present_today": present_today,
        "proxy_alerts_total": proxy_alerts,
        "at_risk_count": len(at_risk),
    }
