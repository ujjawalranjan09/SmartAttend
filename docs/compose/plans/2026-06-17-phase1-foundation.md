# Phase 1: Foundation Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SmartAttend production-quality with tests, complete auth flows, structured logging, form validation, error/loading/empty states, mobile responsiveness, QR scanner, and CI quality gates.

**Architecture:** Backend gets aiosqlite-based unit tests (with testcontainers for integration tests when Docker is available), new auth endpoints (admin-created user, forgot/reset/change password), database-backed notifications with SQLAlchemy event-based audit logging, and standardized error responses. Frontend gets form validation, error/loading/empty states, responsive fixes, QR scanner (with backend JWT-based student_id inference), and new pages. Infrastructure gets CI coverage reporting and pre-commit hooks.

**Tech Stack:** FastAPI, SQLAlchemy async, aiosqlite (tests), structlog, pytest, httpx, html5-qrcode

---

## Key Design Decisions (from feedback)

1. **Testing**: SQLite in-memory for unit tests (fast, no Docker needed). Testcontainers for integration tests only (skipped if Docker unavailable).
2. **Registration**: Admin-created users only in Phase 1. No self-registration or invite codes.
3. **Email**: Abstraction with console fallback when SMTP not configured.
4. **Audit logging**: SQLAlchemy event listeners (after_insert, after_update, after_delete), not manual calls.
5. **Institution scoping**: Helper functions per service (join chains), not a single FastAPI dependency.
6. **Coverage**: Start at 0% threshold (report only), increase weekly.
7. **mypy**: No `--strict` initially.

---

## Workstream A: Backend Foundation

### Task 1: Testing Infrastructure

**Covers:** [S3]

**Files:**
- Create: `apps/backend/tests/__init__.py`
- Create: `apps/backend/tests/conftest.py`
- Modify: `apps/backend/requirements.txt`

- [ ] **Step 1: Add test dependencies to requirements.txt**

Append to `apps/backend/requirements.txt`:
```
aiosqlite==0.20.0
pytest-cov==5.0.0
pytest-asyncio==0.23.6
```

- [ ] **Step 2: Create tests directory**

```python
# apps/backend/tests/__init__.py
# (empty)
```

- [ ] **Step 3: Create conftest.py with SQLite-based fixtures**

```python
# apps/backend/tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.main import app
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole

# SQLite in-memory for fast unit tests — no Docker required
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_institution(db_session: AsyncSession):
    from app.models.institution import Institution
    inst = Institution(name="Test University", short_name="TU", city="Mumbai", state="MH", country="India")
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)
    return inst


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession, test_institution):
    user = User(
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("Admin@123"),
        role=UserRole.ADMIN,
        institution_id=test_institution.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_faculty(db_session: AsyncSession, test_institution):
    user = User(
        email="faculty@test.com",
        full_name="Test Faculty",
        hashed_password=hash_password("Faculty@123"),
        role=UserRole.FACULTY,
        institution_id=test_institution.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_student(db_session: AsyncSession, test_institution):
    user = User(
        email="student@test.com",
        full_name="Test Student",
        hashed_password=hash_password("Student@123"),
        role=UserRole.STUDENT,
        institution_id=test_institution.id,
        is_active=True,
        roll_number="STU001",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "institution_id": str(user.institution_id) if user.institution_id else None}
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
```

- [ ] **Step 4: Verify conftest loads**

Run: `cd apps/backend && python -c "from tests.conftest import *; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add apps/backend/tests/ apps/backend/requirements.txt
git commit -m "test: add testing infrastructure with SQLite in-memory fixtures"
```

---

### Task 2: Build require_roles() and Audit RBAC

**Covers:** [S3]

**Files:**
- Modify: `apps/backend/app/core/deps.py`
- Modify: `apps/backend/app/api/v1/*.py` (all route files)

- [ ] **Step 1: Create require_roles() in deps.py**

The current `deps.py` already has `require_roles(*roles)` defined at line 37. Verify it works, then add institution scoping helpers:

```python
# Add to apps/backend/app/core/deps.py after require_student

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.institution import Institution, Department
from app.models.course import Course


async def get_user_institution_id(current_user: User, db: AsyncSession) -> UUID | None:
    """Get institution_id for the current user. Returns None for super-admins."""
    if current_user.institution_id:
        return current_user.institution_id
    return None


def filter_by_institution(query, model, institution_id: UUID | None):
    """Apply institution filter to a SQLAlchemy query. Handles direct and indirect relations."""
    if institution_id is None:
        return query  # Super-admin: no filter
    # Direct institution_id column
    if hasattr(model, 'institution_id'):
        return query.where(model.institution_id == institution_id)
    return query
```

- [ ] **Step 2: Audit all API routes for RBAC**

Check each file and ensure every protected endpoint has a role dependency:

Run: `cd apps/backend && grep -n "def " app/api/v1/auth.py app/api/v1/sessions.py app/api/v1/attendance.py app/api/v1/students.py app/api/v1/faculty.py app/api/v1/analytics.py app/api/v1/reports.py | grep -v "def _"`

For each endpoint, verify it has `Depends(require_admin)`, `Depends(require_faculty)`, `Depends(require_student)`, or `Depends(get_current_user)`.

Known gaps to fix:
- `auth.py:GET /me` — uses `get_current_user` (correct, no role needed)
- `auth.py:POST /totp/setup` — missing `get_current_user` dependency

- [ ] **Step 3: Fix TOTP setup to require auth**

In `apps/backend/app/api/v1/auth.py`, update the TOTP setup endpoint:

```python
@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    secret = generate_totp_secret()
    return TOTPSetupResponse(secret=secret)
```

- [ ] **Step 4: Commit**

```bash
git add apps/backend/app/core/deps.py apps/backend/app/api/v1/auth.py
git commit -m "feat: add institution scoping helpers and fix RBAC on TOTP endpoint"
```

---

### Task 3: Unit Tests for Existing Services

**Covers:** [S3]

