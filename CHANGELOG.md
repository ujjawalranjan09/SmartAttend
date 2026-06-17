# Changelog

All notable changes to SmartAttend are documented here.

## [Unreleased]

## [0.4.0] — 2026-06-17 — Phase 4: Polish
### Added
- Security headers middleware (CSP, X-Frame-Options, HSTS, Permissions-Policy)
- Request body size limits (1MB default, 10MB for file uploads)
- Token blacklisting via Redis JTI for logout
- `POST /auth/logout` endpoint
- `POST /auth/data-export` — DPDP compliance (right to data portability)
- `DELETE /auth/me` — account deletion with data anonymization
- GZip compression for responses > 1KB
- Health check now verifies DB, Redis, and ML service
- Redis caching helpers (cache_get, cache_set, cache_delete, cache_delete_pattern)
- Redis pub/sub for WebSocket scaling (redis_publish, redis_subscribe)
- Architecture documentation (docs/architecture.md)
- Database schema documentation (docs/db-schema.md)
- API reference documentation (docs/api-reference.md)
- Deployment guide (docs/deployment.md)
- Locust load testing script (scripts/load_test.py)
- Pre-commit hooks configuration

## [0.3.0] — 2026-06-17 — Phase 3: Intelligence
### Added
- ML service (apps/ml-service/) — face embedding, anomaly detection, forecasting
- Face enrollment API (POST /faces/enroll, GET /faces/status, DELETE /faces/enrollment)
- Proxy detection via ML service with heuristic fallback
- Attendance trend forecasting (Prophet + linear fallback)
- Engagement scoring algorithm (weighted: attendance, trend, proxy, punctuality)
- ML service Docker integration

## [0.2.0] — 2026-06-17 — Phase 2: Features
### Added
- Institution CRUD API
- Department CRUD API
- Course CRUD API with enrollment management
- CSV bulk enrollment
- Alert management (list, filter, resolve)
- Timetable service (slots, session generation, weekly view)
- WebSocket notification stream
- Push notification subscription (Web Push API)
- Email templates (verification, password reset, low attendance, proxy alert, daily digest)
- PDF report generation (ReportLab)
- Rate limiting middleware (per-user, per-endpoint group)

## [0.1.0] — 2026-06-17 — Phase 1: Foundation
### Added
- JWT authentication with refresh tokens
- TOTP 2FA skeleton
- Registration with email verification
- Forgot/reset password flow
- Change password endpoint
- Structured logging (structlog) with request ID correlation
- Audit logging via SQLAlchemy event listeners
- Notification system (database-backed)
- QR scanner for students (html5-qrcode)
- Form validation utilities
- 23 passing tests (unit + integration)
