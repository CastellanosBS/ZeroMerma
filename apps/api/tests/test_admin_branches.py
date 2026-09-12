from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRANCH_CODE,
    SEED_BRANCH_NAME,
    SEED_BRAND_EL_MEJOR_PAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch, Brand, Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


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
    return {"Authorization": f"Bearer {_login_admin(client)}"}


def _get_brand_id(code: str) -> str:
    with SessionLocal() as session:
        brand = session.execute(select(Brand).where(Brand.code == code)).scalar_one()
        return str(brand.id)


def _get_branch_id(code: str) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
        return str(branch.id)


def test_admin_branches_list_returns_seeded_branches_and_metrics(client: TestClient) -> None:
    response = client.get("/v1/admin/branches", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    codes = {item["code"] for item in payload["items"]}
    assert SEED_BRANCH_CODE in codes
    assert payload["total"] >= 3
    assert payload["is_backend_connected"] is True
    assert payload["metrics"]["total_branches"] >= 3
    assert payload["metrics"]["active_branches"] >= 3
    assert payload["metrics"]["with_workstations"] >= 3
    assert payload["filter_options"]["brands"]


def test_admin_branches_reject_pos_surface_user(client: TestClient) -> None:
    response = client.get(
        "/v1/admin/branches",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )

    assert response.status_code == 403


def test_admin_branches_filters_by_search_brand_and_active_workstations(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    brand_id = _get_brand_id(SEED_BRAND_EL_MEJOR_PAN_CODE)

    search_response = client.get("/v1/admin/branches?search=main", headers=headers)
    assert search_response.status_code == 200
    assert [item["code"] for item in search_response.json()["items"]] == [SEED_BRANCH_CODE]

    brand_response = client.get(f"/v1/admin/branches?brand_id={brand_id}", headers=headers)
    assert brand_response.status_code == 200
    assert brand_response.json()["items"]
    assert all(item["brand_id"] == brand_id for item in brand_response.json()["items"])

    active_workstations_response = client.get(
        "/v1/admin/branches?has_active_workstations=yes",
        headers=headers,
    )
    assert active_workstations_response.status_code == 200
    assert active_workstations_response.json()["items"]
    assert all(
        item["active_workstation_count"] > 0
        for item in active_workstations_response.json()["items"]
    )


def test_admin_branch_detail_includes_workstations_assignments_and_warnings(
    client: TestClient,
) -> None:
    branch_id = _get_branch_id(SEED_BRANCH_CODE)
    response = client.get(f"/v1/admin/branches/{branch_id}", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["id"] == branch_id
    assert payload["overview"]["code"] == SEED_BRANCH_CODE
    assert payload["overview"]["name"] == SEED_BRANCH_NAME
    assert payload["workstations_summary"]["total"] >= 1
    assert payload["workstations_summary"]["active"] >= 1
    assert payload["user_assignments_summary"]["active"] >= 1
    assert payload["related_operations_summary"]["open_cash_sessions"] == 0


def test_admin_branch_create_persists_branch_and_writes_audit_and_outbox(
    client: TestClient,
) -> None:
    brand_id = _get_brand_id(SEED_BRAND_EL_MEJOR_PAN_CODE)
    response = client.post(
        "/v1/admin/branches",
        headers={**_admin_headers(client), "X-Request-ID": "admin-branch-create-test"},
        json={
            "brand_id": brand_id,
            "code": "CENTRO",
            "name": "Sucursal Centro",
            "timezone": "America/Hermosillo",
            "is_active": True,
            "address_line": "Calle Principal 100",
            "city": "Hermosillo",
            "state": "Sonora",
            "country": "Mexico",
            "phone": "6620000000",
            "contact_email": "centro@example.com",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["overview"]["code"] == "CENTRO"
    assert payload["location_contact"]["city"] == "Hermosillo"
    assert payload["warnings"]

    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == "CENTRO")).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(branch.id)),
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(branch.id)),
        ).scalar_one()

    assert audit_record.action == "admin.branch.created"
    assert audit_record.request_id == "admin-branch-create-test"
    assert outbox_event.event_name == "admin.branch.created.v1"


def test_admin_branch_create_validates_required_unique_code_and_timezone(
    client: TestClient,
) -> None:
    brand_id = _get_brand_id(SEED_BRAND_EL_MEJOR_PAN_CODE)
    headers = _admin_headers(client)

    duplicate_response = client.post(
        "/v1/admin/branches",
        headers=headers,
        json={
            "brand_id": brand_id,
            "code": SEED_BRANCH_CODE,
            "name": "Duplicate",
            "timezone": "America/Hermosillo",
        },
    )
    assert duplicate_response.status_code == 400

    timezone_response = client.post(
        "/v1/admin/branches",
        headers=headers,
        json={
            "brand_id": brand_id,
            "code": "TZ-BAD",
            "name": "Bad Timezone",
            "timezone": "Not/AZone",
        },
    )
    assert timezone_response.status_code == 400


def test_admin_branch_update_and_deactivation_flow(client: TestClient) -> None:
    branch_id = _get_branch_id(SEED_BRANCH_CODE)
    headers = _admin_headers(client)

    update_response = client.patch(
        f"/v1/admin/branches/{branch_id}",
        headers={**headers, "X-Request-ID": "admin-branch-update-test"},
        json={"name": "Main Branch Updated", "city": "Hermosillo"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["overview"]["name"] == "Main Branch Updated"
    assert update_response.json()["location_contact"]["city"] == "Hermosillo"

    deactivate_response = client.patch(
        f"/v1/admin/branches/{branch_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["overview"]["status"] == "inactive"

    activate_response = client.patch(
        f"/v1/admin/branches/{branch_id}",
        headers=headers,
        json={"is_active": True},
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["overview"]["status"] == "active"


def test_admin_branch_deactivation_blocks_open_cash_session(client: TestClient) -> None:
    branch_id = _get_branch_id(SEED_BRANCH_CODE)
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
        f"/v1/admin/branches/{branch_id}",
        headers=_admin_headers(client),
        json={"is_active": False},
    )

    assert response.status_code == 409
    assert "open cash sessions" in response.json()["message"]
