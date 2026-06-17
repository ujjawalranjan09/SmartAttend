from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np

from app.models.face import FaceEmbedding
from app.core.config import settings
from app.services.ml_client import get_face_embedding, compare_embeddings
from app.services.encryption_service import encrypt_embedding, decrypt_embedding


class FaceService:
    """Face embedding verification using ML service for extraction and comparison."""

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

        # Decrypt stored embedding if it's encrypted bytes
        stored_emb = stored.embedding
        if isinstance(stored_emb, bytes):
            try:
                stored_emb = decrypt_embedding(stored_emb)
            except Exception:
                pass  # Fall through — treat as unencrypted

        # Use ML service for comparison, fall back to local computation
        similarity = await compare_embeddings(embedding, stored_emb)
        if similarity is not None:
            return similarity

        # Fallback: local cosine similarity
        vec_a = np.array(embedding)
        vec_b = np.array(stored_emb)
        norm_b = np.linalg.norm(vec_b)
        if norm_b == 0:
            return 0.0
        similarity = float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * norm_b))
        return max(0.0, similarity)

    async def enroll_face(
        self, user_id: UUID, embedding: list[float], model_version: str = "arcface_r100"
    ) -> FaceEmbedding:
        """
        Enroll or update a student's face embedding.
        Embeddings are encrypted before storage for privacy.
        """
        encrypted = encrypt_embedding(embedding)

        result = await self.db.execute(
            select(FaceEmbedding).where(FaceEmbedding.user_id == user_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.embedding = encrypted
            existing.model_version = model_version
            await self.db.commit()
            return existing

        record = FaceEmbedding(
            user_id=user_id,
            embedding=encrypted,
            model_version=model_version,
        )
        self.db.add(record)
        await self.db.commit()
        return record

    async def extract_embedding_from_image(self, image_bytes: bytes) -> list[float] | None:
        """Send image to ML service for face embedding extraction."""
        return await get_face_embedding(image_bytes)

    async def has_enrollment(self, student_id: UUID) -> bool:
        """Check if student has a face enrollment."""
        result = await self.db.execute(
            select(FaceEmbedding).where(
                FaceEmbedding.user_id == student_id,
                FaceEmbedding.is_active == True,
            )
        )
        return result.scalar_one_or_none() is not None
