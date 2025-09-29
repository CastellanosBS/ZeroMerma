from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Strongly-typed application configuration loaded from env variables."""

    # --- Identity  & runtime ---
    app_name: str = "ZeroMerma API"
    env: str = "development"
    log_level: str = "INFO"
    port: int = 8000

    # ---- DB ----
    database_url: str = (
        "postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma"
    )

    model_config = SettingsConfigDict(
        env_prefix="",  # reaf variables as APP_NAME, ENV, PORT, etc.
        env_file=".env",  # load local overrides when present
        extra="ignore",  # ignore unknown env vars (safer for container envs)
    )


@lru_cache
def get_settings() -> AppSettings:
    """Cache settings so we only parse env once the process."""
    return AppSettings()
