from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRANCH_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers

ALLOWED_POS_ORIGIN = "http://127.0.0.1:5173"


def _login(client: TestClient) -> dict[str, str]:
    return login_headers(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS")


def _authorization_header(client: TestClient) -> dict[str, str]:
    return _login(client)


def test_login_and_auth_me_return_authenticated_user(client: TestClient) -> None:
    token = _login(client)

    response = client.get(
        "/v1/auth/me",
        headers=token,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == SEED_USER_EMAIL
    assert payload["default_surface"] == "POS"


def test_seeded_admin_can_login_for_backoffice(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/login",
        headers={"Origin": "http://localhost:5174", "X-ZeroMerma-Surface": "BACKOFFICE"},
        json={"email": SEED_ADMIN_EMAIL, "password": SEED_ADMIN_PASSWORD, "audience": "BACKOFFICE"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["audience"] == "BACKOFFICE"
    assert payload["csrf_token"]
    assert payload["user"]["email"] == SEED_ADMIN_EMAIL
    assert payload["user"]["full_name"] == "ZeroMerma Admin"
    assert payload["user"]["default_surface"] == "BACKOFFICE"
    assert "access_token" not in payload
    assert "__Host-zm-backoffice-session" in response.headers["set-cookie"]


def test_login_cors_preflight_allows_supported_local_pos_origin(client: TestClient) -> None:
    response = client.options(
        "/v1/auth/login",
        headers={
            "Origin": ALLOWED_POS_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token,x-zeromerma-surface",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_POS_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
    assert "x-csrf-token" in response.headers["access-control-allow-headers"].lower()
    assert "x-zeromerma-surface" in response.headers["access-control-allow-headers"].lower()


def test_login_response_includes_cors_headers_for_supported_local_pos_origin(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/auth/login",
        headers={"Origin": ALLOWED_POS_ORIGIN, "X-ZeroMerma-Surface": "POS"},
        json={
            "email": SEED_USER_EMAIL,
            "password": SEED_USER_PASSWORD,
            "audience": "POS",
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_POS_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_pos_bootstrap_returns_branch_workstation_and_local_context(client: TestClient) -> None:
    response = client.get(
        f"/v1/pos/bootstrap?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == SEED_USER_EMAIL
    assert payload["branch"]["code"] == SEED_BRANCH_CODE
    assert payload["workstation"]["code"] == SEED_WORKSTATION_CODE
    assert payload["active_cash_session"] is None
    assert datetime.fromisoformat(payload["local_timestamp"]).tzinfo is not None


def test_open_cash_session_writes_audit_and_outbox_and_exposes_current_session(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "aa72f502-17ac-5181-a575-00090f0744a2",
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "150.00",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "OPEN"
    assert Decimal(str(payload["opening_amount"])) == Decimal("150.00")

    current_response = client.get(
        f"/v1/cash-sessions/current?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )
    assert current_response.status_code == 200
    assert current_response.json()["id"] == payload["id"]
    assert current_response.json()["workstation_code"] == SEED_WORKSTATION_CODE
    assert current_response.json()["user_email"] == SEED_USER_EMAIL

    with SessionLocal() as session:
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.action == "cash_session.opened")
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.event_name == "cash.session.opened.v1")
        ).scalar_one()

    assert audit_record.action == "cash_session.opened"
    assert audit_record.request_id == "aa72f502-17ac-5181-a575-00090f0744a2"
    assert audit_record.metadata_["workstation_code"] == SEED_WORKSTATION_CODE
    assert outbox_event.event_name == "cash.session.opened.v1"
    assert outbox_event.payload["cash_session_id"] == payload["id"]


def test_opening_second_session_for_same_workstation_is_rejected(client: TestClient) -> None:
    headers = _authorization_header(client)
    first_response = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "100.00",
        },
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "80.00",
        },
    )

    assert second_response.status_code == 409
    assert "already has an open cash session" in second_response.json()["message"]


def test_opening_second_session_for_same_user_on_another_workstation_is_rejected(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).scalar_one()
        session.add(
            Workstation(
                branch_id=branch.id,
                code="POS-02",
                name="Front Register 02",
                is_active=True,
            )
        )
        session.commit()

    headers = _authorization_header(client)
    first_response = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "120.00",
        },
    )
    assert first_response.status_code == 201

    second_station_headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code="POS-02",
    )
    second_response = client.post(
        "/v1/cash-sessions/open",
        headers={**second_station_headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": "POS-02",
            "opening_amount": "90.00",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["message"] == "User already has an open cash session."
