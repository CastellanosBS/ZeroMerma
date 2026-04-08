from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_BRANCH_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent

ALLOWED_POS_ORIGIN = "http://127.0.0.1:5173"


def _login(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == SEED_USER_EMAIL
    return str(payload["access_token"])


def _authorization_header(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client)}"}


def test_login_and_auth_me_return_authenticated_user(client: TestClient) -> None:
    token = _login(client)

    response = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == SEED_USER_EMAIL


def test_login_cors_preflight_allows_supported_local_pos_origin(client: TestClient) -> None:
    response = client.options(
        "/v1/auth/login",
        headers={
            "Origin": ALLOWED_POS_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_POS_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_login_response_includes_cors_headers_for_supported_local_pos_origin(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/auth/login",
        headers={"Origin": ALLOWED_POS_ORIGIN},
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
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
            "X-Request-ID": "phase-1a-open-session",
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
    assert payload["workstation_code"] == SEED_WORKSTATION_CODE
    assert payload["user_email"] == SEED_USER_EMAIL

    current_response = client.get(
        f"/v1/cash-sessions/current?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )
    assert current_response.status_code == 200
    assert current_response.json()["id"] == payload["id"]

    with SessionLocal() as session:
        audit_record = session.execute(select(AuditLog)).scalar_one()
        outbox_event = session.execute(select(OutboxEvent)).scalar_one()

    assert audit_record.action == "cash_session.opened"
    assert audit_record.request_id == "phase-1a-open-session"
    assert audit_record.metadata_["workstation_code"] == SEED_WORKSTATION_CODE
    assert outbox_event.event_name == "cash.session.opened.v1"
    assert outbox_event.payload["cash_session_id"] == payload["id"]


def test_opening_second_session_for_same_workstation_is_rejected(client: TestClient) -> None:
    headers = _authorization_header(client)
    first_response = client.post(
        "/v1/cash-sessions/open",
        headers=headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "100.00",
        },
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/v1/cash-sessions/open",
        headers=headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "80.00",
        },
    )

    assert second_response.status_code == 409
    assert "already has an open cash session" in second_response.json()["detail"]


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
        headers=headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "120.00",
        },
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/v1/cash-sessions/open",
        headers=headers,
        json={
            "workstation_code": "POS-02",
            "opening_amount": "90.00",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "User already has an open cash session."
