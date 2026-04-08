from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ZEROMERMA_WORKER_",
        extra="ignore",
    )

    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma"
    poll_interval_seconds: int = Field(default=5, ge=1)
    batch_size: int = Field(default=25, ge=1, le=500)


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
