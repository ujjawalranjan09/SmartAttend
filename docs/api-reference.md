# API Reference

## Authentication

### POST /api/v1/auth/login
Authenticate user and receive JWT tokens.

**Request:**
```json
{"email": "user@example.com", "password": "securepass", "totp_code": "123456"}
```
**Response (200):**
```json
{"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer", "role": "student", "user_id": "uuid"}
```

### POST /api/v1/auth/register
Register a new user.

**Request:**
```json
{"email": "new@example.com", "password": "securepass", "full_name": "John Doe", "role": "student", "institution_id": "uuid"}
```
**Response (201):**
```json
{"id": "uuid", "email": "new@example.com", "full_name": "John Doe", "role": "student"}
```

### POST /api/v1/auth/logout
Blacklist the current access token.

**Headers:** `Authorization: Bearer <token>`

**Response (200):** `{"detail": "Logged out successfully"}`

### POST /api/v1/auth/refresh
Refresh an expired access token.

**Request:** `{"refresh_token": "eyJ..."}`

### POST /api/v1/auth/data-export
Export all user data (DPDP compliance).

### DELETE /api/v1/auth/me
Delete account and anonymize personal data.

## Sessions

### GET /api/v1/sessions
List class sessions. **Query params:** `course_id`, `faculty_id`, `status`, `from_date`, `to_date`, `page`, `page_size`

### POST /api/v1/sessions
Create a session. **Body:** `{course_id, date, start_time, end_time}`

### POST /api/v1/sessions/{id}/start
Activate a session and generate QR token.

### POST /api/v1/sessions/{id}/end
End an active session.

### GET /api/v1/sessions/{id}/qr
Get QR code data (token + session ID).

## Attendance

### POST /api/v1/attendance/mark
Mark attendance. **Body:**
```json
{
  "session_id": "uuid",
  "qr_token": "abc123",
  "lat": 28.6139,
  "lon": 77.2090,
  "face_embedding": [0.1, 0.2, ...],
  "wifi_bssid": "00:11:22:33:44:55",
  "device_fingerprint": "hash123"
}
```

### GET /api/v1/attendance
List attendance records. **Query params:** `student_id`, `session_id`, `course_id`, `status`, `from_date`, `to_date`, `limit`, `offset`

## Analytics

### GET /api/v1/analytics/student/{id}
Student analytics with trend and ML-powered forecast.

**Response:**
```json
{
  "student_id": "uuid",
  "full_name": "John Doe",
  "overall_attendance_pct": 82.5,
  "trend": [{"date": "2024-01-01", "attended": 5, "total": 6, "percentage": 83.33}],
  "proxy_incidents": 1,
  "at_risk": false,
  "forecast_7d_pct": 84.2
}
```

### GET /api/v1/analytics/course/{id}
Course analytics with engagement scoring.

### GET /api/v1/analytics/at-risk
List at-risk students. **Query params:** `institution_id`, `threshold_pct` (default 75)

## Face Enrollment

### POST /api/v1/faces/enroll
Upload face image for enrollment. **Form data:** `image` (JPEG/PNG file)

### GET /api/v1/faces/status
Check face enrollment status.

### DELETE /api/v1/faces/enrollment
Remove face enrollment.

## Alerts

### GET /api/v1/alerts
List alerts. **Query params:** `is_resolved`, `alert_type`, `severity`, `page`, `page_size`

### PATCH /api/v1/alerts/{id}/resolve
Mark alert as resolved.

## Institutions

### GET /api/v1/institutions
List institutions (admin only).

### POST /api/v1/institutions
Create institution (admin only).

### GET /api/v1/institutions/{id}
Get institution details.

### PUT /api/v1/institutions/{id}
Update institution (admin only).

## Courses

### POST /api/v1/courses
Create course. **Body:** `{institution_id, department_id, name, code, semester, academic_year}`

### POST /api/v1/courses/{id}/enroll
Enroll students. **Body:** `{student_ids: ["uuid1", "uuid2"]}`

### POST /api/v1/courses/{id}/enroll/csv
Bulk enroll from CSV. **Form data:** `file` (CSV with `email` or `roll_number` column)

## Machine Learning Service (Internal)

### POST /api/v1/face/embed
Extract face embedding from image.

### POST /api/v1/face/compare
Compare two embeddings. **Body:** `{emb1: [512 floats], emb2: [512 floats]}`

### POST /api/v1/anomaly/score
Score anomaly for a feature vector.

### POST /api/v1/anomaly/train
Train Isolation Forest model.

### POST /api/v1/forecast/predict
Forecast attendance trends.

## WebSocket

### WS /ws/session/{session_id}
Real-time attendance feed. Join with `?token=JWT` query param.

### WS /ws/notifications/{user_id}
Real-time notifications. Join with `?token=JWT` query param.

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient role) |
| 404 | Resource not found |
| 409 | Conflict (duplicate entry) |
| 413 | Request body too large |
| 429 | Rate limit exceeded |
| 503 | Service unavailable (ML/DB down) |