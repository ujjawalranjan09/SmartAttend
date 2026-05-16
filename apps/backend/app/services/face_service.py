from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np

from app.models.face import FaceEmbedding
from app.core.config import settings


class FaceService:
    """Face embedding verification using cosine similarity against pgvector."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def verify_embedding(
        self, student_id: UUID, embedding: list[float]
    ) -> float:
        """Returns cosine similarity score (0-1) between submitted and stored embedding."""
        result = await self.db.execute(
            select(FaceEmbedding).where(
                FaceEmbedding.user_id == student_id,
                FaceEmbedding.is_active == True,
            )
        )
        stored = result.scalar_one_or_none()
        if not stored:
            return 0.0  # No enrollment — cannot verify

        vec_a = np.array(embedding)
        vec_b = np.array(stored.embedding)
        similarity = float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)))
        return max(0.0, similarity)  # clamp to [0, 1]

    async def enroll_face(
        self, user_id: UUID, embedding: list[float], model_version: str = "arcface_r100"
    ) -> FaceEmbedding:
        """Enroll or update a student's face embedding."""
        result = await self.db.execute(
            select(FaceEmbedding).where(FaceEmbedding.user_id == user_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.embedding = embedding
            existing.model_version = model_version
            await self.db.commit()
            return existing

        record = FaceEmbedding(
            user_id=user_id,
            embedding=embedding,
            model_version=model_version,
        )
        self.db.add(record)
        await self.db.commit()
        return record
