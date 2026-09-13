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
    SanitaryVerification,
    SanitaryVerificationChecklistItem,
    SanitaryVerificationTemplate,
    SanitaryVerificationTemplateItem,
)
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
        template = SanitaryVerificationTemplate(
            area_type="PRODUCTION_AREA",
            code="SAN-PROD",
            created_at=now,
            description="Revision sanitaria de mesa y utensilios de produccion.",
            frequency="DAILY",
            is_active=True,
            name="Revision sanitaria produccion",
            pass_threshold_percent=80,
            process_type="PRODUCTION",
            requires_evidence_on_failure=True,
            risk_level="HIGH",
            updated_at=now,
        )
        session.add(template)
        session.flush()
        session.add_all(
            [
                SanitaryVerificationTemplateItem(
                    created_at=now,
                    display_order=1,
                    evidence_required_on_failure=False,
                    expected_standard="Sin residuos visibles.",
                    is_required=True,
                    label="Superficies limpias",
                    risk_level="HIGH",
                    template_id=template.id,
                ),
                SanitaryVerificationTemplateItem(
                    created_at=now,
                    display_order=2,
                    evidence_required_on_failure=True,
                    expected_standard="Sanitizante vigente y aplicado.",
                    is_required=True,
                    label="Sanitizante aplicado",
                    risk_level="CRITICAL",
                    template_id=template.id,
                ),
            ]
        )
        session.commit()
        return str(template.id)


def _create_related_cleaning_log() -> None:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).scalar_one()
        user = session.execute(select(User).where(User.email == SEED_ADMIN_EMAIL)).scalar_one()
        now = datetime.now(tz=UTC)
        session.add(
            CleaningLog(
                area_name="Mesa produccion",
                area_type="PRODUCTION_AREA",
                branch_id=branch.id,
                cleaning_type="SANITATION",
                completed_at=now,
                created_at=now,
                created_by_user_id=user.id,
                evidence_note="Foto en archivo interno.",
                folio="CLN-RELATED",
                has_evidence=True,
                responsible_user_id=user.id,
                risk_level="HIGH",
                scheduled_at=now - timedelta(hours=1),
                shift_code="MORNING",
                started_at=now - timedelta(minutes=20),
                status="COMPLETED",
                task_name="Sanitizacion mesa produccion",
                updated_at=now,
            )
        )
        session.commit()


def _create_verification(client: TestClient, **overrides: object) -> dict[str, object]:
    payload = {
        "area_name": "Mesa produccion",
        "area_type": "PRODUCTION_AREA",
        "branch_id": _get_branch_id(),
        "checklist_results": [
            {
                "expected_standard": "Sin residuos visibles.",
                "is_required": True,
                "label": "Superficies limpias",
                "result": "PENDING",
                "risk_level": "HIGH",
            },
            {
                "evidence_required_on_failure": True,
                "expected_standard": "Sanitizante aplicado.",
                "is_required": True,
                "label": "Sanitizante aplicado",
                "result": "PENDING",
                "risk_level": "CRITICAL",
            },
        ],
        "complete_immediately": False,
        "inspector_user_id": _get_user_id(),
        "notes": "Revision programada",
        "process_name": "Produccion diaria",
        "process_type": "PRODUCTION",
        "risk_level": "HIGH",
        "scheduled_at": (datetime.now(tz=UTC) + timedelta(hours=1)).isoformat(),
        "template_name": "Revision sanitaria produccion",
    }
    payload.update(overrides)
    response = client.post(
        "/v1/admin/sanitary-verifications",
        headers={**_admin_headers(client), "X-Request-ID": "sanitary-test"},
        json=payload,
    )
    assert response.status_code == 201
    return dict(response.json())


