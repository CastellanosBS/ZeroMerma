from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from zeromerma_api.core.config import ApiSettings
from zeromerma_api.core.logging import JsonFormatter as ApiFormatter
from zeromerma_api.core.runtime_secrets import read_private_secret, write_private_secret
from zeromerma_api.core.security import install_security_boundary
from zeromerma_api.presentation.errors import install_error_handlers
from zeromerma_worker.core.config import WorkerSettings
from zeromerma_worker.core.logging import JsonFormatter as WorkerFormatter

DATABASE_URL = "postgresql+psycopg://api_runtime:test_only_random_credential_2Ek98z@db/site_staging"
POS_ORIGIN = "https://pos.example.test"
BACKOFFICE_ORIGIN = "https://backoffice.example.test"


@pytest.fixture(autouse=True)
def clean_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith(("ZEROMERMA_API_", "ZEROMERMA_WORKER_")):
            monkeypatch.delenv(key)


def deployment_settings(**overrides: object) -> ApiSettings:
    return ApiSettings(
        _env_file=None,
        **{
            "environment": "staging",
            "database_url": DATABASE_URL,
            "cors_origins": [POS_ORIGIN, BACKOFFICE_ORIGIN],
            "session_pos_origins": [POS_ORIGIN],
            "session_backoffice_origins": [BACKOFFICE_ORIGIN],
            "allowed_hosts": ["api.example.test"],
            **overrides,
        },
    )


@pytest.mark.parametrize("environment", ["staging", "production", "prod", "unknown"])
@pytest.mark.parametrize("model", [ApiSettings, WorkerSettings])
def test_deployment_rejects_defaults_and_unknown_environment(model, environment: str) -> None:
    with pytest.raises(ValidationError):
        model(_env_file=None, environment=environment)


@pytest.mark.parametrize(
    "override",
    [
        {"training_mode_enabled": True},
        {"enable_dev_audit_endpoint": True},
        {"enable_api_docs": True},
        {"dev_audit_token": "private-development-value"},
        {"database_url": "sqlite:///data.db"},
        {"database_url": "postgresql+psycopg://user:password@db/site_staging"},
        {"database_url": DATABASE_URL.replace("site_staging", "zeromerma")},
        {"allowed_hosts": ["*"]},
        {"allowed_hosts": ["localhost"]},
        {"trusted_proxy_ips": ["*"]},
        {"trusted_proxy_ips": ["0.0.0.0/0"]},
        {"trusted_proxy_ips": ["::/0"]},
        {"session_backoffice_origins": [POS_ORIGIN]},
        {"session_pos_origins": ["https://foreign.example.test"]},
        {"cors_origins": ["*"]},
        {"cors_origins": [POS_ORIGIN + "/"]},
        {"cors_origins": [POS_ORIGIN + "?token=value"]},
    ],
)
def test_invalid_deployment_configuration_fails_closed(override: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        deployment_settings(**override)


@pytest.mark.parametrize(
    "origin", ["http://pos.example.test", "https://localhost", "https://127.0.0.1"]
)
def test_deployment_rejects_development_origins(origin: str) -> None:
    with pytest.raises(ValidationError):
        deployment_settings(cors_origins=[origin, BACKOFFICE_ORIGIN], session_pos_origins=[origin])


def test_valid_explicit_configuration_does_not_expose_database_in_repr() -> None:
    settings = deployment_settings(environment="production")
    assert settings.cors_origins == [POS_ORIGIN, BACKOFFICE_ORIGIN]
    assert "test_only_random_credential" not in repr(settings)
    assert "database_url" not in settings.model_dump()
    worker = WorkerSettings(_env_file=None, environment="production", database_url=DATABASE_URL)
    assert "test_only_random_credential" not in repr(worker)
    assert "database_url" not in worker.model_dump()


def test_private_runtime_file_is_loaded_and_conflicting_sources_are_rejected(
    tmp_path: Path,
) -> None:
    secret = tmp_path / "database-url"
    write_private_secret(secret, DATABASE_URL)
    assert read_private_secret(secret) == DATABASE_URL
    assert ApiSettings(_env_file=None, database_url_file=secret).database_url == DATABASE_URL
    assert WorkerSettings(_env_file=None, database_url_file=secret).database_url == DATABASE_URL
    for model in (ApiSettings, WorkerSettings):
        with pytest.raises(ValidationError, match="one database credential source"):
            model(_env_file=None, database_url_file=secret, database_url=DATABASE_URL)
    with pytest.raises(FileExistsError):
        write_private_secret(secret, "must-not-replace-existing-material")
    assert read_private_secret(secret) == DATABASE_URL


def test_runtime_secret_file_rejects_missing_and_multiline_material(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        read_private_secret(tmp_path / "missing")
    with pytest.raises(ValueError):
        write_private_secret(tmp_path / "invalid", "first\nsecond")
    assert not (tmp_path / "invalid").exists()


def test_deployment_factories_ignore_checkout_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeromerma_api.core import config as api_config
    from zeromerma_worker.core import config as worker_config

    (tmp_path / ".env").write_text(
        "ZEROMERMA_API_DATABASE_URL=" + DATABASE_URL + "\n"
        "ZEROMERMA_WORKER_DATABASE_URL=" + DATABASE_URL + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    for prefix, factory in (
        ("ZEROMERMA_API_", api_config.get_settings),
        ("ZEROMERMA_WORKER_", worker_config.get_settings),
    ):
        monkeypatch.setenv(prefix + "ENVIRONMENT", "production")
        factory.cache_clear()
        try:
            with pytest.raises(ValidationError):
                factory()
        finally:
            factory.cache_clear()


def test_actual_application_cors_and_deployment_route_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from zeromerma_api.core import config

    settings = deployment_settings()
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    main = import_module("zeromerma_api.main")
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    app = main.create_app()
    paths = {getattr(route, "path", "") for route in app.routes}
    assert not {"/docs", "/redoc", "/openapi.json"} & paths
    assert not any(path.startswith("/dev/") for path in paths)
    with TestClient(app, base_url="https://api.example.test") as client:
        headers = {
            "Origin": POS_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": (
                "Content-Type,X-CSRF-Token,X-ZeroMerma-Surface,X-Request-ID"
            ),
        }
        accepted = client.options("/v1/auth/login", headers=headers)
        assert accepted.status_code == 200
        assert accepted.headers["access-control-allow-origin"] == POS_ORIGIN
        assert accepted.headers["access-control-allow-credentials"] == "true"
        assert "*" not in accepted.headers["access-control-allow-methods"]
        rejected = client.options(
            "/v1/auth/login", headers={**headers, "Origin": "https://foreign.example.test"}
        )
        assert rejected.status_code == 400
        assert "access-control-allow-origin" not in rejected.headers


def test_deployment_import_refuses_before_engine_creation_and_redacts_validation() -> None:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("ZEROMERMA_API_", "ZEROMERMA_WORKER_"))
    }
    marker = "private-value-never-print"
    environment.update(
        {"ZEROMERMA_API_ENVIRONMENT": "production", "ZEROMERMA_API_DATABASE_URL": marker}
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sqlalchemy; sqlalchemy.create_engine = lambda *a, **k: "
            "(_ for _ in ()).throw(RuntimeError('ENGINE_WAS_CALLED')); import zeromerma_api.main",
        ],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "ValidationError" in output
    assert marker not in output
    assert "ENGINE_WAS_CALLED" not in output


