from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import date

from app.core.database import get_db
from app.schemas.analytics import StudentAnalyticsResponse, CourseAnalyticsResponse, AtRiskStudent
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/student/{student_id}", response_model=StudentAnalyticsResponse)
async def student_analytics(
    student_id: UUID,
    course_id: UUID | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    return await svc.get_student_analytics(student_id, course_id, from_date, to_date)


@router.get("/course/{course_id}", response_model=CourseAnalyticsResponse)
async def course_analytics(
    course_id: UUID,
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    return await svc.get_course_analytics(course_id, from_date, to_date)


@router.get("/at-risk", response_model=list[AtRiskStudent])
async def at_risk_students(
    institution_id: UUID = Query(...),
    threshold_pct: int = Query(75, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Returns students below attendance threshold — updated within 24 hours."""
    svc = AnalyticsService(db)
    return await svc.get_at_risk_students(institution_id, threshold_pct)
