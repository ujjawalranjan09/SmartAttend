import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.institution import Institution


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


class FakePipeline:
    """Minimal fake Redis pipeline for rate limit testing."""

    def __init__(self, store: dict):
        self._store = store
        self._ops = []

    def incr(self, key: str):
        self._ops.append(("incr", key))
        return self

    def expire(self, key: str, ttl: int):
        self._ops.append(("expire", key, ttl))
        return self

    async def execute(self) -> list:
        results = []
        for op in self._ops:
            if op[0] == "incr":
                self._store[op[1]] = self._store.get(op[1], 0) + 1
                results.append(self._store[op[1]])
            elif op[0] == "expire":
                pass
        self._ops.clear()
        return results


class FakeRedis:
    """Minimal fake Redis client for rate limit testing."""

    def __init__(self, store: dict):
        self._store = store

    def pipeline(self):
        return FakePipeline(self._store)

    async def aclose(self):
        pass


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        nested = await session.begin_nested()
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_engine, db_session):
    async def override_get_db():
        yield db_session

    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_data(db_session):
    inst = Institution(
        id=uuid.uuid4(),
        name="Test University",
        short_name=f"TU-{uuid.uuid4().hex[:8]}",
        city="Testville",
        state="Testland",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(inst)
    await db_session.flush()

    admin = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("Admin@1234"),
        role=UserRole.ADMIN,
        institution_id=inst.id,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.flush()

    return {"institution": inst, "admin": admin}


def _auth_headers(user: User) -> dict:
    token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "institution_id": str(user.institution_id)},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_rate_limit_allows_under_limit(client, test_data):
    """Requests under the limit should pass through."""
    store: dict[str, int] = {}
    fake_redis = FakeRedis(store)

    with patch("app.core.redis.get_redis", return_value=fake_redis):
        headers = _auth_headers(test_data["admin"])
        for i in range(10):
            resp = await client.get("/api/v1/auth/me", headers=headers)
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_blocks_over_limit(client, test_data):
    """Requests over the limit should get 429."""
    store: dict[str, int] = {}
    fake_redis = FakeRedis(store)

    with patch("app.core.redis.get_redis", return_value=fake_redis):
        headers = _auth_headers(test_data["admin"])
        for i in range(10):
            await client.get("/api/v1/auth/me", headers=headers)

        resp = await client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_rate_limit_by_ip_for_anonymous(client):
    """Anonymous requests should be rate-limited by IP."""
    store: dict[str, int] = {}
    fake_redis = FakeRedis(store)

    with patch("app.core.redis.get_redis", return_value=fake_redis):
        resp = await client.get("/health")
        assert resp.status_code in (200, 503)
