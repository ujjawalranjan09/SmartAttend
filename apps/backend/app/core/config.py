from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
from typing import Literal
import os
import warnings

from dotenv import load_dotenv
from pydantic import Field, model_validator


def _load_env_file() -> None:
    """Load .env from multiple candidate locations.

    This makes local development (running uvicorn from apps/backend/)
    and Docker volume mounts (where only apps/backend/ is mounted to /app)
    both able to find the project-root .env file.
    """
    candidates = [
        # When running with CWD at project root
        Path.cwd() / ".env",
        # Common when running uvicorn from inside apps/backend/
        Path.cwd().parent / ".env",
        # Docker container with volume mount or built image
        Path("/app/.env"),
        Path("/app/app/.env"),  # unlikely but harmless
    ]

    # Walk up from this file towards root, looking for .env at each level
    _this = Path(__file__).resolve()
    for i in range(len(_this.parents)):  # safe — won't IndexError
        candidates.append(_this.parents[i] / ".env")

    for candidate in candidates:
        if candidate.is_file():
            load_dotenv(dotenv_path=candidate, override=False)
            # Also tell pydantic-settings about it for this process
            os.environ.setdefault("_SMARTATTEND_DOTENV_LOADED", str(candidate))
            return


_load_env_file()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "SmartAttend"
    secret_key: str = Field(
        default="dev-insecure-secret-key-change-this-in-production-please",
        description="JWT signing secret. MUST be overridden in staging/production.",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://smartattend:smartattend_secret@localhost:5432/smartattend",
        description="SQLAlchemy database URL. MUST be overridden when using Docker Compose or in production.",
    )
    database_pool_size: int = 20
    database_max_overflow: int = 0

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    qr_token_ttl_seconds: int = 120

    # ML Service
    ml_service_url: str = "http://localhost:8001"
    face_similarity_threshold: float = 0.60
    proxy_anomaly_threshold: float = 0.75

    # Storage
    storage_provider: str = "s3"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-south-1"
    s3_bucket_name: str = "smartattend-media"

    # Notifications
    sms_provider: str = "twilio"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    email_from: str = "noreply@smartattend.in"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Web Push (VAPID)
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_claims_email: str = "mailto:admin@smartattend.in"

    # TOTP
    totp_issuer: str = "SmartAttend"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Sentry
    sentry_dsn: str = ""

    # LLM / OpenRouter
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_max_tokens: int = 1000

    @model_validator(mode="after")
    def _validate_production_secrets(self):
        insecure_secret = "dev-insecure-secret-key-change-this-in-production-please"
        insecure_db = "postgresql+asyncpg://smartattend:smartattend_secret@localhost:5432/smartattend"

        if self.app_env == "production":
            if self.secret_key == insecure_secret:
                raise ValueError(
                    "In production you MUST set a strong SECRET_KEY (at least 32 chars). "
                    "Do not use the development default."
                )
            if self.database_url == insecure_db or "localhost" in self.database_url:
                raise ValueError(
                    "In production you MUST set DATABASE_URL to your real database "
                    "(do not use localhost or the dev default)."
                )
        elif self.secret_key == insecure_secret or self.database_url == insecure_db:
            # Only warn once in development
            warnings.warn(
                "Using development default for secret_key or database_url. "
                "This is fine for local/dev but never use in production. "
                "Set real values via environment variables or .env file.",
                UserWarning,
                stacklevel=2,
            )
        return self


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as exc:  # Pydantic ValidationError or others
        # Re-raise with a much more actionable message for Docker / first-run users
        msg = (
            "\n"
            "═══════════════════════════════════════════════════════════════\n"
            "  SmartAttend Settings Error\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "  Missing required environment variables: SECRET_KEY and/or DATABASE_URL\n"
            "\n"
            "  Quick fixes:\n"
            "    • Recommended:  docker-compose up --build\n"
            "                      (or: make up)\n"
            "\n"
            "    • Manual Docker:\n"
            "        docker run -e SECRET_KEY=your-32+char-secret \\\n"
            "                   -e DATABASE_URL=postgresql+asyncpg://... \\\n"
            "                   -p 8000:8000 your-image\n"
            "\n"
            "    • Local development (no Docker):\n"
            "        1. Copy .env.example -> .env in the project root\n"
            "        2. Fill in at least SECRET_KEY and DATABASE_URL\n"
            "        3. Run: cd apps/backend && uvicorn app.main:app --reload\n"
            "\n"
            "  The .env file must be in the project root (next to docker-compose.yml).\n"
            "  Docker Compose reads it automatically. Plain `docker run` does not.\n"
            "\n"
            f"  Original error: {exc}\n"
            "═══════════════════════════════════════════════════════════════\n"
        )
        # Print to stderr so it's visible even if logging isn't configured yet
        import sys

        print(msg, file=sys.stderr)
        raise


settings = get_settings()
