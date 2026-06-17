"""
Face embedding comparison using cosine similarity.
"""
import numpy as np


def compare_embeddings(emb1: list[float], emb2: list[float]) -> float:
    """
    Compute cosine similarity between two face embeddings.

    Args:
        emb1: First 512-dim embedding vector
        emb2: Second 512-dim embedding vector

    Returns:
        Cosine similarity score between 0 and 1.
        Higher values indicate more similar faces.
    """
    vec_a = np.array(emb1, dtype=np.float32)
    vec_b = np.array(emb2, dtype=np.float32)

    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    # Cosine similarity ranges from -1 to 1, but face embeddings are positive
    similarity = dot_product / (norm_a * norm_b)
    # Clamp to [0, 1]
    return max(0.0, min(1.0, float(similarity)))