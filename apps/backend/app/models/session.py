import uuid
from datetime import datetime, time
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, Boolean, Time, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class SessionStatus(str, PyEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"


class TimetableSlot(Base):
    __tablename__ = "timetable_slots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False
    )
    day_of_week: Mapped[int]  # 0=Mon, 6=Sun
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    room: Mapped[str | None] = mapped_column(String(100))
    building: Mapped[str | None] = mapped_column(String(100))
    # Override geo-fence for this specific room
    geo_lat: Mapped[float | None]
    geo_lon: Mapped[float | None]
    geo_radius_m: Mapped[int | None]

    sessions = relationship("ClassSession", back_populates="timetable_slot")


class ClassSession(Base):
    """A single occurrence of a class (instantiated from a timetable slot)."""
    __tablename__ = "class_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True
    )
    timetable_slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timetable_slots.id")
    )
    faculty_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.SCHEDULED
    )
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    meeting_url: Mapped[str | None] = mapped_column(String(500))  # Zoom/GMeet
    qr_rotation_interval_sec: Mapped[int] = mapped_column(default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    course = relationship("Course", back_populates="sessions")
    faculty = relationship("User", foreign_keys=[faculty_id])
    timetable_slot = relationship("TimetableSlot", back_populates="sessions")
    attendance_records = relationship("AttendanceRecord", back_populates="session")
