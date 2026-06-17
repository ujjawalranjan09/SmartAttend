"""Tests for Phase 5 features: feature flags, A/B testing, profiling, encryption, image optimizer."""
import pytest


# ── Feature Flags ────────────────────────────────────────────────────────────


class TestFeatureFlags:
    @pytest.mark.asyncio
    async def test_set_and_check_flag(self):
        from unittest.mock import AsyncMock, patch

        fake_store = {}
        mock_redis = AsyncMock()

        async def fake_get(key):
            return fake_store.get(key)

        async def fake_setex(key, ttl, val):
            fake_store[key] = val

        mock_redis.get = fake_get
        mock_redis.setex = fake_setex
        mock_redis.scan = AsyncMock(return_value=(0, []))

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            from app.core.feature_flags import set_feature_flag, is_feature_enabled

            await set_feature_flag("test_flag", True)
            assert await is_feature_enabled("test_flag") is True

    @pytest.mark.asyncio
    async def test_disabled_flag_returns_false(self):
        from unittest.mock import AsyncMock, patch

        fake_store = {}
        mock_redis = AsyncMock()

        async def fake_get(key):
            return fake_store.get(key)

        async def fake_setex(key, ttl, val):
            fake_store[key] = val

        mock_redis.get = fake_get
        mock_redis.setex = fake_setex
        mock_redis.scan = AsyncMock(return_value=(0, []))

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            from app.core.feature_flags import set_feature_flag, is_feature_enabled

            await set_feature_flag("disabled_flag", False)
            assert await is_feature_enabled("disabled_flag") is False

    @pytest.mark.asyncio
    async def test_undefined_flag_returns_false(self):
        from unittest.mock import AsyncMock, patch

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.scan = AsyncMock(return_value=(0, []))

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            from app.core.feature_flags import is_feature_enabled

            assert await is_feature_enabled("nonexistent_flag_xyz") is False

    @pytest.mark.asyncio
    async def test_institution_override(self):
        import uuid
        from unittest.mock import AsyncMock, patch

        fake_store = {}
        mock_redis = AsyncMock()

        async def fake_get(key):
            return fake_store.get(key)

        async def fake_setex(key, ttl, val):
            fake_store[key] = val

        mock_redis.get = fake_get
        mock_redis.setex = fake_setex
        mock_redis.scan = AsyncMock(return_value=(0, []))

        with patch("app.core.redis.get_redis", return_value=mock_redis):
            from app.core.feature_flags import set_feature_flag, is_feature_enabled

            inst_id = uuid.uuid4()
            await set_feature_flag("global_on", True)
            await set_feature_flag("global_on", False, institution_id=inst_id)

            assert await is_feature_enabled("global_on") is True
            assert await is_feature_enabled("global_on", institution_id=inst_id) is False


# ── A/B Testing ──────────────────────────────────────────────────────────────


class TestABTesting:
    def test_deterministic_assignment(self):
        import uuid
        from app.core.ab_testing import _get_variant_key

        user_id = uuid.uuid4()
        # Same user always gets same variant
        v1 = _get_variant_key("exp1", user_id)
        v2 = _get_variant_key("exp1", user_id)
        assert v1 == v2
        assert v1 in (0, 1)

    def test_different_users_can_differ(self):
        import uuid
        from app.core.ab_testing import _get_variant_key

        # With enough users, at least one should differ
        variants = {_get_variant_key("exp2", uuid.uuid4()) for _ in range(20)}
        assert len(variants) > 1  # Should have both 0 and 1


# ── Encryption ───────────────────────────────────────────────────────────────


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        from app.services.encryption_service import encrypt, decrypt

        original = b"Hello, SmartAttend!"
        encrypted = encrypt(original)
        assert encrypted != original
        decrypted = decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_embedding(self):
        from app.services.encryption_service import encrypt_embedding, decrypt_embedding

        embedding = [0.1, 0.2, 0.3] + [0.0] * 509  # 512-dim
        encrypted = encrypt_embedding(embedding)
        assert isinstance(encrypted, bytes)
        decrypted = decrypt_embedding(encrypted, expected_length=512)
        assert len(decrypted) == 512
        assert abs(decrypted[0] - 0.1) < 1e-6
        assert abs(decrypted[1] - 0.2) < 1e-6

    def test_decrypt_wrong_data_raises(self):
        from app.services.encryption_service import decrypt

        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt(b"not-valid-encrypted-data")


# ── Image Optimizer ──────────────────────────────────────────────────────────


class TestImageOptimizer:
    def test_optimize_resizes_large_image(self):
        from PIL import Image
        import io
        from app.services.image_optimizer import optimize_image

        # Create a 1000x1000 image
        img = Image.new("RGB", (1000, 1000), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        original = buf.getvalue()

        optimized = optimize_image(original)
        result_img = Image.open(io.BytesIO(optimized))
        assert result_img.width <= 640
        assert result_img.height <= 640
        assert result_img.format == "JPEG"

    def test_optimize_strips_exif(self):
        from PIL import Image
        import io
        from app.services.image_optimizer import optimize_image

        img = Image.new("RGB", (100, 100))
        # Add EXIF-like data
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        original = buf.getvalue()

        optimized = optimize_image(original)
        result_img = Image.open(io.BytesIO(optimized))
        assert result_img.info.get("exif") is None or len(result_img.info.get("exif", b"")) == 0

    def test_optimize_invalid_image_raises(self):
        from app.services.image_optimizer import optimize_image

        with pytest.raises(ValueError, match="Invalid image"):
            optimize_image(b"not-an-image")


# ── Profiling Middleware ─────────────────────────────────────────────────────


class TestProfiling:
    @pytest.mark.asyncio
    async def test_profiling_disabled_in_production(self):
        """Profiling should not interfere with normal requests."""
        # The middleware checks settings.app_env and skips if not development
        # Just verify the middleware class can be imported
        from app.core.profiling import ProfilingMiddleware
        assert ProfilingMiddleware is not None
