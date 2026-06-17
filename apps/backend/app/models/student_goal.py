import uuid
from datetime import datetime, date

from sqlalchemy import String, DateTime, ForeignKey, Text, Date, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from app.core.database import Base


class StudentGoal(Base):
    __tablename__ = "student_goals"
    __table_args__ = (
        Index("ix_student_goals_student_status", "student_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # academic | career | skill | project | exam_prep
    priority: Mapped[str] = mapped_column(
        String(20), default="medium"
    )  # low | medium | high
    target_date: Mapped[date | None] = mapped_column(Date)
    estimated_hours: Mapped[int | None] = mapped_column(Integer)
    completed_hours: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(20), default="active"
    )  # active | completed | paused | abandoned
    milestones: Mapped[list] = mapped_column(
        JSON, default=list
    )  # list[{"title": str, "completed": bool}]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    student = relationship("User", back_populates="student_goals")