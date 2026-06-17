import csv
import io
import json
import tempfile
from datetime import datetime
from uuid import UUID

from app.tasks.celery_app import celery_app


@celery_app.task(name="tasks.generate_report", bind=True, max_retries=3)
def generate_report_task(
    self,
    job_id: str,
    institution_id: str,
    report_type: str,
    from_date: str,
    to_date: str,
    course_id: str | None = None,
    format: str = "csv",
):
    """
    Celery task: generate attendance report as CSV or PDF.
    Stores result path in Redis for status polling.
    """
    try:
        from app.core.database import SyncSessionLocal
        from app.models.attendance import AttendanceRecord, AttendanceStatus
        from app.models.session import ClassSession
        from app.models.course import Course
        from app.models.user import User
        from sqlalchemy import select

        with SyncSessionLocal() as db:
            q = (
                db.query(
                    User.full_name,
                    User.roll_number,
                    User.email,
                    Course.name.label("course_name"),
                    ClassSession.date,
                    AttendanceRecord.status,
                    AttendanceRecord.method,
                    AttendanceRecord.proxy_score,
                )
                .join(User, User.id == AttendanceRecord.student_id)
                .join(ClassSession, ClassSession.id == AttendanceRecord.session_id)
                .join(Course, Course.id == ClassSession.course_id)
                .filter(User.institution_id == institution_id)
            )
            if course_id:
                q = q.filter(ClassSession.course_id == course_id)
            if from_date:
                q = q.filter(
                    ClassSession.date >= datetime.fromisoformat(from_date)
                )
            if to_date:
                q = q.filter(
                    ClassSession.date <= datetime.fromisoformat(to_date)
                )

            rows = q.all()

        if format == "csv":
            path = _write_csv(job_id, rows)
        elif format == "pdf":
            path = _write_pdf(job_id, rows, institution_id, from_date, to_date)
        else:
            path = _write_csv(job_id, rows)

        import redis.asyncio as aioredis
        from app.core.config import settings

        r = aioredis.from_url(settings.redis_url, decode_responses=True)

        async def _store():
            await r.set(f"report_status:{job_id}", "completed", ex=3600)
            await r.set(f"report_path:{job_id}", path, ex=3600)
            await r.aclose()

        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_store())
        except RuntimeError:
            asyncio.run(_store())

        return {"job_id": job_id, "status": "done", "file_path": path}

    except Exception as exc:
        import redis.asyncio as aioredis
        from app.core.config import settings

        r = aioredis.from_url(settings.redis_url, decode_responses=True)

        async def _fail():
            await r.set(f"report_status:{job_id}", "failed", ex=3600)
            await r.aclose()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_fail())
        except RuntimeError:
            asyncio.run(_fail())

        raise self.retry(exc=exc, countdown=30)


def _write_csv(job_id: str, rows) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Student Name",
            "Roll",
            "Email",
            "Course",
            "Session Date",
            "Status",
            "Method",
            "Proxy Score",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.full_name,
                row.roll_number or "",
                row.email,
                row.course_name,
                row.date.strftime("%Y-%m-%d %H:%M") if row.date else "",
                row.status,
                row.method,
                f"{row.proxy_score:.3f}" if row.proxy_score is not None else "",
            ]
        )
    path = tempfile.mktemp(suffix=".csv", prefix=f"report_{job_id}_")
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(output.getvalue())
    return path


def _write_pdf(
    job_id: str, rows, institution_id: str, from_date: str, to_date: str
) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )

    path = tempfile.mktemp(suffix=".pdf", prefix=f"report_{job_id}_")
    doc = SimpleDocTemplate(path, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("SmartAttend — Attendance Report", styles["Title"]))
    elements.append(
        Paragraph(
            f"Institution: {institution_id} | Period: {from_date} to {to_date}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Total Records: {len(rows)}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    header = ["Student Name", "Roll", "Email", "Course", "Date", "Status", "Method"]
    data = [header]
    for row in rows:
        data.append(
            [
                row.full_name,
                row.roll_number or "",
                row.email,
                row.course_name,
                row.date.strftime("%Y-%m-%d %H:%M") if row.date else "",
                str(row.status),
                row.method or "",
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976d2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f5f5f5")],
                ),
            ]
        )
    )
    elements.append(table)

    doc.build(elements)
    return path
