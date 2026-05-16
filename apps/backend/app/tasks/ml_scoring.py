from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.ml_scoring.score_all_students")
def score_all_students():
    """
    Periodic task: runs Prophet forecasting on all active students.
    Updates attendance trajectory and triggers early-warning alerts.
    """
    print("[ML] Running Prophet attendance forecasting for all students...")
    # Production:
    # 1. Fetch all active student-course enrollments
    # 2. For each: build time series from attendance_records
    # 3. Fit Prophet model, forecast 14 days
    # 4. If predicted pct < threshold: trigger alert
