"""
Isolation Forest-based proxy attendance detection.
Trains models on normal attendance patterns and detects anomalous ones.
"""
import json
import logging
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


def train_model(
    feature_vectors: list[list[float]], model_version: str
) -> dict:
    """
    Train an Isolation Forest model on feature vectors.

    Args:
        feature_vectors: List of feature vectors (each is a list of floats)
        model_version: Version string for the model (e.g., "v1718612345")

    Returns:
        Metadata dict with training_date, sample_count, feature_count
    """
    from sklearn.ensemble import IsolationForest

    X = np.array(feature_vectors, dtype=np.float32)
    n_samples, n_features = X.shape

    contamination = min(0.05, 1.0 / n_samples)  # At least 1 outlier

    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)

    # Save model
    model_dir = Path(settings.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / f"isolation_forest_{model_version}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    # Save metadata
    metadata = {
        "model_version": model_version,
        "training_date": datetime.utcnow().isoformat(),
        "sample_count": n_samples,
        "feature_count": n_features,
        "contamination": contamination,
        "algorithm": "IsolationForest",
    }
    meta_path = model_dir / f"isolation_forest_{model_version}_meta.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(
        f"Trained Isolation Forest model {model_version} "
        f"({n_samples} samples, {n_features} features)"
    )
    return metadata


def _find_latest_model() -> Optional[tuple]:
    """Find the latest model version. Returns (version, model_path) or None."""
    model_dir = Path(settings.model_dir)
    if not model_dir.exists():
        return None

    models = sorted(model_dir.glob("isolation_forest_*.pkl"))
    if not models:
        return None

    latest = models[-1]
    version = latest.stem.replace("isolation_forest_", "")
    return version, str(latest)


def predict_anomaly(
    features: list[float], model_version: Optional[str] = None
) -> float:
    """
    Predict anomaly score for a feature vector.

    Args:
        features: Feature vector (list of floats)
        model_version: Specific model version, or "latest" for most recent

    Returns:
        Anomaly score between 0 (normal) and 1 (anomalous).
        Returns 0.1 if no model is available (default low risk).
    """
    model_dir = Path(settings.model_dir)

    if model_version:
        model_path = model_dir / f"isolation_forest_{model_version}.pkl"
        if not model_path.exists():
            logger.warning(f"Model version '{model_version}' not found, using latest")
            model_version = None

    if not model_version:
        found = _find_latest_model()
        if not found:
            logger.warning("No trained model found, returning default low risk (0.1)")
            return 0.1
        model_version, model_path_str = found
        model_path = Path(model_path_str)

    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        X = np.array(features, dtype=np.float32).reshape(1, -1)
        # decision_function returns negative for anomalies, positive for normal
        raw_score = model.decision_function(X)[0]
        # Normalize to [0, 1] where higher = more anomalous
        # IsolationForest decision_function typically ranges from ~-0.5 to ~0.5
        # Anomalies have negative scores
        normalized = 1.0 - (raw_score + 0.5)  # Shift and invert
        normalized = max(0.0, min(1.0, normalized))
        return round(normalized, 6)

    except Exception as e:
        logger.error(f"Error during anomaly prediction: {e}")
        return 0.1  # Default low risk on error