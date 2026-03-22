"""
Application configuration using Pydantic BaseSettings.
Reads from environment variables and .env file.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # App
    APP_NAME: str = "VieNeu TTS API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://vietneu:vietneu@localhost:5432/vietneu_tts"

    # Auth
    SECRET_KEY: str = "change-this-to-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # VieNeu SDK
    VIENEU_MODE: str = "standard"
    VIENEU_BACKBONE_REPO: str = "pnnbao-ump/VieNeu-TTS"
    VIENEU_CODEC_REPO: str = "neuphonic/distill-neucodec"

    # Training
    TRAINING_GPU_ID: int = 1
    TRAINING_MAX_STEPS: int = 5000
    TRAINING_BASE_MODEL: str = "pnnbao-ump/VieNeu-TTS-0.3B"

    # Storage
    STORAGE_PATH: str = str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data")
    RECORDINGS_PATH: str = ""
    VIENEU_TTS_PATH: str = str(Path(__file__).resolve().parent.parent.parent.parent.parent / "VieNeu-TTS")

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Admin
    ADMIN_EMAIL: str = "admin@vietneu.io"
    ADMIN_PASSWORD: str = "changeme"

    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.RECORDINGS_PATH:
            self.RECORDINGS_PATH = os.path.join(self.STORAGE_PATH, "recordings")


settings = Settings()