**Files:**
- Create: `apps/backend/tests/test_user_service.py`
- Create: `apps/backend/tests/test_session_service.py`
- Create: `apps/backend/tests/test_attendance_service.py`
- Create: `apps/backend/tests/test_analytics_service.py`

> Note: Only testing existing services with real logic. Skipping face_service and proxy_service (stubs) — those get tests in Phase 3.

- [ ] **Step 1: Write UserService tests**

```python
# apps/backend/tests/test_user_service.py
import pytest
from uuid import uuid4
from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import UserRole


@pytest.mark.asyncio
async def test_create_user(db_session):
    svc = UserService(db_session)
    data = UserCreate(
        email="new@test.com", full_name="New User", password="Pass@123",
        role=UserRole.STUDENT, institution_id=uuid4()
    )
    user = await svc.create(data)
    assert user.email == "new@test.com"
    assert user.role == UserRole.STUDENT


@pytest.mark.asyncio
async def test_get_by_email(db_session, test_student):
    svc = UserService(db_session)
    user = await svc.get_by_email("student@test.com")
    assert user is not None
    assert user.email == "student@test.com"


@pytest.mark.asyncio
async def test_get_by_email_not_found(db_session):
    svc = UserService(db_session)
    user = await svc.get_by_email("nobody@test.com")
    assert user is None


@pytest.mark.asyncio
async def test_get_by_id(db_session, test_student):
    svc = UserService(db_session)
    user = await svc.get_by_id(str(test_student.id))
    assert user is not None


@pytest.mark.asyncio
async def test_update_user(db_session, test_student):
    svc = UserService(db_session)
    updated = await svc.update(test_student.id, UserUpdate(full_name="Updated"))
    assert updated.full_name == "Updated"


@pytest.mark.asyncio
async def test_deactivate_user(db_session, test_student):
    svc = UserService(db_session)
    result = await svc.deactivate(test_student.id)
    assert result is True
    user = await svc.get_by_id(str(test_student.id))
    assert user.is_active is False


@pytest.mark.asyncio
async def test_bulk_create(db_session):
    svc = UserService(db_session)
    inst_id = uuid4()
    users = [
        UserCreate(email=f"bulk{i}@test.com", full_name=f"Bulk {i}",
                   password="Pass@123", role=UserRole.STUDENT, institution_id=inst_id)
        for i in range(3)
    ]
    result = await svc.bulk_create(users)
    assert result["created"] == 3
    assert result["failed"] == 0
```

- [ ] **Step 2: Write AttendanceService tests**

```python
# apps/backend/tests/test_attendance_service.py
import pytest
from uuid import uuid4
from app.services.attendance_service import AttendanceService


def test_haversine_same_point():
    svc = AttendanceService.__new__(AttendanceService)
    assert svc._haversine_distance(19.0760, 72.8777, 19.0760, 72.8777) == 0.0


def test_haversine_known_distance():
    svc = AttendanceService.__new__(AttendanceService)
    dist = svc._haversine_distance(19.0760, 72.8777, 19.0770, 72.8787)
    assert 100 < dist < 200


@pytest.mark.asyncio
async def test_get_by_session_empty(db_session):
    svc = AttendanceService(db_session)
    records = await svc.get_by_session(uuid4())
    assert records == []
```

- [ ] **Step 3: Write AnalyticsService tests**

```python
# apps/backend/tests/test_analytics_service.py
import pytest
from uuid import uuid4
from app.services.analytics_service import AnalyticsService


@pytest.mark.asyncio
async def test_get_student_analytics_no_data(db_session):
    svc = AnalyticsService(db_session)
    result = await svc.get_student_analytics(uuid4())
    assert result is not None
    assert "attendance_percentage" in result
```

- [ ] **Step 4: Run tests**

Run: `cd apps/backend && python -m pytest tests/ -v --asyncio-mode=auto -x`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/backend/tests/test_user_service.py apps/backend/tests/test_attendance_service.py apps/backend/tests/test_analytics_service.py
git commit -m "test: add unit tests for UserService, AttendanceService, AnalyticsService"
```

---

### Task 4: Integration Tests for Auth and Students API

**Covers:** [S3]

**Files:**
- Create: `apps/backend/tests/test_auth_api.py`
- Create: `apps/backend/tests/test_students_api.py`

- [ ] **Step 1: Write auth integration tests**

```python
# apps/backend/tests/test_auth_api.py
import pytest


