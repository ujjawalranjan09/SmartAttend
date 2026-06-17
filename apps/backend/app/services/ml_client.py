"""
HTTP client for calling the ML Service endpoints.
Provides async access to face embedding, anomaly scoring, and forecasting.
"""
import logging
from typing import Optional
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0  # seconds


async def get_face_embedding(image_bytes: bytes) -> Optional[list[float]]:
    """
    POST image to ML service /api/v1/face/embed, return 512-dim embedding.
    Returns None if the ML service is unreachable.
    """
    url = f"{settings.ml_service_url}/api/v1/face/embed"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                url, files={"image": ("face.jpg", image_bytes, "image/jpeg")}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding")
    except httpx.RequestError as e:
        logger.warning(f"ML service unreachable at {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Face embedding request failed: {e}")
        return None


async def compare_embeddings(
    emb1: list[float], emb2: list[float]
) -> Optional[float]:
    """
    POST two embeddings to ML service /api/v1/face/compare.
    Returns cosine similarity score (0-1) or None on failure.
    """
    url = f"{settings.ml_service_url}/api/v1/face/compare"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                url, json={"emb1": emb1, "emb2": emb2}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("similarity")
    except httpx.RequestError as e:
        logger.warning(f"ML service unreachable at {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Face comparison request failed: {e}")
        return None


async def score_anomaly(features: list[float]) -> Optional[float]:
    """
    POST feature vector to ML service /api/v1/anomaly/score.
    Returns anomaly score (0-1) or None on failure.
    """
    url = f"{settings.ml_service_url}/api/v1/anomaly/score"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(url, json=features)
            response.raise_for_status()
            data = response.json()
            return data.get("anomaly_score")
    except httpx.RequestError as e:
        logger.warning(f"ML service unreachable at {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Anomaly score request failed: {e}")
        return None


async def forecast_attendance(
    historical_data: list[dict],
) -> Optional[dict]:
    """
    POST historical attendance data to ML service /api/v1/forecast/predict.
    Returns forecast dict or None on failure.
    """
    url = f"{settings.ml_service_url}/api/v1/forecast/predict"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(url, json=historical_data)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.warning(f"ML service unreachable at {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Forecast request failed: {e}")
        return None