def test_admin_sanitary_verifications_list_empty_templates_and_rejects_pos_user(
    client: TestClient,
) -> None:
    response = client.get("/v1/admin/sanitary-verifications", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["is_backend_connected"] is True
    assert (
        payload["backend_contract"]["create_endpoint"]
        == "POST /v1/admin/sanitary-verifications"
    )
    assert payload["filter_options"]["statuses"]

    templates_response = client.get(
        "/v1/admin/sanitary-verifications/templates",
        headers=_admin_headers(client),
    )
    assert templates_response.status_code == 200
    assert templates_response.json() == []

    forbidden_response = client.get(
        "/v1/admin/sanitary-verifications",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )
    assert forbidden_response.status_code == 403


def test_admin_sanitary_verification_create_persists_checklist_audit_and_outbox(
    client: TestClient,
) -> None:
    _create_related_cleaning_log()
    payload = _create_verification(client)
    verification_id = payload["overview"]["id"]

    assert payload["overview"]["folio"].startswith("SAN-")
    assert payload["overview"]["status"] == "PENDING"
    assert payload["overview"]["result"] == "NOT_EVALUATED"
    assert payload["scope"]["area_type"] == "PRODUCTION_AREA"
    assert len(payload["checklist_results"]) == 2
    assert payload["related_cleaning_logs"][0]["folio"] == "CLN-RELATED"
    assert payload["available_actions"]["can_start"] is True

    with SessionLocal() as session:
        verification = session.execute(
            select(SanitaryVerification).where(SanitaryVerification.id == verification_id)
        ).scalar_one()
        checklist_items = (
            session.execute(
                select(SanitaryVerificationChecklistItem).where(
                    SanitaryVerificationChecklistItem.verification_id == verification_id
                )
            )
            .scalars()
            .all()
        )
        audit_records = (
            session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == str(verification_id))
                .order_by(AuditLog.occurred_at.asc())
            )
            .scalars()
            .all()
        )
        outbox_events = (
            session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.aggregate_id == str(verification_id))
                .order_by(OutboxEvent.occurred_at.asc())
            )
            .scalars()
            .all()
        )

    assert verification.folio == payload["overview"]["folio"]
    assert len(checklist_items) == 2
    assert audit_records[0].action == "admin.sanitary_verification.created"
    assert audit_records[0].request_id == "sanitary-test"
    assert any(
        record.action == "admin.sanitary_verification.high_risk.notified"
        for record in audit_records
    )
    assert outbox_events[0].event_name == "sanitary_verification.created.v1"
    assert any(
        event.event_name == "sanitary_verification.high_risk_alert.v1"
        for event in outbox_events
    )


def test_admin_sanitary_verification_filters_by_branch_status_result_date_and_search(
    client: TestClient,
) -> None:
    created = _create_verification(
        client,
        area_name="Mostrador",
        area_type="COUNTER_DISPLAY",
        process_name="Mostrador",
        process_type="DISPLAY",
        risk_level="MEDIUM",
    )
    verification_id = created["overview"]["id"]

    branch_response = client.get(
        f"/v1/admin/sanitary-verifications?branch_id={_get_branch_id()}",
        headers=_admin_headers(client),
    )
    assert branch_response.status_code == 200
    assert [item["id"] for item in branch_response.json()["items"]] == [verification_id]

    status_response = client.get(
        "/v1/admin/sanitary-verifications?status=PENDING",
        headers=_admin_headers(client),
    )
    assert status_response.status_code == 200
    assert [item["id"] for item in status_response.json()["items"]] == [verification_id]

    result_response = client.get(
        "/v1/admin/sanitary-verifications?result=NOT_EVALUATED",
        headers=_admin_headers(client),
    )
    assert result_response.status_code == 200
    assert [item["id"] for item in result_response.json()["items"]] == [verification_id]

    date_from = datetime.now(tz=UTC).date().isoformat()
    date_response = client.get(
        f"/v1/admin/sanitary-verifications?date_from={date_from}",
        headers=_admin_headers(client),
    )
    assert date_response.status_code == 200
    assert [item["id"] for item in date_response.json()["items"]] == [verification_id]

    search_response = client.get(
        "/v1/admin/sanitary-verifications?search=mostrador",
        headers=_admin_headers(client),
    )
    assert search_response.status_code == 200
    assert [item["id"] for item in search_response.json()["items"]] == [verification_id]
    assert search_response.json()["metrics"]["pending_count"] == 1


