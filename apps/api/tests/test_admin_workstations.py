from __future__ import annotations

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
    SEED_WORKSTATION_NAME,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers


def _login_admin(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_ADMIN_EMAIL, "password": SEED_ADMIN_PASSWORD},
    )

    assert response.status_code == 200
    return str(response.json()["access_token"])


def _login_cashier(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
    )

    assert response.status_code == 200
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    return owner_headers()


def _get_branch_id(code: str) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
        return str(branch.id)


def _get_workstation_id(code: str) -> str:
    with SessionLocal() as session:
        workstation = session.execute(
            select(Workstation).where(Workstation.code == code)
        ).scalar_one()
        return str(workstation.id)


def test_admin_workstations_list_returns_seeded_stations_and_metrics(client: TestClient) -> None:
    response = client.get("/v1/admin/workstations", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    codes = {item["code"] for item in payload["items"]}
    assert SEED_WORKSTATION_CODE in codes
    assert payload["total"] >= 3
    assert payload["is_backend_connected"] is True
    assert payload["metrics"]["total_workstations"] >= 3
    assert payload["metrics"]["active_workstations"] >= 3
    assert payload["metrics"]["with_open_cash_session"] == 0
    assert payload["filter_options"]["branches"]


def test_admin_workstations_reject_pos_surface_user(client: TestClient) -> None:
    response = client.get(
        "/v1/admin/workstations",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )

    assert response.status_code == 403


def test_admin_workstations_filters_by_branch_status_cash_state_and_search(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    branch_id = _get_branch_id(SEED_BRANCH_CODE)

    search_response = client.get("/v1/admin/workstations?search=pos-01", headers=headers)
    assert search_response.status_code == 200
    assert [item["code"] for item in search_response.json()["items"]] == [SEED_WORKSTATION_CODE]

    branch_response = client.get(f"/v1/admin/workstations?branch_id={branch_id}", headers=headers)
    assert branch_response.status_code == 200
    assert branch_response.json()["items"]
    assert all(item["branch_id"] == branch_id for item in branch_response.json()["items"])

    status_response = client.get("/v1/admin/workstations?status=active", headers=headers)
    assert status_response.status_code == 200
    assert status_response.json()["items"]
    assert all(item["status"] == "active" for item in status_response.json()["items"])

    no_recent_response = client.get(
        "/v1/admin/workstations?cash_session_state=no_recent_session",
        headers=headers,
    )
    assert no_recent_response.status_code == 200
    assert no_recent_response.json()["items"]
    assert all(not item["has_active_cash_session"] for item in no_recent_response.json()["items"])


def test_admin_workstation_detail_includes_branch_access_and_cash_context(
    client: TestClient,
) -> None:
    workstation_id = _get_workstation_id(SEED_WORKSTATION_CODE)
    response = client.get(
        f"/v1/admin/workstations/{workstation_id}",
        headers=_admin_headers(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["id"] == workstation_id
    assert payload["overview"]["code"] == SEED_WORKSTATION_CODE
    assert payload["overview"]["name"] == SEED_WORKSTATION_NAME
    assert payload["branch_relationship"]["branch_code"] == SEED_BRANCH_CODE
    assert payload["access_context"]["active_assigned_user_count"] >= 1
    assert payload["cash_session_context"]["active_session"] is None


def test_admin_workstation_create_persists_and_writes_audit_and_outbox(
    client: TestClient,
) -> None:
    branch_id = _get_branch_id(SEED_BRANCH_CODE)
    response = client.post(
        "/v1/admin/workstations",
        headers={**_admin_headers(client), "X-Request-ID": "admin-workstation-create-test"},
        json={
            "branch_id": branch_id,
            "code": "POS-CENTRO-02",
            "name": "Centro Register 02",
            "is_active": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["overview"]["code"] == "POS-CENTRO-02"
    assert payload["branch_relationship"]["branch_code"] == SEED_BRANCH_CODE

    with SessionLocal() as session:
        workstation = session.execute(
            select(Workstation).where(Workstation.code == "POS-CENTRO-02"),
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(workstation.id)),
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(workstation.id)),
        ).scalar_one()

    assert audit_record.action == "admin.workstation.created"
    assert audit_record.request_id == "admin-workstation-create-test"
    assert outbox_event.event_name == "admin.workstation.created.v1"


def test_admin_workstation_create_validates_required_unique_code_and_branch(
    client: TestClient,
) -> None:
    branch_id = _get_branch_id(SEED_BRANCH_CODE)
    headers = _admin_headers(client)

    duplicate_response = client.post(
        "/v1/admin/workstations",
        headers=headers,
        json={
            "branch_id": branch_id,
            "code": SEED_WORKSTATION_CODE,
            "name": "Duplicate",
        },
    )
    assert duplicate_response.status_code == 400

    branch_response = client.post(
        "/v1/admin/workstations",
        headers=headers,
        json={
            "branch_id": "00000000-0000-0000-0000-000000000000",
            "code": "POS-NO-BRANCH",
            "name": "No Branch",
        },
    )
    assert branch_response.status_code == 404


def test_admin_workstation_update_and_activation_flow(client: TestClient) -> None:
    workstation_id = _get_workstation_id(SEED_WORKSTATION_CODE)
    headers = _admin_headers(client)

    update_response = client.patch(
        f"/v1/admin/workstations/{workstation_id}",
        headers={**headers, "X-Request-ID": "admin-workstation-update-test"},
        json={"name": "Front Register 01 Updated"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["overview"]["name"] == "Front Register 01 Updated"

    deactivate_response = client.patch(
        f"/v1/admin/workstations/{workstation_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["overview"]["status"] == "inactive"
    assert deactivate_response.json()["available_actions"]["can_activate"] is True

    activate_response = client.patch(
        f"/v1/admin/workstations/{workstation_id}",
        headers=headers,
        json={"is_active": True},
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["overview"]["status"] == "active"


def test_admin_workstation_deactivation_blocks_open_cash_session(client: TestClient) -> None:
    workstation_id = _get_workstation_id(SEED_WORKSTATION_CODE)
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).scalar_one()
        workstation = session.execute(
            select(Workstation).where(Workstation.code == SEED_WORKSTATION_CODE),
        ).scalar_one()
        user = session.execute(select(User).where(User.email == SEED_ADMIN_EMAIL)).scalar_one()
        session.add(
            CashSession(
                branch_id=branch.id,
                workstation_id=workstation.id,
                user_id=user.id,
                opening_amount=Decimal("100.00"),
            ),
        )
        session.commit()

    response = client.patch(
        f"/v1/admin/workstations/{workstation_id}",
        headers=_admin_headers(client),
        json={"is_active": False},
    )

    assert response.status_code == 409
    assert "open cash session" in response.json()["message"]
