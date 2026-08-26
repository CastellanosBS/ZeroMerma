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
    EquipmentAsset,
    EquipmentMaintenanceRecord,
    SanitaryVerification,
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


def _create_equipment(client: TestClient, **overrides: object) -> dict[str, object]:
    payload = {
        "area_name": "Hornos",
        "area_type": "PRODUCTION",
        "branch_id": _get_branch_id(),
        "brand": "BakeryPro",
        "code": "EQ-OVEN-01",
        "equipment_type": "OVEN",
        "food_safety_critical": True,
        "is_critical": True,
        "maintenance_frequency_days": 30,
        "model": "HX-10",
        "name": "Horno principal",
        "notes": "Equipo critico para produccion.",
        "operational_status": "OPERATIONAL",
        "provider_name": "Servicio Hornos Norte",
        "purchase_date": "2026-01-10",
        "risk_level": "HIGH",
        "serial_number": "SN-001",
        "warranty_expires_at": "2027-01-10",
    }
    payload.update(overrides)
    response = client.post(
        "/v1/admin/equipment-maintenance/equipment",
        headers={**_admin_headers(client), "X-Request-ID": "equipment-test"},
        json=payload,
    )
    assert response.status_code == 201
    return dict(response.json())


def _create_related_quality_records(equipment_name: str = "Horno principal") -> None:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).scalar_one()
        user = session.execute(select(User).where(User.email == SEED_ADMIN_EMAIL)).scalar_one()
        now = datetime.now(tz=UTC)
        session.add(
            CleaningLog(
                area_name="Hornos",
                area_type="EQUIPMENT",
                branch_id=branch.id,
                cleaning_type="EQUIPMENT",
                completed_at=now,
                created_at=now,
                created_by_user_id=user.id,
                equipment_name=equipment_name,
                folio="CLN-EQ-001",
                has_evidence=True,
                responsible_user_id=user.id,
                risk_level="HIGH",
                scheduled_at=now - timedelta(hours=1),
                shift_code="MORNING",
                status="COMPLETED",
                task_name="Limpieza horno",
                updated_at=now,
            )
        )
        session.add(
            SanitaryVerification(
                area_name="Hornos",
                area_type="EQUIPMENT",
                branch_id=branch.id,
                checklist_total_count=1,
                completed_at=now,
                created_at=now,
                created_by_user_id=user.id,
                equipment_name=equipment_name,
                failed_count=1,
                folio="SAN-EQ-001",
                follow_up_required=True,
                has_evidence=False,
                has_incident=False,
                inspector_user_id=user.id,
                max_score=1,
                not_applicable_count=0,
                pass_threshold_percent=80,
                passed_count=0,
                process_type="EQUIPMENT",
                result="FAILED",
                risk_level="HIGH",
                scheduled_at=now,
                score_percent=0,
                status="REQUIRES_FOLLOW_UP",
                template_name="Revision sanitaria equipo",
                updated_at=now,
            )
        )
        session.commit()


def test_admin_equipment_list_empty_contract_and_rejects_pos_user(client: TestClient) -> None:
    response = client.get(
        "/v1/admin/equipment-maintenance/equipment", headers=_admin_headers(client)
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["is_backend_connected"] is True
    assert (
        payload["backend_contract"]["create_equipment_endpoint"]
        == "POST /v1/admin/equipment-maintenance/equipment"
    )
    assert payload["filter_options"]["equipment_types"]

    forbidden_response = client.get(
        "/v1/admin/equipment-maintenance/equipment",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )
    assert forbidden_response.status_code == 403


def test_admin_equipment_create_persists_audit_outbox_and_related_quality_records(
    client: TestClient,
) -> None:
    _create_related_quality_records()
    detail = _create_equipment(client)
    equipment_id = detail["overview"]["id"]

    assert detail["overview"]["code"] == "EQ-OVEN-01"
    assert detail["overview"]["operational_status"] == "OPERATIONAL"
    assert detail["location_context"]["is_critical"] is True
    assert detail["current_maintenance_status"]["next_scheduled_maintenance_at"] is None
    assert any(document["folio"] == "CLN-EQ-001" for document in detail["related_documents"])
    assert any(document["folio"] == "SAN-EQ-001" for document in detail["related_documents"])

    with SessionLocal() as session:
        equipment = session.execute(
            select(EquipmentAsset).where(EquipmentAsset.id == equipment_id)
        ).scalar_one()
        audit_records = (
            session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == str(equipment_id))
                .order_by(AuditLog.occurred_at.asc())
            )
            .scalars()
            .all()
        )
        outbox_events = (
            session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.aggregate_id == str(equipment_id))
                .order_by(OutboxEvent.occurred_at.asc())
            )
            .scalars()
            .all()
        )

    assert equipment.code == "EQ-OVEN-01"
    assert audit_records[0].action == "admin.equipment.created"
    assert audit_records[0].request_id == "equipment-test"
    assert any(record.action == "admin.equipment.high_risk.notified" for record in audit_records)
    assert outbox_events[0].event_name == "equipment.created.v1"
    assert any(event.event_name == "equipment.high_risk_alert.v1" for event in outbox_events)


