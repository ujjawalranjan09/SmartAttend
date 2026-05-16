from uuid import UUID
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.proxy_analysis.analyze_record", bind=True, max_retries=3)
def analyze_attendance_record(self, record_id: str):
    """
    Runs Isolation Forest proxy detection on a single attendance record.
    Updates proxy_anomaly_score and raises alert if above threshold.
    """
    from app.services.proxy_service import ProxyDetectionService
    from app.core.database import AsyncSessionLocal
    import asyncio

    async def _run():
        async with AsyncSessionLocal() as db:
            svc = ProxyDetectionService(db)
            await svc.analyze_and_update(UUID(record_id))

    asyncio.run(_run())


@celery_app.task(name="app.tasks.proxy_analysis.batch_analyze")
def batch_analyze_session(session_id: str):
    """Post-session batch analysis of all attendance records for a session."""
    from app.services.proxy_service import ProxyDetectionService
    from app.core.database import AsyncSessionLocal
    import asyncio

    async def _run():
        async with AsyncSessionLocal() as db:
            svc = ProxyDetectionService(db)
            await svc.batch_analyze_session(UUID(session_id))

    asyncio.run(_run())
