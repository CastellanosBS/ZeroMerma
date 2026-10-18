from __future__ import annotations

import ipaddress
import os
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from zeromerma_api.core.runtime_secrets import read_private_secret

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
    cors_origins: list[str] = Field(default_factory=lambda: list(DEFAULT_LOCAL_CORS_ORIGINS))
    session_pos_origins: list[str] = Field(
        default_factory=lambda: list(DEFAULT_LOCAL_CORS_ORIGINS[:2])
    )
    session_backoffice_origins: list[str] = Field(
        default_factory=lambda: list(DEFAULT_LOCAL_CORS_ORIGINS[2:])
    )
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "[::1]", "testserver"]
    )
    trusted_proxy_ips: list[str] = Field(default_factory=list)
    enable_api_docs: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_login_window_seconds: int = Field(default=900, ge=1, le=86400)
    auth_login_account_limit: int = Field(default=10, ge=1, le=100)
    auth_login_ip_limit: int = Field(default=50, ge=1, le=1000)
    auth_login_block_seconds: int = Field(default=900, ge=1, le=86400)
    password_reset_ttl_minutes: int = Field(default=30, ge=1, le=60)
    training_mode_enabled: bool = False
    training_mode_label: str = Field(default="Modo entrenamiento", min_length=1, max_length=80)
    enable_dev_audit_endpoint: bool = False
    dev_audit_token: str | None = Field(default=None, repr=False, exclude=True)
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

    @model_validator(mode="before")
    @classmethod
    def load_runtime_database_file(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("database_url_file"):
            if data.get("database_url"):
                raise ValueError("Configure one database credential source: environment or file.")
            data = {**data, "database_url": read_private_secret(Path(data["database_url_file"]))}
        return data

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Unsupported API log level.")
        return normalized

    @field_validator("cors_origins", "session_pos_origins", "session_backoffice_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            parsed = urlsplit(value)
            try:
                port = parsed.port
            except ValueError as error:
                raise ValueError("Origins require a valid port.") from error
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "*" in value
                or value != value.strip()
                or (port is not None and not 1 <= port <= 65535)
            ):
                raise ValueError(
                    "Origins must be exact HTTP(S) origins without paths or wildcards."
                )
            if value not in result:
                result.append(value)
        if not result:
            raise ValueError("At least one explicit application origin is required.")
        return result

    @field_validator("allowed_hosts")
    @classmethod
    def validate_hosts(cls, values: list[str]) -> list[str]:
        if not values or any(
            not value
            or "*" in value
            or "/" in value
            or "@" in value
            or value != value.lower().strip()
            or any(char.isspace() for char in value)
            for value in values
        ):
            raise ValueError(
                "Allowed hosts must be explicit lowercase host names without wildcards."
            )
        return values

    @field_validator("trusted_proxy_ips")
    @classmethod
    def validate_proxies(cls, values: list[str]) -> list[str]:
        for value in values:
            try:
                network = ipaddress.ip_network(value)
            except ValueError as error:
                raise ValueError(
                    "Trusted proxies require explicit IP addresses or narrow CIDRs."
                ) from error
            if network.prefixlen == 0:
                raise ValueError("A universal trusted-proxy network is forbidden.")
        return values

    @model_validator(mode="after")
    def validate_deployment(self) -> ApiSettings:
        pos_origins = set(self.session_pos_origins)
        backoffice_origins = set(self.session_backoffice_origins)
        if pos_origins & backoffice_origins:
            raise ValueError("POS and Backoffice must have independent application origins.")
        if not (pos_origins | backoffice_origins).issubset(self.cors_origins):
            raise ValueError("Session audience origins must be included in the CORS allowlist.")
        try:
            database = make_url(self.database_url)
            port = database.port
        except (ArgumentError, TypeError, ValueError) as error:
            raise ValueError("API database URL is malformed.") from error
        if (
            database.drivername != "postgresql+psycopg"
            or not database.host
            or not database.database
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise ValueError("API requires PostgreSQL psycopg with an explicit host and database.")
        if self.environment not in {"staging", "production"}:
            return self
        if self.training_mode_enabled or self.enable_dev_audit_endpoint or self.enable_api_docs:
            raise ValueError(
                "Training, development audit and API docs are forbidden in deployment."
            )
        if self.dev_audit_token:
            raise ValueError("Development audit credentials are forbidden in deployment.")
        if (
            "database_url" not in self.model_fields_set
            or not database.username
            or not database.password
            or len(database.password) < 24
            or database.password.lower() in {"zeromerma-local-development-token-secret"}
            or database.database in {"zeromerma", "postgres", "template0", "template1"}
        ):
            raise ValueError("Deployment requires explicit non-sample database credentials.")
        if not {
            "allowed_hosts",
            "cors_origins",
            "session_pos_origins",
            "session_backoffice_origins",
        }.issubset(self.model_fields_set):
            raise ValueError("Deployment requires explicit application origins and API hosts.")
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            host = parsed.hostname or ""
            if parsed.scheme != "https" or host in {"localhost", "testserver", "0.0.0.0"}:
                raise ValueError("Deployment origins require HTTPS and non-development hosts.")
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                if host.endswith(".localhost"):
                    raise ValueError("Development hosts cannot be deployment origins.") from None
            else:
                if address.is_loopback or address.is_unspecified:
                    raise ValueError("Loopback origins cannot be used in deployment.")
        if any(
            host in {"localhost", "127.0.0.1", "[::1]", "testserver", "0.0.0.0"}
            or host.endswith(".localhost")
            for host in self.allowed_hosts
        ):
            raise ValueError("Development hosts cannot be deployment API hosts.")
        return self


class _InjectedApiSettings(ApiSettings):
    model_config = SettingsConfigDict(env_file=None)


@lru_cache
def get_settings() -> ApiSettings:
    if os.environ.get("ZEROMERMA_API_ENVIRONMENT", "").strip().lower() in {"staging", "production"}:
        return _InjectedApiSettings()
    settings = ApiSettings()
    if settings.environment in {"staging", "production"}:
        raise ValueError("Deployment mode must be selected through ZEROMERMA_API_ENVIRONMENT.")
    return settings
