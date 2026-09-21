from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings. Secrets are never committed or logged."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Existing ML service settings ---
    model_dir: Path = Path("models")
    model_registry_path: Path = Path("config/model_registry.yaml")
    log_level: str = "INFO"
    max_input_length: int = Field(default=10_000, ge=1, le=100_000)
    max_conversation_messages: int = Field(default=100, ge=1, le=1_000)
    model_confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    request_timeout_seconds: float = Field(default=15.0, gt=0.0, le=120.0)
    external_reputation_timeout_seconds: float = Field(default=3.0, gt=0.0, le=30.0)

    # --- Gemini AI provider ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_enabled: bool = False
    gemini_live_test: bool = False
    gemini_timeout_seconds: float = Field(default=20.0, gt=0.0, le=120.0)
    gemini_max_retries: int = Field(default=2, ge=0, le=5)
    gemini_use_for_classification: bool = True
    gemini_use_for_sentiment: bool = True
    gemini_use_for_summary: bool = True
    gemini_use_for_social_engineering: bool = True
    gemini_use_for_embeddings: bool = False  # Off by default (quota cost)

    # --- Demo mode ---
    demo_mode: bool = False

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be a standard Python log level")
        return normalized

    @model_validator(mode="after")
    def validate_gemini_key(self) -> "Settings":
        # If explicitly enabled with no key, provider will handle or validation error
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
