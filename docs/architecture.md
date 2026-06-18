# SmartAttend Architecture

## System Overview

SmartAttend is an AI-augmented student attendance monitoring and analytics platform. It uses a multi-service architecture with separate frontend, backend, ML service, and supporting infrastructure.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React 19 + TypeScript)               │
│                   apps/frontend/ — Port 5173                      │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │Dashboard │ │QR Scanner│ │Analytics │ │ Settings & Admin │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS + JWT / WebSocket
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
│  │  → GZip → Profiling → Prometheus → Router                │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ Celery Worker│  │ Celery Beat  │  Scheduled tasks          │
│  │  (async jobs)│  │  (scheduler) │  reports, ML scoring,      │
│  └──────────────┘  └──────────────┘  notifications              │
└──────┬─────────────┬──────────────────┬─────────────────────────┘
       │             │                  │
       ▼             ▼                  ▼
┌──────────┐  ┌──────────┐  ┌──────────────────────┐
│PostgreSQL│  │  Redis   │  │   ML Service         │
│  Port    │  │  Port    │  │   apps/ml-service/   │
│  5432    │  │  6379    │  │   Port 8001          │
│          │  │          │  │                      │
│  • users │  │  • QR    │  │  ┌────────────────┐   │
│  • sess. │  │    tokens│  │  │ Face Embedding │   │
│  • attend│  │  • cache │  │  │ (InsightFace)  │   │
│  • alerts│  │  • pub/  │  │  ├────────────────┤   │
│  • notifs│  │    sub   │  │  │ Anomaly Detect │   │
│  • goals │  │  • Celery│  │  │(IsolationForest)│  │
│  • faces │  │    broker│  │  ├────────────────┤   │
│  • pgvec │  │          │  │  │ Forecasting    │   │
└──────────┘  └──────────┘  │  │  (Prophet)     │   │
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
   b. POST /face/compare to ML service
   c. Store confidence score
8. Create AttendanceRecord (status determined by face score)
9. Queue proxy analysis (Celery task → ML service)
10. Check attendance % → send low-attendance alert if < 75%
11. Broadcast update via WebSocket to connected clients
12. Return success to frontend
```

## Data Flow: Proxy Detection

```
1. Celery worker picks up analyze_attendance_record task
2. Extract feature vector from AttendanceRecord
3. POST /anomaly/score to ML service
4. ML service loads Isolation Forest model → predicts anomaly score
5. If score >= threshold (0.75): mark PROXY_SUSPECTED
6. Create Alert record
7. Send notification to faculty via WebSocket + Email
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend  | React 19, TypeScript 5.7, Vite 6, Tailwind CSS v4, TanStack Query, Zustand |
| UI        | Radix primitives + CVA (shadcn-style), Recharts, lucide-react, Sonner |
| Backend   | Python 3.11+, FastAPI 0.111, SQLAlchemy 2 (async), Pydantic v2 |
| Database  | PostgreSQL 16 with pgvector |
| Cache     | Redis 7 (QR tokens, rate limiting, pub/sub, Celery broker) |
| ML        | FastAPI, InsightFace (ArcFace), scikit-learn (Isolation Forest), Prophet |
| Task Queue| Celery 5 + Redis broker (reports, notifications, ML scoring) |
| Auth      | JWT (python-jose), bcrypt, TOTP (pyotp) |
| Real-time | WebSocket (FastAPI) for live session feed |
| PWA       | vite-plugin-pwa (autoUpdate, NetworkFirst) |

## Directory Structure

```
SmartAttend/
├── apps/
│   ├── backend/           # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/v1/    # Route handlers
│   │   │   ├── core/      # Config, security, middleware, database, redis
│   │   │   ├── models/    # SQLAlchemy models
│   │   │   ├── schemas/   # Pydantic schemas
│   │   │   ├── services/  # Business logic
│   │   │   ├── tasks/     # Celery tasks (worker + beat)
│   │   │   └── websocket/ # WebSocket handlers
│   │   ├── alembic/       # Database migrations
│   │   ├── tests/         # pytest suite
│   │   ├── scripts/       # seed_demo.py
│   │   └── Dockerfile
│   ├── frontend/          # React 19 + Vite 6 SPA
│   │   ├── src/
│   │   │   ├── components/ # UI primitives, layout, common
│   │   │   ├── features/   # Page-level components (auth, dashboard, sessions, etc.)
│   │   │   ├── lib/        # API client, utilities
│   │   │   └── styles/     # Tailwind v4 globals
│   │   └── vite.config.js
│   └── ml-service/        # ML microservice
│       ├── app/
│       │   ├── face/       # Face recognition (InsightFace)
│       │   ├── anomaly/    # Proxy detection (Isolation Forest)
│       │   └── forecast/   # Attendance forecasting (Prophet)
│       └── Dockerfile
├── docs/                   # Documentation
├── .env.example            # Environment template
└── docker-compose.yml      # Multi-service orchestration
```

## Middleware Stack (Backend)

Applied in order for each request:

1. **CORS** — allows configured origins (wildcard in dev)
2. **RequestID** — assigns unique ID to each request for tracing
3. **SecurityHeaders** — X-Content-Type-Options, X-Frame-Options, etc.
4. **RequestBodySize** — limits request body size
5. **RateLimitMiddleware** — per-IP rate limiting via Redis
6. **GZip** — response compression for payloads > 1KB
7. **ProfilingMiddleware** — request timing (development only)
8. **Prometheus** — metrics collection at `/metrics`

## Auth Flow

```
1. POST /api/v1/auth/login { email, password }
2. Backend verifies credentials → returns JWT access token + refresh token
3. Frontend stores tokens in Zustand + localStorage
4. Every subsequent request includes `Authorization: Bearer <token>`
5. Middleware extracts user_id from token, loads from DB
6. Role-based guards on routes (admin, faculty, student)
```
