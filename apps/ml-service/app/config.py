from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
import os


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # App
    app_name: str = "SmartAttend ML Service"
    app_env: str = "development"

    # Model paths
    face_model_name: str = "buffalo_l"
    anomaly_threshold: float = 0.6
    model_dir: str = str(Path(__file__).resolve().parent.parent / "models")

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    # CORS
    allowed_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()