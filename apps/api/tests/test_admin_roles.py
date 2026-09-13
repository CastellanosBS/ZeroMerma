from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.identity.domain.constants import (
    IDENTITY_ROLE_ADMIN,
    IDENTITY_ROLE_CASHIER,
    IDENTITY_SURFACE_BACKOFFICE,
    IDENTITY_SURFACE_POS,
)
from zeromerma_api.modules.identity.infrastructure.models import Role, User, UserRoleAssignment
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers


def _login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    return owner_headers()


def _cashier_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def _role_id(code: str) -> str:
    with SessionLocal() as session:
        role = session.execute(select(Role).where(Role.code == code)).scalar_one()
        return str(role.id)


def _user_id(email: str) -> str:
    with SessionLocal() as session:
        user = session.execute(select(User).where(User.email == email)).scalar_one()
        return str(user.id)


def test_admin_roles_list_permissions_metrics_and_contract(client: TestClient) -> None:
    response = client.get("/v1/admin/roles", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    codes = {item["code"] for item in payload["items"]}
    assert IDENTITY_ROLE_ADMIN in codes
    assert IDENTITY_ROLE_CASHIER in codes
    assert payload["backend_contract"]["scoped_roles_supported"] is True
    assert payload["backend_contract"]["destructive_delete_supported"] is False
    assert payload["metrics"]["total_roles"] >= 3
    assert payload["metrics"]["high_privilege"] >= 1
    assert payload["filter_options"]["permission_modules"]

    permissions_response = client.get("/v1/admin/roles/permissions", headers=_admin_headers(client))
    assert permissions_response.status_code == 200
    permissions_payload = permissions_response.json()
    assert any(group["permissions"] for group in permissions_payload["groups"])
    assert "roles.manage" in permissions_payload["sensitive_permission_codes"]


def test_admin_roles_rejects_pos_only_user(client: TestClient) -> None:
    response = client.get("/v1/admin/roles", headers=_cashier_headers(client))

    assert response.status_code == 403


def test_admin_roles_filter_and_detail(client: TestClient) -> None:
    headers = _admin_headers(client)
    admin_role_id = _role_id(IDENTITY_ROLE_ADMIN)

    surface_response = client.get("/v1/admin/roles?app_surface=BACKOFFICE", headers=headers)
    assert surface_response.status_code == 200
    assert all(
        IDENTITY_SURFACE_BACKOFFICE in item["surfaces"] for item in surface_response.json()["items"]
    )

    high_response = client.get("/v1/admin/roles?high_privilege=yes", headers=headers)
    assert high_response.status_code == 200
    assert all(item["is_high_privilege"] for item in high_response.json()["items"])

    detail_response = client.get(f"/v1/admin/roles/{admin_role_id}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["overview"]["code"] == IDENTITY_ROLE_ADMIN
    assert detail["permission_matrix"]
    assert detail["sensitive_permissions"]
    assert detail["assigned_users"]
    assert detail["scopes"]["is_supported"] is True


def test_admin_role_create_update_status_audit_and_outbox(client: TestClient) -> None:
    headers = _admin_headers(client)

    create_response = client.post(
        "/v1/admin/roles",
        headers={**headers, "X-Request-ID": "role-create-test"},
        json={
            "code": "cash_auditor",
            "name": "Auditor de caja",
            "description": "Consulta cortes y auditoria financiera.",
            "surfaces": [IDENTITY_SURFACE_BACKOFFICE],
            "permission_codes": ["cash_finance.view", "audit.view"],
            "confirmed_high_risk_change": True,
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    role_id = payload["overview"]["id"]
    assert payload["overview"]["is_high_privilege"] is True
    assert payload["available_actions"]["can_edit"] is True

    update_without_confirmation = client.patch(
        f"/v1/admin/roles/{role_id}",
        headers=headers,
        json={"permission_codes": ["cash_finance.view", "roles.manage"]},
    )
    assert update_without_confirmation.status_code == 409

    update_response = client.patch(
        f"/v1/admin/roles/{role_id}",
        headers=headers,
        json={
            "name": "Auditor financiero",
            "permission_codes": ["cash_finance.view", "roles.manage"],
            "confirmed_high_risk_change": True,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["overview"]["name"] == "Auditor financiero"

    deactivate_response = client.post(
        f"/v1/admin/roles/{role_id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["overview"]["status"] == "inactive"

    with SessionLocal() as session:
        audit_events = (
            session.execute(select(AuditLog).where(AuditLog.resource_id == role_id)).scalars().all()
        )
        outbox_events = (
            session.execute(select(OutboxEvent).where(OutboxEvent.aggregate_id == role_id))
            .scalars()
            .all()
        )

    assert {event.action for event in audit_events} >= {
        "admin.role.created",
        "admin.role.updated",
        "admin.role.status_changed",
    }
    assert any(event.event_name == "admin.role.created.v1" for event in outbox_events)


def test_admin_role_validations_and_system_role_safety(client: TestClient) -> None:
    headers = _admin_headers(client)
    admin_role_id = _role_id(IDENTITY_ROLE_ADMIN)

    duplicate_response = client.post(
        "/v1/admin/roles",
        headers=headers,
        json={
            "code": IDENTITY_ROLE_ADMIN,
            "name": "Duplicate admin",
            "surfaces": [IDENTITY_SURFACE_BACKOFFICE],
            "permission_codes": ["audit.view"],
            "confirmed_high_risk_change": True,
        },
    )
    assert duplicate_response.status_code == 400

    invalid_permission_response = client.post(
        "/v1/admin/roles",
        headers=headers,
        json={
            "code": "invalid_permission",
            "name": "Invalid permission",
            "surfaces": [IDENTITY_SURFACE_BACKOFFICE],
            "permission_codes": ["not.real"],
        },
    )
    assert invalid_permission_response.status_code == 400

    system_update_response = client.patch(
        f"/v1/admin/roles/{admin_role_id}",
        headers=headers,
        json={"name": "Renamed system admin"},
    )
    assert system_update_response.status_code == 409

    system_status_response = client.post(
        f"/v1/admin/roles/{admin_role_id}/status",
        headers=headers,
        json={"is_active": False, "confirmed_high_risk_change": True},
    )
    assert system_status_response.status_code == 409


def test_admin_role_user_assignment_flow_and_user_module_integration(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    role_response = client.post(
        "/v1/admin/roles",
        headers=headers,
        json={
            "code": "pos_helper",
            "name": "Auxiliar POS",
            "surfaces": [IDENTITY_SURFACE_POS],
            "permission_codes": ["pos.operate"],
            "confirmed_high_risk_change": True,
        },
    )
    assert role_response.status_code == 201
    role_id = role_response.json()["overview"]["id"]
    user_id = _user_id(SEED_USER_EMAIL)

    assign_response = client.post(
        f"/v1/admin/roles/{role_id}/users/{user_id}",
        headers=headers,
        json={"scope_type": "GLOBAL", "branch_ids": []},
    )
    assert assign_response.status_code == 200
    assert any(user["user_id"] == user_id for user in assign_response.json()["assigned_users"])

    user_detail_response = client.get(f"/v1/admin/users/{user_id}", headers=headers)
    assert user_detail_response.status_code == 200
    assert user_detail_response.json()["role_assignments"]["is_supported"] is True
    assert any(
        role["role_id"] == role_id
        for role in user_detail_response.json()["role_assignments"]["items"]
    )

    user_list_response = client.get(f"/v1/admin/users?role_id={role_id}", headers=headers)
    assert user_list_response.status_code == 200
    assert [item["id"] for item in user_list_response.json()["items"]] == [user_id]

    remove_response = client.post(
        f"/v1/admin/roles/{role_id}/users/{user_id}/remove",
        headers=headers,
    )
    assert remove_response.status_code == 200
    assert not any(user["user_id"] == user_id for user in remove_response.json()["assigned_users"])

    with SessionLocal() as session:
        assignment = session.execute(
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role_id == role_id,
            )
        ).scalar_one()
    assert assignment.is_active is False
