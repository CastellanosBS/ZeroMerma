import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from zeromerma_worker.core.runtime_secrets import read_private_secret


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ZEROMERMA_WORKER_",
        extra="ignore",
        hide_input_in_errors=True,
    )

    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma",
        repr=False,
        exclude=True,
    )
    database_url_file: Path | None = Field(default=None, repr=False, exclude=True)
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    poll_interval_seconds: int = Field(default=5, ge=1)
    batch_size: int = Field(default=25, ge=1, le=500)

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode="before")
    @classmethod
    def load_runtime_database_file(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("database_url_file"):
            if data.get("database_url"):
                raise ValueError("Configure one database credential source: environment or file.")
            data = {**data, "database_url": read_private_secret(Path(data["database_url_file"]))}
        return data

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

    @model_validator(mode="after")
    def validate_deployment(self) -> "WorkerSettings":
        if self.environment in {"staging", "production"}:
            database = make_url(self.database_url)
            if (
                "database_url" not in self.model_fields_set
                or not database.username
                or not database.password
                or len(database.password) < 24
                or database.database in {"zeromerma", "postgres", "template0", "template1"}
            ):
                raise ValueError("Deployment requires explicit non-sample worker credentials.")
        return self


class _InjectedWorkerSettings(WorkerSettings):
    model_config = SettingsConfigDict(env_file=None)


@lru_cache
def get_settings() -> WorkerSettings:
    if os.environ.get("ZEROMERMA_WORKER_ENVIRONMENT", "").strip().lower() in {
        "staging",
        "production",
    }:
        return _InjectedWorkerSettings()
    return WorkerSettings()
