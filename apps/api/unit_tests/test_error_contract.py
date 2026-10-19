from __future__ import annotations

from typing import NoReturn

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from zeromerma_api.presentation.errors import error_responses, install_error_handlers
from zeromerma_api.presentation.operation_context import OperationContextMiddleware


class ValidationPayload(BaseModel):
    quantity: int


def _test_app() -> FastAPI:
    app = FastAPI(responses=error_responses())
    install_error_handlers(app)
    app.add_middleware(OperationContextMiddleware)

    @app.get("/error/{status_code}", response_model=None)
    def error(status_code: int) -> NoReturn:
        if status_code == 500:
            raise RuntimeError("database password=must-not-leak")
        raise HTTPException(status_code=status_code, detail=f"safe {status_code} message")

    @app.post("/validation")
    def validation(payload: ValidationPayload) -> ValidationPayload:
        return payload

    return app


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (400, "BAD_REQUEST"),
        (401, "AUTHENTICATION_REQUIRED"),
        (403, "FORBIDDEN"),
        (404, "NOT_FOUND"),
        (409, "CONFLICT"),
        (423, "SESSION_LOCKED"),
        (429, "LOGIN_RATE_LIMITED"),
    ],
)
def test_http_error_contract(status_code: int, expected_code: str) -> None:
    response = TestClient(_test_app()).get(
        f"/error/{status_code}",
        headers={"X-Request-ID": "c43d8ec5-1af1-4e1b-9b29-011071580488"},
    )

    assert response.status_code == status_code
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "code": expected_code,
        "message": f"safe {status_code} message",
        "details": None,
        "request_id": "c43d8ec5-1af1-4e1b-9b29-011071580488",
        "field_errors": None,
    }


def test_validation_error_contract_is_structured_and_redacted() -> None:
    response = TestClient(_test_app()).post(
        "/validation",
        json={"quantity": "not-an-integer", "password": "must-not-leak"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["message"] == "Request validation failed."
    assert payload["details"] is None
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert payload["field_errors"] == [
        {
            "location": ["body", "quantity"],
            "message": "Input should be a valid integer, unable to parse string as an integer",
            "type": "int_parsing",
        }
    ]
    assert "must-not-leak" not in response.text


def test_unhandled_error_contract_does_not_leak_internals(
    caplog: pytest.LogCaptureFixture,
) -> None:
    response = TestClient(_test_app(), raise_server_exceptions=False).get("/error/500")

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"
    assert response.json()["message"] == "An unexpected error occurred."
    assert "password" not in response.text
    assert "traceback" not in response.text.lower()
    assert "must-not-leak" not in caplog.text


def test_openapi_declares_the_canonical_error_envelope() -> None:
    schema = _test_app().openapi()
    responses = schema["paths"]["/validation"]["post"]["responses"]

    assert {"400", "401", "403", "404", "409", "422", "423", "429", "500"} <= responses.keys()
    assert responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ApiErrorResponse"
    )


def test_explicit_server_errors_are_safe_and_do_not_restore_legacy_alias() -> None:
    app = _test_app()

    @app.get("/explicit-failure", response_model=None)
    def explicit_failure() -> NoReturn:
        raise HTTPException(status_code=500, detail="password=must-not-leak")

    response = TestClient(app).get("/explicit-failure")
    assert response.status_code == 500
    assert response.json()["message"] == "An unexpected error occurred."
    assert "must-not-leak" not in response.text
    assert "detail" not in response.json()


@pytest.mark.parametrize(
    ("status_code", "requested_code", "expected_code"),
    [
        (401, "SESSION_REVOKED", "SESSION_REVOKED"),
        (401, "SESSION_EXPIRED", "SESSION_EXPIRED"),
        (403, "PASSWORD_RESET_REQUIRED", "PASSWORD_RESET_REQUIRED"),
        (403, "CSRF_FAILED", "CSRF_FAILED"),
        (403, "SESSION_REVOKED", "FORBIDDEN"),
        (401, "unregistered-code", "AUTHENTICATION_REQUIRED"),
    ],
)
def test_domain_error_codes_are_allowlisted_and_bound_to_status(
    status_code: int, requested_code: str, expected_code: str
) -> None:
    app = _test_app()

    @app.get("/domain-error", response_model=None)
    def domain_error() -> NoReturn:
        raise HTTPException(
            status_code=status_code,
            detail={"code": requested_code, "message": "Safe domain error", "token": "private"},
        )

    response = TestClient(app).get("/domain-error")
    assert response.status_code == status_code
    assert response.json()["code"] == expected_code
    assert "private" not in response.text


@pytest.mark.parametrize(
    ("method", "path", "body", "status_code", "code"),
    [
        ("GET", "/v1/auth/me", None, 401, "AUTHENTICATION_REQUIRED"),
        ("GET", "/v1/does-not-exist", None, 404, "NOT_FOUND"),
        ("POST", "/v1/auth/login", {}, 422, "VALIDATION_ERROR"),
    ],
)
def test_real_application_routes_use_the_canonical_envelope(
    method: str,
    path: str,
    body: dict[str, object] | None,
    status_code: int,
    code: str,
) -> None:
    from zeromerma_api.main import create_app

    response = TestClient(create_app()).request(method, path, json=body)

    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert set(response.json()) == {
        "code",
        "message",
        "details",
        "request_id",
        "field_errors",
    }
