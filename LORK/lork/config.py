"""
LORK global configuration — loaded once at startup via pydantic-settings.
All values are overridable via environment variables or a .env file.
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "lork"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.PRODUCTION
    DEBUG: bool = False
    LOG_LEVEL: LogLevel = LogLevel.INFO

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    SECRET_KEY: str = Field(..., min_length=32)
    ENCRYPTION_KEY: str = Field(..., min_length=32)

    DATABASE_URL: PostgresDsn
    REDIS_URL: RedisDsn = Field(default="redis://localhost:6379/0")  # type: ignore

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
