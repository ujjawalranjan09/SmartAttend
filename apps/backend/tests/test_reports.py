import uuid
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.institution import Institution


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _mock_rate_limit_redis():
    """Prevent RateLimitMiddleware from connecting to real Redis."""
    mock_redis = AsyncMock()
    mock_pipe = AsyncMock()
    mock_pipe.execute = AsyncMock(return_value=[0])
    mock_redis.pipeline.return_value = mock_pipe
    with patch("app.core.redis.get_redis", return_value=mock_redis):
        yield


@pytest.fixture(autouse=True)
def _mock_celery():
    """Prevent Celery tasks from connecting to broker.

    The task is imported locally inside the endpoint function body
    (from app.tasks.report_generation import generate_report_task).
    We pre-populate sys.modules so the import succeeds with a mock.
    """
    import sys

    mock_task = MagicMock()
    mock_task.delay.return_value = MagicMock(id="test-job-id")

    mock_module = MagicMock()
    mock_module.generate_report_task = mock_task

    saved = sys.modules.get("app.tasks.report_generation")
    sys.modules["app.tasks.report_generation"] = mock_module
    yield
    if saved is not None:
        sys.modules["app.tasks.report_generation"] = saved
    else:
        sys.modules.pop("app.tasks.report_generation", None)


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
async def test_generate_csv_report(client, test_data):
    headers = _auth_headers(test_data["admin"])
    resp = await client.post(
        "/api/v1/reports/generate",
        json={
            "institution_id": str(test_data["institution"].id),
            "report_type": "institution",
            "from_date": "2026-01-01",
            "to_date": "2026-12-31",
            "format": "csv",
        },
        headers=headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_generate_pdf_report(client, test_data):
    headers = _auth_headers(test_data["admin"])
    resp = await client.post(
        "/api/v1/reports/generate",
        json={
            "institution_id": str(test_data["institution"].id),
            "report_type": "institution",
            "from_date": "2026-01-01",
            "to_date": "2026-12-31",
            "format": "pdf",
        },
        headers=headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_report_status_not_found(client, test_data):
    headers = _auth_headers(test_data["admin"])
    resp = await client.get(
        "/api/v1/reports/status/nonexistent-job-id",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_report_download_not_found(client, test_data):
    headers = _auth_headers(test_data["admin"])
    resp = await client.get(
        "/api/v1/reports/download/nonexistent-job-id",
        headers=headers,
    )
    assert resp.status_code == 404
