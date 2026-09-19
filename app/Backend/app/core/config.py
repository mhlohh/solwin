from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Solwin API"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/solwin_db"

    # External APIs & Security
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    JWT_SECRET_KEY: str = "default-development-secret-key-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Attachments & Storage
    ATTACHMENTS_STORAGE_DIR: str = "storage/attachments"
    MAX_ATTACHMENT_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Frontend CORS
    FRONTEND_ORIGINS: str = "http://localhost:5173"

    # ML Service
    ML_SERVICE_URL: str = "http://localhost:8001"
    ML_SERVICE_TIMEOUT_SECONDS: float = 10.0
    CUSTOMER_INTELLIGENCE_PROVIDER: Literal["auto", "ml", "gemini"] = "auto"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
