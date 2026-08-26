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
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.quality.infrastructure.models import (
    CleaningLog,
    CleaningLogChecklistItem,
    CleaningTemplate,
    CleaningTemplateItem,
)


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


def _get_branch_id(code: str = SEED_BRANCH_CODE) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
        return str(branch.id)


def _get_user_id(email: str = SEED_ADMIN_EMAIL) -> str:
    with SessionLocal() as session:
        user = session.execute(select(User).where(User.email == email)).scalar_one()
        return str(user.id)


def _create_template() -> str:
    with SessionLocal() as session:
        now = datetime.now(tz=UTC)
        template = CleaningTemplate(
            area_type="PRODUCTION_AREA",
            cleaning_type="SANITATION",
            code="PROD-SAN",
            created_at=now,
            description="Sanitizacion de mesa de produccion.",
            estimated_duration_minutes=20,
            frequency="DAILY",
            is_active=True,
            method_summary="Lavar, sanitizar y secar superficie de contacto.",
            name="Sanitizacion mesa produccion",
            requires_evidence=True,
            required_tools="Sanitizante grado alimenticio",
            risk_level="HIGH",
            updated_at=now,
        )
        session.add(template)
        session.flush()
        session.add_all(
            [
                CleaningTemplateItem(
                    created_at=now,
                    display_order=1,
                    is_required=True,
                    label="Retirar residuos visibles",
                    template_id=template.id,
                ),
                CleaningTemplateItem(
                    created_at=now,
                    display_order=2,
                    is_required=True,
                    label="Aplicar sanitizante",
                    template_id=template.id,
                ),
            ]
        )
        session.commit()
        return str(template.id)


def _create_log(client: TestClient, **overrides: object) -> dict[str, object]:
    payload = {
        "area_name": "Mesa produccion",
        "area_type": "PRODUCTION_AREA",
        "branch_id": _get_branch_id(),
        "checklist_items": [
            {"is_completed": False, "is_required": True, "label": "Retirar residuos"},
            {"is_completed": False, "is_required": True, "label": "Sanitizar superficie"},
        ],
        "cleaning_type": "SANITATION",
        "complete_immediately": False,
        "notes": "Limpieza programada",
        "responsible_user_id": _get_user_id(),
        "risk_level": "HIGH",
        "scheduled_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
        "shift_code": "MORNING",
        "task_name": "Sanitizacion mesa produccion",
    }
    payload.update(overrides)
    response = client.post(
        "/v1/admin/cleaning-logs",
        headers={**_admin_headers(client), "X-Request-ID": "cleaning-test"},
        json=payload,
    )
    assert response.status_code == 201
    return dict(response.json())


def test_admin_cleaning_logs_list_empty_templates_and_rejects_pos_user(client: TestClient) -> None:
    response = client.get("/v1/admin/cleaning-logs", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["is_backend_connected"] is True
    assert payload["backend_contract"]["create_endpoint"] == "POST /v1/admin/cleaning-logs"
    assert payload["filter_options"]["statuses"]

    templates_response = client.get(
        "/v1/admin/cleaning-logs/templates", headers=_admin_headers(client)
    )
    assert templates_response.status_code == 200
    assert templates_response.json() == []

    forbidden_response = client.get(
        "/v1/admin/cleaning-logs",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )
    assert forbidden_response.status_code == 403


def test_admin_cleaning_log_create_persists_checklist_audit_and_outbox(client: TestClient) -> None:
    payload = _create_log(client)
    log_id = payload["overview"]["id"]

    assert payload["overview"]["folio"].startswith("CLN-")
    assert payload["overview"]["status"] == "PENDING"
    assert payload["overview"]["risk_level"] == "HIGH"
    assert payload["location_area"]["area_type"] == "PRODUCTION_AREA"
    assert len(payload["checklist"]) == 2
    assert payload["available_actions"]["can_complete"] is True

    with SessionLocal() as session:
        log = session.execute(select(CleaningLog).where(CleaningLog.id == log_id)).scalar_one()
        checklist_items = (
            session.execute(
                select(CleaningLogChecklistItem).where(
                    CleaningLogChecklistItem.cleaning_log_id == log_id
                )
            )
            .scalars()
            .all()
        )
        audit_records = (
            session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == str(log_id))
                .order_by(AuditLog.occurred_at.asc())
            )
            .scalars()
            .all()
        )
        outbox_events = (
            session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.aggregate_id == str(log_id))
                .order_by(OutboxEvent.occurred_at.asc())
            )
            .scalars()
            .all()
        )

    assert log.folio == payload["overview"]["folio"]
    assert len(checklist_items) == 2
    assert audit_records[0].action == "admin.cleaning_log.created"
    assert audit_records[0].request_id == "cleaning-test"
    assert any(record.action == "admin.cleaning_log.high_risk.notified" for record in audit_records)
    assert outbox_events[0].event_name == "cleaning_log.created.v1"
    assert any(event.event_name == "cleaning_log.high_risk_alert.v1" for event in outbox_events)


