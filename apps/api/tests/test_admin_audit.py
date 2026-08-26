from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRANCH_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.infrastructure.models import User


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


def _seed_audit_events() -> tuple[str, str, str, str]:
    with SessionLocal() as session:
        admin = session.execute(select(User).where(User.email == SEED_ADMIN_EMAIL)).scalar_one()
        cashier = session.execute(select(User).where(User.email == SEED_USER_EMAIL)).scalar_one()
        branch = session.execute(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).scalar_one()
        now = datetime.now(tz=UTC)

        user_event = AuditLog(
            actor_id=admin.id,
            action="admin.user.updated",
            resource_type="user",
            resource_id=str(cashier.id),
            branch_id=branch.id,
            request_id="audit-user-update",
            occurred_at=now,
            metadata_={
                "current": {
                    "email": cashier.email,
                    "full_name": "Updated Cashier",
                    "password_hash": "new-secret-hash",
                    "phone": "6622222222",
                },
                "endpoint": "/v1/admin/users",
                "method": "PATCH",
                "previous": {
                    "email": cashier.email,
                    "full_name": cashier.full_name,
                    "password_hash": "old-secret-hash",
                    "phone": "6621111111",
                },
                "source_app": "BACKOFFICE",
                "status_code": 200,
                "workstation_code": "CAJA-01",
            },
        )
        inventory_event = AuditLog(
            actor_id=None,
            action="admin.inventory.adjustment_created",
            resource_type="inventory_balance",
            resource_id="balance-1",
            branch_id=branch.id,
            request_id="audit-inventory-blocked",
            occurred_at=now - timedelta(minutes=2),
            metadata_={
                "error_code": "inventory.closed_period",
                "product_id": "product-1",
                "reference": "INV-ADJ-1",
                "result": "blocked",
                "source_app": "SYSTEM",
            },
        )
        related_user_event = AuditLog(
            actor_id=admin.id,
            action="admin.user.status_changed",
            resource_type="user",
            resource_id=str(cashier.id),
            branch_id=branch.id,
            request_id="audit-user-status",
            occurred_at=now - timedelta(minutes=4),
            metadata_={"new_status": "active", "previous_status": "locked"},
        )
        session.add_all([user_event, inventory_event, related_user_event])
        session.commit()
        return str(user_event.id), str(inventory_event.id), str(admin.id), str(branch.id)


def test_admin_audit_list_metrics_filters_and_contract(client: TestClient) -> None:
    event_id, _, actor_id, branch_id = _seed_audit_events()
    headers = _admin_headers(client)

    response = client.get("/v1/admin/audit", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend_contract"]["immutable_events"] is True
    assert payload["backend_contract"]["mutation_supported"] is False
    assert payload["metrics"]["total_events"] >= 3
    assert payload["metrics"]["sensitive_events"] >= 2
    assert payload["metrics"]["access_events"] >= 2
    assert payload["filter_options"]["modules"]
    assert event_id in {item["id"] for item in payload["items"]}

    actor_response = client.get(f"/v1/admin/audit?actor_user_id={actor_id}", headers=headers)
    assert actor_response.status_code == 200
    assert all(item["actor_user_id"] == actor_id for item in actor_response.json()["items"])

    branch_response = client.get(f"/v1/admin/audit?branch_id={branch_id}", headers=headers)
    assert branch_response.status_code == 200
    assert branch_response.json()["items"]

    module_response = client.get("/v1/admin/audit?module=users", headers=headers)
    assert module_response.status_code == 200
    assert all(item["module"] == "users" for item in module_response.json()["items"])

    blocked_response = client.get("/v1/admin/audit?result=blocked", headers=headers)
    assert blocked_response.status_code == 200
    assert [item["result"] for item in blocked_response.json()["items"]] == ["blocked"]


def test_admin_audit_rejects_pos_only_user(client: TestClient) -> None:
    _seed_audit_events()

    response = client.get("/v1/admin/audit", headers=_cashier_headers(client))

    assert response.status_code == 403


def test_admin_audit_detail_masks_sensitive_values_and_shows_context(
    client: TestClient,
) -> None:
    event_id, _, _, _ = _seed_audit_events()

    response = client.get(f"/v1/admin/audit/{event_id}", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload)
    assert "old-secret-hash" not in serialized
    assert "new-secret-hash" not in serialized
    assert "[masked]" in serialized
    assert payload["overview"]["action"] == "admin.user.updated"
    assert payload["actor_context"]["can_open_user"] is True
    assert payload["entity_context"]["entity_type"] == "user"
    assert payload["request_context"]["request_id"] == "audit-user-update"
    assert payload["request_context"]["endpoint"] == "/v1/admin/users"
    assert payload["change_summary"]
    assert payload["related_documents"]
    assert payload["timeline_related_events"]


def test_admin_audit_export_returns_filtered_safe_rows(client: TestClient) -> None:
    _seed_audit_events()

    response = client.get("/v1/admin/audit/export?module=inventory", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "json"
    assert payload["total"] == 1
    assert payload["rows"][0]["module"] == "inventory"
    assert payload["rows"][0]["result"] == "blocked"
