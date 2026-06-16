import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

TABLES_TO_SKIP = {"face_embeddings"}


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        tables = [
            t for t in Base.metadata.sorted_tables if t.name not in TABLES_TO_SKIP
        ]
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=tables
            )
        )
    yield engine
    async with engine.begin() as conn:
        tables = [
            t for t in Base.metadata.sorted_tables if t.name not in TABLES_TO_SKIP
        ]
        await conn.run_sync(
            lambda sync_conn: Base.metadata.drop_all(
                sync_conn, tables=tables
            )
        )
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
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

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
        short_name="TU",
        city="Testville",
        state="Testland",
        country="Testia",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)
    return inst


@pytest_asyncio.fixture
async def test_admin(db_session, test_institution):
    admin = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("Admin@1234"),
        role=UserRole.ADMIN,
        institution_id=test_institution.id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_faculty(db_session, test_institution):
    faculty = User(
        id=uuid.uuid4(),
        email="faculty@test.com",
        full_name="Test Faculty",
        hashed_password=hash_password("Faculty@1234"),
        role=UserRole.FACULTY,
        institution_id=test_institution.id,
        employee_id="EMP001",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(faculty)
    await db_session.commit()
    await db_session.refresh(faculty)
    return faculty


@pytest_asyncio.fixture
async def test_student(db_session, test_institution):
    student = User(
        id=uuid.uuid4(),
        email="student@test.com",
        full_name="Test Student",
        hashed_password=hash_password("Student@1234"),
        role=UserRole.STUDENT,
        institution_id=test_institution.id,
        roll_number="STU001",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)
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
