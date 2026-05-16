from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "smartattend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.proxy_analysis",
        "app.tasks.notifications",
        "app.tasks.report_generation",
        "app.tasks.ml_scoring",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_routes={
        "app.tasks.proxy_analysis.*": {"queue": "ml"},
        "app.tasks.notifications.*": {"queue": "notifications"},
        "app.tasks.report_generation.*": {"queue": "reports"},
        "app.tasks.ml_scoring.*": {"queue": "ml"},
    },
    beat_schedule={
        # Run at-risk student scoring every 6 hours
        "score-at-risk-students": {
            "task": "app.tasks.ml_scoring.score_all_students",
            "schedule": 6 * 3600,
        },
        # Daily attendance digest notifications
        "daily-digest": {
            "task": "app.tasks.notifications.send_daily_digest",
            "schedule": 86400,
        },
    },
)
