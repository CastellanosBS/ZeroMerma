from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRANCH_CODE,
    SEED_DESTINATION_BRANCH_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.domain.constants import (
    IDENTITY_SURFACE_BACKOFFICE,
    IDENTITY_SURFACE_POS,
)
from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


def _login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_ADMIN_EMAIL, password=SEED_ADMIN_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def _cashier_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def _get_branch_id(code: str = SEED_BRANCH_CODE) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
        return str(branch.id)


def _get_user_id(email: str) -> str:
    with SessionLocal() as session:
        user = session.execute(select(User).where(User.email == email)).scalar_one()
        return str(user.id)


def test_admin_users_list_returns_seeded_users_metrics_and_contract(client: TestClient) -> None:
    response = client.get("/v1/admin/users", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    emails = {item["email"] for item in payload["items"]}
    assert SEED_ADMIN_EMAIL in emails
    assert SEED_USER_EMAIL in emails
    assert payload["is_backend_connected"] is True
    assert payload["backend_contract"]["role_assignment_supported"] is True
    assert payload["backend_contract"]["password_reset_supported"] is False
    assert payload["metrics"]["total_users"] >= 2
    assert payload["metrics"]["pos_users"] >= 1
    assert payload["metrics"]["backoffice_users"] >= 1
    assert payload["filter_options"]["branches"]


def test_admin_users_rejects_pos_only_user(client: TestClient) -> None:
    response = client.get("/v1/admin/users", headers=_cashier_headers(client))

    assert response.status_code == 403


def test_admin_users_filter_by_status_app_access_branch_and_search(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    branch_id = _get_branch_id()

    search_response = client.get("/v1/admin/users?search=admin", headers=headers)
    assert search_response.status_code == 200
    assert [item["email"] for item in search_response.json()["items"]] == [SEED_ADMIN_EMAIL]

    app_access_response = client.get("/v1/admin/users?app_access=POS", headers=headers)
    assert app_access_response.status_code == 200
    assert all(
        IDENTITY_SURFACE_POS in item["allowed_surfaces"]
        for item in app_access_response.json()["items"]
    )

    branch_response = client.get(f"/v1/admin/users?branch_id={branch_id}", headers=headers)
    assert branch_response.status_code == 200
    assert branch_response.json()["items"]
    assert all(item["branch_count"] > 0 for item in branch_response.json()["items"])


def test_admin_user_create_persists_access_branches_audit_and_outbox(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    branch_id = _get_branch_id()

    response = client.post(
        "/v1/admin/users",
        headers={**headers, "X-Request-ID": "admin-user-create-test"},
        json={
            "full_name": "Backoffice Cash User",
            "email": "backoffice-cash-user@zeromerma.local",
            "temporary_password": "TempUser123!",
            "allowed_surfaces": [IDENTITY_SURFACE_POS, IDENTITY_SURFACE_BACKOFFICE],
            "default_surface": IDENTITY_SURFACE_BACKOFFICE,
            "branch_assignments": [{"branch_id": branch_id, "is_default": True}],
            "notes": "Created by admin user test",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["overview"]["email"] == "backoffice-cash-user@zeromerma.local"
    assert payload["app_access"]["has_both_surfaces"] is True
    assert payload["branch_assignments"][0]["branch_id"] == branch_id
    assert payload["role_assignments"]["is_supported"] is True
    assert "password_hash" not in str(payload)

    with SessionLocal() as session:
        user = session.execute(
            select(User).where(User.email == "backoffice-cash-user@zeromerma.local")
        ).scalar_one()
        assignment = session.execute(
            select(UserBranchAssignment).where(UserBranchAssignment.user_id == user.id)
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(user.id))
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(user.id))
        ).scalar_one()

    assert assignment.is_default is True
    assert audit_record.action == "admin.user.created"
    assert audit_record.request_id == "admin-user-create-test"
    assert outbox_event.event_name == "admin.user.created.v1"


def test_admin_user_create_validates_email_pos_branch_and_missing_contracts(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    branch_id = _get_branch_id()

    invalid_email_response = client.post(
        "/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Invalid Email",
            "email": "not-email",
            "temporary_password": "TempUser123!",
            "allowed_surfaces": [IDENTITY_SURFACE_BACKOFFICE],
        },
    )
    assert invalid_email_response.status_code == 422

    duplicate_response = client.post(
        "/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Duplicate Admin",
            "email": SEED_ADMIN_EMAIL,
            "temporary_password": "TempUser123!",
            "allowed_surfaces": [IDENTITY_SURFACE_BACKOFFICE],
        },
    )
    assert duplicate_response.status_code == 400

    pos_without_branch_response = client.post(
        "/v1/admin/users",
        headers=headers,
        json={
            "full_name": "POS Without Branch",
            "email": "pos-without-branch@zeromerma.local",
            "temporary_password": "TempUser123!",
            "allowed_surfaces": [IDENTITY_SURFACE_POS],
        },
    )
    assert pos_without_branch_response.status_code == 400

    invite_response = client.post(
        "/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Invite Unsupported",
            "email": "invite-unsupported@zeromerma.local",
            "allowed_surfaces": [IDENTITY_SURFACE_POS],
            "branch_assignments": [{"branch_id": branch_id}],
            "send_invitation": True,
        },
    )
    assert invite_response.status_code == 400

    role_response = client.post(
        "/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Role Unsupported",
            "email": "role-unsupported@zeromerma.local",
            "temporary_password": "TempUser123!",
            "allowed_surfaces": [IDENTITY_SURFACE_BACKOFFICE],
            "role_ids": ["admin"],
        },
    )
    assert role_response.status_code == 400


