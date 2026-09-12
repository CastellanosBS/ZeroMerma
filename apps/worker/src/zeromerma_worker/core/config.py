from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ZEROMERMA_WORKER_",
        extra="ignore",
    )

    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma"
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    poll_interval_seconds: int = Field(default=5, ge=1)
    batch_size: int = Field(default=25, ge=1, le=500)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Unsupported worker log level")
        return normalized

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        try:
            parsed = make_url(value)
            port = parsed.port
        except (ArgumentError, TypeError, ValueError) as error:
            raise ValueError("Worker database URL is malformed") from error
        if (
            parsed.drivername != "postgresql+psycopg"
            or not parsed.host
            or not parsed.database
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise ValueError("Worker requires a PostgreSQL psycopg URL with host and database")
        return value


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
