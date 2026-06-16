import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class UserRole(str, PyEnum):
    STUDENT = "student"
    FACULTY = "faculty"
    HOD = "hod"
    ADMIN = "admin"
    PARENT = "parent"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), nullable=False)
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id"), index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id")
    )
    roll_number: Mapped[str | None] = mapped_column(String(50))  # students only
    employee_id: Mapped[str | None] = mapped_column(String(50))  # faculty/staff
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    totp_secret: Mapped[str | None] = mapped_column(String(64))  # for 2FA
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    institution = relationship("Institution", back_populates="users")
    department = relationship("Department", back_populates="users")
    face_embedding = relationship("FaceEmbedding", back_populates="user", uselist=False)
    attendance_records = relationship("AttendanceRecord", back_populates="student")
    enrollments = relationship("Enrollment", back_populates="student")

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"
