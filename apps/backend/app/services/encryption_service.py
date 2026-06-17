"""
AES-256 encryption service for sensitive data (face embeddings, etc.).
Uses Fernet (symmetric encryption) with the app's secret key.
"""
import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet

from app.core.config import settings

logger = logging.getLogger(__name__)

# Derive a 32-byte Fernet key from the app's secret key
_fernet_key: Optional[bytes] = None


def _get_fernet() -> Fernet:
    """Get or create a Fernet instance keyed off the app's secret key."""
    global _fernet_key
    if _fernet_key is None:
        # Hash the secret key to get a deterministic 32-byte base64-encoded key
        key_material = hashlib.sha256(settings.secret_key.encode()).digest()
        _fernet_key = base64.urlsafe_b64encode(key_material)
    return Fernet(_fernet_key)


def encrypt(data: bytes) -> bytes:
    """Encrypt data using AES-256 (Fernet)."""
    f = _get_fernet()
    return f.encrypt(data)


def decrypt(token: bytes) -> bytes:
    """Decrypt data that was encrypted with encrypt()."""
    f = _get_fernet()
    try:
        return f.decrypt(token)
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError("Decryption failed — data may be corrupted or key has changed")


def encrypt_embedding(embedding: list[float]) -> bytes:
    """Encrypt a face embedding (list of floats) for storage."""
    import struct

    data = struct.pack(f"{len(embedding)}f", *embedding)
    return encrypt(data)


def decrypt_embedding(encrypted_bytes: bytes, expected_length: int = 512) -> list[float]:
    """Decrypt a face embedding back to a list of floats."""
    import struct

    data = decrypt(encrypted_bytes)
    count = len(data) // 4
    embedding = list(struct.unpack(f"{count}f", data))
    return embedding[:expected_length]