from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.notifications.send_low_attendance_alert")
def send_low_attendance_alert(student_id: str, course_name: str, pct: float):
    """Send SMS + Email to student and parent when attendance drops below threshold."""
    # In production: use Twilio for SMS, SMTP for email
    print(f"[ALERT] Student {student_id}: {pct:.1f}% attendance in {course_name}")


@celery_app.task(name="app.tasks.notifications.send_proxy_alert")
def send_proxy_alert(faculty_id: str, student_name: str, session_id: str, score: float):
    """Notify faculty of suspected proxy attendance in real time."""
    print(f"[PROXY] {student_name} flagged in session {session_id} (score: {score:.2f})")


@celery_app.task(name="app.tasks.notifications.send_daily_digest")
def send_daily_digest():
    """Send daily attendance summary to HODs and admins."""
    print("[DIGEST] Sending daily attendance digest...")
