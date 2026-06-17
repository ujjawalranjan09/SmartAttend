# SmartAttend — Phase 2-5 Detailed Implementation Plan

> **Prerequisite:** Phase 1 is complete (23/23 tests passing, bcrypt fixed, UUID handling fixed, conftest working, audit/notification/password-reset models created, auth flows implemented, QR scanner built, validators added).
>
> **Purpose:** Each task below is written so an agent can execute it without ambiguity. Every task specifies the exact file to create/modify, what to build, and how to verify.

---

## Phase 2: Features (Week 3-4) — "Make It Complete"

### 2.1 — Institution CRUD API

**Create file:** `apps/backend/app/api/v1/institutions.py`

Build a FastAPI router with these endpoints:
- `GET /api/v1/institutions` — List all institutions. Admin-only via `require_admin`. Return paginated list with `id`, `name`, `short_name`, `city`, `state`, `is_active`.
- `POST /api/v1/institutions` — Create institution. Admin-only. Accept `name` (required), `short_name` (required, unique), `city`, `state`, `country`. Validate `short_name` uniqueness — return 409 if duplicate.
- `GET /api/v1/institutions/{institution_id}` — Get single institution. Any authenticated user.
- `PUT /api/v1/institutions/{institution_id}` — Update institution. Admin-only. Allow updating `name`, `city`, `state`, `is_active`. Do NOT allow changing `short_name` after creation.
- `GET /api/v1/institutions/{institution_id}/departments` — List departments for an institution. Any authenticated user.

**Create file:** `apps/backend/app/schemas/institution.py`

Pydantic schemas: `InstitutionCreate` (name, short_name, city, state, country), `InstitutionUpdate` (name, city, state, is_active — all optional), `InstitutionResponse` (all fields + id + created_at, with `from_attributes=True`), `InstitutionListResponse` (items, total, page, page_size).

**Register router in:** `apps/backend/app/main.py`

Add import and `app.include_router(institutions.router, prefix="/api/v1/institutions", tags=["Institutions"])`.

**Write test:** `apps/backend/tests/test_institutions.py`

Test: create as admin returns 201, list returns paginated data, duplicate short_name returns 409, student cannot create (403), update works for admin.

**Verify:** `pytest tests/test_institutions.py -v` — all tests pass.

---

### 2.2 — Department CRUD API

**Create file:** `apps/backend/app/api/v1/departments.py`

Endpoints:
- `POST /api/v1/departments` — Create department. Admin-only. Accept `institution_id`, `name`, `code`. Validate that `code` is unique within the institution (not globally). Return 409 if duplicate.
- `GET /api/v1/departments` — List departments. Optional query param `institution_id` to filter. Any authenticated user.
- `GET /api/v1/departments/{department_id}` — Get single department. Any authenticated user.
- `PUT /api/v1/departments/{department_id}` — Update department name or code. Admin-only.

**Create file:** `apps/backend/app/schemas/department.py`

Schemas: `DepartmentCreate` (institution_id, name, code), `DepartmentUpdate` (name, code — both optional), `DepartmentResponse` (all fields + from_attributes).

**Register in main.py and write tests:** `apps/backend/tests/test_departments.py`

Test: create returns 201, list by institution works, duplicate code in same institution returns 409, same code in different institution is allowed.

**Verify:** `pytest tests/test_departments.py -v`

---

### 2.3 — Course CRUD API

**Create file:** `apps/backend/app/api/v1/courses.py`