def boundary_app(settings: ApiSettings) -> FastAPI:
    app = FastAPI()

    @app.get("/probe")
    def probe() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("password=never-expose-this")

    install_error_handlers(app)
    install_security_boundary(app, settings)
    return app


def test_security_headers_cover_success_and_safe_server_error() -> None:
    with TestClient(
        boundary_app(deployment_settings()),
        base_url="https://api.example.test",
        raise_server_exceptions=False,
    ) as client:
        for path, expected in (("/probe", 200), ("/failure", 500)):
            response = client.get(path)
            assert response.status_code == expected
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-frame-options"] == "DENY"
            assert response.headers["cache-control"] == "no-store"
            assert "default-src 'none'" in response.headers["content-security-policy"]
            assert response.headers["strict-transport-security"] == "max-age=31536000"
            assert "never-expose-this" not in response.text


@pytest.mark.parametrize(
    "host", ["evil.example.test", "evil@api.example.test", "api.example.test/path"]
)
def test_host_spoofing_is_rejected(host: str) -> None:
    with TestClient(
        boundary_app(deployment_settings()), base_url="https://api.example.test"
    ) as client:
        assert client.get("/probe", headers={"Host": host}).status_code == 403


def test_untrusted_forwarded_proto_cannot_upgrade_http() -> None:
    with TestClient(
        boundary_app(deployment_settings()), base_url="http://api.example.test"
    ) as client:
        assert client.get("/probe", headers={"X-Forwarded-Proto": "https"}).status_code == 403


def test_trusted_proxy_only_accepts_single_sanitized_client_and_protocol() -> None:
    app = boundary_app(deployment_settings(trusted_proxy_ips=["127.0.0.1"]))
    with TestClient(app, base_url="http://api.example.test", client=("127.0.0.1", 40000)) as client:
        headers = {"X-Forwarded-Proto": "https", "X-Forwarded-For": "192.0.2.50"}
        assert client.get("/probe", headers=headers).status_code == 200
        assert (
            client.get(
                "/probe", headers={**headers, "X-Forwarded-For": "192.0.2.50, 192.0.2.60"}
            ).status_code
            == 403
        )


def test_trusted_proxy_safe_error_keeps_https_headers() -> None:
    with TestClient(
        boundary_app(deployment_settings(trusted_proxy_ips=["127.0.0.1"])),
        base_url="http://api.example.test",
        client=("127.0.0.1", 40000),
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/failure", headers={"X-Forwarded-Proto": "https"})
        assert response.status_code == 500
        assert response.headers["strict-transport-security"] == "max-age=31536000"
        assert "never-expose-this" not in response.text
        assert (
            client.get(
                "/probe",
                headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "api.example.test"},
            ).status_code
            == 403
        )


@pytest.mark.parametrize("formatter", [ApiFormatter, WorkerFormatter])
def test_logs_redact_credentials_urls_and_raw_exception(formatter) -> None:
    record = logging.LogRecord(
        "test",
        logging.ERROR,
        "",
        0,
        "request https://api.example.test/reset?credential=hidden-url "
        "database=postgresql://user:hidden-db@db/app Authorization=Bearer hidden-bearer\n"
        "Cookie: first=hidden-cookie; second=hidden-cookie-two",
        (),
        None,
    )
    record.secret = "hidden-extra"
    record.payload = {"safe": "keep", "nested": {"csrf_token": "hidden-structured"}}
    try:
        raise RuntimeError("hidden-exception")
    except RuntimeError:
        record.exc_info = sys.exc_info()
    output = formatter().format(record)
    for secret in (
        "hidden-url",
        "hidden-db",
        "hidden-bearer",
        "hidden-extra",
        "hidden-structured",
        "hidden-exception",
        "hidden-cookie",
        "hidden-cookie-two",
    ):
        assert secret not in output
    assert json.loads(output)["exception_type"] == "RuntimeError"
