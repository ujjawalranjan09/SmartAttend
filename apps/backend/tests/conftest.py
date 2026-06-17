import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

TABLES_TO_SKIP = {"face_embeddings"}


def get_tables():
    return [t for t in Base.metadata.sorted_tables if t.name not in TABLES_TO_SKIP]


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    tables = get_tables()
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables)
        )
    yield engine
    tables = get_tables()
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.drop_all(sync_conn, tables=tables)
        )
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Single shared session used by both fixtures AND the test client.

    Uses begin_nested() (savepoint) so each test's data is rolled back
    after the test completes, keeping tests isolated.
    """
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        nested = await session.begin_nested()
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_engine, db_session):
    """Test client that uses the SAME session as fixtures.

    This ensures test_admin / test_student data is visible to API endpoints.
    """

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
async def test_institution(db_session):
    from app.models.institution import Institution

    inst = Institution(
        id=uuid.uuid4(),
        name="Test University",
        short_name=f"TU-{uuid.uuid4().hex[:8]}",
        city="Testville",
        state="Testland",
        country="Testia",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(inst)
    await db_session.flush()
    return inst


@pytest_asyncio.fixture
async def test_admin(db_session, test_institution):
    admin = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("Admin@1234"),
        role=UserRole.ADMIN,
        institution_id=test_institution.id,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.flush()
    return admin


@pytest_asyncio.fixture
async def test_faculty(db_session, test_institution):
    faculty = User(
        id=uuid.uuid4(),
        email=f"faculty-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Test Faculty",
        hashed_password=hash_password("Faculty@1234"),
        role=UserRole.FACULTY,
        institution_id=test_institution.id,
        employee_id="EMP001",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(faculty)
    await db_session.flush()
    return faculty


@pytest_asyncio.fixture
async def test_student(db_session, test_institution):
    student = User(
        id=uuid.uuid4(),
        email=f"student-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Test Student",
        hashed_password=hash_password("Student@1234"),
        role=UserRole.STUDENT,
        institution_id=test_institution.id,
        roll_number=f"STU-{uuid.uuid4().hex[:8]}",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(student)
    await db_session.flush()
    return student


def auth_headers(user: User) -> dict:
    token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "institution_id": str(user.institution_id)},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(test_admin):
    return auth_headers(test_admin)


@pytest_asyncio.fixture
async def faculty_headers(test_faculty):
    return auth_headers(test_faculty)


@pytest_asyncio.fixture
async def student_headers(test_student):
    return auth_headers(test_student)