@pytest.mark.asyncio
async def test_login_success(client, test_admin):
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com", "password": "Admin@123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_admin):
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com", "password": "Wrong",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "ghost@test.com", "password": "Pass@123",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client, test_admin, admin_headers):
    response = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_get_me_no_token(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client, test_admin):
    login = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com", "password": "Admin@123",
    })
    refresh = login.json()["refresh_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_change_password(client, test_admin, admin_headers):
    response = await client.post("/api/v1/auth/change-password", headers=admin_headers, json={
        "current_password": "Admin@123", "new_password": "NewPass@1234",
    })
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(client, test_admin, admin_headers):
    response = await client.post("/api/v1/auth/change-password", headers=admin_headers, json={
        "current_password": "WrongPass", "new_password": "NewPass@1234",
    })
    assert response.status_code == 400
```

- [ ] **Step 2: Write students API tests**

```python
# apps/backend/tests/test_students_api.py
import pytest


@pytest.mark.asyncio
async def test_list_students(client, admin_headers):
    response = await client.get("/api/v1/students", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_student_requires_admin(client, student_headers):
    response = await client.get("/api/v1/students", headers=student_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_student(client, admin_headers, test_institution):
    response = await client.post("/api/v1/students", headers=admin_headers, json={
        "email": "created@test.com", "full_name": "Created",
        "password": "Pass@123", "role": "student",
        "institution_id": str(test_institution.id),
    })
    assert response.status_code == 200
    assert response.json()["email"] == "created@test.com"
```

- [ ] **Step 3: Run all tests**

Run: `cd apps/backend && python -m pytest tests/ -v --asyncio-mode=auto`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add apps/backend/tests/test_auth_api.py apps/backend/tests/test_students_api.py
git commit -m "test: add integration tests for auth and students API"
```

---

### Task 5: Structured Logging

**Covers:** [S3]

**Files:**
- Create: `apps/backend/app/core/logging.py`
- Modify: `apps/backend/app/main.py`
- Modify: `apps/backend/requirements.txt`

- [ ] **Step 1: Add structlog**

Append to `apps/backend/requirements.txt`:
```
structlog==24.1.0
```

- [ ] **Step 2: Create logging module**

```python
# apps/backend/app/core/logging.py
import structlog
import logging
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


def setup_logging(log_level: str = "INFO"):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

- [ ] **Step 3: Wire into main.py**

In `apps/backend/app/main.py`, add after imports:
```python
from app.core.logging import setup_logging, RequestIDMiddleware
setup_logging(log_level="INFO" if settings.app_env == "development" else "WARNING")
```

Add middleware after CORS:
```python
app.add_middleware(RequestIDMiddleware)
```

- [ ] **Step 4: Commit**

```bash
git add apps/backend/app/core/logging.py apps/backend/app/main.py apps/backend/requirements.txt
git commit -m "feat: add structlog with request ID correlation middleware"
```

---

### Task 6: New Database Models + Migration

**Covers:** [S3]

**Files:**
- Create: `apps/backend/app/models/notification.py`
- Create: `apps/backend/app/models/audit_log.py`
- Create: `apps/backend/app/models/password_reset.py`
- Modify: `apps/backend/app/models/__init__.py`

- [ ] **Step 1: Create Notification model**

```python
# apps/backend/app/models/notification.py
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    link: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
```

- [ ] **Step 2: Create AuditLog model**

```python
# apps/backend/app/models/audit_log.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    old_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
```

- [ ] **Step 3: Create PasswordReset model**

```python
# apps/backend/app/models/password_reset.py
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
```

- [ ] **Step 4: Update models __init__.py**

```python
# apps/backend/app/models/__init__.py
from app.models.user import User, UserRole
from app.models.institution import Institution, Department
from app.models.course import Course, Enrollment
from app.models.session import ClassSession, TimetableSlot
from app.models.attendance import AttendanceRecord, AttendanceMethod
from app.models.face import FaceEmbedding
from app.models.alert import Alert, AlertType
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.models.password_reset import PasswordReset

__all__ = [
    "User", "UserRole", "Institution", "Department",
    "Course", "Enrollment", "ClassSession", "TimetableSlot",
    "AttendanceRecord", "AttendanceMethod", "FaceEmbedding",
    "Alert", "AlertType", "Notification", "AuditLog", "PasswordReset",
]
```

- [ ] **Step 5: Generate Alembic migration**

Run: `cd apps/backend && alembic revision --autogenerate -m "add notifications, audit_logs, password_resets tables"`
Expected: New migration file in `alembic/versions/`

- [ ] **Step 6: Commit**

```bash
git add apps/backend/app/models/ apps/backend/alembic/versions/
git commit -m "feat: add Notification, AuditLog, PasswordReset models and migration"
```

---

### Task 7: Registration Endpoint (Admin-Created Users)

**Covers:** [S3]

> Phase 1: Admin creates users via the existing `/students` POST endpoint. No self-registration. Registration page on frontend is removed from Phase 1 scope.

**Files:**
- Verify: `apps/backend/app/api/v1/students.py` (already has POST /students)

- [ ] **Step 1: Verify admin can create users**

The existing `POST /api/v1/students` endpoint already supports creating students with admin role check. Test it:

Run: `cd apps/backend && python -m pytest tests/test_students_api.py::test_create_student -v`
Expected: PASS

- [ ] **Step 2: Add frontend API for admin user creation**

The `studentsApi.create` already exists in `apps/frontend/src/utils/api.js`. No changes needed.

- [ ] **Step 3: Commit (no changes needed)**

This task is a verification-only task. No code changes.

---

### Task 8: Forgot/Reset/Change Password with Email Fallback

**Covers:** [S3]

**Files:**
- Modify: `apps/backend/app/schemas/auth.py`
- Modify: `apps/backend/app/api/v1/auth.py`
- Create: `apps/backend/app/services/email_service.py`

- [ ] **Step 1: Add password schemas**

```python
# Add to apps/backend/app/schemas/auth.py

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
```

- [ ] **Step 2: Create email service with console fallback**

```python
# apps/backend/app/services/email_service.py
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str):
    """Send email. Falls back to console logging when SMTP not configured."""
    if not settings.smtp_user or not settings.smtp_password:
        logger.info(f"[EMAIL CONSOLE] To: {to} | Subject: {subject} | Body: {body}")
        return

    import aiosmtplib
    from email.mime.text import MIMEText
    msg = MIMEText(body, "html")
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        use_tls=True,
    )
```

- [ ] **Step 3: Add forgot-password and reset-password endpoints**

```python
# Add to apps/backend/app/api/v1/auth.py

import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.security import generate_secure_token, hash_password, verify_password
from app.models.password_reset import PasswordReset
from app.services.email_service import send_email
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    svc = UserService(db)
    user = await svc.get_by_email(body.email)
    if user:
        token = generate_secure_token(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        reset = PasswordReset(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        db.add(reset)
        await db.commit()
        reset_link = f"http://localhost:8000/#forgot-password?token={token}"
        await send_email(user.email, "SmartAttend Password Reset", f"<p>Reset link: <a href='{reset_link}'>{reset_link}</a></p>")
    return {"message": "If an account exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.token_hash == token_hash,
            PasswordReset.used == False,
            PasswordReset.expires_at > datetime.now(timezone.utc),
        )
    )
    reset = result.scalar_one_or_none()
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    svc = UserService(db)
    user = await svc.get_by_id(reset.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    user.hashed_password = hash_password(body.new_password)
    reset.used = True
    await db.commit()
    return {"message": "Password reset successful"}


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}
```

- [ ] **Step 4: Test**

Add to `tests/test_auth_api.py`:
```python
@pytest.mark.asyncio
async def test_forgot_password(client, test_admin):
    response = await client.post("/api/v1/auth/forgot-password", json={"email": "admin@test.com"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_forgot_password_unknown_email(client):
    response = await client.post("/api/v1/auth/forgot-password", json={"email": "unknown@test.com"})
    assert response.status_code == 200  # Always returns 200 to prevent enumeration
```

Run: `cd apps/backend && python -m pytest tests/test_auth_api.py -v --asyncio-mode=auto`

- [ ] **Step 5: Commit**

```bash
git add apps/backend/app/schemas/auth.py apps/backend/app/api/v1/auth.py apps/backend/app/services/email_service.py
git commit -m "feat: add forgot/reset/change password with email console fallback"
```

---

### Task 9: Notification Service + Celery Wiring

**Covers:** [S3]

**Files:**
- Create: `apps/backend/app/services/notification_service.py`
- Modify: `apps/backend/app/tasks/notifications.py`

- [ ] **Step 1: Create notification service**

```python
# apps/backend/app/services/notification_service.py
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.models.notification import Notification


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: uuid.UUID, title: str, body: str, type: str = "system", link: str | None = None):
        notif = Notification(user_id=user_id, title=title, body=body, type=type, link=link)
        self.db.add(notif)
        await self.db.commit()
        await self.db.refresh(notif)
        return notif

    async def list_for_user(self, user_id: uuid.UUID, page: int = 1, page_size: int = 20):
        q = select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
        unread = (await self.db.execute(select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.is_read == False))).scalar() or 0
        q = q.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        return result.scalars().all(), total, unread

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            update(Notification).where(Notification.id == notification_id, Notification.user_id == user_id).values(is_read=True)
        )
        await self.db.commit()
        return result.rowcount > 0
```

- [ ] **Step 2: Wire Celery tasks to create DB notifications**

Replace `apps/backend/app/tasks/notifications.py`:

```python
# apps/backend/app/tasks/notifications.py
from celery import shared_task
from app.core.database import SyncSessionLocal
from app.models.notification import Notification
from uuid import UUID


@shared_task
def send_low_attendance_alert(student_id: str, percentage: float):
    with SyncSessionLocal() as db:
        db.add(Notification(user_id=UUID(student_id), title="Low Attendance Warning",
                           body=f"Your attendance has dropped to {percentage:.1f}%.", type="alert"))
        db.commit()


@shared_task
def send_proxy_alert(student_id: str, session_id: str):
    with SyncSessionLocal() as db:
        db.add(Notification(user_id=UUID(student_id), title="Proxy Attempt Detected",
                           body="A proxy attendance attempt was detected.", type="alert"))
        db.commit()


@shared_task
def send_daily_digest(institution_id: str):
    with SyncSessionLocal() as db:
        from app.models.user import User
        users = db.query(User).filter(User.institution_id == UUID(institution_id), User.role == "faculty").all()
        for user in users:
            db.add(Notification(user_id=user.id, title="Daily Digest",
                               body="Your daily attendance summary is ready.", type="reminder"))
        db.commit()
```

- [ ] **Step 3: Add notification API endpoints**

Create `apps/backend/app/api/v1/notifications.py`:
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/")
async def list_notifications(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                             db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = NotificationService(db)
    items, total, unread = await svc.list_for_user(current_user.id, page, page_size)
    return {"items": [{"id": str(n.id), "title": n.title, "body": n.body, "type": n.type,
                        "is_read": n.is_read, "link": n.link, "created_at": n.created_at.isoformat()} for n in items],
            "total": total, "unread_count": unread}


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, db: AsyncSession = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    svc = NotificationService(db)
    await svc.mark_read(UUID(notification_id), current_user.id)
    return {"message": "Marked as read"}
```

Register in `main.py`:
```python
from app.api.v1 import notifications
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
```

- [ ] **Step 4: Commit**

```bash
git add apps/backend/app/services/notification_service.py apps/backend/app/tasks/notifications.py apps/backend/app/api/v1/notifications.py apps/backend/app/main.py
git commit -m "feat: add notification service, API, and Celery task wiring"
```

---

### Task 10: Audit Logging via SQLAlchemy Events

**Covers:** [S3]

**Files:**
- Create: `apps/backend/app/core/audit.py`

> Uses SQLAlchemy event listeners (after_insert, after_update, after_delete) instead of manual calls in every endpoint.

- [ ] **Step 1: Create audit event listener**

```python
# apps/backend/app/core/audit.py
from sqlalchemy import event
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
import uuid
from datetime import datetime


def _capture_audit(session: Session, flush_ctx, instances):
    """SQLAlchemy after_flush event — captures pending changes for audit log."""
    for obj in session.new:
        if isinstance(obj, AuditLog):
            continue  # Don't audit audit logs
        session.add(AuditLog(
            user_id=getattr(obj, 'institution_id', None),  # Will be overridden by middleware
            action=f"{type(obj).__name__}.create",
            resource_type=type(obj).__name__,
            resource_id=obj.id if hasattr(obj, 'id') else None,
            new_value=_obj_to_dict(obj),
            created_at=datetime.utcnow(),
        ))
    for obj in session.dirty:
        if isinstance(obj, AuditLog):
            continue
        session.add(AuditLog(
            action=f"{type(obj).__name__}.update",
            resource_type=type(obj).__name__,
            resource_id=obj.id if hasattr(obj, 'id') else None,
            new_value=_obj_to_dict(obj),
            created_at=datetime.utcnow(),
        ))


def _obj_to_dict(obj):
    """Serialize model attributes to dict (exclude relationships and large fields)."""
    if not hasattr(obj, '__table__'):
        return {}
    return {c.name: str(getattr(obj, c.name)) for c in obj.__table__.columns
            if c.name not in ('hashed_password', 'embedding', 'totp_secret')}


def setup_audit_listeners():
    """Register audit listeners on all auditable models."""
    from app.models.user import User
    from app.models.session import ClassSession
    from app.models.attendance import AttendanceRecord
    from app.models.course import Course, Enrollment

    for model in [User, ClassSession, AttendanceRecord, Course, Enrollment]:
        event.listen(model, 'after_insert', _capture_audit, propagate=True)
        event.listen(model, 'after_update', _capture_audit, propagate=True)
```

- [ ] **Step 2: Wire into app startup**

In `apps/backend/app/main.py`, add in the lifespan:
```python
from app.core.audit import setup_audit_listeners

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
    setup_audit_listeners()
    yield
```

- [ ] **Step 3: Commit**

```bash
git add apps/backend/app/core/audit.py apps/backend/app/main.py
git commit -m "feat: add audit logging via SQLAlchemy event listeners"
```

---

### Task 11: Standardized Error Responses

**Covers:** [S3]

**Files:**
- Create: `apps/backend/app/core/errors.py`
- Modify: `apps/backend/app/main.py`

- [ ] **Step 1: Create error handlers**

```python
# apps/backend/app/core/errors.py
from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


async def general_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred", "details": {}}},
    )
```

- [ ] **Step 2: Register handlers in main.py**

```python
from app.core.errors import AppError, app_error_handler, general_error_handler
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, general_error_handler)
```

- [ ] **Step 3: Commit**

```bash
git add apps/backend/app/core/errors.py apps/backend/app/main.py
git commit -m "feat: add standardized error response handlers"
```

---

### Task 12: Fix /attendance/mark to Infer Student from JWT

**Covers:** [S3]

**Files:**
- Modify: `apps/backend/app/api/v1/attendance.py`

> The current mark endpoint accepts `student_id` in the request body. This allows students to mark attendance for others. Fix: infer `student_id` from the JWT token.

- [ ] **Step 1: Read current attendance.py to understand the endpoint**

Read `apps/backend/app/api/v1/attendance.py` and find the `POST /mark` endpoint.

- [ ] **Step 2: Modify to infer student_id from JWT**

Change the mark endpoint to use `get_current_user` dependency and extract `student_id` from the JWT:

```python
from app.core.deps import get_current_user

@router.post("/mark")
async def mark_attendance(
    body: MarkAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Infer student_id from JWT, ignore any student_id in body
    student_id = current_user.id
    # ... rest of existing logic using student_id
```

- [ ] **Step 3: Update MarkAttendanceRequest schema**

Remove `student_id` from the request body (or make it optional/ignored):

In `apps/backend/app/schemas/attendance.py`, remove or mark `student_id` as deprecated in `MarkAttendanceRequest`.

- [ ] **Step 4: Commit**

```bash
git add apps/backend/app/api/v1/attendance.py apps/backend/app/schemas/attendance.py
git commit -m "fix: infer student_id from JWT in attendance mark endpoint"
```

---

## Workstream B: Frontend Foundation

### Task 13: Form Validation Utility

**Covers:** [S4]

**Files:**
- Create: `apps/frontend/src/utils/validators.js`

- [ ] **Step 1: Create validators**

```javascript
// apps/frontend/src/utils/validators.js

export const validators = {
  required: (value) => (!value || (typeof value === 'string' && !value.trim())) ? 'This field is required' : null,
  email: (value) => (!value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) ? null : 'Invalid email',
  minLength: (min) => (value) => (!value || value.length >= min) ? null : `Min ${min} characters`,
  maxLength: (max) => (value) => (!value || value.length <= max) ? null : `Max ${max} characters`,
  match: (fieldName) => (value, all) => value === all[fieldName] ? null : `Must match ${fieldName}`,
};

export function validateForm(fields, values) {
  const errors = {};
  let valid = true;
  for (const [name, rules] of Object.entries(fields)) {
    for (const rule of rules) {
      const err = rule(values[name], values);
      if (err) { errors[name] = err; valid = false; break; }
    }
  }
  return { valid, errors };
}

export function showFieldError(el, msg) {
  const g = el.closest('.form-group');
  if (!g) return;
  g.classList.add('has-error');
  let e = g.querySelector('.field-error');
  if (!e) { e = document.createElement('span'); e.className = 'field-error'; g.appendChild(e); }
  e.textContent = msg;
}

export function clearFieldError(el) {
  const g = el.closest('.form-group');
  if (!g) return;
  g.classList.remove('has-error');
  const e = g.querySelector('.field-error');
  if (e) e.textContent = '';
}
```

- [ ] **Step 2: Add error styles**

Append to `apps/frontend/src/styles/main.css`:
```css
.form-group.has-error input, .form-group.has-error select { border-color: #ef4444; }
.field-error { color: #ef4444; font-size: 0.75rem; margin-top: 0.25rem; display: block; }
```

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/utils/validators.js apps/frontend/src/styles/main.css
git commit -m "feat: add form validation utility and error styles"
```

---

### Task 14: Error/Loading/Empty States

**Covers:** [S4]

**Files:**
- Modify: `apps/frontend/src/utils/ui.js`
- Modify: `apps/frontend/src/views/sessions.js`
- Modify: `apps/frontend/src/views/students.js`
- Modify: `apps/frontend/src/views/analytics.js`
- Modify: `apps/frontend/src/views/reports.js`

- [ ] **Step 1: Rewrite ui.js with state helpers**

```javascript
// apps/frontend/src/utils/ui.js

export function renderError(container, message, onRetry) {
  container.innerHTML = `<div class="empty-state">
    <div class="empty-icon"><i data-lucide="alert-circle"></i></div>
    <h3>Something went wrong</h3>
    <p class="text-muted">${message}</p>
    ${onRetry ? '<button class="btn btn-primary" id="retry-btn">Try Again</button>' : ''}
  </div>`;
  if (onRetry) container.querySelector('#retry-btn')?.addEventListener('click', onRetry);
}

export function renderLoading(container, count = 3) {
  container.innerHTML = `<div class="skeleton-grid">${Array(count).fill('').map(() =>
    `<div class="skeleton-card"><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text short"></div><div class="skeleton skeleton-text shorter"></div></div>`
  ).join('')}</div>`;
}

export function renderEmpty(container, icon, title, subtitle) {
  container.innerHTML = `<div class="empty-state">
    <div class="empty-icon"><i data-lucide="${icon}"></i></div>
    <h3>${title}</h3><p class="text-muted">${subtitle}</p></div>`;
}

export function formatDate(d) { return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }); }
export function formatTime(d) { return new Date(d).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }); }
export function formatPercent(n) { return `${Math.round(n || 0)}%`; }
```

