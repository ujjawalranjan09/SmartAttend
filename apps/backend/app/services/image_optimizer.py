"""
Image optimization for face enrollment uploads.
Resizes, compresses, and strips EXIF data for privacy.
"""
import io
import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

MAX_DIMENSION = 640  # Max width or height
JPEG_QUALITY = 85    # Compression quality


def optimize_image(
    image_bytes: bytes,
    max_dimension: int = MAX_DIMENSION,
    quality: int = JPEG_QUALITY,
) -> bytes:
    """
    Optimize an uploaded face image:
    1. Open with PIL
    2. Convert to RGB (strip alpha, handle grayscale)
    3. Resize maintaining aspect ratio (max 640x640)
    4. Save as JPEG with specified quality
    5. Strip EXIF data (no location/camera metadata)

    Returns optimized JPEG bytes.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.error(f"Failed to open image: {e}")
        raise ValueError("Invalid image file")

    # Convert to RGB (handles RGBA, P, L modes)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if larger than max_dimension
    width, height = img.size
    if width > max_dimension or height > max_dimension:
        # Calculate new size maintaining aspect ratio
        if width > height:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        else:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))

        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        logger.info(
            f"Resized image from {width}x{height} to {new_width}x{new_height}"
        )

    # Save as JPEG with quality setting (strips EXIF)
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    optimized_bytes = output.getvalue()

    original_size = len(image_bytes)
    optimized_size = len(optimized_bytes)
    reduction = (1 - optimized_size / original_size) * 100 if original_size > 0 else 0

    logger.info(
        f"Image optimized: {original_size} → {optimized_size} bytes ({reduction:.1f}% reduction)"
    )

    return optimized_bytes


def get_image_info(image_bytes: bytes) -> dict:
    """Get image metadata without modifying the image."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return {
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "size_bytes": len(image_bytes),
        }
    except Exception:
        return {"error": "Invalid image"}