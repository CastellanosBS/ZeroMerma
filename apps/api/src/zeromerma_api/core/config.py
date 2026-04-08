from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_LOCAL_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
)


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ZEROMERMA_API_",
        extra="ignore",
    )

    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma"
    cors_origins: list[str] = Field(default_factory=lambda: list(DEFAULT_LOCAL_CORS_ORIGINS))
    auth_token_secret: str = "zeromerma-local-development-token-secret"
    auth_token_ttl_minutes: int = Field(default=480, ge=1)


@lru_cache
def get_settings() -> ApiSettings:
    return ApiSettings()
