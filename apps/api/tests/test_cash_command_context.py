"""Cash references are authorized before idempotency foreign keys are reserved."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument
from zeromerma_api.modules.sales.infrastructure.models import CashMovement
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers
from zeromerma_api.testing.transfer_operators import transfer_cashier_email


def _login(client: TestClient, workstation: str = SEED_WORKSTATION_CODE) -> dict[str, str]:
    return login_headers(
        client,
        email=(
            SEED_USER_EMAIL
            if workstation == SEED_WORKSTATION_CODE
            else transfer_cashier_email(workstation)
        ),
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=workstation,
    )


def _open(client: TestClient, headers: dict[str, str], workstation: str) -> str:
    response = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": workstation, "opening_amount": "100.00"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _command(kind: str, cash_id: str) -> tuple[str, dict[str, Any]]:
    with SessionLocal() as session:
        product_id = session.scalars(
            select(Product.id).where(Product.code == SEED_PRODUCT_CONCHA_VAN_CODE)
        ).one()
        destination = session.scalars(
            select(Workstation.branch_id).where(
                Workstation.code == SEED_DESTINATION_WORKSTATION_CODE
            )
        ).one()
    body: dict[str, Any] = {
        "workstation_code": SEED_WORKSTATION_CODE,
        "cash_session_id": cash_id,
        "lines": [{"product_id": str(product_id), "quantity": "1.000"}],
    }
    if kind == "transfer":
        return "/v1/transfers/dispatch/commit", {
            **body,
            "destination_branch_id": str(destination),
        }
    return "/v1/operations/counter-transfer/commit", body


def _effects() -> tuple[int, ...]:
    with SessionLocal() as session:
        return tuple(
            int(session.scalar(select(func.count()).select_from(model)) or 0)
            for model in (OperationDocument, CashMovement, IdempotencyRecord)
        )


def _assert_unused_key(key: str) -> None:
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(IdempotencyRecord.id).where(IdempotencyRecord.idempotency_key == UUID(key))
            )
            is None
        )


@pytest.mark.parametrize("kind", ["counter", "transfer"])
def test_new_command_rejects_missing_cash_before_reservation(client: TestClient, kind: str) -> None:
    headers = _login(client)
    cash_id = _open(client, headers, SEED_WORKSTATION_CODE)
    path, body = _command(kind, cash_id)
    key = new_idempotency_key()
    before = _effects()
    rejected = client.post(
        path,
        headers={**headers, "Idempotency-Key": key},
        json={**body, "cash_session_id": str(uuid4())},
    )
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "CASH_SESSION_NOT_FOUND"
    assert _effects() == before
    _assert_unused_key(key)
    admitted = client.post(path, headers={**headers, "Idempotency-Key": key}, json=body)
    assert admitted.status_code == 201, admitted.text


@pytest.mark.parametrize("kind", ["counter", "transfer"])
def test_new_command_rejects_other_cash_owner_and_station_before_reservation(
    client: TestClient, kind: str
) -> None:
    headers = _login(client)
    cash_id = _open(client, headers, SEED_WORKSTATION_CODE)
    foreign_headers = _login(client, SEED_DESTINATION_WORKSTATION_CODE)
    foreign_cash = _open(client, foreign_headers, SEED_DESTINATION_WORKSTATION_CODE)
    path, body = _command(kind, cash_id)
    key = new_idempotency_key()
    before = _effects()
    rejected = client.post(
        path,
        headers={**headers, "Idempotency-Key": key},
        json={**body, "cash_session_id": foreign_cash},
    )
    assert rejected.status_code == 403, rejected.text
    assert rejected.json()["code"] == "FORBIDDEN"
    assert _effects() == before
    _assert_unused_key(key)


def test_cash_reference_validation_preserves_closed_replay_and_key_mismatch(
    client: TestClient,
) -> None:
    headers = _login(client)
    cash_id = _open(client, headers, SEED_WORKSTATION_CODE)
    key = new_idempotency_key()
    body = {
        "workstation_code": SEED_WORKSTATION_CODE,
        "cash_session_id": cash_id,
        "payee_name": "Test supplier",
        "concept": "Test payment",
        "payment_method_code": "CASH",
        "total_amount": "10.00",
    }
    committed = client.post("/v1/payments", headers={**headers, "Idempotency-Key": key}, json=body)
    assert committed.status_code == 201, committed.text
    closed = client.post(
        "/v1/cash-close/commit",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "cash_session_id": cash_id,
            "close_mode": "WITH_COUNT",
            "counter_empty_confirmed": True,
            "counted_payment_methods": [{"payment_method_code": "CASH", "counted_amount": "90.00"}],
        },
    )
    assert closed.status_code == 200, closed.text
    fresh = _login(client)
    before = _effects()
    replay = client.post("/v1/payments", headers={**fresh, "Idempotency-Key": key}, json=body)
    recovered = client.get(
        f"/v1/payments/confirmations/{key}",
        headers=fresh,
        params={"workstation_code": SEED_WORKSTATION_CODE, "cash_session_id": cash_id},
    )
    assert replay.status_code == 201, replay.text
    assert recovered.status_code == 200, recovered.text
    assert committed.json() == replay.json() == recovered.json()
    mismatch = client.post(
        "/v1/payments",
        headers={**fresh, "Idempotency-Key": key},
        json={**body, "cash_session_id": str(uuid4())},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    new_key = new_idempotency_key()
    new_command = client.post(
        "/v1/payments", headers={**fresh, "Idempotency-Key": new_key}, json=body
    )
    assert new_command.status_code == 409
    assert new_command.json()["code"] == "CASH_SESSION_CLOSED"
    _assert_unused_key(new_key)
    assert _effects() == before
