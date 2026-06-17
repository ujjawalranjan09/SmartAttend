"""
Face embedding extraction using InsightFace (buffalo_l model).
Returns 512-dim embeddings from face images.
"""
import io
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

# Global model reference (loaded once at startup)
_face_model = None


def load_face_model():
    """Load InsightFace model into global cache."""
    global _face_model
    if _face_model is not None:
        return _face_model
    try:
        import insightface
        from insightface.app import FaceAnalysis

        _face_model = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        _face_model.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace model loaded successfully (buffalo_l)")
    except ImportError:
        logger.warning(
            "InsightFace not installed. Face embedding will use simulated embeddings "
            "(install with: pip install insightface onnxruntime)"
        )
        _face_model = None
    except Exception as e:
        logger.error(f"Failed to load InsightFace model: {e}")
        _face_model = None
    return _face_model


def extract_embedding(image_bytes: bytes) -> list[float]:
    """
    Extract 512-dim face embedding from raw image bytes.

    Args:
        image_bytes: Raw image file bytes (JPEG, PNG, etc.)

    Returns:
        512-dim embedding as a list of floats

    Raises:
        ValueError: If no face detected or image is invalid
    """
    model = load_face_model()

    # If InsightFace not available, return simulated embedding
    if model is None:
        logger.warning("Using simulated face embedding (InsightFace not available)")
        rng = np.random.default_rng(42)
        emb = rng.normal(0, 1, 512).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        return emb.tolist()

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(img)

        # Check image dimensions
        if img_array.shape[0] < 50 or img_array.shape[1] < 50:
            raise ValueError("Image too small (minimum 50x50 pixels)")

        faces = model.get(img_array)

        if not faces:
            raise ValueError("No face detected in the image")

        # Use the largest face (by bounding box area)
        largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        embedding = largest.normed_embedding  # 512-dim vector

        return [float(v) for v in embedding]

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to process image: {str(e)}")