import csv
import io
from datetime import datetime
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import require_faculty
from app.models.user import User
from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.session import ClassSession
from app.models.course import Course
from app.schemas.report import ReportRequest, ReportJobResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/export/csv")
async def export_csv(
    institution_id: UUID = Query(...),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    course_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    """
    Stream a CSV report of attendance records.
    Columns: student_name, roll_number, email, course, session_date,
             status, method, proxy_score, verification_notes
    """
    q = (
        select(
            User.full_name,
            User.roll_number,
            User.email,
            Course.name.label("course_name"),
            ClassSession.scheduled_at,
            AttendanceRecord.status,
            AttendanceRecord.method,
            AttendanceRecord.proxy_score,
            AttendanceRecord.verification_notes,
        )
        .join(User, User.id == AttendanceRecord.student_id)
        .join(ClassSession, ClassSession.id == AttendanceRecord.session_id)
        .join(Course, Course.id == ClassSession.course_id)
        .where(User.institution_id == institution_id)
        .order_by(User.full_name, ClassSession.scheduled_at)
    )
    if course_id:
        q = q.where(ClassSession.course_id == course_id)
    if from_date:
        q = q.where(ClassSession.scheduled_at >= datetime.fromisoformat(from_date))
    if to_date:
        q = q.where(ClassSession.scheduled_at <= datetime.fromisoformat(to_date))

    rows = (await db.execute(q)).all()

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Student Name",
                "Roll Number",
                "Email",
                "Course",
                "Session Date",
                "Status",
                "Method",
                "Proxy Score",
                "Notes",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.full_name,
                    row.roll_number or "",
                    row.email,
                    row.course_name,
                    row.scheduled_at.strftime("%Y-%m-%d %H:%M")
                    if row.scheduled_at
                    else "",
                    row.status,
                    row.method,
                    f"{row.proxy_score:.3f}" if row.proxy_score is not None else "",
                    row.verification_notes or "",
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    filename = f"attendance_{institution_id}_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/generate", response_model=ReportJobResponse, status_code=202)
async def generate_report(
    body: ReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    """
    Enqueue an async report generation job (PDF / detailed JSON).
    Returns a job_id that can be polled or will deliver via webhook/email.
    """
    from app.tasks.report_generation import generate_report_task
    import secrets

    job_id = secrets.token_hex(16)
    # Fire Celery task
    generate_report_task.delay(
        job_id=job_id,
        institution_id=str(body.institution_id),
        report_type=body.report_type,
        from_date=body.from_date.isoformat(),
        to_date=body.to_date.isoformat(),
        course_id=str(body.course_id) if body.course_id else None,
        format=body.format,
    )

    return ReportJobResponse(
        job_id=job_id,
        status="queued",
        message="Report generation queued. You will be notified when ready.",
        download_url=None,
        created_at=datetime.utcnow(),
    )


@router.get("/summary/{institution_id}")
async def attendance_summary(
    institution_id: UUID,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    """Quick JSON summary: total students, avg attendance %, top absent, proxy count."""
    svc = AnalyticsService(db)
    at_risk = await svc.get_at_risk_students(institution_id)

    proxy_q = (
        select(func.count(AttendanceRecord.id))
        .join(ClassSession, ClassSession.id == AttendanceRecord.session_id)
        .join(User, User.id == AttendanceRecord.student_id)
        .where(
            User.institution_id == institution_id,
            AttendanceRecord.status == AttendanceStatus.PROXY_SUSPECTED,
        )
    )
    proxy_count = (await db.execute(proxy_q)).scalar() or 0

    return {
        "institution_id": str(institution_id),
        "at_risk_students": len(at_risk),
        "proxy_incidents": proxy_count,
        "top_defaulters": [
            {"name": s.full_name, "pct": s.attendance_pct} for s in at_risk[:10]
        ],
    }
