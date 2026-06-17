import logging
import json

from app.tasks.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.models.notification import Notification
from app.models.user import User, UserRole
from sqlalchemy import select

logger = logging.getLogger(__name__)


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

        # Broadcast via WebSocket (2.7)
        try:
            import asyncio
            from app.websocket.handlers import broadcast_to_user

            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(
                    broadcast_to_user(
                        student_id,
                        {
                            "title": notification.title,
                            "body": notification.body,
                            "type": notification.type,
                            "link": notification.link,
                        },
                    )
                )
        except Exception as e:
            logger.debug("WebSocket broadcast failed: %s", e)

        # Send push notification (2.8)
        try:
            _send_push_sync(
                student_id,
                "Low Attendance Alert",
                f"Your attendance in {course_name} has dropped to {pct:.1f}%.",
                "/student/attendance",
            )
        except Exception as e:
            logger.debug("Push notification failed: %s", e)

        # Send email (2.9)
        try:
            import asyncio
            from app.services.email_service import send_templated_email

            user = db.get(User, student_id)
            if user:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(
                        send_templated_email(
                            user.email,
                            "low_attendance",
                            {
                                "student_name": user.full_name,
                                "course_name": course_name,
                                "attendance_pct": f"{pct:.1f}",
                                "dashboard_url": "/student/attendance",
                            },
                        )
                    )
        except Exception as e:
            logger.debug("Email send failed: %s", e)


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

        # Broadcast via WebSocket (2.7)
        try:
            import asyncio
            from app.websocket.handlers import broadcast_to_user

            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(
                    broadcast_to_user(
                        faculty_id,
                        {
                            "title": notification.title,
                            "body": notification.body,
                            "type": notification.type,
                            "link": notification.link,
                        },
                    )
                )
        except Exception as e:
            logger.debug("WebSocket broadcast failed: %s", e)

        # Send push notification (2.8)
        try:
            _send_push_sync(
                faculty_id,
                "Proxy Attendance Detected",
                f"Suspected proxy for {student_name} in session {session_id}",
                f"/sessions/{session_id}",
            )
        except Exception as e:
            logger.debug("Push notification failed: %s", e)

        # Send email (2.9)
        try:
            import asyncio
            from app.services.email_service import send_templated_email

            user = db.get(User, faculty_id)
            if user:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(
                        send_templated_email(
                            user.email,
                            "proxy_alert",
                            {
                                "student_name": student_name,
                                "session_id": session_id,
                                "anomaly_score": f"{score:.2f}",
                                "session_url": f"/sessions/{session_id}",
                            },
                        )
                    )
        except Exception as e:
            logger.debug("Email send failed: %s", e)


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

        # Send emails (2.9)
        try:
            import asyncio
            from app.services.email_service import send_templated_email

            for user in users:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(
                        send_templated_email(
                            user.email,
                            "daily_digest",
                            {
                                "recipient_name": user.full_name,
                                "total_sessions": "—",
                                "avg_attendance": "—",
                                "proxy_count": "—",
                                "at_risk_count": "—",
                                "analytics_url": "/analytics",
                            },
                        )
                    )
        except Exception as e:
            logger.debug("Email send failed: %s", e)


def _send_push_sync(user_id: str, title: str, body: str, link: str):
    """Send push notification to all subscriptions of a user (sync wrapper)."""
    try:
        from sqlalchemy import text

        with SyncSessionLocal() as db:
            result = db.execute(
                text(
                    "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = :uid"
                ),
                {"uid": user_id},
            )
            subs = result.fetchall()

        if not subs:
            return

        from app.core.config import settings

        if not settings.vapid_private_key:
            return

        from pywebpush import webpush, WebPushException
        import json

        subscription_info = {
            "endpoint": subs[0][0],
            "keys": {"p256dh": subs[0][1], "auth": subs[0][2]},
        }
        payload = json.dumps({"title": title, "body": body, "link": link})

        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_claims_email},
            )
        except WebPushException as e:
            logger.debug("Push failed for subscription: %s", e)
            # If 410 Gone, remove expired subscription
            if hasattr(e, "response") and e.response and e.response.status_code == 410:
                with SyncSessionLocal() as db:
                    db.execute(
                        text("DELETE FROM push_subscriptions WHERE endpoint = :ep"),
                        {"endpoint": subs[0][0]},
                    )
                    db.commit()
    except Exception as e:
        logger.debug("Push notification error: %s", e)