def test_admin_cleaning_log_filters_by_branch_status_responsible_date_and_search(
    client: TestClient,
) -> None:
    created = _create_log(
        client, area_name="Mostrador", area_type="COUNTER_DISPLAY", risk_level="MEDIUM"
    )
    log_id = created["overview"]["id"]

    branch_response = client.get(
        f"/v1/admin/cleaning-logs?branch_id={_get_branch_id()}",
        headers=_admin_headers(client),
    )
    assert branch_response.status_code == 200
    assert [item["id"] for item in branch_response.json()["items"]] == [log_id]

    status_response = client.get(
        "/v1/admin/cleaning-logs?status=PENDING", headers=_admin_headers(client)
    )
    assert status_response.status_code == 200
    assert [item["id"] for item in status_response.json()["items"]] == [log_id]

    responsible_response = client.get(
        f"/v1/admin/cleaning-logs?responsible_user_id={_get_user_id()}",
        headers=_admin_headers(client),
    )
    assert responsible_response.status_code == 200
    assert [item["id"] for item in responsible_response.json()["items"]] == [log_id]

    date_from = datetime.now(tz=UTC).date().isoformat()
    date_response = client.get(
        f"/v1/admin/cleaning-logs?date_from={date_from}", headers=_admin_headers(client)
    )
    assert date_response.status_code == 200
    assert [item["id"] for item in date_response.json()["items"]] == [log_id]

    search_response = client.get(
        "/v1/admin/cleaning-logs?search=mostrador", headers=_admin_headers(client)
    )
    assert search_response.status_code == 200
    assert [item["id"] for item in search_response.json()["items"]] == [log_id]
    assert search_response.json()["metrics"]["pending_count"] == 1


def test_admin_cleaning_completion_validates_required_checklist_and_evidence(
    client: TestClient,
) -> None:
    created = _create_log(client)
    log_id = created["overview"]["id"]

    missing_checklist_response = client.post(
        f"/v1/admin/cleaning-logs/{log_id}/complete",
        headers=_admin_headers(client),
        json={
            "checklist_items": [
                {"is_completed": True, "is_required": True, "label": "Retirar residuos"},
                {"is_completed": False, "is_required": True, "label": "Sanitizar superficie"},
            ],
            "evidence_note": "Foto en archivo interno.",
        },
    )
    assert missing_checklist_response.status_code == 409

    missing_evidence_response = client.post(
        f"/v1/admin/cleaning-logs/{log_id}/complete",
        headers=_admin_headers(client),
        json={
            "checklist_items": [
                {"is_completed": True, "is_required": True, "label": "Retirar residuos"},
                {"is_completed": True, "is_required": True, "label": "Sanitizar superficie"},
            ],
        },
    )
    assert missing_evidence_response.status_code == 409

    complete_response = client.post(
        f"/v1/admin/cleaning-logs/{log_id}/complete",
        headers={**_admin_headers(client), "X-Request-ID": "cleaning-complete-test"},
        json={
            "checklist_items": [
                {"is_completed": True, "is_required": True, "label": "Retirar residuos"},
                {"is_completed": True, "is_required": True, "label": "Sanitizar superficie"},
            ],
            "completed_at": datetime.now(tz=UTC).isoformat(),
            "evidence_note": "Foto en archivo interno.",
        },
    )
    assert complete_response.status_code == 200
    payload = complete_response.json()
    assert payload["overview"]["status"] == "COMPLETED"
    assert payload["evidence"]["has_evidence"] is True
    assert all(item["is_completed"] for item in payload["checklist"])

    with SessionLocal() as session:
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == str(log_id),
                AuditLog.action == "admin.cleaning_log.completed",
            )
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(log_id),
                OutboxEvent.event_name == "cleaning_log.completed.v1",
            )
        ).scalar_one()

    assert audit_record.request_id == "cleaning-complete-test"
    assert outbox_event.payload["status"] == "COMPLETED"


def test_admin_cleaning_templates_can_seed_checklist(client: TestClient) -> None:
    template_id = _create_template()

    templates_response = client.get(
        "/v1/admin/cleaning-logs/templates", headers=_admin_headers(client)
    )
    assert templates_response.status_code == 200
    assert templates_response.json()[0]["id"] == template_id
    assert len(templates_response.json()[0]["items"]) == 2

    created = _create_log(
        client,
        area_name="Mesa produccion",
        area_type="PRODUCTION_AREA",
        checklist_items=[],
        evidence_note="Foto en archivo interno.",
        complete_immediately=True,
        task_name=None,
        task_template_id=template_id,
    )

    assert created["overview"]["status"] == "COMPLETED"
    assert created["task_template"]["task_template_id"] == template_id
    assert created["task_template"]["frequency"] == "DAILY"
    assert [item["label"] for item in created["checklist"]] == [
        "Retirar residuos visibles",
        "Aplicar sanitizante",
    ]
