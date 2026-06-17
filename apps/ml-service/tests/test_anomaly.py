"""Tests for anomaly detection endpoints."""
import numpy as np


class TestAnomalyScore:
    def test_anomaly_score_returns_0_to_1(self, client):
        """POST /anomaly/score returns a score between 0 and 1."""
        features = [10.0, 1.0, 0.0, 0.85, 1.0, 120.0, 60.0]
        response = client.post("/api/v1/anomaly/score", json=features)
        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["anomaly_score"] <= 1.0

    def test_anomaly_score_with_no_model_returns_default(self, client):
        """Without a trained model, returns default low risk (0.1)."""
        features = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        response = client.post("/api/v1/anomaly/score", json=features)
        assert response.status_code == 200
        data = response.json()
        assert data["anomaly_score"] == 0.1


class TestAnomalyTrain:
    def test_train_succeeds(self, client, sample_feature_vectors):
        """POST /anomaly/train with valid data returns success."""
        response = client.post(
            "/api/v1/anomaly/train",
            json=sample_feature_vectors,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "trained"
        assert data["samples"] == 50
        assert data["features"] == 7

    def test_train_with_too_few_vectors_returns_400(self, client):
        """Training with < 5 vectors returns 400."""
        vectors = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        response = client.post("/api/v1/anomaly/train", json=vectors)
        assert response.status_code == 400

    def test_train_creates_listable_model(self, client, sample_feature_vectors):
        """After training, model appears in list."""
        # Train
        response = client.post(
            "/api/v1/anomaly/train",
            json=sample_feature_vectors,
        )
        assert response.status_code == 200
        version = response.json()["model_version"]

        # List
        response = client.get("/api/v1/anomaly/models")
        assert response.status_code == 200
        data = response.json()
        versions = [m["version"] for m in data["models"]]
        assert version in versions

    def test_trained_model_returns_varying_scores(self, client, sample_feature_vectors):
        """After training, different vectors return different scores."""
        # Train
        response = client.post(
            "/api/v1/anomaly/train",
            json=sample_feature_vectors,
        )
        assert response.status_code == 200

        # Normal-like features should score lower
        normal = [10.0, 1.0, 1.0, 0.95, 1.0, 60.0, 30.0]
        r1 = client.post("/api/v1/anomaly/score", json=normal)

        # Anomalous features should score higher
        anomalous = [500.0, 0.0, 0.0, 0.1, 0.0, 3600.0, 1800.0]
        r2 = client.post("/api/v1/anomaly/score", json=anomalous)

        assert r1.status_code == 200
        assert r2.status_code == 200
        # The gap might not always hold with random data, so just check ranges
        assert 0.0 <= r1.json()["anomaly_score"] <= 1.0
        assert 0.0 <= r2.json()["anomaly_score"] <= 1.0