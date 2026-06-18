from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.session import ClassSession
from app.models.user import User
from app.models.alert import Alert, AlertType, AlertSeverity
from app.core.config import settings
from app.services.ml_client import score_anomaly


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
            session_result = await self.db.execute(
                select(ClassSession.faculty_id).where(
                    ClassSession.id == record.session_id
                )
            )
            faculty_id = session_result.scalar_one()
            student_result = await self.db.execute(
                select(User.full_name).where(User.id == record.student_id)
            )
            student_name = student_result.scalar_one()
            from app.tasks.notifications import send_proxy_alert

            send_proxy_alert.delay(
                str(faculty_id), student_name, str(record.session_id), score
            )

        record.is_verified = True
        await self.db.commit()

    def _extract_features(self, record: AttendanceRecord) -> list[float]:
        """Build feature vector for Isolation Forest ML service."""
        features = [
            record.geo_accuracy_m or 0,
            1 if record.wifi_bssid else 0,
            1 if record.ble_beacon_id else 0,
            record.face_confidence or 0,
            1 if record.device_fingerprint else 0,
            0.0,  # time_deviation_seconds (placeholder)
            0.0,  # historical_avg_time (placeholder)
        ]
        return features

    async def _compute_anomaly_score(
        self, student_id: UUID, features: list[float]
    ) -> float:
        """
        Call ML service for anomaly scoring.
        Falls back to heuristic if ML service is unreachable.
        """
        ml_score = await score_anomaly(features)
        if ml_score is not None:
            return ml_score

        # Fallback heuristic
        score = 0.1  # default low risk
        if features[3] < 0.5 and features[0] == 0:  # low face + no GPS
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
