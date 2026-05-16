from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import date

from app.core.database import get_db

router = APIRouter()


@router.get("/export")
async def export_report(
    course_id: UUID = Query(...),
    format: str = Query("pdf", regex="^(pdf|csv|xlsx)$"),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """Trigger async report generation via Celery."""
    from app.tasks.report_generation import generate_course_report
    task = generate_course_report.apply_async(
        args=[str(course_id), format, str(from_date), str(to_date)],
        queue="reports",
    )
    return {"task_id": task.id, "status": "queued", "message": "Report will be emailed when ready"}