Endpoints:
- `POST /api/v1/courses` — Create course. Admin or faculty. Accept `institution_id`, `department_id`, `faculty_id`, `name`, `code`, `semester`, `academic_year`, `min_attendance_pct`. Auto-set `faculty_id` to current user if role is faculty.
- `GET /api/v1/courses` — List courses. Filter by `institution_id`, `department_id`, `faculty_id`. Paginated.
- `GET /api/v1/courses/{course_id}` — Get single course with enrollment count.
- `PUT /api/v1/courses/{course_id}` — Update course. Admin can update anything. Faculty can only update their own courses.
- `GET /api/v1/courses/{course_id}/students` — List enrolled students for a course. Return student `id`, `full_name`, `roll_number`, `email`, `attendance_pct`.
- `POST /api/v1/courses/{course_id}/enroll` — Enroll students. Accept `student_ids` (list of UUIDs). Admin or faculty only. Skip already-enrolled students (don't error). Return count of newly enrolled.
- `DELETE /api/v1/courses/{course_id}/enroll/{student_id}` — Remove enrollment. Admin or faculty only.

**Create file:** `apps/backend/app/schemas/course.py`

Schemas: `CourseCreate`, `CourseUpdate`, `CourseResponse` (with `from_attributes`), `CourseListResponse`, `EnrollRequest` (student_ids: list[UUID4]).

**Register in main.py and write tests:** `apps/backend/tests/test_courses.py`

Test: create as admin, create as faculty auto-sets faculty_id, list with filters, enroll students returns count, duplicate enrollment is skipped, remove enrollment works.

**Verify:** `pytest tests/test_courses.py -v`

---

### 2.4 — Enrollment Management (CSV Upload)

**Create file:** `apps/backend/app/services/enrollment_service.py`

Methods:
- `bulk_enroll_from_csv(course_id, csv_content: str)` — Parse CSV with columns `email` OR `roll_number`. Look up each student by email or roll_number in the same institution. Enroll found students into the course. Skip students not found (log warning). Skip already-enrolled. Return dict with `enrolled_count`, `skipped_count`, `not_found` list.
- `bulk_enroll_from_ids(course_id, student_ids: list[UUID])` — Same as the course endpoint but extracted as a reusable service method.

**Add endpoint to:** `apps/backend/app/api/v1/courses.py`

`POST /api/v1/courses/{course_id}/enroll/csv` — Accept `UploadFile` (CSV). Admin or faculty only. Call `EnrollmentService.bulk_enroll_from_csv`. Return the result dict.

**Frontend — Add to:** `apps/frontend/src/views/courses.js` (created in 2.3 frontend task)

Add a "Bulk Enroll" button on the course detail page. On click, show a file upload modal (reuse Modal component from 2.22). Accept `.csv` file. POST to `/api/v1/courses/{course_id}/enroll/csv`. Show result toast: "Enrolled X students, Y skipped, Z not found."

**Write test:** `apps/backend/tests/test_enrollments.py`

Test: CSV with valid emails enrolls students, CSV with unknown emails skips them, already-enrolled students are skipped, empty CSV returns zeros.

**Verify:** `pytest tests/test_enrollments.py -v`

---

### 2.5 — Alert Management API

**Create file:** `apps/backend/app/api/v1/alerts.py`

Endpoints:
- `GET /api/v1/alerts` — List alerts. Faculty/admin see alerts for their institution. Students see only their own alerts. Filter by `is_resolved`, `alert_type`, `severity`. Paginated.
- `GET /api/v1/alerts/{alert_id}` — Get single alert detail.
- `PATCH /api/v1/alerts/{alert_id}/resolve` — Mark alert as resolved. Set `is_resolved=True`, `resolved_by_id=current_user.id`, `resolved_at=now()`. Faculty/admin only.

**Create file:** `apps/backend/app/schemas/alert.py`

Schemas: `AlertResponse` (all fields from Alert model + student_name + course_name, with `from_attributes`), `AlertListResponse` (items, total, page).

**Register in main.py and write tests:** `apps/backend/tests/test_alerts.py`

Test: faculty can list institution alerts, student sees only own alerts, resolve sets resolved_by and resolved_at, cannot resolve already-resolved alert (return 400).

**Verify:** `pytest tests/test_alerts.py -v`

---

### 2.6 — Timetable Service

**Create file:** `apps/backend/app/services/timetable_service.py`

Methods:
- `create_slot(data)` — Create a TimetableSlot with course_id, day_of_week (0-6), start_time, end_time, room, building, optional geo coordinates.
- `list_slots(course_id=None, department_id=None)` — List timetable slots with optional filters.
- `generate_sessions_for_week(start_date: date)` — For each TimetableSlot, find the matching date in the week (slot.day_of_week matches start_date + N days). Create a ClassSession with status=SCHEDULED for each slot that doesn't already have a session that week. Return count of sessions created.
- `get_weekly_view(institution_id, week_start: date)` — Return a structured weekly timetable grouped by day, with session status (scheduled/active/ended/cancelled).

**Create file:** `apps/backend/app/api/v1/timetable.py`

Endpoints:
- `POST /api/v1/timetable/slots` — Create slot. Admin or faculty.
- `GET /api/v1/timetable/slots` — List slots. Filter by course_id.
- `PUT /api/v1/timetable/slots/{slot_id}` — Update slot.
- `DELETE /api/v1/timetable/slots/{slot_id}` — Delete slot.
- `POST /api/v1/timetable/generate` — Generate sessions for a week. Accept `week_start: date`. Return count of sessions created.
- `GET /api/v1/timetable/weekly` — Get weekly view. Accept `institution_id`, `week_start: date`.

**Create file:** `apps/backend/app/schemas/timetable.py`

Schemas: `SlotCreate`, `SlotUpdate`, `SlotResponse`, `WeeklyViewResponse` (days: list of day objects, each with slots: list of session objects).

**Register in main.py and write tests:** `apps/backend/tests/test_timetable.py`

Test: create slot, generate sessions creates correct count, duplicate session for same slot+week is skipped, weekly view returns structured data.

**Verify:** `pytest tests/test_timetable.py -v`

---

### 2.7 — WebSocket Notification Stream

**Modify file:** `apps/backend/app/websocket/handlers.py`

Add a second WebSocket endpoint: `WS /ws/notifications/{user_id}`

Implementation:
- Accept connection, validate JWT token from query param `?token=XXX` (decode using `decode_token`). If invalid, close with code 4001.
- Store connection in a dict: `_notif_connections: Dict[str, Set[WebSocket]]` keyed by user_id string.
- On disconnect, remove from set.
- Add a `broadcast_to_user(user_id: str, message: dict)` function that sends to all connections for that user.

**Add broadcast calls in:** `apps/backend/app/tasks/notifications.py`

In `send_low_attendance_alert` and `send_proxy_alert` tasks, after creating the Notification DB record, also try to call `broadcast_to_user` with the notification data. Wrap in try/except — broadcast failure should not break the task.

**Frontend — Add to:** `apps/frontend/src/utils/websocket.js` (new file)

Create a WebSocket manager: `connectNotifications(userId, token, onMessage)` — opens `ws://host/ws/notifications/{userId}?token={token}`, calls `onMessage(notification)` on each message, auto-reconnects on close with exponential backoff (1s, 2s, 4s, max 30s).

**Wire in:** `apps/frontend/src/app.js`

In `bootApp()`, after login, call `connectNotifications(user.id, token, handleNewNotification)`. The `handleNewNotification` function should: update the notification badge count, show a toast, and if the notification panel is open, prepend the new notification to the list.

**Verify:** Manual test — start a session, mark attendance as student, check that faculty sees a real-time notification via WebSocket.

---

### 2.8 — Push Notification Support (Web Push API)

**Modify file:** `apps/backend/app/core/config.py`

Add settings: `vapid_public_key: str = ""`, `vapid_private_key: str = ""`, `vapid_claims_email: str = "mailto:admin@smartattend.in"`.

**Create file:** `apps/backend/app/api/v1/push.py`

Endpoints:
- `POST /api/v1/push/subscribe` — Accept `endpoint`, `keys.p256dh`, `keys.auth` from the browser PushSubscription. Store in `push_subscriptions` table linked to current user.
- `POST /api/v1/push/unsubscribe` — Remove subscription by endpoint.
- `GET /api/v1/push/vapid-public-key` — Return the VAPID public key (needed by frontend to subscribe).

**Create migration:** `apps/backend/alembic/versions/003_add_push_subscriptions.sql`

Create `push_subscriptions` table: id (UUID PK), user_id (UUID FK users.id), endpoint (TEXT), p256dh (TEXT), auth (TEXT), created_at (TIMESTAMP).

**Add to Celery task:** `apps/backend/app/tasks/notifications.py`

Add helper `send_push_notification(user_id, title, body, link)`. Look up user's push subscriptions. For each, send Web Push using `pywebpush` library. If subscription is expired/invalid (410 response), delete it.

**Frontend — Add to:** `apps/frontend/src/utils/push.js` (new file)

Functions: `requestPushPermission()` — checks if Notification API exists, requests permission, subscribes to push with VAPID key, POSTs subscription to `/api/v1/push/subscribe`. `initPushOnLogin()` — called after login, silently subscribes if permission was already granted.

**Wire in:** `apps/frontend/src/app.js`

Call `initPushOnLogin()` inside `bootApp()`.

**Add dependency:** Add `pywebpush==2.0.0` to `requirements.txt`.

**Verify:** Manual test — grant push permission in browser, trigger a notification, verify browser shows native push.

---

### 2.9 — Email Notification Delivery

**Modify file:** `apps/backend/app/services/email_service.py`

Currently this file has a `send_email` function. Enhance it:
- Add `send_templated_email(to, template_name, context)` function. Load HTML template from `apps/backend/app/templates/email/{template_name}.html`, render with simple string replacement (use `{key}` placeholders in template, replace from context dict).
- Add fallback: if SMTP is not configured, log the email content to stdout (current behavior — keep it).

**Create directory:** `apps/backend/app/templates/email/`

**Create files:**
- `apps/backend/app/templates/email/low_attendance.html` — Template with student name, course name, attendance percentage, and a link to the dashboard.
- `apps/backend/app/templates/email/proxy_alert.html` — Template with student name, session details, anomaly score.
- `apps/backend/app/templates/email/daily_digest.html` — Template with summary stats.
- `apps/backend/app/templates/email/password_reset.html` — Template with reset link.
- `apps/backend/app/templates/email/verification.html` — Template with verification link.

**Modify:** `apps/backend/app/tasks/notifications.py`

In `send_low_attendance_alert`, after creating the DB notification, call `send_templated_email` with the `low_attendance` template. Get student email from DB.
In `send_proxy_alert`, after creating the DB notification, call `send_templated_email` with the `proxy_alert` template. Get faculty email from DB.
In `send_daily_digest`, after creating DB notifications, call `send_templated_email` for each HOD/admin.

**Modify:** `apps/backend/app/api/v1/auth.py`

In `register()`, change `logger.info("Verification token...")` to `await send_templated_email(user.email, "verification", {"name": user.full_name, "token": raw_token})`.
In `forgot_password()`, change the plain-text email to `await send_templated_email(user.email, "password_reset", {"name": user.full_name, "token": raw_token})`.

**Verify:** Start the backend without SMTP configured. Register a user. Check server logs for the rendered email content. Confirm template variables are replaced.

---

### 2.10 — PDF Report Generation

**Modify file:** `apps/backend/app/tasks/report_generation.py`

Currently a skeleton. Implement:
- Function `generate_report_task(job_id, institution_id, report_type, from_date, to_date, course_id, format)` as a Celery task.
- If format is "csv": reuse the same query logic from `reports.py` export_csv endpoint but write to a temp file and store the path in a Redis key `report:{job_id}` with TTL of 1 hour.
- If format is "pdf": use `reportlab` library. Create a PDF with: title, date range, institution name, summary stats table, then a table of attendance records (student name, roll, course, date, status, method). Store PDF in temp file, path in Redis.
- Update a Redis key `report_status:{job_id}` with value "completed" and `report_path:{job_id}` with the file path.

**Create endpoint:** Add to `apps/backend/app/api/v1/reports.py`

`GET /api/v1/reports/status/{job_id}` — Check Redis for `report_status:{job_id}`. Return status (queued/completed/failed) and download_url if completed.
`GET /api/v1/reports/download/{job_id}` — Serve the generated file from the path stored in Redis. Return 404 if expired or not found.

**Add dependency:** Add `reportlab==4.2.0` to `requirements.txt`.

**Write test:** `apps/backend/tests/test_reports.py`

Test: generate CSV report returns job_id, generate PDF report returns job_id, status endpoint returns queued then completed (mock Celery with `CELERY_ALWAYS_EAGER=True` in test config).

**Verify:** `pytest tests/test_reports.py -v`

---

### 2.11 — API Rate Limiting Per User

**Modify file:** `apps/backend/app/core/redis.py`

Currently has `rate_limit_check` used only for attendance. Ensure it works generically: `rate_limit_check(key: str, limit: int, window_seconds: int) -> bool`. It should use Redis INCR with TTL. Return True if under limit, False if over.

**Create file:** `apps/backend/app/core/middleware.py`

Build a FastAPI middleware `RateLimitMiddleware`:
- For every request, extract user from JWT (decode token from Authorization header without full DB lookup — just decode and check expiry).
- Build rate limit key: `rate_limit:{user_id}:{endpoint_group}` where endpoint_group is derived from the URL path (e.g., `/api/v1/auth/login` → `auth`, `/api/v1/attendance/mark` → `attendance`).
- Apply limits: auth endpoints = 10/minute, attendance = 5/minute, read endpoints = 60/minute, write endpoints = 30/minute.
- If over limit, return 429 with `Retry-After` header.
- If no auth header (anonymous), rate limit by IP address instead.

**Register in:** `apps/backend/app/main.py`

Add `app.add_middleware(RateLimitMiddleware)` after the RequestIDMiddleware.

**Write test:** `apps/backend/tests/test_rate_limit.py`

Test: send 11 login requests rapidly, 11th returns 429. Send 61 read requests, 61st returns 429.

**Verify:** `pytest tests/test_rate_limit.py -v`

---

### 2.12 — Frontend: Admin Institution Settings Page

**Create file:** `apps/frontend/src/views/institutions.js`

Build a view with:
- A table listing all institutions (name, short_name, city, state, is_active badge).
- "Create Institution" button that opens a modal with form fields: name, short_name, city, state, country.
- Edit button on each row — opens same modal pre-filled, allows updating.
- Use the reusable Data Table component (from 2.22) and Modal component (from 2.23).

**Add to API client:** `apps/frontend/src/utils/api.js`

Add `institutionsApi`: `list()`, `create(data)`, `get(id)`, `update(id, data)`, `departments(id)`.

**Add to nav:** `apps/frontend/src/app.js`

Add `{ id: 'institutions', label: 'Institutions', icon: 'building-2' }` to the admin NAV under "Management" section.
Add `institutions: renderInstitutions` to the VIEWS map.

**Verify:** Login as admin, navigate to Institutions, create an institution, edit it, verify table updates.

---

### 2.13 — Frontend: Department Management Page

**Create file:** `apps/frontend/src/views/departments.js`

Build a view with:
- Table listing departments (name, code, institution name).
- Filter dropdown for institution.
- "Create Department" modal with fields: institution (dropdown), name, code.
- Edit button per row.

**Add to API client:** `apps/frontend/src/utils/api.js`

Add `departmentsApi`: `list(params)`, `create(data)`, `update(id, data)`.

**Add to nav:** Add `{ id: 'departments', label: 'Departments', icon: 'landmark' }` to admin NAV.

**Verify:** Login as admin, create department under institution, verify it appears in the list.

---

### 2.14 — Frontend: Course Management Page

**Create file:** `apps/frontend/src/views/courses.js`

Build a view with:
- Table listing courses (name, code, faculty, department, semester, enrolled count).
- Filters: institution, department, faculty.
- "Create Course" modal with fields: institution, department, faculty (dropdown), name, code, semester, academic_year, min_attendance_pct.
- Course detail view (expand row or separate view): enrolled students list, enroll/unenroll buttons, bulk CSV upload button.

**Add to API client:** `apps/frontend/src/utils/api.js`

Add `coursesApi`: `list(params)`, `create(data)`, `get(id)`, `update(id, data)`, `students(id)`, `enroll(id, studentIds)`, `enrollCsv(id, file)`, `unenroll(id, studentId)`.

**Add to nav:** Add to both admin and faculty NAVs.

**Verify:** Login as admin, create course, enroll students, verify enrollment count updates.

---

### 2.15 — Frontend: Enrollment CSV Upload

**Add to:** `apps/frontend/src/views/courses.js` (the course detail section)

Add a "Bulk Enroll from CSV" button. On click:
- Show modal with file input accepting `.csv`.
- Show expected format: "CSV should have a column named `email` or `roll_number`".
- On submit, use `FormData` to upload the file to `POST /api/v1/courses/{id}/enroll/csv`.
- Show result: "Enrolled X, Skipped Y, Not Found: [list of emails]".
- Refresh the enrolled students list.

**Also create:** `apps/frontend/src/components/FileUpload.js` (reusable — see 2.22)

**Verify:** Create a CSV with 3 student emails, upload it, verify students appear in enrolled list.

---

### 2.16 — Frontend: Faculty Live Session View

**Create file:** `apps/frontend/src/views/live-session.js`

Build a view that shows when a faculty member has an active session:
- At the top: session info (course name, start time, duration timer counting up).
- "Generate QR" button that calls `/api/v1/sessions/{id}/qr`, displays the QR code using QRCode.js (already loaded via CDN), and auto-refreshes every 30 seconds.
- Below: live attendance feed — a table that updates in real-time via WebSocket (`/ws/session/{id}`). Columns: student name, roll number, marked_at, method, status badge (green=present, red=proxy_suspected).
- Summary stats at top: "X/Y present (Z%)".
- "End Session" button with confirmation dialog.

**Modify:** `apps/frontend/src/views/sessions.js`

In the sessions list, for active sessions, add a "View Live" button that navigates to the live-session view with the session ID.

**Add WebSocket client:** `apps/frontend/src/utils/websocket.js`

(If not already created in 2.7) Add `connectSession(sessionId, onMessage)` that opens `ws://host/ws/session/{sessionId}` and calls `onMessage` on each attendance event.

**Add to nav:** No nav change needed — accessed from sessions list.

**Verify:** Start a session as faculty, mark attendance as student, verify the live feed updates in real-time.

---

### 2.17 — Frontend: Alert Center

**Create file:** `apps/frontend/src/views/alerts.js`

Build a view with:
- Filter bar: alert type (dropdown: low_attendance, proxy_suspected, trend_anomaly), severity (low/medium/high/critical), resolved status (all/unresolved/resolved).
- Table listing alerts: student name, course, alert type badge, severity badge, message, created_at, resolved status.
- "Resolve" button on unresolved alerts (faculty/admin only).
- Unresolved count badge in the nav.

**Add to API client:** `apps/frontend/src/utils/api.js`

Add `alertsApi`: `list(params)`, `get(id)`, `resolve(id)`.

**Add to nav:** Add `{ id: 'alerts', label: 'Alerts', icon: 'bell-ring', badge: 'alerts_count' }` to faculty and admin NAVs.

**In `bootApp()`:** Fetch unresolved alert count and set the badge dynamically.

**Verify:** Create a proxy alert (mark attendance with suspicious data), verify it appears in alerts, resolve it.

---

### 2.18 — Frontend: Faculty Timetable View

**Create file:** `apps/frontend/src/views/timetable.js`

Build a weekly timetable grid:
- 7 columns (Mon-Sun), rows are time slots (e.g., 8:00-9:00, 9:00-10:00, etc.).
- Each cell shows the course name, room, and status (scheduled/active/ended).
- Clicking a scheduled session shows options: "Start Session", "Edit Slot".
- "Generate Sessions for This Week" button at the top (calls `POST /api/v1/timetable/generate`).
- "Add Slot" button opens a modal: course (dropdown), day of week, start time, end time, room, building.

**Add to API client:** `apps/frontend/src/utils/api.js`

Add `timetableApi`: `listSlots(params)`, `createSlot(data)`, `updateSlot(id, data)`, `deleteSlot(id)`, `generateSessions(weekStart)`, `weeklyView(institutionId, weekStart)`.

**Add to nav:** Add `{ id: 'timetable', label: 'Timetable', icon: 'calendar-clock' }` to faculty NAV.

**Verify:** Create a timetable slot, generate sessions for the week, verify sessions appear in the grid.

---

### 2.19 — Frontend: Student Course Schedule

**Create file:** `apps/frontend/src/views/schedule.js`

Build a simplified timetable view for students:
- Show only the courses the student is enrolled in.
- Weekly grid similar to faculty timetable but read-only.
- Show today's classes highlighted.
- Each slot shows: course name, faculty name, room, time.

**Add to nav:** Replace the student's "Schedule" nav item (currently `{ id: 'sessions', label: 'Schedule', icon: 'calendar' }`) with `{ id: 'schedule', label: 'Schedule', icon: 'calendar-clock' }` pointing to the new view.

**Verify:** Login as student, verify schedule shows enrolled courses with correct times.

---

### 2.20 — Frontend: Profile Settings Page

**Modify file:** `apps/frontend/src/views/settings.js`

Currently the settings view exists but may be minimal. Build it out with sections:

**Section 1: Profile**
- Display: full name, email, phone, role, institution, department, roll_number/employee_id.
- "Edit Profile" button — inline editing of full_name and phone.
- Save calls `PUT /api/v1/students/{id}` or `PUT /api/v1/faculty/{id}` depending on role.

**Section 2: Change Password**
- Form: current password, new password, confirm new password.
- Client-side validation: min 8 chars, passwords match.
- Submit calls `POST /api/v1/auth/change-password`.
- Show success toast on completion.

**Section 3: Two-Factor Authentication (2FA)**
- If TOTP not enabled: "Enable 2FA" button.
- On click, call `POST /api/v1/auth/totp/setup` to get the secret.
- Display QR code (using QRCode.js) for the TOTP URI.
- Input field for the 6-digit code to confirm.
- On confirm, call a new `POST /api/v1/auth/totp/confirm` endpoint (add this to auth.py — accepts code, verifies against stored secret, sets `totp_enabled=True`).
- If TOTP already enabled: show "Disable 2FA" button (add `POST /api/v1/auth/totp/disable` endpoint).

**Section 4: Notification Preferences**
- Checkboxes: email notifications, push notifications.
- These are client-side toggles stored in localStorage for now (backend preferences can be Phase 4).

**Verify:** Login, change password, enable 2FA, verify TOTP code works on next login.

---

### 2.21 — Frontend: Notification Center (Full Page)

**Create file:** `apps/frontend/src/views/notifications.js`

Build a full-page notification view:
- List all notifications with pagination.
- Each notification: icon (based on type), title, body, timestamp, read/unread styling.
- Click a notification to mark as read and navigate to the `link` if present.
- "Mark All as Read" button at the top.
- Filter: unread only toggle.

**Add to nav:** Add `{ id: 'notifications', label: 'All Notifications', icon: 'bell' }` to all roles.

**Modify:** `apps/frontend/src/app.js`

In `setupNotifications()`, add a "View All" link at the bottom of the notification panel that navigates to the notifications page.

**Verify:** Create notifications via API, verify they appear in the list, mark as read, verify unread count updates.

---

### 2.22 — Reusable Data Table Component

**Create file:** `apps/frontend/src/components/DataTable.js`

Build a reusable function `renderDataTable(container, config)` where config has:
- `columns`: array of `{ key, label, render?, sortable?, width? }`.
- `data`: array of row objects.
- `onRowClick(row)`: optional click handler.
- `sortable`: boolean (enable column header click to sort).
- `paginated`: boolean + `pageSize`, `currentPage`, `totalItems`, `onPageChange(page)`.
- `emptyMessage`: string shown when data is empty.
- `loading`: boolean (show skeleton rows).

Features:
- Renders a `<table>` with proper `<thead>` and `<tbody>`.
- Column sorting (click header to toggle asc/desc, show arrow icon).
- Pagination controls at the bottom (Previous, page numbers, Next).
- Loading state: show 5 skeleton rows with animated pulse.
- Empty state: show the emptyMessage with an illustration icon.
- Responsive: wrap in a div with `overflow-x: auto` for mobile.

**Verify:** Use it in the students view to replace the existing inline table. Verify sorting and pagination work.

---

### 2.23 — Reusable Modal Component

**Create file:** `apps/frontend/src/components/Modal.js`

Build a function `createModal(config)` that returns `{ open(), close(), element }`:
- `config`: `{ title, content (HTML string or DOM element), size ('sm'|'md'|'lg'), onClose, onConfirm, confirmText, cancelText }`.
- The modal has: backdrop (click to close), header with title and X button, body with content, footer with Cancel and optional Confirm buttons.
- Keyboard: Escape closes, Tab traps focus inside modal.
- `open()`: appends to document body, shows with fade-in animation.
- `close()`: removes with fade-out animation.
- Only one modal open at a time (close previous if opening new).

**Verify:** Use it in the institution create flow. Open modal, fill form, submit, verify it closes.

---

### 2.24 — Reusable Form Builder

**Create file:** `apps/frontend/src/components/FormBuilder.js`

Build a function `renderForm(container, config)` where config has:
- `fields`: array of `{ name, label, type ('text'|'email'|'password'|'number'|'select'|'textarea'|'file'), required, placeholder, options (for select), validators (array of validator functions from validators.js), value (initial) }`.
- `onSubmit(values)`: called when form is valid.
- `submitText`: string.
- `cancelText`: string + `onCancel` handler.

Features:
- Renders form groups with labels, inputs, and inline error messages.
- On submit: runs all validators, shows errors inline, prevents submit if invalid.
- On input change: clears the error for that field.
- Returns a `setValues(obj)` function to programmatically set field values (for edit mode).

**Verify:** Use it to build the create institution form. Verify validation works (required fields, email format, etc.).

---

### 2.25-2.29 — Database Migrations & Indexes

These tasks were completed in Phase 1 (migration 002 created audit_logs, notifications, password_resets). The push_subscriptions migration is created in task 2.8.

**Additional migration:** `apps/backend/alembic/versions/004_performance_indexes.sql`

Add indexes:
- `idx_attendance_session_student` on `attendance_records(session_id, student_id)`.
- `idx_sessions_course_date` on `class_sessions(course_id, date)`.
- `idx_alerts_institution_unresolved` on `alerts(institution_id, is_resolved)` WHERE `is_resolved = FALSE`.
- `idx_enrollments_student_course` on `enrollments(student_id, course_id)`.
- `idx_timetable_course_day` on `timetable_slots(course_id, day_of_week)`.

**Write migration, run:** `cd apps/backend && alembic upgrade head`

**Verify:** `alembic upgrade head` succeeds. `\d attendance_records` in psql shows the new indexes.

---

## Phase 3: Intelligence (Week 5-6) — "Make It Smart"

### 3.1 — ML Service Skeleton

**Create directory structure:**
```
apps/ml-service/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app with CORS, health check
│   ├── api.py           # Route definitions
│   ├── config.py         # Settings (model paths, thresholds)
│   ├── face/
│   │   ├── __init__.py
│   │   ├── embedding.py  # Extract 512-dim face embedding from image
│   │   └── comparison.py # Cosine similarity between two embeddings
│   ├── anomaly/
│   │   ├── __init__.py
│   │   ├── features.py   # Extract feature vector from attendance record
│   │   └── isolation_forest.py  # Train/predict with Isolation Forest
│   └── forecast/
│       ├── __init__.py
│       └── prophet_model.py  # Attendance trend forecasting
├── models/               # Serialized .pkl model artifacts (gitignored)
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_face.py
│   ├── test_anomaly.py
│   └── test_forecast.py
├── Dockerfile
└── requirements.txt
```

**`app/main.py`:** FastAPI app with CORS (allow main backend origin), `/health` endpoint, include api router.

**`app/config.py`:** Settings for `FACE_MODEL_NAME` (default "buffalo_l" for InsightFace), `ANOMALY_THRESHOLD` (default 0.6), `MODEL_DIR` (path to serialized models).

**`app/api.py`:** Three route groups:
- `POST /face/embed` — Accept image file (UploadFile), return 512-dim embedding as list of floats.
- `POST /face/compare` — Accept two embeddings (list of floats each), return cosine similarity score (0-1).
- `POST /anomaly/score` — Accept feature vector (list of floats), return anomaly score (0-1).
- `POST /anomaly/train` — Accept list of feature vectors, train Isolation Forest model, save to disk. Return model version.
- `POST /forecast/predict` — Accept list of {date, attendance_pct} historical data points, return forecast for next 14 days with confidence intervals.

**`requirements.txt`:** fastapi, uvicorn, insightface, onnxruntime, numpy, scikit-learn, prophet, opencv-python-headless, pillow.

**`Dockerfile`:** Python 3.11-slim, install deps, copy app, expose 8001, run uvicorn on port 8001.

**Write tests:** Test each endpoint with sample data. For face endpoints, use a test image. For anomaly, use random feature vectors. For forecast, use synthetic time series.

**Verify:** `cd apps/ml-service && python -m pytest tests/ -v`

---

### 3.2 — Face Embedding Extraction

**Modify file:** `apps/ml-service/app/face/embedding.py`

Implementation:
- Load InsightFace model (buffalo_l) on startup, cache in a global variable.
- `extract_embedding(image_bytes: bytes) -> list[float]`: Convert bytes to numpy array using cv2/PIL, run through InsightFace face detection + ArcFace embedding. If no face detected, raise HTTPException 400. If multiple faces, use the largest. Return the 512-dim embedding as a Python list of floats.
- Handle edge cases: no face found, image too small, image too dark.

**Verify:** `POST /face/embed` with a test image returns a 512-element list of floats.

---

### 3.3 — Face Comparison

**Modify file:** `apps/ml-service/app/face/comparison.py`

Implementation:
- `compare_embeddings(emb1: list[float], emb2: list[float]) -> float`: Compute cosine similarity using numpy. Return score between 0 and 1. Higher = more similar.
- The formula: `dot(emb1, emb2) / (norm(emb1) * norm(emb2))`. Then normalize to 0-1 range (cosine similarity is -1 to 1, but face embeddings are always positive, so it's effectively 0 to 1).

**Verify:** `POST /face/compare` with two identical embeddings returns ~1.0, with random embeddings returns ~0.5.

---

### 3.4 — Isolation Forest Proxy Detection

**Modify file:** `apps/ml-service/app/anomaly/isolation_forest.py`

Implementation:
- `train_model(feature_vectors: list[list[float]], model_version: str)`: Fit an Isolation Forest with `n_estimators=100`, `contamination=0.05`. Serialize model to `models/isolation_forest_{model_version}.pkl` using joblib/pickle.
- `predict_anomaly(features: list[float], model_version: str = "latest") -> float`: Load the model, call `decision_function` to get raw score, normalize to 0-1 range (higher = more anomalous). If model not found, return 0.1 (default low risk).

**Modify file:** `apps/ml-service/app/anomaly/features.py`

Feature extraction function `extract_features(record: dict) -> list[float]`:
- Input: dict with keys `geo_accuracy_m`, `wifi_bssid_present`, `ble_beacon_present`, `face_confidence`, `device_fingerprint_present`, `time_deviation_seconds` (how far from session start the attendance was marked), `historical_avg_time` (student's average check-in time).
- Output: normalized feature vector (list of floats).

**Verify:** Train with 100 random vectors, predict on a new vector, verify score is between 0 and 1.

---

### 3.5 — Attendance Trend Forecasting

**Modify file:** `apps/ml-service/app/forecast/prophet_model.py`

Implementation:
- `forecast_attendance(historical_data: list[dict]) -> dict`: Input is list of `{date: "YYYY-MM-DD", attendance_pct: float}`. Fit Prophet model with `daily_seasonality=False`, `weekly_seasonality=True`. Predict next 14 days. Return `{forecast: [{date, predicted_pct, lower_bound, upper_bound}], trend_direction: "improving"|"declining"|"stable"}`.
- Handle edge cases: less than 14 data points (use simple linear extrapolation instead of Prophet), all values identical (return flat forecast).

**Verify:** `POST /forecast/predict` with 30 days of synthetic data returns 14-day forecast with confidence intervals.

---

### 3.6 — Model Versioning

**Modify file:** `apps/ml-service/app/api.py`

Add endpoints:
- `GET /anomaly/models` — List all trained model versions (scan the models/ directory).
- `GET /anomaly/models/{version}` — Get model metadata (training date, number of samples, feature count).

Add model metadata storage: when training, save a `{model_name}_meta.json` alongside the `.pkl` file with training_date, sample_count, feature_count.

**Verify:** Train a model, list models, verify metadata is correct.

---

### 3.7 — ML Service Docker Integration

**Modify file:** `docker-compose.yml`

Add service:
```yaml
ml-service:
  build: ./apps/ml-service
  ports:
    - "8001:8001"
  volumes:
    - ml-models:/app/models
  environment:
    - MODEL_DIR=/app/models
```

Add named volume `ml-models`.

**Modify file:** `apps/backend/app/core/config.py`

Add setting: `ml_service_url: str = "http://localhost:8001"`.

**Verify:** `docker-compose up ml-service` starts without errors, `curl http://localhost:8001/health` returns 200.

---

### 3.8 — ML Service Tests

**Create files:**
- `apps/ml-service/tests/conftest.py` — Fixtures: FastAPI test client, sample image bytes, sample feature vectors, sample time series data.
- `apps/ml-service/tests/test_face.py` — Test embed returns 512-dim vector, compare returns 0-1, embed with no face returns 400.
- `apps/ml-service/tests/test_anomaly.py` — Test train succeeds, predict returns 0-1, predict with missing model returns default.
- `apps/ml-service/tests/test_forecast.py` — Test forecast returns 14 days, handles short data, handles flat data.

**Verify:** `cd apps/ml-service && python -m pytest tests/ -v` — all pass.

---

### 3.9 — Wire ProxyDetectionService to ML Service

**Modify file:** `apps/backend/app/services/proxy_service.py`

Replace the `_compute_anomaly_score` method:
- Instead of the hardcoded heuristic, make an HTTP POST to `http://{ml_service_url}/anomaly/score` with the feature vector.
- Use `httpx.AsyncClient` with a 5-second timeout.
- If the ML service is unreachable, fall back to the current heuristic (don't break attendance marking if ML is down).
- Cache the ML service URL from settings.

**Modify file:** `apps/backend/app/core/config.py`

Ensure `ml_service_url` is used in proxy_service.

**Write test:** `apps/backend/tests/test_proxy_service.py`

Test: mock the ML service HTTP call, verify proxy_service calls it with correct features, verify fallback works when ML service returns error.

**Verify:** `pytest tests/test_proxy_service.py -v`

---

### 3.10 — Wire Face Service to ML Service

**Modify file:** `apps/backend/app/services/face_service.py`

Currently a stub. Implement:
- `enroll_face(student_id, image_bytes)` — POST image to ML service `/face/embed`, get embedding back, store in `face_embeddings` table (upsert — update if exists).
- `verify_embedding(student_id, embedding: list[float])` — Get stored embedding from DB, POST both to ML service `/face/compare`, return similarity score.
- `has_enrollment(student_id) -> bool` — Check if face_embeddings record exists.

**Modify file:** `apps/backend/app/api/v1/attendance.py`

In `mark_attendance`, the face verification logic already exists in `attendance_service.create_record`. Ensure it calls `face_service.verify_embedding` which now hits the real ML service.

**Write test:** `apps/backend/tests/test_face_service.py`

Test: mock ML service, verify enrollment stores embedding, verify verification returns score, verify missing enrollment returns 0.

**Verify:** `pytest tests/test_face_service.py -v`

---

### 3.11 — Face Enrollment Endpoint

**Create file:** `apps/backend/app/api/v1/faces.py`

Endpoints:
- `POST /api/v1/faces/enroll` — Accept image file (UploadFile). Student must be authenticated. Call `FaceService.enroll_face(current_user.id, image_bytes)`. Return success.
- `GET /api/v1/faces/status` — Return whether current user has face enrolled.
- `DELETE /api/v1/faces/enrollment` — Remove face enrollment. Student or admin.

**Create file:** `apps/backend/app/schemas/face.py`

Schemas: `FaceEnrollmentResponse` (enrolled: bool, enrolled_at: datetime).

**Register in main.py.**

**Write test:** `apps/backend/tests/test_faces.py`

Test: enroll returns success, status shows enrolled, delete removes enrollment, re-enroll works.

**Verify:** `pytest tests/test_faces.py -v`

---

### 3.12 — Face Verification in Attendance Flow

**Modify file:** `apps/backend/app/services/attendance_service.py`

In `create_record`, the face verification logic already exists. Enhance it:
- If `face_embedding` is provided in the request, check if student has a stored enrollment first (call `face_service.has_enrollment`).
- If no enrollment, skip face verification (don't mark as proxy — just note in `verification_notes` that face was not enrolled).
- If enrollment exists, call `face_service.verify_embedding` which now uses the ML service.
- Set `face_confidence` on the record.
- If confidence < 0.5, set status to PROXY_SUSPECTED.
- If confidence >= 0.5 but < 0.7, set `verification_notes` to "Low face confidence — review recommended" but keep status as PRESENT.

**Write test:** Verify the three scenarios: no enrollment (skip), high confidence (present), low confidence (proxy suspected).

**Verify:** `pytest tests/test_attendance_service.py -v`

---

### 3.13 — Real Prophet Forecasting in Analytics

**Modify file:** `apps/backend/app/services/analytics_service.py`

Replace the `_forecast` method (currently linear extrapolation of last 2 points):
- Collect the weekly trend data (already computed in `_student_weekly_trend`).
- POST to ML service `/forecast/predict` with the historical data.
- Return the 7-day forecast from the response.
- If ML service is unreachable, fall back to the current linear extrapolation.

**Modify the response schema:** `apps/backend/app/schemas/analytics.py`

Update `StudentAnalyticsResponse` to include `forecast_7d_pct` (already exists) and optionally `forecast_trend` (list of daily predictions).

**Verify:** Hit `/api/v1/analytics/student/{id}` and verify the forecast field is populated with ML service data.

---

### 3.14 — Engagement Scoring

**Modify file:** `apps/backend/app/services/analytics_service.py`

Add method `get_engagement_score(course_id: UUID) -> float`:
- Compute a weighted score based on:
  - Average attendance percentage (weight: 0.4)
  - Trend direction — improving/stable/declining (weight: 0.3)
  - Proxy incident rate — lower is better (weight: 0.2)
  - Punctuality — average time between session start and attendance mark (weight: 0.1)
- Return a score between 0 and 100.

Use this in `get_course_analytics` instead of the current `avg_pct * 0.9` heuristic.

**Verify:** Call course analytics, verify engagement_score is computed from real data.

---

### 3.15 — Frontend: Face Enrollment UI

**Modify file:** `apps/frontend/src/views/settings.js`

Add a "Face Recognition" section in settings:
- Show current enrollment status (enrolled/not enrolled, with date).
- "Enroll Face" button — opens a camera view (reuse the camera code from qr-scanner.js).
- Capture a photo, send to `POST /api/v1/faces/enroll`.
- Show success/failure message.
- "Remove Enrollment" button with confirmation dialog.

**Verify:** Login as student, go to settings, enroll face, verify status changes.

---

### 3.16 — Frontend: Face Verification in Attendance

**Modify file:** `apps/frontend/src/views/qr-scanner.js`

After scanning QR and before marking attendance:
- If student has face enrollment (check `GET /api/v1/faces/status`), add a face verification step.
- Capture photo from camera, send the embedding (computed client-side using TF.js, or send the image to the backend) along with the attendance mark request.
- Show "Verifying face..." loading state.
- If face verification fails, show "Face mismatch — attendance flagged for review" warning.

**Note:** Client-side TF.js face embedding is the ideal approach for privacy (no photos sent to server). This is a stretch goal — for Phase 3, sending the image to the backend for embedding is acceptable.

**Verify:** Enroll face, scan QR, verify face check runs, mark attendance with face data.

---

### 3.17 — Frontend: Forecast Visualization

**Modify file:** `apps/frontend/src/views/analytics.js`

In the student analytics view, after the attendance trend chart, add a "Forecast" section:
- Line chart showing historical trend (solid line) extending into a forecast (dashed line with shaded confidence interval).
- Use Chart.js `fill` option for the confidence interval area.
- Label: "Predicted attendance in 7 days: X%".

**Verify:** View analytics for a student with attendance history, verify forecast chart renders.

---

### 3.18 — Frontend: Proxy Risk Indicators

**Modify file:** `apps/frontend/src/views/attendance.js`

In the attendance records table:
- Add a "Risk" column showing the `proxy_anomaly_score`.
- Render as a colored badge: green (0-0.3), yellow (0.3-0.6), red (0.6-1.0).
- Add filter: "Show flagged only" toggle.
- For proxy_suspected records, add a red highlight on the row.

**Verify:** Mark attendance, check the attendance table, verify risk scores appear.

---

### 3.19 — Frontend: Anomaly Alerts in Dashboard

**Modify file:** `apps/frontend/src/views/dashboard.js`

In the admin and faculty dashboards:
- Add an "Alerts" card in the KPI grid showing unresolved alert count.
- Add a "Recent Alerts" section below the charts showing the latest 5 alerts with type badge, student name, and timestamp.
- Clicking an alert navigates to the alerts page.

**Verify:** Create alerts, verify dashboard shows them.

---

## Phase 4: Polish (Week 7-8) — "Make It Professional"

### 4.1 — Redis Caching

**Modify file:** `apps/backend/app/core/redis.py`

Add generic caching functions:
- `cache_get(key: str) -> Optional[str]`: Get value from Redis.
- `cache_set(key: str, value: str, ttl_seconds: int)`: Set value with TTL.
- `cache_delete(key: str)`: Delete key.

**Apply caching to:**
- `AnalyticsService.get_student_analytics` — cache result for 5 minutes keyed by `analytics:student:{id}:{course_id}:{from}:{to}`.
- `AnalyticsService.get_course_analytics` — cache for 5 minutes.
- `AnalyticsService.get_at_risk_students` — cache for 10 minutes.
- `UserService.get_by_id` — cache for 1 minute (user data changes infrequently).

Add cache invalidation: when attendance is marked, delete relevant analytics caches. When user is updated, delete user cache.

**Write test:** Verify cache hit returns same data, cache miss queries DB, cache invalidation works.

**Verify:** `pytest tests/test_caching.py -v`

---

### 4.2 — Database Query Optimization

**Audit all queries for N+1 patterns:**

Key files to check:
- `apps/backend/app/services/analytics_service.py` — The `_student_weekly_trend` method runs 16 queries (8 weeks × 2 queries each). Refactor to a single query with GROUP BY week.
- `apps/backend/app/api/v1/reports.py` — The CSV export does a JOIN but may miss some data. Verify the JOIN chain is correct.
- `apps/backend/app/api/v1/attendance.py` — The list endpoint does 3 outer JOINs. Add `selectinload` for related objects instead.

**Modify:** Add `selectinload` or `joinedload` to queries that access relationships.

**Verify:** Run `EXPLAIN ANALYZE` on key queries in PostgreSQL to verify index usage.

---

### 4.3 — API Response Compression

**Modify file:** `apps/backend/app/main.py`

Add gzip middleware:
```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

This compresses responses larger than 1KB.

**Verify:** `curl -H "Accept-Encoding: gzip" http://localhost:8000/api/v1/analytics/summary` — response should have `Content-Encoding: gzip` header.

---

### 4.4 — Frontend Code Splitting

**Modify file:** `apps/frontend/src/app.js`

Currently, all view modules are imported at the top of app.js. Change to lazy loading:
- For views not in the initial screen (everything except dashboard), use dynamic `import()` in the VIEWS map.
- Already done for forgot-password and reset-password — apply the same pattern to all other views.

Example pattern in VIEWS map:
```javascript
'sessions': (c, s) => import('./views/sessions.js').then(m => m.renderSessions(c, s)),
```

**Verify:** Open Network tab, verify that sessions.js is only loaded when navigating to Sessions view.

---

### 4.5 — Load Testing

**Create file:** `scripts/load_test.py`

Write a Locust load test script:
- `UserBehavior` class with tasks: login (weight 1), list sessions (weight 3), mark attendance (weight 5), view analytics (weight 2).
- Target: 200 concurrent users, 10 minutes duration.
- Measure: response time p50/p95/p99, error rate, throughput (req/sec).

**Add dependency:** `locust==2.28.0` to requirements.txt (dev only).

**Add Makefile target:** `load-test: cd scripts && locust -f load_test.py --host http://localhost:8000`

**Verify:** Run load test locally, identify bottlenecks, fix if response time p99 > 300ms.

---

### 4.6 — WebSocket Scaling with Redis Pub/Sub

**Modify file:** `apps/backend/app/websocket/handlers.py`

Currently uses in-memory dict `_connections`. This doesn't work with multiple workers.

Replace with Redis pub/sub:
- On WebSocket connect: subscribe to Redis channel `ws:session:{session_id}`.
- On broadcast: publish to the Redis channel instead of directly sending to WebSocket.
- Add a background task that listens to Redis subscriptions and forwards messages to connected WebSockets.
- On disconnect: unsubscribe from Redis channel.

**Modify file:** `apps/backend/app/core/redis.py`

Add functions: `redis_publish(channel, message)`, `redis_subscribe(channel, callback)`.

**Verify:** Start 2 uvicorn workers, connect WebSocket to one, send message via the other, verify delivery.

---

### 4.7 — Security Headers Middleware

**Create file:** `apps/backend/app/core/middleware.py` (or add to existing)

Build `SecurityHeadersMiddleware`:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (only in production)
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://api.fontshare.com https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com https://api.fontshare.com; connect-src 'self' ws: wss:; img-src 'self' data: blob:`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(self), geolocation=(self)`

**Register in main.py** after other middleware.

**Verify:** `curl -I http://localhost:8000/health` — verify all headers are present.

---

### 4.8 — CORS Strict Mode

**Modify file:** `apps/backend/app/main.py`

In production mode, CORS already restricts to `https://app.smartattend.in`. Verify this is correct and add the backend origin if needed:
- `allow_origins=["https://app.smartattend.in"]` for production.
- Keep `["*"]` only for development.

**Verify:** In production config, a request from `https://evil.com` gets CORS rejection.

---

### 4.9 — Token Blacklisting for Logout

**Modify file:** `apps/backend/app/core/redis.py`

Add functions:
- `blacklist_token(jti: str, ttl_seconds: int)`: Store token JTI in Redis with TTL matching token expiry.
- `is_token_blacklisted(jti: str) -> bool`: Check if JTI is in Redis.

**Modify file:** `apps/backend/app/core/security.py`

In `create_access_token`, add a `jti` claim (random UUID) to the JWT payload.

**Modify file:** `apps/backend/app/core/deps.py`

In `get_current_user`, after decoding the token, check `is_token_blacklisted(payload["jti"])`. If blacklisted, return 401.

**Modify file:** `apps/backend/app/api/v1/auth.py`

Add `POST /api/v1/auth/logout` endpoint: decode the access token, blacklist its JTI. Also blacklist the refresh token if provided.

**Write test:** Login, logout, verify subsequent requests with the old token return 401.

**Verify:** `pytest tests/test_auth.py -v` — add logout test.

---

### 4.10 — Request Body Size Limits

**Modify file:** `apps/backend/app/main.py`

Add middleware that checks `Content-Length` header. Reject requests larger than:
- Default: 1MB
- File upload endpoints (`/faces/enroll`, `/courses/{id}/enroll/csv`): 10MB

Alternatively, configure this in nginx if using a reverse proxy.

**Verify:** Send a 2MB JSON body to a regular endpoint, verify 413 response.

---

### 4.11-4.13 — OWASP Scan, DPDP Compliance, Face Encryption

These are manual/security tasks:

**4.11 OWASP ZAP:** Run OWASP ZAP against the local API. Fix any findings (likely: missing rate limiting — done in 2.11, missing security headers — done in 4.7, verbose error messages).

**4.12 DPDP Compliance:** Add to `apps/backend/app/api/v1/auth.py`:
- `DELETE /api/v1/auth/me` — Account deletion endpoint. Soft-delete (set `is_active=False`) and anonymize personal data (replace name with "Deleted User", email with hash, phone with null). Cascade: delete face embeddings, mark enrollments inactive.
- Add consent acceptance field to registration (boolean `accept_terms`).
- Add a `/api/v1/auth/data-export` endpoint that returns all user data as JSON (right to data portability).

**4.13 Face Encryption:** Modify `face_service.enroll_face` to AES-256 encrypt the embedding before storing. Modify `verify_embedding` to decrypt before comparing. Use the `secret_key` from config as the encryption key (or a dedicated `face_encryption_key`). Use `cryptography.fernet` for simple symmetric encryption.

---

### 4.14-4.20 — Documentation

**Create files:**
- `docs/architecture.md` — System architecture overview, component diagram, data flow for key operations (attendance marking, proxy detection, report generation).
- `docs/db-schema.md` — ER diagram (Mermaid syntax), table descriptions, field descriptions, relationships.
- `docs/api-reference.md` — For each endpoint: method, path, description, request body schema, response schema, error codes, example curl command. Organize by tag (Auth, Sessions, Attendance, etc.).
- `docs/deployment.md` — Step-by-step for Render, Railway, and AWS. Include: env var reference table, database setup, Redis setup, Docker commands, health check verification, SSL setup.
- `docs/user-guide/` — Directory with separate files per role: `student.md`, `faculty.md`, `admin.md`. Each with screenshots (or ASCII representations) of the UI and step-by-step workflows.
- `CHANGELOG.md` — Document all changes from Phase 1 through current phase, following Keep a Changelog format.
- `CONTRIBUTING.md` — Developer setup instructions, code style guide (ruff config), PR process, branch naming convention, commit message format (conventional commits).

**Update:** `README.md` — Replace any inaccurate setup instructions. Update the "Quick Start" section with actual commands that work. Update the "Repository Structure" to match actual file tree.

---

### 4.21-4.22 — Staging Environment & Deployment Pipeline

**Create file:** `.github/workflows/deploy.yml`

Workflow:
- Trigger on push to `main` branch (after CI passes).
- Deploy to staging environment first.
- Run smoke tests against staging (curl health endpoint, login with test account, mark attendance).
- If smoke tests pass, deploy to production.
- If smoke tests fail, auto-rollback staging.

**Create file:** `infra/docker-compose.prod.yml`

Production compose with:
- Proper restart policies (`restart: always`).
- Named volumes for PostgreSQL data, Redis data, ML models.
- Health checks for all services.
- Resource limits (memory).
- Environment variables loaded from `.env` (not hardcoded).

**Create file:** `infra/nginx/nginx.conf`

Nginx config for reverse proxy:
- Proxy `/` to frontend.
- Proxy `/api` to backend.
- Proxy `/ws` to backend (with WebSocket upgrade headers).
- SSL termination (if not using Cloudflare).
- Gzip compression.
- Rate limiting at nginx level (backup to app-level).
- Security headers (backup to app-level).

---

### 4.23 — Database Backup Automation

**Create file:** `scripts/backup_db.sh`

Shell script that:
- Runs `pg_dump` against the production database.
- Compresses with gzip.
- Uploads to S3 (or local backup directory).
- Retains last 30 days of backups.
- Logs success/failure.

**Add to cron or Celery beat:** Schedule daily at 3 AM.

**Document in:** `docs/deployment.md` — backup and restore procedures.

---

### 4.24-4.25 — Grafana Dashboards & Alerting

**Create file:** `infra/grafana/dashboards/smartattend.json`

Dashboard with panels:
- API request rate (from Prometheus metrics).
- Response time p50/p95/p99.
- Error rate (4xx, 5xx).
- Active WebSocket connections.
- Attendance marks per hour.
- Proxy detection alerts per day.
- Database connection pool usage.
- Redis memory usage.

**Create file:** `infra/grafana/alerts/rules.yml`

Alert rules:
- API error rate > 5% for 5 minutes → alert.
- Response time p99 > 1s for 5 minutes → alert.
- Database connections > 80% of pool → alert.
- Redis memory > 80% → alert.

---

### 4.26 — E2E Tests

**Create directory:** `apps/frontend/tests/`

**Create file:** `apps/frontend/tests/e2e.spec.js` (Playwright)

Test scenarios:
- Login flow: navigate to app, fill credentials, click login, verify dashboard loads.
- Student attendance: login as student, navigate to QR scanner, verify camera view loads.
- Faculty session: login as faculty, start session, verify QR code displays.
- Admin management: login as admin, navigate to students, create a student, verify it appears in list.
- Password reset: click forgot password, enter email, verify confirmation message.
- Responsive: test at 375px and 1024px widths, verify sidebar collapses.

**Add dependency:** `@playwright/test` in a `package.json` at the frontend root.

**Add Makefile target:** `e2e: cd apps/frontend && npx playwright test`

**Verify:** `make e2e` — all tests pass.

---

### 4.27-4.30 — Accessibility & i18n

**4.27 ARIA labels:** Audit every interactive element in `index.html` and all view files. Add `aria-label` to buttons without text, `aria-describedby` for form fields with error messages, `role="alert"` for error toasts, `role="dialog"` for modals.

**4.28 Keyboard navigation:** Ensure all interactive elements are focusable (tab order). Add `tabindex` where needed. Modal focus trap (already in 2.23). Escape key closes modals and panels.

**4.29 Color contrast:** Run a contrast checker on the CSS variables. Ensure text/background combinations meet WCAG 2.1 AA ratio (4.5:1 for normal text, 3:1 for large text). Adjust colors if needed.

**4.30 i18n:** Create `apps/frontend/src/utils/i18n.js`:
- Store translations in a `translations` object keyed by language code (`en`, `hi`).
- Export `t(key)` function that returns the translated string for the current language.
- Current language stored in localStorage, switchable from settings.
- Start with `en` (extract all hardcoded strings from views) and `hi` (Hindi translations for key UI strings).
- Add language selector dropdown in the settings page.

---

## Phase 5: Scale (Week 9-10) — "Make It Scale"

### 5.1 — Multi-Tenant Data Isolation

**Modify file:** `apps/backend/app/core/deps.py`

Add `require_institution_scoping` dependency:
- Extract `institution_id` from the current user's JWT claims.
- For admin users without an institution, allow access to all data.
- For all other users, automatically filter queries by their `institution_id`.

**Apply to all list endpoints:** Every `GET /` endpoint should use this dependency to scope results.

**Modify:** Add PostgreSQL Row-Level Security (RLS) policies as a defense-in-depth measure:
- `ALTER TABLE users ENABLE ROW LEVEL SECURITY`
- `CREATE POLICY tenant_isolation ON users USING (institution_id = current_setting('app.current_institution_id')::uuid)`
- Set `app.current_institution_id` at the start of each request via a middleware.

**Verify:** Login as faculty from institution A, verify they cannot see students from institution B.

---

### 5.2 — Database Connection Pooling

**Modify file:** `apps/backend/app/core/database.py`

Optimize connection pool settings:
- `pool_size=20` (already set, verify it's appropriate for the expected load).
- `max_overflow=10` (allow burst connections).
- `pool_timeout=30` (wait up to 30s for a connection).
- `pool_recycle=1800` (recycle connections every 30 minutes to avoid stale connections).
- `pool_pre_ping=True` (verify connection is alive before using it).

Add a connection pool health check to the `/health` endpoint: report `pool_size`, `checked_in`, `checked_out`, `overflow`.

**Verify:** Under load, verify connections are properly recycled and no "connection pool exhausted" errors occur.

---

### 5.3 — Horizontal Scaling

**Modify file:** `apps/backend/app/main.py`

Ensure the app works with multiple workers:
- All state must be in Redis or PostgreSQL (no in-memory state except WebSocket connections — addressed in 4.6).
- Celery tasks must be idempotent (safe to run twice).
- QR token validation uses Redis (already does).

**Modify:** `Makefile` or `docker-compose.yml`

Add production run command with multiple workers: `uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000`.

**Verify:** Start 4 workers, send requests, verify all workers handle traffic correctly.

---

### 5.4 — WebSocket Scaling (Redis Pub/Sub)

Already addressed in Phase 4 (task 4.6). Verify it works with multiple workers.

**Verify:** Start 2+ workers, connect WebSocket via worker A, publish message via worker B, verify delivery.

---

### 5.5 — CDN for Static Assets

**Modify:** Deployment config (nginx or Cloudflare)

- Serve `apps/frontend/` static files via CDN (Cloudflare or AWS CloudFront).
- Set cache headers: `Cache-Control: public, max-age=31536000` for hashed assets, `no-cache` for `index.html`.
- Configure CDN to proxy `/api/*` and `/ws/*` to the backend.

**Document in:** `docs/deployment.md`

---

### 5.6 — Image Optimization Pipeline

**Modify file:** `apps/backend/app/services/face_service.py`

When a face image is uploaded for enrollment:
- Resize to max 640x640 (maintain aspect ratio).
- Convert to JPEG with 85% quality.
- Strip EXIF data (privacy).
- Store the processed image in S3 (or local storage).

**Add dependency:** `Pillow==10.3.0` to requirements.txt.

**Verify:** Upload a 5MB image, verify it's resized to <200KB, verify face embedding still works.

---

### 5.7 — Celery Monitoring (Flower)

**Modify file:** `docker-compose.yml`

Add Flower service:
```yaml
flower:
  image: mher/flower
  command: celery -A app.tasks.celery_app flower
  ports:
    - "5555:5555"
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
```

**Verify:** Access `http://localhost:5555`, verify task history, active workers, and queue status are visible.

---

### 5.8 — Feature Flags

**Create file:** `apps/backend/app/core/feature_flags.py`

Simple feature flag system using Redis:
- `is_feature_enabled(flag_name: str, institution_id: UUID = None) -> bool`: Check Redis for flag value. Supports global flags and per-institution overrides.
- `set_feature_flag(flag_name: str, enabled: bool, institution_id: UUID = None)`: Set flag in Redis.

**Create endpoint:** `GET /api/v1/admin/feature-flags` — List all flags and their states. Admin only.
`PUT /api/v1/admin/feature-flags/{flag_name}` — Enable/disable a flag.

**Use flags to gate:** ML face recognition, push notifications, offline mode. When a flag is off, the feature is hidden from the UI and the backend returns a standard "feature not available" response.

**Verify:** Disable a feature flag, verify the feature is hidden from the UI.

---

### 5.9 — A/B Testing Framework

This is a stretch goal. Simple implementation:

**Create file:** `apps/backend/app/core/ab_testing.py`

- `get_variant(experiment_name: str, user_id: UUID) -> str`: Deterministically assign user to variant ("control" or "treatment") based on hash of user_id + experiment_name. Store assignment in Redis for consistency.
- Track events: `track_event(experiment_name, user_id, event_name)` — increment a Redis counter.

**Use for:** Testing different attendance UI flows, notification timing, etc.

**Verify:** Same user always gets same variant. Distribution is roughly 50/50 across users.

---

### 5.10 — Performance Profiling

**Modify file:** `apps/backend/app/main.py`

Add a profiling middleware (development only):
- Use `cProfile` or `pyinstrument` to profile requests.
- Add a `?profile=true` query parameter that returns the profiling output instead of the normal response.
- Only enabled when `app_env == "development"`.

**Run profiling on:** Analytics endpoints (most complex queries), attendance marking (highest traffic), report generation (heaviest computation).

**Document findings:** Create `docs/performance.md` with identified bottlenecks and optimizations applied.

---

## Summary

| Phase | Tasks | Key Deliverables |
|-------|-------|-----------------|
| **Phase 2** | 29 tasks | Institution/Department/Course/Enrollment CRUD, Alert management, Timetable, WebSocket notifications, Push notifications, Email templates, PDF reports, Rate limiting, 8 new frontend pages, 3 reusable components |
| **Phase 3** | 19 tasks | ML service (face, anomaly, forecast), Real proxy detection, Face enrollment/verification, Prophet forecasting, Engagement scoring, 4 new frontend features |
| **Phase 4** | 26 tasks | Redis caching, Query optimization, Compression, Code splitting, Security headers, Token blacklisting, Load testing, Documentation, Deployment pipeline, Accessibility, i18n |
| **Phase 5** | 10 tasks | Multi-tenant RLS, Connection pooling, Horizontal scaling, CDN, Image optimization, Celery monitoring, Feature flags, Performance profiling |

**Total: 84 tasks across Phases 2-5.**

---

*Phase 1 is complete. Start Phase 2 with task 2.1 (Institution CRUD).*
