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
    QualityIncident,
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


def _get_branch_id() -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).scalar_one()
        return str(branch.id)


def _get_user_id(email: str = SEED_ADMIN_EMAIL) -> str:
    with SessionLocal() as session:
        user = session.execute(select(User).where(User.email == email)).scalar_one()
        return str(user.id)


def _create_sanitary_verification() -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).scalar_one()
        user = session.execute(select(User).where(User.email == SEED_ADMIN_EMAIL)).scalar_one()
        now = datetime.now(tz=UTC)
        verification = SanitaryVerification(
            area_name="Produccion",
            area_type="PRODUCTION_AREA",
            branch_id=branch.id,
            checklist_total_count=2,
            completed_at=now,
            created_at=now,
            created_by_user_id=user.id,
            failed_count=1,
            findings_notes="Sanitizante vencido.",
            folio="SAN-INC-001",
            has_evidence=True,
            inspector_user_id=user.id,
            process_name="Produccion diaria",
            process_type="PRODUCTION",
            result="FAILED",
            risk_level="HIGH",
            scheduled_at=now - timedelta(hours=2),
            status="REQUIRES_FOLLOW_UP",
            template_name="Revision sanitaria",
            updated_at=now,
        )
        session.add(verification)
        session.commit()
        return str(verification.id)


def _create_incident(client: TestClient, **overrides: object) -> dict[str, object]:
    payload = {
        "area_name": "Produccion",
        "branch_id": _get_branch_id(),
        "corrective_action": "Repetir sanitizacion y retirar insumo vencido.",
        "description": "Se encontro sanitizante vencido en area de produccion.",
        "due_at": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
        "evidence_note": "Foto interna 123.",
        "food_safety_impact": True,
        "incident_type": "SANITATION_ISSUE",
        "notes": "Detectado durante revision de turno.",
        "operational_impact": "Riesgo de retraso en produccion.",
        "responsible_user_id": _get_user_id(),
        "severity": "HIGH",
        "source_type": "MANUAL",
        "title": "Sanitizante vencido en produccion",
    }
    payload.update(overrides)
    response = client.post(
        "/v1/admin/incidents",
        headers={**_admin_headers(client), "X-Request-ID": "incident-test"},
        json=payload,
    )
    assert response.status_code == 201
    return dict(response.json())


def test_admin_incidents_list_empty_and_reject_pos_user(client: TestClient) -> None:
    admin_response = client.get("/v1/admin/incidents", headers=_admin_headers(client))
    assert admin_response.status_code == 200
    body = admin_response.json()
    assert body["items"] == []
    assert body["metrics"]["total_count"] == 0
    assert body["backend_contract"]["list_endpoint"] == "GET /v1/admin/incidents"

    pos_token = _login_cashier(client)
    pos_response = client.get(
        "/v1/admin/incidents",
        headers={"Authorization": f"Bearer {pos_token}"},
    )
    assert pos_response.status_code == 403


def test_admin_can_create_high_risk_incident_from_sanitary_verification(
    client: TestClient,
) -> None:
    verification_id = _create_sanitary_verification()
    detail = _create_incident(
        client,
        area_name=None,
        source_document_id=verification_id,
        source_type="SANITARY_VERIFICATION",
    )

    assert detail["overview"]["folio"] == "INC-000001"
    assert detail["overview"]["severity"] == "HIGH"
    assert detail["source_document"]["source_reference"] == "SAN-INC-001"
    assert detail["location_scope"]["area_name"] == "Produccion"
    assert detail["evidence"]["has_evidence"] is True
    assert detail["related_documents"]
    assert any(warning["code"] == "high_risk" for warning in detail["warnings"])

    with SessionLocal() as session:
        incident = session.execute(select(QualityIncident)).scalar_one()
        verification = session.get(SanitaryVerification, verification_id)
        assert incident.folio == "INC-000001"
        assert verification is not None
        assert verification.has_incident is True
        assert verification.incident_reference == "INC-000001"
        audit_actions = [record.action for record in session.scalars(select(AuditLog)).all()]
        assert "admin.incident.created" in audit_actions
        assert "admin.incident.high_risk.notified" in audit_actions
        event_names = [record.event_name for record in session.scalars(select(OutboxEvent)).all()]
        assert "quality_incident.created.v1" in event_names
        assert "quality_incident.high_risk_alert.v1" in event_names


def test_admin_incidents_filter_detail_and_validation(client: TestClient) -> None:
    detail = _create_incident(client)
    incident_id = detail["overview"]["id"]

    list_response = client.get(
        "/v1/admin/incidents",
        headers=_admin_headers(client),
        params={
            "branch_id": _get_branch_id(),
            "evidence_state": "with_evidence",
            "incident_type": "SANITATION_ISSUE",
            "search": "sanitizante",
            "severity": "HIGH",
            "status": "OPEN",
        },
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["folio"] == "INC-000001"

    detail_response = client.get(
        f"/v1/admin/incidents/{incident_id}",
        headers=_admin_headers(client),
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["corrective_action"]["corrective_action"].startswith("Repetir")

    invalid_response = client.post(
        "/v1/admin/incidents",
        headers=_admin_headers(client),
        json={
            "branch_id": _get_branch_id(),
            "description": "Otro problema.",
            "incident_type": "OTHER",
            "severity": "LOW",
            "source_type": "MANUAL",
            "title": "Otro",
        },
    )
    assert invalid_response.status_code == 409
    assert "requires notes" in invalid_response.json()["message"]


def test_admin_incident_follow_up_status_resolve_and_reopen(client: TestClient) -> None:
    detail = _create_incident(client)
    incident_id = detail["overview"]["id"]

    follow_response = client.post(
        f"/v1/admin/incidents/{incident_id}/follow-ups",
        headers=_admin_headers(client),
        json={"note": "Tecnico asignado.", "status_change": "IN_PROGRESS"},
    )
    assert follow_response.status_code == 200
    assert follow_response.json()["overview"]["status"] == "IN_PROGRESS"
    assert follow_response.json()["follow_ups"][0]["note"] == "Tecnico asignado."

    bad_resolve = client.post(
        f"/v1/admin/incidents/{incident_id}/resolve",
        headers=_admin_headers(client),
        json={"resolution_note": "", "result": ""},
    )
    assert bad_resolve.status_code == 422

    resolve_response = client.post(
        f"/v1/admin/incidents/{incident_id}/resolve",
        headers=_admin_headers(client),
        json={
            "evidence_note": "Foto de correccion.",
            "resolution_note": "Sanitizante retirado y area sanitizada.",
            "result": "resolved_with_corrective_action",
        },
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["overview"]["status"] == "RESOLVED"
    assert resolve_response.json()["corrective_action"]["resolution_result"] == (
        "resolved_with_corrective_action"
    )

    reopen_response = client.post(
        f"/v1/admin/incidents/{incident_id}/reopen",
        headers=_admin_headers(client),
        json={"note": "Reabierta por reincidencia."},
    )
    assert reopen_response.status_code == 200
    assert reopen_response.json()["overview"]["status"] == "OPEN"
