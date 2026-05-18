from uuid import UUID
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.session import ClassSession
from app.models.course import Course, Enrollment
from app.models.user import User, UserRole
from app.schemas.analytics import (
    StudentAnalyticsResponse,
    CourseAnalyticsResponse,
    AtRiskStudent,
    AttendanceTrend,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Student analytics ────────────────────────────────────────────────

    async def get_student_analytics(
        self,
        student_id: UUID,
        course_id: UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> StudentAnalyticsResponse:
        user_result = await self.db.execute(select(User).where(User.id == student_id))
        user = user_result.scalar_one()

        # Total sessions the student was enrolled in
        total_q = (
            select(func.count(ClassSession.id))
            .join(Enrollment, Enrollment.course_id == ClassSession.course_id)
            .where(Enrollment.student_id == student_id, ClassSession.status == "completed")
        )
        if course_id:
            total_q = total_q.where(ClassSession.course_id == course_id)
        if from_date:
            total_q = total_q.where(ClassSession.scheduled_at >= datetime.combine(from_date, datetime.min.time()))
        if to_date:
            total_q = total_q.where(ClassSession.scheduled_at <= datetime.combine(to_date, datetime.max.time()))

        total_result = await self.db.execute(total_q)
        total_sessions = total_result.scalar() or 0

        # Attended
        attended_q = (
            select(func.count(AttendanceRecord.id))
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status == AttendanceStatus.PRESENT,
            )
        )
        if course_id:
            attended_q = attended_q.join(ClassSession).where(ClassSession.course_id == course_id)
        if from_date:
            attended_q = attended_q.where(AttendanceRecord.marked_at >= datetime.combine(from_date, datetime.min.time()))
        if to_date:
            attended_q = attended_q.where(AttendanceRecord.marked_at <= datetime.combine(to_date, datetime.max.time()))

        attended_result = await self.db.execute(attended_q)
        attended = attended_result.scalar() or 0

        # Proxy incidents
        proxy_q = select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.status == AttendanceStatus.PROXY_SUSPECTED,
        )
        proxy_result = await self.db.execute(proxy_q)
        proxy_incidents = proxy_result.scalar() or 0

        pct = round((attended / total_sessions * 100), 2) if total_sessions else 0.0

        # Weekly trend (last 8 weeks)
        trend = await self._student_weekly_trend(student_id, course_id)

        # Simple 7-day forecast: linear extrapolation of last 2 weeks
        forecast = self._forecast(trend)

        return StudentAnalyticsResponse(
            student_id=student_id,
            full_name=user.full_name,
            overall_attendance_pct=pct,
            courses=[],
            trend=trend,
            proxy_incidents=proxy_incidents,
            at_risk=pct < 75,
            forecast_7d_pct=forecast,
        )

    async def _student_weekly_trend(
        self, student_id: UUID, course_id: UUID | None = None
    ) -> list[AttendanceTrend]:
        weeks = 8
        now = datetime.utcnow()
        trend = []
        for i in range(weeks - 1, -1, -1):
            week_start = now - timedelta(weeks=i + 1)
            week_end = now - timedelta(weeks=i)
            q = select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status == AttendanceStatus.PRESENT,
                AttendanceRecord.marked_at >= week_start,
                AttendanceRecord.marked_at < week_end,
            )
            if course_id:
                q = q.join(ClassSession).where(ClassSession.course_id == course_id)
            result = await self.db.execute(q)
            attended = result.scalar() or 0

            total_q = select(func.count(ClassSession.id)).where(
                ClassSession.scheduled_at >= week_start,
                ClassSession.scheduled_at < week_end,
                ClassSession.status == "completed",
            )
            if course_id:
                total_q = total_q.where(ClassSession.course_id == course_id)
            total_result = await self.db.execute(total_q)
            total = total_result.scalar() or 1  # avoid div by zero

            trend.append(AttendanceTrend(
                period=week_start.strftime("%Y-W%V"),
                attendance_pct=round(attended / total * 100, 2),
                sessions_held=total,
                sessions_attended=attended,
            ))
        return trend

    def _forecast(self, trend: list[AttendanceTrend]) -> float | None:
        if len(trend) < 2:
            return None
        last_two = [t.attendance_pct for t in trend[-2:]]
        delta = last_two[1] - last_two[0]
        forecast = last_two[1] + delta
        return round(max(0.0, min(100.0, forecast)), 2)

    # ── At-risk students ─────────────────────────────────────────────────

    async def get_at_risk_students(
        self, institution_id: UUID, threshold_pct: float = 75.0
    ) -> list[AtRiskStudent]:
        # Aggregate attendance per student across all completed sessions
        attended_subq = (
            select(
                AttendanceRecord.student_id,
                func.count(AttendanceRecord.id).label("attended"),
            )
            .where(AttendanceRecord.status == AttendanceStatus.PRESENT)
            .group_by(AttendanceRecord.student_id)
            .subquery()
        )
        total_subq = (
            select(
                Enrollment.student_id,
                func.count(ClassSession.id).label("total"),
            )
            .join(ClassSession, ClassSession.course_id == Enrollment.course_id)
            .where(ClassSession.status == "completed")
            .group_by(Enrollment.student_id)
            .subquery()
        )

        q = (
            select(
                User,
                func.coalesce(attended_subq.c.attended, 0).label("attended"),
                func.coalesce(total_subq.c.total, 1).label("total"),
            )
            .outerjoin(attended_subq, attended_subq.c.student_id == User.id)
            .outerjoin(total_subq, total_subq.c.student_id == User.id)
            .where(
                User.institution_id == institution_id,
                User.role == UserRole.STUDENT,
                User.is_active,
            )
        )
        results = await self.db.execute(q)
        rows = results.all()

        at_risk = []
        for user, attended, total in rows:
            pct = round(attended / total * 100, 2) if total else 0.0
            if pct < threshold_pct:
                at_risk.append(AtRiskStudent(
                    student_id=user.id,
                    full_name=user.full_name,
                    roll_number=user.roll_number,
                    attendance_pct=pct,
                    sessions_missed=total - attended,
                    risk_level=("critical" if pct < 60 else "moderate"),
                ))
        at_risk.sort(key=lambda x: x.attendance_pct)
        return at_risk

    # ── Course analytics ─────────────────────────────────────────────────

    async def get_course_analytics(
        self, course_id: UUID, from_date: date | None = None, to_date: date | None = None
    ) -> CourseAnalyticsResponse:
        course_result = await self.db.execute(select(Course).where(Course.id == course_id))
        course = course_result.scalar_one()

        total_sessions_q = select(func.count(ClassSession.id)).where(
            ClassSession.course_id == course_id,
            ClassSession.status == "completed",
        )
        if from_date:
            total_sessions_q = total_sessions_q.where(ClassSession.scheduled_at >= datetime.combine(from_date, datetime.min.time()))
        if to_date:
            total_sessions_q = total_sessions_q.where(ClassSession.scheduled_at <= datetime.combine(to_date, datetime.max.time()))
        total_sessions = (await self.db.execute(total_sessions_q)).scalar() or 0

        # Average attendance
        enrolled_q = select(func.count(Enrollment.id)).where(Enrollment.course_id == course_id)
        enrolled = (await self.db.execute(enrolled_q)).scalar() or 1

        attended_q = (
            select(func.count(AttendanceRecord.id))
            .join(ClassSession, ClassSession.id == AttendanceRecord.session_id)
            .where(
                ClassSession.course_id == course_id,
                AttendanceRecord.status == AttendanceStatus.PRESENT,
            )
        )
        attended = (await self.db.execute(attended_q)).scalar() or 0

        avg_pct = round(attended / (total_sessions * enrolled) * 100, 2) if (total_sessions * enrolled) else 0.0

        proxy_q = (
            select(func.count(AttendanceRecord.id))
            .join(ClassSession, ClassSession.id == AttendanceRecord.session_id)
            .where(
                ClassSession.course_id == course_id,
                AttendanceRecord.status == AttendanceStatus.PROXY_SUSPECTED,
            )
        )
        proxy_count = (await self.db.execute(proxy_q)).scalar() or 0

        # At-risk count for this course
        at_risk_count = 0  # Full calculation in get_at_risk_students

        return CourseAnalyticsResponse(
            course_id=course_id,
            course_name=course.name,
            total_sessions=total_sessions,
            avg_attendance_pct=avg_pct,
            engagement_score=round(avg_pct * 0.9, 2),  # simplified heuristic
            at_risk_students=at_risk_count,
            proxy_incidents=proxy_count,
            trend=[],
        )
