from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Strongly typed application configuration.

    Why this class exists:
    - It centralizes all runtime configuration in one place.
    - It gives us IDE autocomplete and static typing.
    - It validates env values when the app starts.
    - It avoids scattering os.getenv(...) across the codebase.

    How it works:
    - Pydantic Settings reads environment variables automatically.
    - Each class attribute is a typed configuration field.
    - If an environment variable is missing, the default value is used.
    - If a value has the wrong type, Pydantic raises a validation error.
    """

    # -------------------------------------------------------------------------
    # App identity / runtime
    # -------------------------------------------------------------------------
    # Human-readable application name.
    app_name: str = "ZeroMerma API"

    # Runtime environment label used by the app (development, test, production).
    env: str = "development"

    # Logging verbosity.
    log_level: str = "INFO"

    # Port where the API process should run.
    # We validate a sane TCP range.
    port: int = Field(default=8000, ge=1, le=65535)

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    # Full SQLAlchemy connection URL.
    # Example:
    # postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma
    database_url: str = "postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma"

    # -------------------------------------------------------------------------
    # Authentication / JWT
    # -------------------------------------------------------------------------
    # Secret key used to sign JWT tokens.
    #
    # IMPORTANT:
    # - This default is only acceptable for local development.
    # - In production, ALWAYS override with a strong secret from the environment.
    # - A compromised secret means attackers could forge tokens.
    auth_secret_key: str = Field(
        default="change-this-in-production-min-32-chars",
        min_length=32,
    )

    # JWT signing algorithm.
    # HS256 is a good default for symmetric-signing setups.
    auth_algorithm: str = "HS256"

    # Access token lifetime in minutes.
    # This is used by security.py to compute the "exp" claim.
    auth_access_token_expires_minutes: int = Field(default=60, ge=1)

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    # IMPORTANT:
    # - For local development, this should include the frontend origin.
    # - Pydantic Settings can parse JSON arrays from environment variables.
    # - Example in .env:
    #   CORS_ALLOWED_ORIGINS=["http://localhost:3000"]
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # -------------------------------------------------------------------------
    # Pydantic Settings configuration
    # -------------------------------------------------------------------------
    # env_prefix=""
    #   Means field names map directly to env vars in uppercase:
    #   - app_name  -> APP_NAME
    #   - database_url -> DATABASE_URL
    #   - auth_secret_key -> AUTH_SECRET_KEY
    #
    # env_file=".env"
    #   Loads local overrides from the backend .env file.
    #
    # extra="ignore"
    #   Ignores unknown env vars instead of failing.
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> AppSettings:
    """
    Return a cached AppSettings instance.

    Why cache it:
    - Parsing environment variables repeatedly is unnecessary.
    - Settings are process-level configuration and should behave like a singleton.
    - This keeps the rest of the app fast and consistent.

    Important behavior:
    - The first call reads and validates the environment.
    - Subsequent calls return the same in-memory object.
    """
    return AppSettings()
