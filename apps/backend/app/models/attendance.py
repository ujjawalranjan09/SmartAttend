import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, Boolean, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class AttendanceMethod(str, PyEnum):
    QR_CODE = "qr_code"
    FACE_RECOGNITION = "face_recognition"
    BLE_PROXIMITY = "ble_proximity"
    WIFI_PROXIMITY = "wifi_proximity"
    MANUAL_OVERRIDE = "manual_override"
    ONLINE_MEETING = "online_meeting"


class AttendanceStatus(str, PyEnum):
    PRESENT = "present"
    ABSENT = "absent"
    PROXY_SUSPECTED = "proxy_suspected"
    EXCUSED = "excused"


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("class_sessions.id"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.PRESENT
    )
    method: Mapped[AttendanceMethod] = mapped_column(
        Enum(AttendanceMethod), nullable=False
    )
    marked_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    # Anti-spoofing evidence
    geo_lat: Mapped[float | None]
    geo_lon: Mapped[float | None]
    geo_accuracy_m: Mapped[float | None]
    device_fingerprint: Mapped[str | None] = mapped_column(String(255))
    wifi_bssid: Mapped[str | None] = mapped_column(String(50))  # classroom router MAC
    ble_beacon_id: Mapped[str | None] = mapped_column(String(100))
    face_confidence: Mapped[float | None]  # 0-1 cosine similarity score

    # ML proxy detection
    proxy_anomaly_score: Mapped[float | None]  # 0-1, higher = more suspicious
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_notes: Mapped[str | None] = mapped_column(String(500))

    # Audit
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    raw_metadata: Mapped[dict | None] = mapped_column(JSON)

    session = relationship("ClassSession", back_populates="attendance_records")
    student = relationship("User", back_populates="attendance_records")
