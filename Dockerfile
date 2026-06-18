# SmartAttend — Root Dockerfile for the FastAPI backend.
# Used by Render (and other Docker-based hosts) when building from the repo root.
FROM python:3.11-slim

WORKDIR /app

# Minimal system deps — only what Pillow and QR codes actually need
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY apps/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY apps/backend/ .

EXPOSE 8000

# Run migrations then start the API. Demo users are seeded automatically by
# the app's lifespan hook (_ensure_demo_users) — no separate seed step needed.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
