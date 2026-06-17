import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # pgvector not installed — fall back to LargeBinary for local dev
    from sqlalchemy import LargeBinary as Vector  # type: ignore[assignment]

from app.core.database import Base


class FaceEmbedding(Base):
    """Stores AES-256 encrypted 512-dim face embedding vectors per student."""
    __tablename__ = "face_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(512), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="arcface_r100")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = relationship("User", back_populates="face_embedding")
