from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.session import ClassSession
from app.models.course import Course, Enrollment
from app.models.user import User
from app.schemas.analytics import (
    StudentAnalyticsResponse, CourseAnalyticsResponse, AtRiskStudent, AttendanceTrend
)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_student_analytics(
        self,
        student_id: UUID,
        course_id: UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> StudentAnalyticsResponse:
        # Fetch user
        user_result = await self.db.execute(select(User).where(User.id == student_id))
        user = user_result.scalar_one()

        # Count attended vs total sessions
        query = (
            select(
                func.count(AttendanceRecord.id).label("attended"),
            )
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status == AttendanceStatus.PRESENT,
            )
        )
        if course_id:
            query = query.join(ClassSession).where(ClassSession.course_id == course_id)

        attended_result = await self.db.execute(query)
        attended = attended_result.scalar() or 0

        total_sessions = 30  # placeholder — fetch from DB in real impl
        pct = (attended / total_sessions * 100) if total_sessions else 0

        return StudentAnalyticsResponse(
            student_id=student_id,
            full_name=user.full_name,
            overall_attendance_pct=round(pct, 2),
            courses=[],
            trend=[],
            proxy_incidents=0,
            at_risk=pct < 75,
            forecast_7d_pct=None,
        )

    async def get_at_risk_students(
        self, institution_id: UUID, threshold_pct: int = 75
    ) -> list[AtRiskStudent]:
        # Production: complex query joining enrollments + attendance aggregates
        # Returning empty list as scaffold
        return []

    async def get_course_analytics(
        self, course_id: UUID, from_date=None, to_date=None
    ) -> CourseAnalyticsResponse:
        course_result = await self.db.execute(select(Course).where(Course.id == course_id))
        course = course_result.scalar_one()
        return CourseAnalyticsResponse(
            course_id=course_id,
            course_name=course.name,
            total_sessions=0,
            avg_attendance_pct=0.0,
            engagement_score=0.0,
            at_risk_students=0,
            proxy_incidents=0,
            trend=[],
        )
