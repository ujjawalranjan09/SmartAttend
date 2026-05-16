# 🎓 SmartAttend — AI-Augmented Attendance Intelligence Platform

> **Eliminate manual roll calls. Detect proxy fraud in real time. Give faculty actionable insights.**  
> Built for India's 40,000+ colleges and 1,000+ universities.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

---

## 📋 Table of Contents

1. [Problem Statement](#-problem-statement)
2. [Solution Overview](#-solution-smartattend)
3. [System Architecture](#-system-architecture)
4. [Tech Stack](#-tech-stack)
5. [Repository Structure](#-repository-structure)
6. [Quick Start](#-quick-start)
7. [API Documentation](#-api-documentation)
8. [ML Modules](#-ml-modules)
9. [Deployment](#-deployment)
10. [Success Metrics](#-success-metrics)
11. [Risks & Mitigations](#-risks--mitigations)
12. [Contributing](#-contributing)
13. [License](#-license)

---

## 🔴 Problem Statement

India's higher education system enrolls **43+ million students** across 1,000+ universities and 40,000+ colleges — yet attendance tracking remains largely manual. Here's what that costs:

| Pain Point | Impact |
|---|---|
| Manual roll call (8–12 min/session) | 15–25 hours of lost teaching time per course/year |
| Undetected proxy attendance | Fraudulent records affect exam eligibility & scholarships |
| Fragmented data across departments | No unified academic risk visibility |
| Delayed detection of absenteeism | At-risk students identified too late for intervention |
| Manual report compilation | Admin staff burdened for days before exams |
| Online/hybrid class gap | No reliable attendance mechanism for virtual sessions |
| Poor Tier-2/3 infrastructure | Internet outages break most existing digital solutions |

### Why Existing Solutions Fail

- **Biometric devices** — High cost, no analytics, vulnerable to spoofing, useless for online classes
- **Excel/ERP modules** — Faculty still waste time entering data; zero proxy detection or ML insights
- **Simple QR apps** — Screenshot sharing defeats the system; no location binding, no offline support

---

## ✅ Solution: SmartAttend

SmartAttend is a **cloud-native, offline-first attendance platform** combining three anti-spoofing input methods:

```
┌─────────────────────────────────────────────────────────────┐
│              MULTI-LAYER ATTENDANCE VALIDATION               │
├────────────────┬──────────────────┬─────────────────────────┤
│  Dynamic QR    │  Facial Recog.   │  BLE/WiFi Proximity     │
│  + Geo-fence   │  (On-device)     │  (Network fingerprint)  │
└────────────────┴──────────────────┴─────────────────────────┘
         ↓                 ↓                    ↓
         └─────────────────┴────────────────────┘
                           ↓
              Proxy Detection ML Engine
                           ↓
              Real-time Analytics Dashboard
```

**Supported Class Modes:** In-person · Online (Zoom/GMeet) · Hybrid

---

## 🏗️ System Architecture

### Three-Layer Technical Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  React PWA (Student & Faculty)  │  Admin Dashboard              │
│  Offline-first (IndexedDB)      │  React + Recharts             │
│  On-device face embed (TF.js)   │  BLE/WiFi scan                │
│  Dynamic QR + liveness check    │  Role-based views             │
└──────────────────┬───────────────────────────────────────────────┘
                   │  HTTPS / WebSocket
┌──────────────────▼───────────────────────────────────────────────┐
│                      BACKEND / API LAYER                         │
│  FastAPI (Python 3.11+)  │  JWT + OAuth2 Auth                   │
│  WebSocket (live feed)   │  Celery task queue (async)           │
│  Proxy Detection Service │  Notification service (SMS/Email)    │
└──────────────────┬───────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────┐
│                      DATA & ML LAYER                             │
│  PostgreSQL 16 + TimescaleDB  │  Redis (cache, rate limit)      │
│  pgvector (face embeddings)   │  Scikit-learn anomaly detect    │
│  AWS S3 / Cloudflare R2       │  Prophet (trend forecasting)    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite | PWA, component reuse across roles |
| Mobile (opt.) | React Native / Flutter | Camera access, BLE scanning |
| Backend API | FastAPI (Python 3.11+) | Async endpoints, auto OpenAPI docs |
| Auth | JWT + OAuth2 + TOTP 2FA | Role-based: student/faculty/HOD/admin/parent |
| Primary DB | PostgreSQL 16 + TimescaleDB | ACID transactions + time-series hypertables |
| Cache | Redis 7 | QR token TTL, rate limiting, WebSocket pub/sub |
| Face Recognition | DeepFace / InsightFace + pgvector | 512-dim embeddings, cosine similarity |
| ML Analytics | Scikit-learn + Prophet | Isolation Forest anomaly detection + forecasting |
| Task Queue | Celery + Redis broker | Async reports, bulk notifications, ML scoring |
| Real-time | WebSockets (FastAPI) | Live attendance feed during class |
| Cloud Infra | AWS / Railway / Render | Auto-scaling API, managed PostgreSQL |
| CI/CD | GitHub Actions + Docker | Automated tests, containerized deploys |

---

## 📁 Repository Structure

```
SmartAttend/
├── apps/
│   ├── frontend/              # React 18 + TypeScript PWA
│   │   ├── src/
│   │   │   ├── components/    # Reusable UI components
│   │   │   ├── pages/         # Route-level pages
│   │   │   ├── hooks/         # Custom React hooks
│   │   │   ├── store/         # Zustand state management
│   │   │   ├── services/      # API client + WebSocket
│   │   │   └── utils/         # QR scanner, face embed utils
│   │   ├── public/
│   │   │   └── sw.js          # Service Worker (offline-first)
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   ├── backend/               # FastAPI Python 3.11+
│   │   ├── app/
│   │   │   ├── api/           # Route handlers
│   │   │   │   ├── v1/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── attendance.py
│   │   │   │   │   ├── sessions.py
│   │   │   │   │   ├── students.py
│   │   │   │   │   ├── faculty.py
│   │   │   │   │   ├── analytics.py
│   │   │   │   │   └── reports.py
│   │   │   ├── core/
│   │   │   │   ├── config.py
│   │   │   │   ├── security.py
│   │   │   │   ├── database.py
│   │   │   │   └── redis.py
│   │   │   ├── models/        # SQLAlchemy ORM models
│   │   │   ├── schemas/       # Pydantic request/response schemas
│   │   │   ├── services/      # Business logic layer
│   │   │   ├── tasks/         # Celery async tasks
│   │   │   └── websocket/     # WebSocket handlers
│   │   ├── alembic/           # DB migrations
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── ml-service/            # Python ML microservice
│       ├── app/
│       │   ├── face/          # InsightFace embedding pipeline
│       │   ├── anomaly/       # Isolation Forest proxy detection
│       │   ├── forecast/      # Prophet trend forecasting
│       │   └── api.py         # FastAPI ML endpoints
│       ├── models/            # Serialized ML model artifacts
│       ├── requirements.txt
│       └── Dockerfile
│
├── packages/
│   └── shared-types/          # Shared TypeScript + Pydantic types
│
├── infra/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
│       └── nginx.conf
│
├── .github/
│   └── workflows/
│       ├── ci.yml             # Lint + test + build
│       └── deploy.yml         # Staging/prod deployment
│
├── docs/
│   ├── architecture.md
│   ├── db-schema.md
│   ├── api-reference.md
│   └── ml-pipeline.md
│
├── scripts/
│   ├── seed_db.py
│   └── load_test.py
│
├── .env.example
├── pnpm-workspace.yaml
├── turbo.json
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required
Node.js 20+, pnpm 9+
Python 3.11+, Poetry or pip
Docker + Docker Compose
PostgreSQL 16 (or use Docker)
Redis 7 (or use Docker)
```

### 1. Clone & Install

```bash
git clone https://github.com/ujjawalranjan09/SmartAttend.git
cd SmartAttend

# Install all workspaces
pnpm install

# Install Python deps
cd apps/backend && pip install -r requirements.txt
cd ../ml-service && pip install -r requirements.txt
```

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env with your DB, Redis, JWT secret, AWS keys, etc.
```

### 3. Run with Docker Compose (Recommended)

```bash
cd infra
docker-compose up --build
```

Services start at:
- **Frontend PWA:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **ML Service:** http://localhost:8001
- **Grafana Metrics:** http://localhost:3000

### 4. Database Setup

```bash
# Run migrations
cd apps/backend
alembic upgrade head

# Seed demo data
python ../../scripts/seed_db.py
```

---

## 📡 API Documentation

Full interactive API docs available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the backend is running.

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login` | JWT token + refresh token |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `POST` | `/api/v1/sessions/start` | Faculty starts a class session |
| `POST` | `/api/v1/sessions/{id}/qr` | Generate dynamic QR token |
| `POST` | `/api/v1/attendance/mark` | Student marks attendance (multi-factor) |
| `GET` | `/api/v1/attendance/session/{id}` | Live attendance for a session |
| `GET` | `/api/v1/analytics/student/{id}` | Student attendance analytics |
| `GET` | `/api/v1/analytics/course/{id}` | Course-level engagement report |
| `GET` | `/api/v1/reports/export` | Export PDF/CSV report |
| `WS` | `/ws/session/{id}` | Real-time session WebSocket feed |

---

## 🤖 ML Modules

### 1. Face Recognition Pipeline
- **Model:** InsightFace ArcFace (evaluated on diverse skin tone datasets)
- **Storage:** 512-dimensional float vectors in pgvector
- **On-device:** TensorFlow.js for browser-side embedding (privacy-preserving)
- **Matching:** Cosine similarity with configurable threshold (default: 0.6)
- **Fallback:** QR + geo-fence only mode if face recognition is disabled

### 2. Proxy Detection (Isolation Forest)
- **Features:** Scan-time deviation, device fingerprint consistency, geo-cluster analysis, BLE beacon match, historical attendance pattern
- **Output:** Anomaly score (0–1); threshold triggers `proxy_suspected` alert
- **Training:** Per-institution model fine-tuning on anonymized behavioral data

### 3. Attendance Trend Forecasting (Prophet)
- Forecasts 2-week attendance trajectory per student
- Triggers early-warning alerts when predicted attendance falls below 75% threshold
- Faculty dashboard shows trend line + confidence interval

---

## ☁️ Deployment

### Production Architecture

```
Cloudflare CDN
      ↓
  Vercel (Frontend PWA)
      ↓
AWS ALB (Load Balancer)
      ↓
┌─────┴─────┐
ECS Fargate  ECS Fargate   (Auto-scaled backend pods)
      ↓
  RDS PostgreSQL + ElastiCache Redis
      ↓
  S3 (face media) + CloudWatch (logs)
```

### Environment Variables

See [`.env.example`](.env.example) for all required configuration keys.

---

## 📊 Success Metrics

| Metric | Target |
|---|---|
| Roll call time saved | ≥ 95% (90 sec vs 8–12 min) |
| Proxy fraud reduction | ≥ 90% |
| At-risk student detection lag | < 24 hours |
| Offline resilience | Zero data loss at 0% connectivity |
| Concurrent QR scan capacity | 200+ simultaneous scans |
| API response time (p99) | < 300ms |
| Face recognition accuracy | ≥ 97% (across demographic groups) |

---

## ⚠️ Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Students without smartphones | Medium | Faculty manual override; shared devices; QR-only fallback |
| Facial recognition bias | High | InsightFace (ArcFace) evaluated on diverse datasets; face always supplementary |
| GPS spoofing | Medium | Cross-validate with WiFi BSSID + BLE beacon proximity |
| Faculty resistance | Medium | Zero-training UX; single button to start/end session |
| Data breach (face embeddings) | High | Vectors only (not photos); AES-256 per-institution encryption; pen testing |
| Exam season scale spike | Medium | AWS ECS auto-scaling; Redis handles QR validation at sub-ms |
| Rural internet outages | Low | Offline-first PWA with Service Worker + IndexedDB sync |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit with conventional commits: `feat:`, `fix:`, `docs:`, `chore:`
4. Push and open a Pull Request against `main`
5. Ensure all GitHub Actions checks pass

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed guidelines.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built for India's students, faculty, and institutions 🇮🇳
  <br/>
  <a href="https://github.com/ujjawalranjan09/SmartAttend">GitHub</a> · 
  <a href="https://github.com/ujjawalranjan09/SmartAttend/issues">Issues</a> · 
  <a href="https://github.com/ujjawalranjan09/SmartAttend/wiki">Wiki</a>
</p>
