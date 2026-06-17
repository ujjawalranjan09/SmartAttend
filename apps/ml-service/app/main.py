from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load models
    from app.face.embedding import load_face_model

    load_face_model()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    description="ML Service for SmartAttend: Face Recognition, Anomaly Detection & Forecasting",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    if settings.app_env == "development"
    else [settings.allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    import time

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": "1.0.0",
        "timestamp": time.time(),
    }