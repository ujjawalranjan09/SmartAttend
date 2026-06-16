from app.tasks.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.models.notification import Notification
from app.models.user import User, UserRole
from sqlalchemy import select


@celery_app.task(name="app.tasks.notifications.send_low_attendance_alert")
def send_low_attendance_alert(student_id: str, course_name: str, pct: float):
    """Create notification for student and parent when attendance drops below threshold."""
    with SyncSessionLocal() as db:
        notification = Notification(
            user_id=student_id,
            title="Low Attendance Alert",
            body=f"Your attendance in {course_name} has dropped to {pct:.1f}%.",
            type="low_attendance",
            link=f"/student/attendance",
        )
        db.add(notification)
        db.commit()


@celery_app.task(name="app.tasks.notifications.send_proxy_alert")
def send_proxy_alert(faculty_id: str, student_name: str, session_id: str, score: float):
    """Notify faculty of suspected proxy attendance in real time."""
    with SyncSessionLocal() as db:
        notification = Notification(
            user_id=faculty_id,
            title="Proxy Attendance Detected",
            body=f"Suspected proxy attendance for {student_name} in session {session_id} (confidence: {score:.2f}).",
            type="proxy_alert",
            link=f"/sessions/{session_id}",
        )
        db.add(notification)
        db.commit()


@celery_app.task(name="app.tasks.notifications.send_daily_digest")
def send_daily_digest():
    """Send daily attendance summary to HODs and admins."""
    with SyncSessionLocal() as db:
        result = db.execute(
            select(User).where(
                User.role.in_([UserRole.HOD.value, UserRole.ADMIN.value]),
                User.is_active == True,
            )
        )
        users = result.scalars().all()
        for user in users:
            notification = Notification(
                user_id=user.id,
                title="Daily Attendance Digest",
                body="Your daily attendance summary is ready. Check the analytics dashboard for details.",
                type="daily_digest",
                link="/analytics",
            )
            db.add(notification)
        db.commit()