def test_admin_equipment_filters_update_and_status_safety(client: TestClient) -> None:
    created = _create_equipment(client, code="EQ-MIX-02", equipment_type="MIXER", name="Batidora")
    equipment_id = created["overview"]["id"]

    filtered = client.get(
        "/v1/admin/equipment-maintenance/equipment?search=batidora&equipment_type=MIXER",
        headers=_admin_headers(client),
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["items"]] == [equipment_id]

    update_payload = {
        "area_name": "Produccion",
        "area_type": "PRODUCTION",
        "branch_id": _get_branch_id(),
        "brand": "BakeryPro",
        "code": "EQ-MIX-02",
        "equipment_type": "MIXER",
        "food_safety_critical": True,
        "is_critical": True,
        "maintenance_frequency_days": 15,
        "model": "MX-2",
        "name": "Batidora masa",
        "notes": "Actualizada",
        "operational_status": "OPERATIONAL",
        "provider_name": "Servicio Hornos Norte",
        "purchase_date": "2026-01-10",
        "risk_level": "CRITICAL",
        "serial_number": "SN-002",
        "warranty_expires_at": "2027-01-10",
    }
    update_response = client.patch(
        f"/v1/admin/equipment-maintenance/equipment/{equipment_id}",
        headers=_admin_headers(client),
        json=update_payload,
    )
    assert update_response.status_code == 200
    assert update_response.json()["overview"]["name"] == "Batidora masa"

    missing_reason = client.post(
        f"/v1/admin/equipment-maintenance/equipment/{equipment_id}/status",
        headers=_admin_headers(client),
        json={"operational_status": "OUT_OF_SERVICE"},
    )
    assert missing_reason.status_code == 409

    status_response = client.post(
        f"/v1/admin/equipment-maintenance/equipment/{equipment_id}/status",
        headers=_admin_headers(client),
        json={"operational_status": "OUT_OF_SERVICE", "reason": "Falla electrica"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["overview"]["operational_status"] == "OUT_OF_SERVICE"


def test_admin_equipment_maintenance_create_start_complete_and_validate(
    client: TestClient,
) -> None:
    created = _create_equipment(client, code="EQ-REF-03", equipment_type="REFRIGERATION")
    equipment_id = created["overview"]["id"]

    invalid_scheduled = client.post(
        "/v1/admin/equipment-maintenance/maintenance",
        headers=_admin_headers(client),
        json={
            "description": "Servicio preventivo",
            "equipment_id": equipment_id,
            "maintenance_type": "PREVENTIVE",
            "status": "SCHEDULED",
        },
    )
    assert invalid_scheduled.status_code == 409

    maintenance_response = client.post(
        "/v1/admin/equipment-maintenance/maintenance",
        headers={**_admin_headers(client), "X-Request-ID": "maintenance-create-test"},
        json={
            "description": "Revision de temperatura y sellos.",
            "equipment_id": equipment_id,
            "expected_cost": "1200.00",
            "maintenance_type": "CORRECTIVE",
            "provider_name": "Frio Norte",
            "related_incident_reference": "INC-001",
            "scheduled_at": (datetime.now(tz=UTC) + timedelta(hours=2)).isoformat(),
            "status": "PENDING",
            "technician_name": "Luis Tecnico",
        },
    )
    assert maintenance_response.status_code == 201
    maintenance = maintenance_response.json()["maintenance_history"][0]
    maintenance_id = maintenance["id"]
    assert maintenance["folio"].startswith("MTN-")
    assert maintenance_response.json()["incidents_related"][0]["folio"] == "INC-001"

    start_response = client.post(
        f"/v1/admin/equipment-maintenance/maintenance/{maintenance_id}/start",
        headers=_admin_headers(client),
    )
    assert start_response.status_code == 200
    assert start_response.json()["overview"]["operational_status"] == "UNDER_MAINTENANCE"

    failed_without_notes = client.post(
        f"/v1/admin/equipment-maintenance/maintenance/{maintenance_id}/complete",
        headers=_admin_headers(client),
        json={"result": "FAILED", "cost": "1500.00"},
    )
    assert failed_without_notes.status_code == 409

    failed_operational = client.post(
        f"/v1/admin/equipment-maintenance/maintenance/{maintenance_id}/complete",
        headers=_admin_headers(client),
        json={
            "cost": "1500.00",
            "equipment_status_after_service": "OPERATIONAL",
            "notes": "Fallo de compresor pendiente.",
            "result": "FAILED",
        },
    )
    assert failed_operational.status_code == 409

    complete_response = client.post(
        f"/v1/admin/equipment-maintenance/maintenance/{maintenance_id}/complete",
        headers={**_admin_headers(client), "X-Request-ID": "maintenance-complete-test"},
        json={
            "completed_at": datetime.now(tz=UTC).isoformat(),
            "cost": "1500.00",
            "evidence_note": "Reporte tecnico en archivo interno.",
            "notes": "Reparacion completada y temperatura estable.",
            "result": "COMPLETED_SUCCESSFULLY",
            "technician_name": "Luis Tecnico",
        },
    )
    assert complete_response.status_code == 200
    payload = complete_response.json()
    assert payload["overview"]["operational_status"] == "OPERATIONAL"
    assert payload["maintenance_history"][0]["result"] == "COMPLETED_SUCCESSFULLY"
    assert payload["evidence"]["has_evidence"] is True
    assert payload["cost_context"]["period_cost"] in ["1500.00", 1500, 1500.0, "1500"]

    with SessionLocal() as session:
        record = session.execute(
            select(EquipmentMaintenanceRecord).where(
                EquipmentMaintenanceRecord.id == maintenance_id
            )
        ).scalar_one()
        completed_audit = session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == str(maintenance_id),
                AuditLog.action == "admin.equipment_maintenance.completed",
            )
        ).scalar_one()
        completed_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(maintenance_id),
                OutboxEvent.event_name == "equipment_maintenance.completed.v1",
            )
        ).scalar_one()

    assert record.status == "COMPLETED"
    assert completed_audit.request_id == "maintenance-complete-test"
    assert completed_event.payload["status"] == "COMPLETED"
