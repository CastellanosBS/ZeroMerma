from decimal import Decimal
from functools import lru_cache

from pydantic import Field, model_validator
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
    training_mode_enabled: bool = False
    training_mode_label: str = Field(default="Modo entrenamiento", min_length=1, max_length=80)
    enable_dev_audit_endpoint: bool = False
    dev_audit_token: str | None = None
    waste_high_impact_quantity_threshold: Decimal = Field(
        default=Decimal("10"),
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=3,
    )
    correction_high_impact_quantity_threshold: Decimal = Field(
        default=Decimal("10"),
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=3,
    )
    discount_high_value_amount_threshold: Decimal = Field(
        default=Decimal("200"),
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=2,
    )
    return_high_refund_amount_threshold: Decimal = Field(
        default=Decimal("200"),
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=2,
    )
    return_old_sale_days_threshold: int = Field(default=7, ge=1)

    @model_validator(mode="after")
    def validate_non_production_training_mode(self) -> "ApiSettings":
        if self.training_mode_enabled and self.environment.strip().lower() == "production":
            raise ValueError("Training mode cannot be enabled in production.")

        return self


@lru_cache
def get_settings() -> ApiSettings:
    return ApiSettings()