- [ ] **Step 2: Add skeleton/empty-state CSS**

Append to `apps/frontend/src/styles/main.css`:
```css
.skeleton-grid { display: flex; flex-direction: column; gap: 1rem; padding: 1rem; }
.skeleton-card { background: var(--surface); border-radius: 12px; padding: 1.5rem; }
.skeleton { background: linear-gradient(90deg, var(--surface) 25%, var(--surface-hover, #333) 50%, var(--surface) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 6px; height: 1rem; margin-bottom: 0.75rem; }
.skeleton-text.short { width: 60%; }
.skeleton-text.shorter { width: 40%; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 3rem; text-align: center; }
.empty-icon { width: 64px; height: 64px; border-radius: 50%; background: var(--surface); display: flex; align-items: center; justify-content: center; margin-bottom: 1rem; color: var(--text-muted); }
```

- [ ] **Step 3: Wire error/loading/empty into sessions.js**

At the top of `renderSessions`, before API call:
```javascript
import { renderError, renderLoading, renderEmpty } from '../utils/ui.js';
// ...
renderLoading(container);
try {
  const data = await sessionsApi.list();
  if (!data?.length) { renderEmpty(container, 'calendar', 'No sessions yet', 'Create a session to get started'); return; }
  // ... existing render
} catch (err) { renderError(container, err.message || 'Failed to load', () => renderSessions(container, state)); }
```

