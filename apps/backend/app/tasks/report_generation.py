import csv
import io
import json
from datetime import datetime

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
    Celery task: generate attendance report and upload to S3 / local storage.
    Supports formats: csv, json.
    PDF support requires WeasyPrint — add to requirements if needed.
    """
    try:
        # Import inside task to avoid circular imports at module load
        from app.core.database import SyncSessionLocal  # synchronous session for Celery
        from app.models.attendance import AttendanceRecord
        from app.models.session import ClassSession
        from app.models.course import Course
        from app.models.user import User

        with SyncSessionLocal() as db:
            q = (
                db.query(
                    User.full_name,
                    User.roll_number,
                    User.email,
                    Course.name.label("course_name"),
                    ClassSession.scheduled_at,
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
                q = q.filter(ClassSession.scheduled_at >= datetime.fromisoformat(from_date))
            if to_date:
                q = q.filter(ClassSession.scheduled_at <= datetime.fromisoformat(to_date))

            rows = q.all()

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Student Name", "Roll", "Email", "Course",
                             "Session Date", "Status", "Method", "Proxy Score"])
            for row in rows:
                writer.writerow([
                    row.full_name, row.roll_number or "", row.email,
                    row.course_name,
                    row.scheduled_at.strftime("%Y-%m-%d %H:%M") if row.scheduled_at else "",
                    row.status, row.method,
                    f"{row.proxy_score:.3f}" if row.proxy_score is not None else "",
                ])
            content = output.getvalue().encode("utf-8")
            content_type = "text/csv"
            filename = f"report_{job_id}.csv"
        else:
            data = [
                {
                    "student_name": row.full_name,
                    "roll_number": row.roll_number,
                    "email": row.email,
                    "course": row.course_name,
                    "session_date": row.scheduled_at.isoformat() if row.scheduled_at else None,
                    "status": row.status,
                    "method": row.method,
                    "proxy_score": row.proxy_score,
                }
                for row in rows
            ]
            content = json.dumps(data, indent=2).encode("utf-8")
            content_type = "application/json"
            filename = f"report_{job_id}.json"

        # Upload to S3 (if configured) or save locally
        try:
            import boto3
            from app.core.config import settings
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
            s3.put_object(
                Bucket=settings.s3_bucket_name,
                Key=f"reports/{filename}",
                Body=content,
                ContentType=content_type,
            )
            download_url = f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/reports/{filename}"
        except Exception:
            # Fallback: write to /tmp
            path = f"/tmp/{filename}"
            with open(path, "wb") as f:
                f.write(content)
            download_url = f"/reports/download/{job_id}"

        return {"job_id": job_id, "status": "done", "download_url": download_url}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
