from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np

from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.alert import Alert, AlertType, AlertSeverity
from app.core.config import settings


class ProxyDetectionService:
    """Isolation Forest-based proxy attendance detection."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def enqueue_analysis(self, record_id: UUID):
        """Fire-and-forget: send to Celery ML queue."""
        from app.tasks.proxy_analysis import analyze_attendance_record
        analyze_attendance_record.apply_async(
            args=[str(record_id)],
            queue="ml",
            countdown=2,  # slight delay to allow DB commit
        )

    async def analyze_and_update(self, record_id: UUID):
        """Core ML analysis — runs in Celery worker."""
        result = await self.db.execute(
            select(AttendanceRecord).where(AttendanceRecord.id == record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return

        features = self._extract_features(record)
        score = await self._compute_anomaly_score(record.student_id, features)
        record.proxy_anomaly_score = score

        if score >= settings.proxy_anomaly_threshold:
            record.status = AttendanceStatus.PROXY_SUSPECTED
            await self._create_alert(
                student_id=record.student_id,
                session_id=record.session_id,
                score=score,
            )

        record.is_verified = True
        await self.db.commit()

    def _extract_features(self, record: AttendanceRecord) -> np.ndarray:
        """Build feature vector for Isolation Forest."""
        features = [
            record.geo_accuracy_m or 0,
            1 if record.wifi_bssid else 0,
            1 if record.ble_beacon_id else 0,
            record.face_confidence or 0,
            1 if record.device_fingerprint else 0,
        ]
        return np.array(features).reshape(1, -1)

    async def _compute_anomaly_score(self, student_id: UUID, features: np.ndarray) -> float:
        """
        In production: load per-institution Isolation Forest model from ML service.
        Here: simplified heuristic returning a score between 0 and 1.
        """
        # Placeholder: replace with actual ML service call
        # score = await ml_client.predict_proxy(student_id, features)
        score = 0.1  # default low risk
        if features[0][3] < 0.5 and features[0][0] == 0:  # low face + no GPS
            score = 0.85
        return score

    async def _create_alert(
        self, student_id: UUID, session_id: UUID, score: float
    ) -> None:
        alert = Alert(
            student_id=student_id,
            session_id=session_id,
            alert_type=AlertType.PROXY_SUSPECTED,
            severity=AlertSeverity.HIGH if score > 0.9 else AlertSeverity.MEDIUM,
            message=f"Proxy attendance suspected (anomaly score: {score:.2f})",
            anomaly_score=score,
        )
        self.db.add(alert)
        await self.db.flush()
