from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Compute backend root deterministically from this file's location.
# Path: apps/backend/src/zeromerma_api/core/settings.py
# parents[0]=core, [1]=zeromerma_api, [2]=src, [3]=backend
BACKEND_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = BACKEND_ROOT / ".env"


class AppSettings(BaseSettings):
    """Strongly-typed application configuration loaded from env variables."""

    # --- Identity & runtime ---
    app_name: str = "ZeroMerma API"
    env: str = "development"
    log_level: str = "INFO"
    port: int = 8000

    # --- Database ---
    # Pydantic will map this field from env var DATABASE_URL (case-insensitive).
    # Example: postgresql+psycopg://user:pass@host:5432/dbname
    database_url: str = (
        "postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma"
    )

    model_config = SettingsConfigDict(
        env_prefix="",  # reads vars as APP_NAME, ENV, PORT, DATABASE_URL, etc.
        env_file=str(ENV_FILE),  # absolute path => stable across working directories
        extra="ignore",  # ignore unknown env vars (safer for containers)
    )


@lru_cache
def get_settings() -> AppSettings:
    """Cache settings so we only parse env once per process."""
    return AppSettings()
