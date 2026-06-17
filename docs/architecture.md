# SmartAttend Architecture

## System Overview

SmartAttend is an AI-augmented student attendance monitoring and analytics platform. It uses a multi-service architecture with separate frontend, backend, ML service, and supporting infrastructure.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vanilla JS)                     │
│                   apps/frontend/ — Port 8080                     │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │Dashboard │ │QR Scanner│ │Analytics │ │ Settings & Admin │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP/WebSocket
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend API (FastAPI)                        │
│                  apps/backend/ — Port 8000                       │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │  Auth &  │ │Sessions &│ │ Analytics│ │ Face & ML       │    │
│  │  Users   │ │Attendance│ │ & Reports│ │ Client           │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                   Middleware Stack                        │    │
│  │  CORS → RequestID → SecurityHeaders → BodySize → RateLim │    │
│  │  → GZip → Prometheus → Router                             │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────┬─────────────┬──────────────────┬─────────────────────────┘
       │             │                  │
       ▼             ▼                  ▼
┌──────────┐  ┌──────────┐  ┌──────────────────────┐
│PostgreSQL│  │  Redis   │  │   ML Service         │
│  Port    │  │  Port    │  │   apps/ml-service/   │
│  5432    │  │  6379    │  │   Port 8001          │
└──────────┘  └──────────┘  │                      │
                            │  ┌────────────────┐   │
                            │  │ Face Embedding │   │
                            │  │ (InsightFace)  │   │
                            │  ├────────────────┤   │
                            │  │ Anomaly Detect │   │
                            │  │(IsolationForest)│   │
                            │  ├────────────────┤   │
                            │  │ Forecasting    │   │
                            │  │  (Prophet)     │   │
                            │  └────────────────┘   │
                            └──────────────────────┘
```

## Data Flow: Attendance Marking

```
1. Student opens QR Scanner
2. Frontend captures QR code → session_id + token
3. (Optional) Face image captured via camera
4. POST /api/v1/attendance/mark {
      session_id, qr_token, face_embedding?, geo?, wifi?
   }
5. Backend validates QR token via Redis
6. Validates geofence (if GPS provided)
7. Face verification via ML service (if enrollment exists)
   a. Check face_embeddings table for enrollment
   b. POST /api/v1/face/compare to ML service
   c. Store confidence score
8. Create AttendanceRecord (status determined by face score)
9. Queue proxy analysis (Celery task → ML service)
10. Check attendance % → send low-attendance alert if < 75%
11. Return success to frontend
```

## Data Flow: Proxy Detection

```
1. Celery worker picks up analyze_attendance_record task
2. Extract feature vector from AttendanceRecord
3. POST /api/v1/anomaly/score to ML service
4. ML service loads Isolation Forest model → predicts anomaly score
5. If score >= threshold (0.75): mark PROXY_SUSPECTED
6. Create Alert record
7. Send notification to faculty via WebSocket + Email
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend  | Vanilla JS, Chart.js, HTML5 QR Scanner, Lucide Icons |
| Backend   | Python 3.11+, FastAPI, SQLAlchemy (async), Pydantic |
| Database  | PostgreSQL 16 with pgvector |
| Cache     | Redis 7 (sessions, rate limiting, pub/sub) |
| ML        | FastAPI, InsightFace, scikit-learn, Prophet |
| Task Queue| Celery with Redis broker |
| Auth      | JWT (python-jose), bcrypt, TOTP (pyotp) |
| Analytics | Chart.js (frontend), Prophet (ML backend) |

## Directory Structure

```
SmartAttend/
├── apps/
│   ├── backend/           # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/v1/    # Route handlers
│   │   │   ├── core/      # Config, security, middleware
│   │   │   ├── models/    # SQLAlchemy models
│   │   │   ├── schemas/   # Pydantic schemas
│   │   │   ├── services/  # Business logic
│   │   │   ├── tasks/     # Celery tasks
│   │   │   ├── templates/ # Email templates
│   │   │   └── websocket/ # WebSocket handlers
│   │   └── tests/
│   ├── frontend/          # Vanilla JS SPA
│   │   └── src/
│   │       ├── utils/     # API client, i18n, store
│   │       ├── views/     # Page components
│   │       └── styles/    # CSS
│   └── ml-service/        # ML microservice
│       └── app/
│           ├── face/      # Face recognition
│           ├── anomaly/   # Proxy detection
│           └── forecast/  # Attendance forecasting
├── docs/                  # Documentation
├── infra/                 # Deployment configs
├── scripts/               # Utility scripts
└── docker-compose.yml     # Multi-service orchestration