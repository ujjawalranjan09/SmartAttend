"""Tests for face embedding and comparison endpoints."""
import numpy as np


class TestFaceEmbed:
    def test_embed_returns_512d_vector(self, client, sample_image_bytes):
        """POST /face/embed returns a 512-dim embedding."""
        response = client.post(
            "/api/v1/face/embed",
            files={"image": ("test.jpg", sample_image_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dim"] == 512
        assert len(data["embedding"]) == 512
        assert all(isinstance(v, float) for v in data["embedding"])

    def test_embed_empty_image_returns_400(self, client):
        """POST /face/embed with empty image returns 400."""
        response = client.post(
            "/api/v1/face/embed",
            files={"image": ("empty.jpg", b"", "image/jpeg")},
        )
        assert response.status_code == 400


class TestFaceCompare:
    def test_compare_identical_embeddings(self, client, sample_embedding):
        """Comparing identical embeddings returns ~1.0 similarity."""
        response = client.post(
            "/api/v1/face/compare",
            json={"emb1": sample_embedding, "emb2": sample_embedding},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["similarity"] >= 0.99

    def test_compare_random_embeddings(self, client):
        """Comparing random embeddings returns < 1.0 similarity."""
        rng = np.random.default_rng(100)
        emb1 = rng.normal(0, 1, 512).tolist()
        emb2 = rng.normal(0, 1, 512).tolist()

        response = client.post(
            "/api/v1/face/compare",
            json={"emb1": emb1, "emb2": emb2},
        )
        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["similarity"] <= 1.0

    def test_compare_dim_mismatch_returns_400(self, client, sample_embedding):
        """Comparing embeddings with different dimensions returns 400."""
        response = client.post(
            "/api/v1/face/compare",
            json={"emb1": sample_embedding, "emb2": [1.0, 2.0, 3.0]},
        )
        assert response.status_code == 400

    def test_compare_zero_vector(self, client):
        """Comparing with a zero vector returns 0 similarity."""
        emb = [0.0] * 512
        response = client.post(
            "/api/v1/face/compare",
            json={"emb1": emb, "emb2": emb},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["similarity"] == 0.0