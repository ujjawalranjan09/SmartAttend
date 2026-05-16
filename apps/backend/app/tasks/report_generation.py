from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.report_generation.generate_course_report")
def generate_course_report(course_id: str, format: str, from_date: str, to_date: str):
    """Generate PDF/CSV/XLSX attendance report and upload to S3."""
    print(f"[REPORT] Generating {format} report for course {course_id}")
    # Production: Use reportlab (PDF), openpyxl (XLSX), csv module
    # Upload to S3 and email download link to requester
