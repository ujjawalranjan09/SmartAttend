# Phase 1: Foundation — SmartAttend Design Spec

> **Date:** 2026-06-17
> **Scope:** 23 tasks across backend, frontend, infrastructure
> **Goal:** Make existing code production-quality with tests, proper auth flows, error handling, and mobile-ready UI

---

## [S1] Problem

SmartAttend has a solid backend (7 API routes, 6 services, 10 models) and frontend (7 views), but lacks:
- Tests (zero exist)
- Complete auth flows (no registration, password reset, change password)
- Structured logging and audit trails
- Frontend form validation, error/loading/empty states
- Mobile responsiveness
- Student QR scanner UI
- CI quality gates (coverage, type checking)

## [S2] Solution Overview

Implement Phase 1 in 3 workstreams:
1. **Backend Foundation** — tests, RBAC audit, auth flows, logging, notifications, audit, error standardization
2. **Frontend Foundation** — validation, states, responsive, QR scanner, registration/forgot-password pages, notifications wiring
3. **Infrastructure** — CI improvements, pre-commit hooks, env documentation

## [S3] Backend Foundation (Tasks 1.1–1.10)

### 1.1–1.2 Testing Infrastructure

**Testcontainers approach:**
- `tests/conftest.py` with session-scoped PostgreSQL 16 and Redis 7 containers
- Async test client via `httpx.AsyncClient` with `ASGITransport`
- Transaction rollback per test for isolation
- Fixtures: `db_session`, `client`, `auth_headers` (factory for each role)

**Unit tests per service:**
- `test_user_service.py`: CRUD, search, bulk create, TOTP
- `test_session_service.py`: start/end/list
- `test_attendance_service.py`: geo-fence, record creation, override
- `test_analytics_service.py`: student/course analytics, at-risk
- `test_proxy_service.py`: feature extraction, scoring, alert creation
- `test_face_service.py`: cosine similarity, enrollment

**Integration tests per route:**
- `test_auth_api.py`: login, refresh, TOTP setup, register, password flows
- `test_sessions_api.py`: start, end, QR generation, list
- `test_attendance_api.py`: mark, override, list by session
- `test_students_api.py`: CRUD, bulk, attendance history
- `test_faculty_api.py`: CRUD, sessions, analytics
- `test_analytics_api.py`: student, course, at-risk, summary
- `test_reports_api.py`: CSV export, report generation

**Coverage target:** 70% minimum (CI gate), aim for 80%+

### 1.3 RBAC Fix

Audit every endpoint in `app/api/v1/`. Ensure `require_roles()` is called on all protected routes. Add institution-scoping dependency to filter data by `user.institution_id`.

### 1.4 Structured Logging

- Add `structlog` to requirements
- Create `app/core/logging.py`: processor chain (timestamp → request_id → JSON)
- Add `X-Request-ID` middleware to generate/propagate correlation IDs
- Configure log level via `LOG_LEVEL` env var

### 1.5 Registration Endpoint

```
POST /api/v1/auth/register
Body: { email, phone, full_name, password, invite_code }
Response: { user, token }
```

- Validate invite_code against a configured list or generate tokens per institution
- Hash password, create user with `is_active=True`
- Send verification email (async via Celery or background task)

### 1.6 Forgot/Reset Password

```
POST /api/v1/auth/forgot-password
Body: { email }
Response: { message: "Reset link sent" }

POST /api/v1/auth/reset-password
Body: { token, new_password }
Response: { message: "Password reset" }
```

New model `PasswordReset`: id, user_id, token_hash (SHA256), expires_at (15 min), used
Email service via `aiosmtplib` (async SMTP)

### 1.7 Change Password

```
POST /api/v1/auth/change-password
Body: { current_password, new_password }
Response: { message: "Password changed" }
```

### 1.8 Database-Backed Notifications

New model `Notification`: id, user_id, title, body, type (alert/reminder/system), is_read, link, created_at

`NotificationService`: create, list (paginated), mark_read, unread_count
Wire Celery tasks to create DB records instead of `print()`

### 1.9 Audit Logging

New model `AuditLog`: id, user_id, action, resource_type, resource_id, old_value (JSONB), new_value (JSONB), ip_address, user_agent, created_at

