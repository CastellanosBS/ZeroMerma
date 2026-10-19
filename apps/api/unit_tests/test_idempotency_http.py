from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from zeromerma_api.modules.idempotency.application.schemas import IdempotencyResult
from zeromerma_api.modules.idempotency.domain.constants import IdempotencyStatus
from zeromerma_api.modules.idempotency.domain.exceptions import (
    IdempotencyInProgress,
    IdempotencyResultUnknown,
)
from zeromerma_api.modules.idempotency.presentation.http import (
    idempotency_response,
    install_idempotency_error_handler,
)
from zeromerma_api.presentation.operation_context import OperationContextMiddleware


@pytest.mark.parametrize("status_code", [204, 205])
def test_empty_http_statuses_have_no_body_on_first_result_or_replay(status_code: int) -> None:
    request = Request({"type": "http", "headers": []})
    for replayed in (False, True):
        result = IdempotencyResult(
            uuid4(),
            IdempotencyStatus.COMPLETED,
            status_code,
            {"resource_id": str(uuid4())},
            replayed,
        )
        response = idempotency_response(result, request)
        assert response.status_code == status_code
        assert response.body == b""
        assert response.headers["Idempotency-Replayed"] == str(replayed).lower()


@pytest.mark.parametrize("unknown", [False, True])
def test_temporary_contention_and_unknown_external_outcome_have_distinct_http_advice(
    unknown: bool,
) -> None:
    app = FastAPI()
    install_idempotency_error_handler(app)
    app.add_middleware(OperationContextMiddleware)

    @app.post("/command")
    def command() -> None:
        raise IdempotencyResultUnknown() if unknown else IdempotencyInProgress()

    with TestClient(app) as client:
        response = client.post(
            "/command", headers={"X-Request-ID": "c43d8ec5-1af1-4e1b-9b29-011071580488"}
        )
    assert response.status_code == 409
    assert response.json()["request_id"] == "c43d8ec5-1af1-4e1b-9b29-011071580488"
    assert response.json()["code"] == (
        "IDEMPOTENCY_RESULT_UNKNOWN" if unknown else "IDEMPOTENCY_IN_PROGRESS"
    )
    assert response.headers["Cache-Control"] == "no-store"
    assert ("Retry-After" in response.headers) is not unknown
