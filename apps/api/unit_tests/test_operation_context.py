from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import FrozenInstanceError, replace
from uuid import UUID, uuid4

import anyio
import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

from zeromerma_api.core.config import ApiSettings
from zeromerma_api.core.logging import JsonFormatter
from zeromerma_api.core.operation_context import (
    OperationContext,
    SourceApp,
    current_operation_context,
    publish_operation_context,
)
from zeromerma_api.core.security import install_security_boundary
from zeromerma_api.presentation.errors import install_error_handlers
from zeromerma_api.presentation.operation_context import OperationContextMiddleware, request_context


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(OperationContextMiddleware)

    @app.get("/context")
    def context(request: Request) -> dict[str, object]:
        value = request_context(request)
        assert value is not None
        return value.log_fields()

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("private payload must not escape")

    return app


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "request-label",
        "secret@example.test",
        "x" * 1000,
        "00000000-0000-0000-0000-000000000000",
    ],
)
def test_invalid_or_missing_request_identity_is_replaced(value: str | None) -> None:
    response = TestClient(_app()).get("/context", headers={"X-Request-ID": value} if value else {})
    payload = response.json()
    assert UUID(payload["request_id"]).int
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert payload["correlation_id"] == response.headers["X-Correlation-ID"]
    assert payload["request_id"] != value
    assert payload["source_app"] == "API"
    assert payload["actor_type"] == "ANONYMOUS"
    assert payload["causation_id"] is None
    assert current_operation_context() is None


def test_valid_request_id_is_preserved_but_client_correlation_and_origin_are_not_authority() -> (
    None
):
    attempt, correlation = str(uuid4()), str(uuid4())
    response = TestClient(_app()).get(
        "/context",
        headers={
            "X-Request-ID": attempt,
            "X-Correlation-ID": correlation,
            "X-ZeroMerma-Surface": "POS",
        },
    )
    assert response.json()["request_id"] == attempt
    assert response.json()["correlation_id"] != correlation
    assert response.json()["source_app"] == "API"
    duplicated = TestClient(_app()).get(
        "/context",
        headers=[
            ("X-Request-ID", attempt),
            ("X-Request-ID", attempt),
        ],
    )
    assert duplicated.headers["X-Request-ID"] != attempt


def test_unhandled_and_routing_errors_keep_the_same_safe_response_context() -> None:
    client = TestClient(_app(), raise_server_exceptions=False)
    for path, status in (("/failure", 500), ("/missing", 404)):
        response = client.get(path)
        assert response.status_code == status
        assert response.json()["request_id"] == response.headers["X-Request-ID"]
        assert UUID(response.headers["X-Correlation-ID"]).int
        assert "private payload" not in response.text


@pytest.mark.parametrize("allowed_origin", [False, True])
def test_server_error_exposes_trace_ids_only_to_allowed_origins(allowed_origin: bool) -> None:
    settings = ApiSettings(
        _env_file=None,
        environment="test",
        cors_origins=["https://pos.example.test", "https://backoffice.example.test"],
        session_pos_origins=["https://pos.example.test"],
        session_backoffice_origins=["https://backoffice.example.test"],
        allowed_hosts=["testserver"],
    )
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )
    install_security_boundary(app, settings)
    app.add_middleware(OperationContextMiddleware)

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("private payload must not escape")

    attempt = str(uuid4())
    origin = "https://pos.example.test" if allowed_origin else "https://foreign.example.test"
    response = TestClient(app, base_url="https://testserver", raise_server_exceptions=False).get(
        "/failure", headers={"Origin": origin, "X-Request-ID": attempt}
    )
    assert response.status_code == 500
    assert response.json()["request_id"] == response.headers["X-Request-ID"] == attempt
    assert UUID(response.headers["X-Correlation-ID"]).int
    assert "private payload" not in response.text
    assert response.headers["Cache-Control"] == "no-store"
    if allowed_origin:
        assert response.headers["Access-Control-Allow-Origin"] == origin
        assert response.headers["Access-Control-Allow-Credentials"] == "true"
        exposed = {
            name.strip().lower()
            for name in response.headers["Access-Control-Expose-Headers"].split(",")
        }
        assert {"x-request-id", "x-correlation-id"}.issubset(exposed)
        assert "origin" in response.headers["Vary"].lower()
    else:
        assert "Access-Control-Allow-Origin" not in response.headers
        assert "Access-Control-Allow-Credentials" not in response.headers
        assert "Access-Control-Expose-Headers" not in response.headers
    assert current_operation_context() is None


def test_concurrent_requests_publish_from_worker_threads_without_cross_contamination() -> None:
    async def run() -> None:
        app = _app()
        ready = asyncio.Event()
        arrivals = 0

        @app.get("/parallel/{actor_id}")
        async def parallel(actor_id: UUID) -> dict[str, object]:
            nonlocal arrivals
            original = current_operation_context()
            assert original is not None
            await anyio.to_thread.run_sync(
                lambda: publish_operation_context(replace(original, actor_id=actor_id))
            )
            arrivals += 1
            if arrivals == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), 5)
            current = current_operation_context()
            assert current is not None
            return current.log_fields()

        actors = [uuid4(), uuid4()]
        attempts = [str(uuid4()), str(uuid4())]
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as c:
            responses = await asyncio.gather(
                *(
                    c.get(f"/parallel/{actor}", headers={"X-Request-ID": attempt})
                    for actor, attempt in zip(actors, attempts, strict=True)
                )
            )
        for index, response in enumerate(responses):
            assert response.json()["actor_id"] == str(actors[index])
            assert response.json()["request_id"] == attempts[index]
        assert responses[0].headers["X-Correlation-ID"] != responses[1].headers["X-Correlation-ID"]
        assert current_operation_context() is None

    asyncio.run(run())


def test_context_is_immutable_and_logs_only_explicit_safe_fields() -> None:
    context = OperationContext.start(SourceApp.SYSTEM)
    with pytest.raises(FrozenInstanceError):
        context.actor_id = uuid4()  # type: ignore[misc]
    record = logging.LogRecord("context", logging.INFO, __file__, 1, "safe message", (), None)
    record.operation_context = context
    record.payload = {"email": "private@example.test"}
    record.headers = {"Cookie": "private-cookie"}
    value = json.loads(JsonFormatter().format(record))
    assert value["operation_id"] == str(context.operation_id)
    assert value["actor_type"] == "SYSTEM"
    assert "payload" not in value and "headers" not in value
