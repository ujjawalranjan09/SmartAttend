# SmartAttend — Root Dockerfile for the FastAPI backend.
# Used by Render (and other Docker-based hosts) when building from the repo root.
# Renders the backend service; Celery worker/beat reuse apps/backend/Dockerfile.
FROM python:3.11-slim

WORKDIR /app

# System deps for Pillow / face libs
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY apps/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY apps/backend/ .

# Expose the API port (Render injects $PORT — uvicorn binds to it at runtime)
EXPOSE 8000

# Run migrations then start the API. Render overrides PORT automatically.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
