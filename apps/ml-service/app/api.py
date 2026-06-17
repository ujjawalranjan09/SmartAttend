from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import json
import os
import time
from pathlib import Path

from app.config import settings

router = APIRouter(tags=["ML Service"])


# ── Face endpoints ──────────────────────────────────────────────────────────


@router.post("/face/embed")
async def face_embed(image: UploadFile = File(...)):
    """Extract 512-dim face embedding from an uploaded image."""
    from app.face.embedding import extract_embedding

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file")

    try:
        embedding = extract_embedding(image_bytes)
        return {"embedding": embedding, "dim": len(embedding)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Face embedding failed: {str(e)}")


class CompareRequest(BaseModel):
    emb1: list[float]
    emb2: list[float]


@router.post("/face/compare")
async def face_compare(body: CompareRequest):
    """Compare two face embeddings and return cosine similarity score (0-1)."""
    from app.face.comparison import compare_embeddings

    if len(body.emb1) != len(body.emb2):
        raise HTTPException(
            status_code=400,
            detail=f"Embedding dimension mismatch: {len(body.emb1)} vs {len(body.emb2)}",
        )

    similarity = compare_embeddings(body.emb1, body.emb2)
    return {"similarity": round(similarity, 6)}


# ── Anomaly endpoints ───────────────────────────────────────────────────────


@router.post("/anomaly/score")
async def anomaly_score(features: list[float]):
    """Score a feature vector for proxy attendance anomaly (0-1)."""
    from app.anomaly.isolation_forest import predict_anomaly

    score = predict_anomaly(features)
    return {"anomaly_score": round(score, 6)}


@router.post("/anomaly/train")
async def anomaly_train(feature_vectors: list[list[float]]):
    """Train a new Isolation Forest model and save to disk."""
    from app.anomaly.isolation_forest import train_model

    if not feature_vectors or len(feature_vectors) < 5:
        raise HTTPException(
            status_code=400,
            detail="At least 5 feature vectors required for training",
        )

    model_version = f"v{int(time.time())}"
    metadata = train_model(feature_vectors, model_version)
    return {
        "model_version": model_version,
        "samples": metadata.get("sample_count", len(feature_vectors)),
        "features": metadata.get("feature_count", len(feature_vectors[0])),
        "status": "trained",
    }


# ── Model versioning endpoints ─────────────────────────────────────────────


@router.get("/anomaly/models")
async def list_models():
    """List all trained anomaly model versions."""
    model_dir = Path(settings.model_dir)
    models = []
    if model_dir.exists():
        for f in sorted(model_dir.glob("isolation_forest_*.pkl")):
            version = f.stem.replace("isolation_forest_", "")
            meta_path = f.with_name(f"isolation_forest_{version}_meta.json")
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                except Exception:
                    pass
            models.append(
                {
                    "version": version,
                    "path": str(f),
                    "training_date": meta.get("training_date", "unknown"),
                    "sample_count": meta.get("sample_count", 0),
                    "feature_count": meta.get("feature_count", 0),
                }
            )
    return {"models": models}


@router.get("/anomaly/models/{version}")
async def get_model_metadata(version: str):
    """Get metadata for a specific model version."""
    model_dir = Path(settings.model_dir)
    meta_path = model_dir / f"isolation_forest_{version}_meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail=f"Model version '{version}' not found")
    try:
        meta = json.loads(meta_path.read_text())
        return meta
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read metadata: {str(e)}")


# ── Forecast endpoints ──────────────────────────────────────────────────────


@router.post("/forecast/predict")
async def forecast_predict(historical_data: list[dict]):
    """
    Predict attendance trend for the next 14 days.
    Input: list of {date: "YYYY-MM-DD", attendance_pct: float}.
    """
    from app.forecast.prophet_model import forecast_attendance

    if not historical_data or len(historical_data) < 1:
        raise HTTPException(
            status_code=400,
            detail="At least 2 data points required for forecasting",
        )

    result = forecast_attendance(historical_data)
    return result