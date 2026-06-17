# Phase 1 Fix Plan — Detailed Agent Instructions

> **Goal:** Make all 23 tests pass. Fix every bug found in the Phase 1 code review.
> **Estimated effort:** ~2 hours of focused work.
> **Verification:** Run `pytest tests/ -v` after each section. All tests should pass (0 xfail, 0 errors).

---

## Table of Contents

1. [Fix 1: Replace passlib with direct bcrypt](#fix-1-replace-passlib-with-direct-bcrypt)
2. [Fix 2: UUID handling in UserService](#fix-2-uuid-handling-in-userservice)
3. [Fix 3: Fix conftest.py session isolation](#fix-3-fix-conftestpy-session-isolation)
4. [Fix 4: Remove all xfail decorators](#fix-4-remove-all-xfail-decorators)
5. [Fix 5: AuditLog JSONB → JSON for SQLite compat](#fix-5-auditlog-jsonb--json-for-sqlite-compat)
6. [Fix 6: Audit listener needs IP/UA from request context](#fix-6-audit-listener-needs-ipua-from-request-context)
7. [Fix 7: Login must check is_verified](#fix-7-login-must-check-is_verified)
8. [Fix 8: NotificationService UUID comparison](#fix-8-notification-service-uuid-comparison)
9. [Fix 9: QR Scanner missing session_id parsing](#fix-9-qr-scanner-missing-session_id-parsing)
10. [Fix 10: Wire forgot-password link in index.html](#fix-10-wire-forgot-password-link-in-indexhtml)
11. [Fix 11: setup_logging timing](#fix-11-setup_logging-timing)
12. [Fix 12: Register endpoint should deactivate user until verified](#fix-12-register-endpoint-should-deactivate-user-until-verified)
13. [Verification Checklist](#verification-checklist)

---

## Fix 1: Replace passlib with direct bcrypt

### Why
`passlib` is incompatible with `bcrypt>=4.1`. The `detect_wrap_bug` check crashes with `ValueError: password cannot be longer than 72 bytes`. This blocks ALL tests that create users.

### File: `apps/backend/app/core/security.py`

### What to do

**Replace the entire file contents with:**

```python
from datetime import datetime, timedelta, timezone
from typing import Any
import secrets
import uuid

import bcrypt
import pyotp
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash password using bcrypt directly (passlib removed due to bcrypt 4.x incompatibility)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: Any, extra_claims: dict = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: Any) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise ValueError("Invalid or expired token")


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
```

### Verify
```python
python -c "from app.core.security import hash_password, verify_password; h = hash_password('test123'); assert verify_password('test123', h); print('OK')"
```

---

## Fix 2: UUID handling in UserService

### Why
`get_by_id()` does `User.id == str(user_id)` which converts UUID to string. PostgreSQL auto-casts strings to UUID, but SQLite doesn't. This causes 11 tests to xfail.

### File: `apps/backend/app/services/user_service.py`

### What to do

**Step 2a:** Add `import uuid` at the top of the file (line 1 area):

```python
import uuid
from uuid import UUID
```

**Step 2b:** Replace `get_by_id` method (currently lines 22-26):

OLD:
```python
    async def get_by_id(self, user_id: str | UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == str(user_id))
        )
        return result.scalar_one_or_none()
```

NEW:
```python
    async def get_by_id(self, user_id: str | UUID) -> Optional[User]:
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
```

**Step 2c:** Replace `deactivate` method (currently lines 97-102):

OLD:
```python
    async def deactivate(self, user_id: UUID) -> bool:
        result = await self.db.execute(
            update(User).where(User.id == str(user_id)).values(is_active=False)
        )
```

NEW:
```python
    async def deactivate(self, user_id: UUID) -> bool:
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        result = await self.db.execute(
            update(User).where(User.id == user_id).values(is_active=False)
        )
```

**Step 2d:** Replace `hard_delete` method (currently lines 104-109):

OLD:
```python
    async def hard_delete(self, user_id: UUID) -> bool:
        result = await self.db.execute(
            delete(User).where(User.id == str(user_id))
        )
```

NEW:
```python
    async def hard_delete(self, user_id: UUID) -> bool:
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        result = await self.db.execute(
            delete(User).where(User.id == user_id)
        )
```

**Step 2e:** Replace `enable_totp` method (currently lines 127-134):

OLD:
```python
    async def enable_totp(self, user_id: UUID, secret: str) -> bool:
        result = await self.db.execute(
            update(User)
            .where(User.id == str(user_id))
            .values(totp_secret=secret, totp_enabled=True)
        )
```

NEW:
```python
    async def enable_totp(self, user_id: UUID, secret: str) -> bool:
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        result = await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(totp_secret=secret, totp_enabled=True)
        )
```

---

## Fix 3: Fix conftest.py session isolation

### Why
The `db_session` fixture creates one session for test data, but the `client` fixture creates a DIFFERENT session via `override_get_db`. Data created in fixtures (test_admin, test_student) is invisible to API endpoints. This causes `test_login_success` to ERROR.

### File: `apps/backend/tests/conftest.py`

### What to do

**Replace the entire file with:**

```python
import uuid
from datetime import datetime, timezone

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

TABLES_TO_SKIP = {"face_embeddings", "audit_logs"}


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
        async with session.begin():
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
        short_name="TU",
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
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("Admin@1234"),
        role=UserRole.ADMIN,
        institution_id=test_institution.id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.flush()
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
    await db_session.flush()
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
```

### Key changes from original:
1. `db_session` uses `session.begin()` instead of `session.begin_nested()` — simpler, works with SQLite
2. Fixtures use `await db_session.flush()` instead of `await db_session.commit()` — data is visible within the transaction without committing
3. `client` fixture yields the SAME `db_session` via `override_get_db` — no more invisible data
4. Removed `session_factory` from `client` — reuses `db_session` directly

---

## Fix 4: Remove all xfail decorators

### Why
After Fixes 1-3, the UUID and bcrypt issues are resolved. All xfail tests should now pass.

### File: `apps/backend/tests/test_auth.py`

**Remove these two blocks:**

Lines 41-44 (before `test_refresh_token`):
```python
@pytest.mark.xfail(
    reason="get_by_id uses str(uuid) with PostgreSQL UUID type on SQLite; "
    "value.hex attribute missing on str"
)
```

Lines 67-70 (before `test_get_me_authenticated`):
```python
@pytest.mark.xfail(
    reason="get_current_user calls get_by_id which uses str(uuid) with "
    "PostgreSQL UUID type on SQLite; value.hex attribute missing on str"
)
```

### File: `apps/backend/tests/test_user_service.py`

**Remove these three blocks:**

Lines 60-63 (before `test_get_by_id`):
```python
@pytest.mark.xfail(
    reason="get_by_id uses str(uuid) with PostgreSQL UUID type on SQLite; "
    "value.hex attribute missing on str"
)
```

Lines 73-75 (before `test_update_user`):
```python
@pytest.mark.xfail(
    reason="update calls get_by_id which uses str(uuid) with PostgreSQL UUID type on SQLite"
)
```

Lines 87-90 (before `test_deactivate_user`):
```python
@pytest.mark.xfail(
    reason="deactivate uses str(uuid) with PostgreSQL UUID type on SQLite; "
    "value.hex attribute missing on str"
)
```

### File: `apps/backend/tests/test_students.py`

**Remove ALL five `@pytest.mark.xfail` blocks** (before each of the 5 test functions).

### File: `apps/backend/tests/test_analytics_service.py`

**Remove the xfail block** (lines 22-25):
```python
@pytest.mark.xfail(
    reason="analytics_service._student_weekly_trend references "
    "ClassSession.scheduled_at which does not exist (field is 'date')"
)
```

**Also fix the analytics service bug** — the test xfail reason says `ClassSession.scheduled_at` doesn't exist. Check `apps/backend/app/services/analytics_service.py` and replace all references to `ClassSession.scheduled_at` with `ClassSession.date` (the actual column name in the model).

### File: `apps/backend/app/services/analytics_service.py`

Search for `scheduled_at` and replace with `date`:

Line 43: `ClassSession.scheduled_at >=` → `ClassSession.date >=`
Line 45: `ClassSession.scheduled_at <=` → `ClassSession.date <=`
Line 116-118: `ClassSession.scheduled_at >=` → `ClassSession.date >=`
Line 212: `ClassSession.scheduled_at >=` → `ClassSession.date >=`
Line 214: `ClassSession.scheduled_at <=` → `ClassSession.date <=`

---

## Fix 5: AuditLog JSONB → JSON for SQLite compat

### Why
`JSONB` is PostgreSQL-only. SQLite tests skip the `audit_logs` table entirely. Using `JSON` works on both.

### File: `apps/backend/app/models/audit_log.py`

**Replace line 7:**
```python
from sqlalchemy.dialects.postgresql import UUID, JSONB
```
**With:**
```python
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
```

**Replace lines 23-24:**
```python
    old_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict | None] = mapped_column(JSONB)
```
**With:**
```python
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
```

### File: `apps/backend/tests/conftest.py`

**Remove `"audit_logs"` from `TABLES_TO_SKIP`:**
```python
TABLES_TO_SKIP = {"face_embeddings"}  # audit_logs now uses JSON, works on SQLite
```

---

## Fix 6: Audit listener needs IP/UA from request context

### Why
The SQLAlchemy event listeners can't access the HTTP request. They always insert `NULL` for `ip_address` and `user_agent`.

### File: `apps/backend/app/core/audit.py`

**Replace the entire file with:**

```python
import logging
import uuid
from datetime import datetime

import structlog
from sqlalchemy import event, insert

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

_SENSITIVE_FIELDS = frozenset({"hashed_password", "embedding", "totp_secret"})

AUDITED_MODELS = frozenset({
    "User", "ClassSession", "AttendanceRecord", "Course", "Enrollment",
})


def _obj_to_dict(obj) -> dict:
    result = {}
    for col in obj.__table__.columns:
        if col.name in _SENSITIVE_FIELDS:
            continue
        value = getattr(obj, col.name)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        elif hasattr(value, "value"):
            value = value.value
        result[col.name] = value
    return result


def _get_user_id(obj) -> uuid.UUID | None:
    for attr in ("user_id", "student_id", "faculty_id"):
        uid = getattr(obj, attr, None)
        if uid is not None:
            return uid
    return None


def _get_request_context() -> dict:
    """Read IP and user-agent from structlog context vars (set by middleware)."""
    ctx = structlog.contextvars.get_contextvars()
    return {
        "ip_address": ctx.get("client_ip"),
        "user_agent": ctx.get("user_agent"),
    }


def _after_insert(mapper, connection, target):
    resource_type = target.__class__.__name__
    if resource_type not in AUDITED_MODELS:
        return
    try:
        resource_id = getattr(target, "id", None)
        if resource_id is not None:
            resource_id = str(resource_id)
        req_ctx = _get_request_context()
        connection.execute(
            insert(AuditLog).values(
                user_id=_get_user_id(target),
                action=f"{resource_type}.create",
                resource_type=resource_type,
                resource_id=resource_id,
                new_value=_obj_to_dict(target),
                ip_address=req_ctx.get("ip_address"),
                user_agent=req_ctx.get("user_agent"),
            )
        )
    except Exception:
        logger.exception("Failed to capture audit log for %s", target)


def _after_update(mapper, connection, target):
    resource_type = target.__class__.__name__
    if resource_type not in AUDITED_MODELS:
        return
    try:
        resource_id = getattr(target, "id", None)
        if resource_id is not None:
            resource_id = str(resource_id)
        req_ctx = _get_request_context()
        connection.execute(
            insert(AuditLog).values(
                user_id=_get_user_id(target),
                action=f"{resource_type}.update",
                resource_type=resource_type,
                resource_id=resource_id,
                new_value=_obj_to_dict(target),
                ip_address=req_ctx.get("ip_address"),
                user_agent=req_ctx.get("user_agent"),
            )
        )
    except Exception:
        logger.exception("Failed to capture audit log for %s", target)


def setup_audit_listeners():
    from app.models.user import User
    from app.models.session import ClassSession
    from app.models.attendance import AttendanceRecord
    from app.models.course import Course, Enrollment

    target_models = [User, ClassSession, AttendanceRecord, Course, Enrollment]
    for model_cls in target_models:
        event.listen(model_cls, "after_insert", _after_insert, propagate=True)
        event.listen(model_cls, "after_update", _after_update, propagate=True)

    logger.info("Audit event listeners registered")
```

### File: `apps/backend/app/core/logging.py`

**Add `client_ip` and `user_agent` to the context vars in `RequestIDMiddleware.dispatch`:**

Replace the `dispatch` method (lines 39-45):

OLD:
```python
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

NEW:
```python
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

---

## Fix 7: Login must check is_verified

### Why
Users can log in before verifying their email. The `is_verified` field exists but is never checked.

### File: `apps/backend/app/api/v1/auth.py`

**After line 55 (`raise HTTPException(status_code=403, detail="Account disabled")`), add:**

```python
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox.")
```

So the login endpoint becomes:
```python
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox.")
```

### Also update test fixtures

### File: `apps/backend/tests/conftest.py`

**Add `is_verified=True` to all three user fixtures** (test_admin, test_faculty, test_student):

```python
    admin = User(
        ...
        is_active=True,
        is_verified=True,   # <-- ADD THIS
        created_at=datetime.now(timezone.utc),
    )
```

Do the same for `test_faculty` and `test_student`.

---

## Fix 8: NotificationService UUID comparison

### Why
`Notification.user_id == str(user_id)` converts UUID to string. On PostgreSQL with UUID columns, this may not use the index efficiently and is inconsistent.

### File: `apps/backend/app/services/notification_service.py`

**Replace line 38:**
```python
        base = select(Notification).where(Notification.user_id == str(user_id))
```
**With:**
```python
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        base = select(Notification).where(Notification.user_id == user_id)
```

**Add `import uuid` at the top of the file.**

**Also fix `mark_read` (line 63):**
```python
            Notification.id == str(notification_id),
            Notification.user_id == str(user_id),
```
**Replace with:**
```python
            Notification.id == uuid.UUID(str(notification_id)) if isinstance(notification_id, str) else notification_id,
            Notification.user_id == uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id,
```

Or more readably, add a helper at the top of the method:
```python
    async def mark_read(self, notification_id: UUID | str, user_id: UUID | str) -> bool:
        if isinstance(notification_id, str):
            notification_id = uuid.UUID(notification_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True)
        )
        await self.db.commit()
        return result.rowcount > 0
```

---

## Fix 9: QR Scanner missing session_id parsing

### Why
The `MarkAttendanceRequest` schema requires `session_id` (not optional). The QR scanner sends only `qr_token` without extracting session_id from the QR data URL format `smartattend://attend?session=XXX&token=YYY`.

### File: `apps/frontend/src/views/qr-scanner.js`

**Replace the `markAttendance` function (lines 73-95):**

OLD:
```javascript
async function markAttendance(code) {
  const resultEl = document.getElementById('qr-result');
  const statusEl = document.getElementById('qr-status');

  statusEl.innerHTML = '<i data-lucide="loader"></i><span>Submitting attendance...</span>';
  if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);

  try {
    await attendanceApi.mark({ qr_token: code });
    ...
```

NEW:
```javascript
async function markAttendance(code) {
  const resultEl = document.getElementById('qr-result');
  const statusEl = document.getElementById('qr-status');

  statusEl.innerHTML = '<i data-lucide="loader"></i><span>Submitting attendance...</span>';
  if (typeof lucide !== 'undefined') setTimeout(() => lucide.createIcons(), 50);

  try {
    // Parse QR data: expected format "smartattend://attend?session=XXX&token=YYY"
    let sessionId = null;
    let qrToken = code;
    try {
      const url = new URL(code);
      sessionId = url.searchParams.get('session');
      qrToken = url.searchParams.get('token') || code;
    } catch {
      // Not a URL — treat as raw token (manual entry)
    }

    if (!sessionId) {
      throw new Error('Invalid QR code: missing session ID. Please scan the session QR again.');
    }

    await attendanceApi.mark({
      session_id: sessionId,
      qr_token: qrToken,
    });
    ...
```

The rest of the function (success/error handling) stays the same.

---

## Fix 10: Wire forgot-password link in index.html

### Why
The "Forgot password?" link on the login page goes to `href="#"` — it does nothing.

### File: `apps/frontend/index.html`

**Replace line 59:**
```html
            <a href="#" class="link">Forgot password?</a>
```
**With:**
```html
            <a href="#forgot-password" class="link">Forgot password?</a>
```

---

## Fix 11: setup_logging timing

### Why
`setup_logging()` is called at module import time in `main.py`. This runs even during tests, polluting test output with structlog JSON.

### File: `apps/backend/app/main.py`

**Move `setup_logging()` into the lifespan:**

Replace lines 14-23:
```python
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
    setup_audit_listeners()
    yield
```

With:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
    setup_audit_listeners()
    yield
```

Remove the standalone `setup_logging()` call on line 14.

---

## Fix 12: Register endpoint should deactivate user until verified

### Why
Users can log in immediately after registration, before verifying their email.

### File: `apps/backend/app/api/v1/auth.py`

**In the `register` function (around line 133), after `user = await svc.create(user_data)`, add:**

```python
    # Deactivate until email is verified
    user.is_active = False
    user.is_verified = False
    await db.commit()
```

**In the `verify_registration` function (around line 170-172), after `pr.used = True`, add:**

```python
    pr.user.is_active = True
    pr.user.is_verified = True
    pr.used = True
    await db.commit()
```

So the full verify_registration becomes:
```python
    pr.user.is_active = True
    pr.user.is_verified = True
    pr.used = True
    await db.commit()
    return {"detail": "Email verified successfully"}
```

---

## Verification Checklist

After applying ALL fixes above, run these commands in order:

### Step 1: Install bcrypt (if not already installed)
```bash
cd apps/backend
python -m pip install bcrypt
```

### Step 2: Run all tests
```bash
python -m pytest tests/ -v --tb=short
```

**Expected result:** 23 tests, ALL passing, 0 xfail, 0 errors.

### Step 3: Check that no xfail remains
```bash
python -m pytest tests/ -v 2>&1 | grep -c "XFAIL"
```
**Expected:** 0

### Step 4: Verify the app still starts
```bash
python -c "from app.main import app; print('App loaded OK')"
```

### Step 5: Verify security module works
```bash
python -c "
from app.core.security import hash_password, verify_password, create_access_token, decode_token
h = hash_password('test123')
assert verify_password('test123', h)
assert not verify_password('wrong', h)
token = create_access_token(subject='test-user', extra_claims={'role': 'admin'})
payload = decode_token(token)
assert payload['sub'] == 'test-user'
assert payload['role'] == 'admin'
print('All security checks passed')
"
```

### Step 6: Verify models import correctly
```bash
python -c "
from app.models import User, Notification, AuditLog, PasswordReset
print('All models imported OK')
"
```

---

## Summary of All Files Changed

| File | Change |
|------|--------|
| `apps/backend/app/core/security.py` | Replace passlib with direct bcrypt |
| `apps/backend/app/services/user_service.py` | Fix UUID handling in get_by_id, deactivate, hard_delete, enable_totp |
| `apps/backend/tests/conftest.py` | Fix session isolation, add is_verified, remove audit_logs from skip |
| `apps/backend/tests/test_auth.py` | Remove 2 xfail decorators |
| `apps/backend/tests/test_user_service.py` | Remove 3 xfail decorators |
| `apps/backend/tests/test_students.py` | Remove 5 xfail decorators |
| `apps/backend/tests/test_analytics_service.py` | Remove 1 xfail decorator |
| `apps/backend/app/services/analytics_service.py` | Fix scheduled_at → date |
| `apps/backend/app/models/audit_log.py` | JSONB → JSON |
| `apps/backend/app/core/audit.py` | Add request context for IP/UA |
| `apps/backend/app/core/logging.py` | Add client_ip, user_agent to context vars |
| `apps/backend/app/api/v1/auth.py` | Add is_verified check in login, deactivate on register, activate on verify |
| `apps/backend/app/services/notification_service.py` | Fix UUID comparison |
| `apps/frontend/src/views/qr-scanner.js` | Parse session_id from QR URL |
| `apps/frontend/index.html` | Wire forgot-password link |
| `apps/backend/app/main.py` | Move setup_logging into lifespan |