`AuditService.log()` called on: user create/update/delete, attendance override, session start/end, password changes

### 1.10 Standardized Error Responses

All errors return:
```json
{
  "error": {
    "code": "ATTENDANCE_GEO_FENCE_FAILED",
    "message": "Location is outside the allowed area",
    "details": {}
  }
}
```

Create `app/core/errors.py` with error code enum and exception handlers.

## [S4] Frontend Foundation (Tasks 1.11–1.19)

### 1.11 Form Validation

`src/utils/validators.js`: reusable validators (required, email, minLength, maxLength, pattern, match)
Wire into: login, create session, create/edit student, settings forms
Show inline errors below fields, prevent submit if invalid

### 1.12 Error States

Every API-backed view catches errors → shows error card with message + retry button
Global error handler in `api.js` intercepts 4xx/5xx responses

### 1.13 Loading States

Skeleton screens for: sessions list, students list, analytics, reports
Currently only dashboard has skeletons — extend pattern to all views

### 1.14 Empty States

SVG illustrations for: "No sessions yet", "No students enrolled", "No attendance records", "No reports generated"

### 1.15 Responsive Design

- Sidebar: collapse to hamburger on < 768px
- Tables: horizontal scroll wrapper on mobile
- Dashboard grid: 2-col → 1-col on < 768px
- Forms: full-width inputs on mobile
- Test at 375px, 768px, 1024px

### 1.16 QR Scanner

New view `src/views/qr-scanner.js`:
- Use `html5-qrcode` library (CDN)
- Camera-based QR scanning
- On scan: call `POST /api/v1/attendance/mark` with QR token
- Show success/failure feedback
- Fallback: manual code entry input

### 1.17 Registration Page

New view `src/views/register.js`:
- Form: full name, email, phone, password, confirm password, invite code
- Link from login page
- Client-side validation before submit
- On success: redirect to login with success toast

### 1.18 Forgot Password Page

New view `src/views/forgot-password.js`:
- Step 1: email input → API call → "Check your email" confirmation
- Step 2: password reset form (token from URL hash)
- Link from login page

### 1.19 Notifications Wiring

Replace hardcoded mock data with real API calls
Add unread badge count in topbar
Wire mark-as-read on click

## [S5] Infrastructure (Tasks 1.20–1.23)

### 1.20 pytest-cov in CI

Add `--cov=app --cov-fail-under=70` to pytest command in `ci.yml`
Add coverage report upload (optional: Codecov)

### 1.21 mypy in CI

Add mypy job to `ci.yml`. Start with `--ignore-missing-imports`, add strict flags incrementally.

### 1.22 Pre-commit Hooks

`.pre-commit-config.yaml`: ruff (lint+format), mypy, trailing-whitespace, end-of-file-fixer, check-yaml

### 1.23 .env.example

Document all vars from `config.py` with descriptions and defaults, grouped by category.

## [S6] File Changes Summary

**New files (backend):**
- `tests/conftest.py`, `tests/test_*.py` (14 test files)
- `app/models/notification.py`, `app/models/audit_log.py`, `app/models/password_reset.py`
- `app/schemas/notification.py`, `app/schemas/password_reset.py`
- `app/services/notification_service.py`, `app/services/audit_service.py`
- `app/core/logging.py`, `app/core/errors.py`
- Alembic migration for new tables

**New files (frontend):**
- `src/views/qr-scanner.js`, `src/views/register.js`, `src/views/forgot-password.js`
- `src/utils/validators.js`

**New files (infra):**
- `.pre-commit-config.yaml`
- Updated `.env.example`

**Modified files:**
- All 7 API route files (RBAC audit, error standardization)
- `app/core/deps.py` (institution scoping)
- `app/main.py` (logging middleware, error handlers)
- `src/utils/api.js` (error interceptor)
- `src/index.html` (new nav items, responsive sidebar)
- All 7 frontend views (validation, error/loading/empty states, responsive)
- `.github/workflows/ci.yml` (coverage, mypy)
- `requirements.txt` (structlog, aiosmtplib, pytest-cov)
- `Makefile` (test coverage target)