def test_admin_sanitary_templates_seed_checklist_and_complete_passed(
    client: TestClient,
) -> None:
    template_id = _create_template()

    templates_response = client.get(
        "/v1/admin/sanitary-verifications/templates",
        headers=_admin_headers(client),
    )
    assert templates_response.status_code == 200
    assert templates_response.json()[0]["id"] == template_id
    assert len(templates_response.json()[0]["items"]) == 2

    created = _create_verification(
        client,
        checklist_results=[],
        complete_immediately=True,
        evidence_note="Foto de verificacion en archivo interno.",
        findings_notes=None,
        template_id=template_id,
        template_name=None,
    )

    assert created["overview"]["status"] == "COMPLETED"
    assert created["overview"]["result"] == "PASSED"
    assert created["checklist_template"]["template_id"] == template_id
    assert created["checklist_template"]["frequency"] == "DAILY"
    assert created["score_result"]["percentage"] == 100
    assert [item["label"] for item in created["checklist_results"]] == [
        "Superficies limpias",
        "Sanitizante aplicado",
    ]


def test_admin_sanitary_completion_validates_failure_notes_evidence_and_follow_up(
    client: TestClient,
) -> None:
    template_id = _create_template()
    created = _create_verification(client, checklist_results=[], template_id=template_id)
    verification_id = created["overview"]["id"]

    start_response = client.post(
        f"/v1/admin/sanitary-verifications/{verification_id}/start",
        headers={**_admin_headers(client), "X-Request-ID": "sanitary-start-test"},
    )
    assert start_response.status_code == 200
    assert start_response.json()["overview"]["status"] == "IN_PROGRESS"

    failed_without_notes = client.post(
        f"/v1/admin/sanitary-verifications/{verification_id}/complete",
        headers=_admin_headers(client),
        json={
            "checklist_results": [
                {
                    "is_required": True,
                    "label": "Superficies limpias",
                    "notes": "Correcto",
                    "result": "PASSED",
                    "risk_level": "HIGH",
                },
                {
                    "evidence_required_on_failure": True,
                    "is_required": True,
                    "label": "Sanitizante aplicado",
                    "result": "FAILED",
                    "risk_level": "CRITICAL",
                },
            ],
            "findings_notes": "Falla critica detectada.",
        },
    )
    assert failed_without_notes.status_code == 409

    missing_evidence = client.post(
        f"/v1/admin/sanitary-verifications/{verification_id}/complete",
        headers=_admin_headers(client),
        json={
            "checklist_results": [
                {
                    "is_required": True,
                    "label": "Superficies limpias",
                    "notes": "Correcto",
                    "result": "PASSED",
                    "risk_level": "HIGH",
                },
                {
                    "evidence_required_on_failure": True,
                    "is_required": True,
                    "label": "Sanitizante aplicado",
                    "notes": "Sanitizante vencido.",
                    "result": "FAILED",
                    "risk_level": "CRITICAL",
                },
            ],
            "findings_notes": "Falla critica detectada.",
        },
    )
    assert missing_evidence.status_code == 409

    complete_response = client.post(
        f"/v1/admin/sanitary-verifications/{verification_id}/complete",
        headers={**_admin_headers(client), "X-Request-ID": "sanitary-complete-test"},
        json={
            "checklist_results": [
                {
                    "is_required": True,
                    "label": "Superficies limpias",
                    "notes": "Correcto",
                    "result": "PASSED",
                    "risk_level": "HIGH",
                },
                {
                    "evidence_required_on_failure": True,
                    "is_required": True,
                    "label": "Sanitizante aplicado",
                    "notes": "Sanitizante vencido.",
                    "result": "FAILED",
                    "risk_level": "CRITICAL",
                },
            ],
            "completed_at": datetime.now(tz=UTC).isoformat(),
            "evidence_note": "Foto del sanitizante vencido en archivo interno.",
            "findings_notes": "Falla critica detectada; retirar sanitizante.",
        },
    )
    assert complete_response.status_code == 200
    payload = complete_response.json()
    assert payload["overview"]["status"] == "REQUIRES_FOLLOW_UP"
    assert payload["overview"]["result"] == "FAILED"
    assert payload["findings_observations"]["follow_up_required"] is True
    assert payload["evidence"]["has_evidence"] is True
    assert payload["score_result"]["percentage"] == 50

    with SessionLocal() as session:
        completed_audit = session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == str(verification_id),
                AuditLog.action == "admin.sanitary_verification.completed",
            )
        ).scalar_one()
        completed_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(verification_id),
                OutboxEvent.event_name == "sanitary_verification.completed.v1",
            )
        ).scalar_one()

    assert completed_audit.request_id == "sanitary-complete-test"
    assert completed_event.payload["status"] == "REQUIRES_FOLLOW_UP"
