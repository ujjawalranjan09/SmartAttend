import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from app.core.database import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        Index("ix_student_profiles_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    interests: Mapped[list] = mapped_column(JSON, default=list)  # list[str]
    strengths: Mapped[list] = mapped_column(JSON, default=list)  # list[str]
    career_goals: Mapped[list] = mapped_column(JSON, default=list)  # list[str]
    preferred_study_style: Mapped[str | None] = mapped_column(
        String(20)
    )  # visual | reading | hands-on | group | mixed
    daily_study_hours_target: Mapped[int] = mapped_column(default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="student_profile")