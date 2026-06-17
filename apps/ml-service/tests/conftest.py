import pytest
from fastapi.testclient import TestClient
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_image_bytes():
    """Generate a small synthetic image for testing."""
    from PIL import Image
    import io

    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def sample_embedding():
    """Generate a random 512-dim embedding for testing."""
    rng = np.random.default_rng(42)
    emb = rng.normal(0, 1, 512).astype(np.float32)
    emb = emb / np.linalg.norm(emb)
    return emb.tolist()


@pytest.fixture
def sample_feature_vectors():
    """Generate sample feature vectors for training."""
    rng = np.random.default_rng(123)
    vectors = []
    # Normal samples (low geo accuracy, high face confidence, device present)
    for _ in range(50):
        vectors.append([
            float(rng.uniform(0, 50)),     # geo_accuracy (0-50m)
            float(rng.choice([0, 1])),      # wifi_bssid_present
            float(rng.choice([0, 1])),      # ble_beacon_present
            float(rng.uniform(0.7, 1.0)),   # face_confidence
            float(rng.choice([0, 1])),      # device_fingerprint_present
            float(rng.uniform(0, 600)),     # time_deviation_seconds (0-10min)
            float(rng.uniform(0, 300)),     # historical_avg_time (0-5min)
        ])
    return vectors


@pytest.fixture
def sample_time_series():
    """Generate sample historical attendance data."""
    data = []
    today = datetime.utcnow()
    for i in range(30, 0, -1):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        pct = 75 + (30 - i) * 0.5 + np.random.normal(0, 3)
        pct = max(0, min(100, pct))
        data.append({"date": date, "attendance_pct": round(pct, 2)})
    return data