def test_admin_user_detail_update_status_and_lock_flow(client: TestClient) -> None:
    headers = _admin_headers(client)
    branch_id = _get_branch_id()
    create_response = client.post(
        "/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Security Flow User",
            "email": "security-flow@zeromerma.local",
            "temporary_password": "TempUser123!",
            "allowed_surfaces": [IDENTITY_SURFACE_POS],
            "branch_assignments": [{"branch_id": branch_id, "is_default": True}],
        },
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["overview"]["id"]

    detail_response = client.get(f"/v1/admin/users/{user_id}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["audit_timeline"]

    update_response = client.patch(
        f"/v1/admin/users/{user_id}",
        headers=headers,
        json={
            "full_name": "Security Flow User Updated",
            "phone": "6620000000",
            "notes": "Updated safe profile fields",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["profile"]["phone"] == "6620000000"

    deactivate_response = client.post(
        f"/v1/admin/users/{user_id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["overview"]["status"] == "inactive"
    assert client.post(
        "/v1/auth/login",
        json={"email": "security-flow@zeromerma.local", "password": "TempUser123!"},
    ).status_code == 401

    activate_response = client.post(
        f"/v1/admin/users/{user_id}/status",
        headers=headers,
        json={"is_active": True},
    )
    assert activate_response.status_code == 200

    lock_response = client.post(
        f"/v1/admin/users/{user_id}/lock",
        headers=headers,
        json={"reason": "Security review"},
    )
    assert lock_response.status_code == 200
    assert lock_response.json()["overview"]["status"] == "locked"
    assert lock_response.json()["account_status"]["lock_reason"] == "Security review"

    unlock_response = client.post(f"/v1/admin/users/{user_id}/unlock", headers=headers)
    assert unlock_response.status_code == 200
    assert unlock_response.json()["overview"]["status"] == "active"


def test_admin_user_branch_assignment_rules(client: TestClient) -> None:
    headers = _admin_headers(client)
    main_branch_id = _get_branch_id(SEED_BRANCH_CODE)
    north_branch_id = _get_branch_id(SEED_DESTINATION_BRANCH_CODE)
    create_response = client.post(
        "/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Branch Rule User",
            "email": "branch-rule@zeromerma.local",
            "temporary_password": "TempUser123!",
            "allowed_surfaces": [IDENTITY_SURFACE_POS],
            "branch_assignments": [{"branch_id": main_branch_id, "is_default": True}],
        },
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["overview"]["id"]

    remove_last_response = client.post(
        f"/v1/admin/users/{user_id}/branch-assignments/{main_branch_id}/deactivate",
        headers=headers,
    )
    assert remove_last_response.status_code == 409

    add_response = client.post(
        f"/v1/admin/users/{user_id}/branch-assignments",
        headers=headers,
        json={"branch_id": north_branch_id, "is_default": True},
    )
    assert add_response.status_code == 200
    assert any(
        assignment["branch_id"] == north_branch_id and assignment["is_default"]
        for assignment in add_response.json()["branch_assignments"]
    )

    deactivate_response = client.post(
        f"/v1/admin/users/{user_id}/branch-assignments/{main_branch_id}/deactivate",
        headers=headers,
    )
    assert deactivate_response.status_code == 200
    assert any(
        assignment["branch_id"] == main_branch_id and not assignment["is_active"]
        for assignment in deactivate_response.json()["branch_assignments"]
    )


def test_admin_user_access_rules_do_not_allow_self_deactivation_or_pos_bootstrap(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    admin_user_id = _get_user_id(SEED_ADMIN_EMAIL)

    self_deactivate_response = client.post(
        f"/v1/admin/users/{admin_user_id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert self_deactivate_response.status_code == 409

    bootstrap_response = client.get(
        f"/v1/pos/bootstrap?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )
    assert bootstrap_response.status_code == 403
