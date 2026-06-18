# 🎓 SmartAttend — AI-Augmented Attendance Intelligence Platform

> **Eliminate manual roll calls. Detect proxy fraud in real time. Give faculty actionable insights.**
> Built for India's 40,000+ colleges and 1,000+ universities.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite)](https://vitejs.dev)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-v4-06B6D4?logo=tailwindcss)](https://tailwindcss.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://postgresql.org)

---

## 📋 Table of Contents

1. [What is SmartAttend](#-what-is-smartattend)
2. [Key Features](#-key-features)
3. [System Architecture](#-system-architecture)
4. [Tech Stack](#-tech-stack)
5. [Repository Structure](#-repository-structure)
6. [Quick Start (Docker)](#-quick-start-docker)
7. [Quick Start (Local)](#-quick-start-local)
8. [Demo Credentials](#-demo-credentials)
9. [API Surface](#-api-surface)
10. [PWA + Classroom Display Kiosk](#-pwa--classroom-display-kiosk)
11. [Deployment Notes](#-deployment-notes)
12. [Contributing](#-contributing)
13. [License](#-license)

---

## 🎯 What is SmartAttend

SmartAttend is a **cloud-native, role-aware attendance platform** combining three anti-spoofing input methods (Dynamic QR + Geofence, Facial Recognition, AI routine planner) into a single fast, modern web experience for students, faculty, and administrators.

**Class modes supported:** In-person · Online · Hybrid

---

## ✨ Key Features

### For Students
- 📊 **Personalized dashboard** — overall attendance %, classes missed, trend delta, 75% threshold tracker
- 🧠 **AI daily routine** — given profile (interests, strengths, career goals), the planner fills free periods with study suggestions and goals
- 🎯 **Goal tracking** — set academic/career/skill goals with milestones and progress bars
- 📷 **QR scanner with face verification** — webcam capture + face enrollment for biometric verification
- 📈 **Progress analytics** — 8-week attendance trend, 14-day forecast, per-course breakdown
- 🌙 **Light/dark theme** with system-aware colors

### For Faculty
- 🚀 **Session start in 3 clicks** — pick course, set duration, push QR
- 📺 **Classroom Display kiosk** — TV-friendly full-screen view with live attendance percentage, hero KPIs, animated live feed
- 🛡️ **Proxy detection** — flagged rows in attendance grid show risk score
- 📥 **CSV export** — one-click download of session or course attendance
- 📅 **Session management** — start/end, QR rotation, room assignment

### For Admins
- 🏛️ **Institution overview** — total students, faculty, avg attendance, active sessions, at-risk count
- 📊 **Trend analytics** — 8-week institution-wide trend, department comparison, at-risk student list
- 🔍 **User management** — searchable student directory, risk-filtered views
- 📄 **Report generation** — quick export cards, recent reports history
- ⚙️ **System settings** — face enrollment management, notification preferences, security (2FA, password reset)

### Cross-cutting
- ⚡ **PWA** — service worker with NetworkFirst cache for `/api`, offline-capable shell, auto-update
- 🔐 **JWT auth + role-based routing** — students see student-only nav, faculty see teaching nav, admins see institutional nav
- 🎨 **Modern SaaS design system** — Linear/Vercel/Stripe-inspired, refined neutrals, teal accent, soft shadows, micro-interactions
- 📱 **Mobile-first responsive** — collapsible sidebar drawer, touch-friendly hit targets

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  Vite + React 19 + TS + Tailwind v4 + shadcn-style UI           │
│  TanStack Query + Zustand  │  Sonner toasts  │  Recharts charts  │
│  html5-qrcode (camera scan) │  getUserMedia (face enrollment)    │
│  Standalone kiosk page (/classroom-display.html)                 │
└──────────────────┬───────────────────────────────────────────────┘
                   │  HTTPS + JWT bearer
┌──────────────────▼───────────────────────────────────────────────┐
│                      BACKEND / API LAYER                         │
│  FastAPI (Python 3.11+)  │  Async SQLAlchemy  │  Alembic       │
│  JWT auth + role guards  │  WebSocket live feed                  │
│  Celery worker + beat    │  Notification service (SMS/Email)    │
└──────────────────┬───────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────┐
│                      DATA & ML LAYER                             │
│  PostgreSQL 16 (smartattend DB)  │  Redis (cache, QR TTL)        │
│  pgvector (face embeddings)     │  FastAPI ML service (:8001)   │
│  Isolation Forest (proxy detect) │  Prophet (forecasting)         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| **Frontend** | Vite 6 + React 19 + TypeScript 5.7 | Strict TS, ESM, `@/` path alias |
| **Styling** | Tailwind CSS v4 (CSS-first) | `@theme` block in `globals.css`, no `tailwind.config.js` |
| **UI primitives** | Custom shadcn-style (Radix + CVA) | `button`, `card`, `dialog`, `dropdown`, `tabs`, `toast`, etc. |
| **State** | Zustand + persist (localStorage) | `auth` (token+user), `theme` (light/dark) |
| **Data fetching** | TanStack Query v5 | Auto-cache, 5s refetch, retry logic |
| **Charts** | Recharts | Area, Bar, Line, Pie, ResponsiveContainer |
| **Forms** | react-hook-form + zod | Tag inputs, multi-step, validation |
| **Icons** | lucide-react | Consistent stroke width, tree-shaken |
| **Toasts** | Sonner | Rich colors, promise API, undo action |
| **Camera** | html5-qrcode + getUserMedia | QR scan + face enrollment |
| **PWA** | vite-plugin-pwa | autoUpdate SW, NetworkFirst for /api |
| **Backend** | FastAPI 0.111 + SQLAlchemy 2 async | Postgres 16, Alembic migrations |
| **Task queue** | Celery + Redis broker | Reports, notifications, ML scoring |
| **Real-time** | WebSockets (FastAPI) | Live session feed |
| **ML service** | Python + FastAPI (:8001) | Face recognition (InsightFace), anomaly detection |

---

## 📁 Repository Structure

```
SmartAttend/
├── apps/
│   ├── frontend/              # Vite + React 19 + TS + Tailwind v4
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── ui/        # 12+ shadcn primitives (button, card, dialog, …)
│   │   │   │   ├── common/    # KpiCard, AttendanceRing, PageHeader, Logo
│   │   │   │   └── layout/    # Sidebar, Topbar, AppShell
│   │   │   ├── features/
│   │   │   │   ├── auth/      # LoginPage
│   │   │   │   ├── dashboard/ # StudentDashboard, FacultyDashboard, AdminDashboard
│   │   │   │   ├── sessions/  # SessionsPage + QR/Display dialogs
│   │   │   │   ├── attendance/# AttendancePage (student + faculty views)
│   │   │   │   ├── students/  # StudentsPage (search + risk filter)
│   │   │   │   ├── analytics/ # AnalyticsPage (trend + forecast + bars)
│   │   │   │   ├── reports/   # ReportsPage (generate + export cards)
│   │   │   │   ├── settings/  # SettingsPage (profile + face enrollment)
│   │   │   │   ├── profile/   # ProfilePage (interests + goals CRUD)
│   │   │   │   ├── daily-plan/# DailyPlanPage (free periods + AI routine)
│   │   │   │   └── qr-scanner/# QrScannerPage (camera + manual entry)
│   │   │   ├── lib/           # api.ts (endpoint groups), utils.ts, nav.ts
│   │   │   └── styles/        # globals.css (Tailwind v4 @theme + dark mode)
│   │   ├── public/            # favicon, manifest, icons
│   │   ├── vite.config.js     # /api proxy → :8000
│   │   └── package.json
│   │
│   ├── backend/               # FastAPI Python 3.11+
│   │   ├── app/
│   │   │   ├── api/v1/        # auth, students, faculty, sessions,
│   │   │   │                  # attendance, analytics, reports, notifications,
│   │   │   │                  # daily-plan, faces, display, admin
│   │   │   ├── core/          # config, security, database, redis
│   │   │   ├── models/        # SQLAlchemy ORM
│   │   │   ├── schemas/       # Pydantic
│   │   │   ├── services/      # Business logic
│   │   │   ├── tasks/         # Celery async (worker + beat)
│   │   │   └── websocket/     # Live session feed
│   │   ├── alembic/           # Database migrations
│   │   ├── tests/             # pytest suite
│   │   ├── scripts/           # seed_demo.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── ml-service/            # Python FastAPI ML microservice (:8001)
│       ├── app/face/          # InsightFace pipeline
│       ├── app/anomaly/       # Isolation Forest
│       ├── app/forecast/      # Prophet
│       ├── requirements.txt
│       └── Dockerfile
│
├── docs/                      # Architecture, DB schema, API reference
├── .env.example               # Environment variable template
├── docker-compose.yml         # Full stack (Postgres, Redis, API, Worker, Beat, ML, Flower)
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🚀 Quick Start (Vercel — Free Tier)

The fastest way to deploy the **frontend**. For the backend, you'll need a separate host (Render free tier, Railway, or your own VPS).

1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com) → Import Project → select this repo
3. Set environment variable:
   - `BACKEND_URL` = your backend URL (e.g. `https://smartattend-api.onrender.com`)
4. Deploy — Vercel builds the Vite frontend and serves it

> **Note:** Vercel free tier serves the frontend (static + serverless API proxy). WebSockets, Celery workers, and ML service must run on a separate host with a persistent server. See [docs/deployment.md](docs/deployment.md) for details.

---

## 🚀 Quick Start (Docker)

The fastest way to run the **full stack** locally. Requires [Docker Desktop](https://docker.com/products/docker-desktop) or Docker + Compose v2.

```bash
git clone https://github.com/ujjawalranjan09/SmartAttend.git
cd SmartAttend

# Copy env template and fill in your values
cp .env.example .env

# Start everything (builds images, runs migrations, starts all services)
docker compose up --build -d

# Verify
curl http://localhost:8000/health
```

**Services started:** PostgreSQL, Redis, FastAPI backend, Celery worker, Celery beat, ML service, Flower monitoring UI (:5555).

---

## 🚀 Quick Start (Local)

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Node.js | 20+ | https://nodejs.org |
| Python | 3.11+ | https://python.org |
| PostgreSQL | 16+ | https://postgresql.org/download/windows |
| Redis | 7+ | https://github.com/tarkh/redis-windows or WSL |
| uv (optional) | latest | https://docs.astral.sh/uv |

### 1. Clone & install

```bash
git clone https://github.com/ujjawalranjan09/SmartAttend.git
cd SmartAttend

# Frontend deps
cd apps/frontend
npm install

# Backend deps
cd ../../apps/backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Database setup

```bash
# Create DB + role in psql:
#   CREATE USER smartattend WITH PASSWORD 'smartattend_secret';
#   CREATE DATABASE smartattend OWNER smartattend;
#   GRANT ALL PRIVILEGES ON DATABASE smartattend TO smartattend;

cd apps/backend
alembic upgrade head
python scripts/seed_demo.py
```

### 3. Environment

Copy `.env.example` → `.env` at the **repo root**. The defaults work for local Postgres + Redis on `localhost:5432` / `localhost:6379`.

### 4. Run all services

```bash
# Terminal 1 — backend API
cd apps/backend
set PYTHONPATH=.
.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Celery worker
cd apps/backend
set PYTHONPATH=.
.venv\Scripts\celery.exe -A app.tasks.celery_app.celery_app worker --loglevel=info --pool=solo -Q default,ml,ml_scoring,reports,notifications

# Terminal 3 — Celery beat (scheduled tasks)
cd apps/backend
set PYTHONPATH=.
.venv\Scripts\celery.exe -A app.tasks.celery_app.celery_app beat --loglevel=info

# Terminal 4 — frontend
cd apps/frontend
npm run dev

# Terminal 5 — ML service (optional, for face recognition)
cd apps/ml-service
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Open http://localhost:5173 — login with a demo account below.

---

## 🔐 Demo Credentials

The seed script creates three role-based users:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@smartattend.in` | `Admin@1234` |
| Faculty | `faculty@smartattend.in` | `Faculty@1234` |
| Student | `student1@smartattend.in` | `Student@1234` |

Login page has **one-click demo chips** that pre-fill + submit these accounts.

---

## 📡 API Surface

Base: `http://localhost:8000/api/v1` (Vite proxies `/api/*` → `:8000` automatically).

| Group | Endpoints | Purpose |
|---|---|---|
| `auth` | `/login`, `/refresh`, `/me`, `/forgot-password`, `/reset-password` | JWT auth |
| `students` | `/students`, `/at-risk`, `/bulk-enroll` | Student records |
| `faculty` | `/faculty`, `/faculty/{id}/courses` | Faculty records |
| `sessions` | CRUD + `/start`, `/end`, `/{id}/qr`, `/{id}/attendance` | Class sessions |
| `attendance` | `/mark`, `/session/{id}`, `/student/{id}` | Attendance marking |
| `analytics` | `/overview`, `/student/{id}`, `/course/{id}`, `/department/{id}` | Aggregations |
| `reports` | `/generate`, `/export/csv`, `/{id}` | PDF/CSV reports |
| `notifications` | CRUD + `/mark-read`, `/unread-count` | In-app inbox |
| `daily-plan` | `/routine`, `/free-periods`, `/invalidate` | AI planner |
| `faces` | `/status`, `/enroll` (multipart), `/delete` | Face enrollment |
| `institutions` | CRUD | Institution management |
| `courses` | CRUD | Course management |
| `departments` | CRUD | Department management |
| `timetable` | CRUD | Timetable slots |
| `display` | `/display-token/{session_id}`, `/sessions/{id}/display` | Kiosk token |
| `admin` | Admin-only operations | System administration |

Full interactive docs at **http://localhost:8000/docs** (Swagger) and **/redoc**.

---

## 📺 PWA + Classroom Display Kiosk

The build produces **two entry points**:

| Entry | URL | Description |
|---|---|---|
| Main app | `/` | Full SPA with all features |
| Kiosk | `/classroom-display.html?session_id={id}&token={token}` | TV-friendly full-screen display |

The kiosk page polls `/sessions/{id}/attendance` every 5 s and shows a giant attendance %, present/total hero cards, an animated live attendance feed, a live clock, and a SmartAttend watermark. Open it from any session's "Display" button — the URL token is rotated automatically.

**PWA:**
- Service worker auto-generated by `vite-plugin-pwa` (`autoUpdate` mode)
- NetworkFirst cache for `/api` requests with 5 s timeout, 50-entry max

**Install:** In Chrome/Edge, click the install icon in the address bar → "Install SmartAttend".

---

## 📝 Deployment Notes

See [docs/deployment.md](docs/deployment.md) for detailed deployment instructions (Docker Compose and production).

See [docs/architecture.md](docs/architecture.md) for system architecture details.

See [docs/db-schema.md](docs/db-schema.md) for database schema documentation.

See [docs/api-reference.md](docs/api-reference.md) for full API reference.

---

## ⚠️ Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Students without smartphones | Medium | Faculty manual override; QR-only fallback; classroom kiosk |
| Facial recognition bias | High | InsightFace ArcFace (evaluated on diverse datasets); face always supplementary to QR |
| GPS spoofing | Medium | Cross-validate with WiFi BSSID + BLE beacon proximity (planned) |
| Faculty resistance | Medium | Zero-training UX; single button to start/end session |
| Data breach (face embeddings) | High | Vectors only (not photos); per-institution encryption (planned) |
| Exam season scale spike | Medium | Redis handles QR validation at sub-ms; backend stateless |
| Rural internet outages | Low | Offline-first PWA with Service Worker + IndexedDB sync |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit with conventional commits: `feat:`, `fix:`, `docs:`, `chore:`
4. Push and open a Pull Request against `main`
5. Ensure all tests pass

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