- [ ] **Step 4: Apply same pattern to students.js, analytics.js, reports.js**

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/utils/ui.js apps/frontend/src/styles/main.css apps/frontend/src/views/
git commit -m "feat: add error, loading, and empty states to all API-backed views"
```

---

### Task 15: Responsive Design

**Covers:** [S4]

**Files:**
- Modify: `apps/frontend/src/styles/main.css`

- [ ] **Step 1: Add responsive media queries**

Append to main.css:
```css
@media (max-width: 768px) {
  .sidebar { position: fixed; left: -260px; z-index: 100; transition: left 0.3s; }
  .sidebar.mobile-open { left: 0; }
  .mobile-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 99; }
  .mobile-overlay.visible { display: block; }
  .main-wrapper { margin-left: 0; }
  .stat-cards { grid-template-columns: 1fr 1fr; }
  .dashboard-grid { grid-template-columns: 1fr; }
  .table-container { overflow-x: auto; }
  .auth-card { margin: 1rem; padding: 1.5rem; }
}
@media (min-width: 769px) {
  .mobile-menu-btn { display: none; }
  .mobile-overlay { display: none !important; }
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/styles/main.css
git commit -m "feat: add responsive CSS for mobile"
```

---

### Task 16: QR Scanner View

**Covers:** [S4]

**Files:**
- Create: `apps/frontend/src/views/qr-scanner.js`
- Modify: `apps/frontend/src/app.js`

- [ ] **Step 1: Create QR Scanner view**

```javascript
// apps/frontend/src/views/qr-scanner.js
import { attendanceApi } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

export async function renderQrScanner(container, state) {
  container.innerHTML = `
    <div class="page-header"><h1>Scan QR Code</h1><p class="text-muted">Point camera at session QR code</p></div>
    <div class="qr-scanner-wrapper">
      <div id="qr-reader" style="width:100%;max-width:400px;margin:0 auto;"></div>
      <div style="margin-top:1rem;text-align:center;">
        <p class="text-muted">Or enter code manually</p>
        <div style="display:flex;gap:0.5rem;justify-content:center;margin-top:0.5rem;">
          <input type="text" id="qr-manual-input" placeholder="QR code" class="input" style="max-width:200px;" />
          <button class="btn btn-primary" id="qr-manual-submit">Submit</button>
        </div>
      </div>
      <div id="qr-result" style="margin-top:1rem;"></div>
    </div>`;

  document.getElementById('qr-manual-submit')?.addEventListener('click', async () => {
    const code = document.getElementById('qr-manual-input')?.value?.trim();
    if (!code) return showToast('Enter a code', 'error');
    await submitAttendance(code);
  });

  try {
    const { Html5Qrcode } = await import('https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js');
    const scanner = new Html5Qrcode('qr-reader');
    await scanner.start({ facingMode: 'environment' }, { fps: 10, qrbox: 250 },
      async (text) => { scanner.stop(); await submitAttendance(text); }, () => {});
  } catch {
    document.getElementById('qr-reader').innerHTML = '<p class="text-muted">Camera not available. Use manual entry.</p>';
  }
}

async function submitAttendance(code) {
  const r = document.getElementById('qr-result');
  try {
    r.innerHTML = '<p class="text-muted">Submitting...</p>';
    await attendanceApi.mark({ qr_token: code });
    r.innerHTML = '<div class="alert alert-success">Attendance marked!</div>';
    showToast('Attendance marked!', 'success');
  } catch (err) {
    r.innerHTML = `<div class="alert alert-error">${err.message || 'Failed'}</div>`;
  }
}
```

- [ ] **Step 2: Add route to app.js**

Add import:
```javascript
import { renderQrScanner } from './views/qr-scanner.js';
```

Add to VIEWS:
```javascript
'qr-scanner': renderQrScanner
```

Add to student NAV:
```javascript
{ id: 'qr-scanner', label: 'Scan QR', icon: 'scan' },
```

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/views/qr-scanner.js apps/frontend/src/app.js
git commit -m "feat: add QR scanner view for students"
```

---

### Task 17: Forgot Password Page

**Covers:** [S4]

**Files:**
- Create: `apps/frontend/src/views/forgot-password.js`
- Modify: `apps/frontend/src/app.js`
- Modify: `apps/frontend/index.html`

- [ ] **Step 1: Create forgot password view**

```javascript
// apps/frontend/src/views/forgot-password.js
import { api } from '../utils/api.js';
import { showToast } from '../utils/toast.js';

export function renderForgotPassword(container) {
  const params = new URLSearchParams(window.location.hash.split('?')[1]);
  const token = params.get('token');

  if (token) {
    container.innerHTML = `<div class="auth-screen" style="position:static;background:none;">
      <div class="auth-card"><h1 class="auth-title">Reset Password</h1>
        <form id="reset-form" class="auth-form">
          <div class="form-group"><label>New Password</label><input type="password" id="new-pw" required /></div>
          <div class="form-group"><label>Confirm</label><input type="password" id="confirm-pw" required /></div>
          <div id="reset-error" class="auth-error hidden"></div>
          <button type="submit" class="btn btn-primary btn-full">Reset</button>
        </form></div></div>`;
    document.getElementById('reset-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const pw = document.getElementById('new-pw').value;
      if (pw.length < 8 || pw !== document.getElementById('confirm-pw').value) {
        document.getElementById('reset-error').textContent = 'Invalid passwords'; document.getElementById('reset-error').classList.remove('hidden'); return;
      }
      try { await api.post('/auth/reset-password', { token, new_password: pw }); showToast('Password reset!', 'success'); window.location.hash = ''; window.location.reload(); }
      catch (err) { document.getElementById('reset-error').textContent = err.message; document.getElementById('reset-error').classList.remove('hidden'); }
    });
  } else {
    container.innerHTML = `<div class="auth-screen" style="position:static;background:none;">
      <div class="auth-card"><h1 class="auth-title">Forgot Password</h1>
        <form id="forgot-form" class="auth-form">
          <div class="form-group"><label>Email</label><input type="email" id="forgot-email" required /></div>
          <div id="forgot-error" class="auth-error hidden"></div>
          <div id="forgot-success" class="hidden" style="text-align:center;padding:1rem;color:green;">Sent!</div>
          <button type="submit" class="btn btn-primary btn-full">Send Reset Link</button>
          <p style="text-align:center;margin-top:1rem;"><a href="#" id="go-login" class="link">Back to sign in</a></p>
        </form></div></div>`;
    document.getElementById('go-login')?.addEventListener('click', (e) => { e.preventDefault(); window.location.hash = ''; window.location.reload(); });
    document.getElementById('forgot-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      try { await api.post('/auth/forgot-password', { email: document.getElementById('forgot-email').value }); document.getElementById('forgot-success').classList.remove('hidden'); }
      catch (err) { document.getElementById('forgot-error').textContent = err.message; document.getElementById('forgot-error').classList.remove('hidden'); }
    });
  }
}
```

- [ ] **Step 2: Add route to app.js**

```javascript
import { renderForgotPassword } from './views/forgot-password.js';
```

Add hash handler before bootApp:
```javascript
if (location.hash.startsWith('#forgot-password')) {
  document.getElementById('auth-screen').classList.add('hidden');
  const w = document.createElement('div'); document.body.appendChild(w);
  renderForgotPassword(w); return;
}
```

- [ ] **Step 3: Update forgot password link in index.html**

Change: `<a href="#forgot-password" class="link">Forgot password?</a>`

- [ ] **Step 4: Commit**

```bash
git add apps/frontend/src/views/forgot-password.js apps/frontend/src/app.js apps/frontend/index.html
git commit -m "feat: add forgot password and reset password pages"
```

---

### Task 18: Wire Notifications to Real API

**Covers:** [S4]

**Files:**
- Modify: `apps/frontend/src/app.js:240-271`
- Modify: `apps/frontend/src/utils/api.js`

- [ ] **Step 1: Add notification API**

```javascript
// Add to apps/frontend/src/utils/api.js
export const notificationsApi = {
  list: (params = {}) => api.get('/notifications?' + new URLSearchParams(params)),
  markRead: (id) => api.patch(`/notifications/${id}/read`),
};
```

- [ ] **Step 2: Replace mock notifications in app.js**

Replace `setupNotifications` function:

```javascript
async function setupNotifications() {
  const btn = document.getElementById('notif-btn');
  const panel = document.getElementById('notif-panel');
  const list = document.getElementById('notif-list');

  async function load() {
    try {
      const { notificationsApi } = await import('./utils/api.js');
      const data = await notificationsApi.list({ page_size: 10 });
      const notifs = data.items || [];
      const unread = data.unread_count || 0;
      if (unread > 0) { document.getElementById('notif-dot')?.classList.remove('hidden'); document.getElementById('notif-dot').textContent = unread; }
      else document.getElementById('notif-dot')?.classList.add('hidden');
      if (!notifs.length) { list.innerHTML = '<p style="text-align:center;padding:2rem;color:var(--text-muted);">No notifications</p>'; return; }
      list.innerHTML = notifs.map(n => `<div class="notif-item ${n.is_read ? '' : 'unread'}" data-id="${n.id}"><div class="notif-dot-icon"></div><div class="notif-body"><p>${n.title}</p><span class="notif-time">${n.body}</span></div></div>`).join('');
      list.querySelectorAll('.notif-item').forEach(i => i.addEventListener('click', async () => {
        if (i.classList.contains('unread')) { await notificationsApi.markRead(i.dataset.id); i.classList.remove('unread'); }
      }));
    } catch { list.innerHTML = '<p style="text-align:center;padding:2rem;">Failed to load</p>'; }
  }

  btn?.addEventListener('click', (e) => { e.stopPropagation(); panel.classList.toggle('hidden'); if (!panel.classList.contains('hidden')) load(); });
  document.getElementById('close-notif')?.addEventListener('click', () => panel.classList.add('hidden'));
  document.addEventListener('click', (e) => { if (!panel.contains(e.target) && e.target !== btn) panel.classList.add('hidden'); });
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/app.js apps/frontend/src/utils/api.js
git commit -m "feat: wire notification panel to real API"
```

---

## Workstream C: Infrastructure

### Task 19: pytest-cov (Report Only, No Threshold)

**Covers:** [S5]

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Update CI test step**

In `.github/workflows/ci.yml`, change test step to:
```yaml
      - name: Run tests
        working-directory: apps/backend
        run: pytest tests/ -v --asyncio-mode=auto --tb=short --cov=app --cov-report=term-missing
```

> Note: No `--cov-fail-under` yet. Coverage is reported but doesn't block CI. Increase threshold by 10% weekly after tests exist.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add pytest-cov reporting (non-blocking)"
```

---

### Task 20: mypy (Non-Strict)

**Covers:** [S5]

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add mypy job**

Add to `.github/workflows/ci.yml`:
```yaml
  typecheck:
    name: Type Check
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -r apps/backend/requirements.txt
      - name: Run mypy
        working-directory: apps/backend
        run: mypy app/ --ignore-missing-imports --no-error-summary || true
```

> Non-blocking (`|| true`). Add `--strict` in Phase 4.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add mypy type checking (non-blocking)"
```

---

### Task 21: Pre-commit Hooks (Correct Order)

**Covers:** [S5]

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Create pre-commit config**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff-format
      - id: ruff
        args: [--fix]
```

> Order: whitespace fixes first → ruff format → ruff lint. No mypy in pre-commit (too slow for commit hooks).

- [ ] **Step 2: Install**

Run: `cd apps/backend && pip install pre-commit && cd ../.. && pre-commit install`

- [ ] **Step 3: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: add pre-commit hooks (whitespace → ruff format → ruff lint)"
```

---

### Task 22: .env.example

**Covers:** [S5]

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Comprehensive .env.example**

```bash
# ══════════════════════════════════════════════════════════════
# SmartAttend — Environment Configuration
# Copy to .env and fill in values.
# ══════════════════════════════════════════════════════════════

# ── App ──────────────────────────────────────────────────────
APP_ENV=development                    # development | staging | production
APP_NAME=SmartAttend
SECRET_KEY=dev-insecure-secret-change  # [REQUIRED in prod] min 32 chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Database ─────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://smartattend:smartattend_secret@localhost:5432/smartattend
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=0

# ── Redis ────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
QR_TOKEN_TTL_SECONDS=120

# ── ML Service ───────────────────────────────────────────────
ML_SERVICE_URL=http://localhost:8001
FACE_SIMILARITY_THRESHOLD=0.60
PROXY_ANOMALY_THRESHOLD=0.75

# ── Storage (S3) ────────────────────────────────────────────
STORAGE_PROVIDER=s3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-south-1
S3_BUCKET_NAME=smartattend-media

# ── Email (SMTP) — leave empty for console fallback ─────────
EMAIL_FROM=noreply@smartattend.in
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# ── SMS (Twilio) ────────────────────────────────────────────
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=

# ── TOTP ────────────────────────────────────────────────────
TOTP_ISSUER=SmartAttend

# ── Celery ───────────────────────────────────────────────────
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ── Monitoring ──────────────────────────────────────────────
SENTRY_DSN=
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: comprehensive .env.example with all variables"
```

---

### Task 23: Add DB + Redis Check to /health

**Covers:** [S3]

**Files:**
- Modify: `apps/backend/app/main.py`

- [ ] **Step 1: Enhance health check**

Replace the health check in `main.py`:

```python
@app.get("/health", tags=["Health"])
async def health_check():
    checks = {"status": "ok", "service": settings.app_name, "env": settings.app_env}
    # DB check
    try:
        from app.core.database import async_engine
        async with async_engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        checks["status"] = "degraded"
    # Redis check
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
        checks["status"] = "degraded"
    status_code = 200 if checks["status"] == "ok" else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(content=checks, status_code=status_code)
```

Add import at top: `import sqlalchemy as sa`

- [ ] **Step 2: Commit**

```bash
git add apps/backend/app/main.py
git commit -m "feat: add DB and Redis connectivity checks to /health endpoint"
```

---

## Final Verification

- [ ] **Run full test suite**

```bash
cd apps/backend && python -m pytest tests/ -v --asyncio-mode=auto --cov=app --cov-report=term-missing
```

- [ ] **Run linter**

```bash
cd apps/backend && ruff check . && ruff format --check .
```

- [ ] **Verify frontend loads**

Open `apps/frontend/index.html` in browser, check login, navigation, QR scanner link, forgot password link.

---

## Summary (23 Tasks)

| Task | Description | Workstream |
|------|-------------|------------|
| 1 | Testing infrastructure (aiosqlite) | Backend |
| 2 | require_roles() + RBAC audit | Backend |
| 3 | Unit tests (existing services only) | Backend |
| 4 | Integration tests (auth, students) | Backend |
| 5 | Structured logging (structlog) | Backend |
| 6 | New models + Alembic migration | Backend |
| 7 | Registration verification (admin-created) | Backend |
| 8 | Forgot/reset/change password + email fallback | Backend |
| 9 | Notification service + Celery | Backend |
| 10 | Audit logging (SQLAlchemy events) | Backend |
| 11 | Standardized error responses | Backend |
| 12 | Fix /attendance/mark JWT inference | Backend |
| 13 | Form validation utility | Frontend |
| 14 | Error/loading/empty states | Frontend |
| 15 | Responsive design | Frontend |
| 16 | QR Scanner view | Frontend |
| 17 | Forgot password page | Frontend |
| 18 | Wire notifications to API | Frontend |
| 19 | pytest-cov (non-blocking) | Infra |
| 20 | mypy (non-strict) | Infra |
| 21 | Pre-commit hooks | Infra |
| 22 | .env.example | Infra |
| 23 | Health check DB/Redis | Infra |
