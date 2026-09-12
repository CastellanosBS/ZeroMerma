from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ALT_DESTINATION_BRANCH_CODE,
    SEED_DESTINATION_BRANCH_CODE,
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_PRODUCT_CAFE_AMERICANO_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.corrections.infrastructure.models import (
    CorrectionDocument,
    CorrectionDocumentLine,
    CorrectionReason,
)
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


def _login(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _authorization_header(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client)}"}


def _open_cash_session(client: TestClient) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "150.00",
        },
    )
    assert response.status_code == 201


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
    return str(product.id)


def _get_branch_id(code: str) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
    return str(branch.id)


def _commit_counter_transfer(
    client: TestClient,
    *,
    quantity: str = "4",
) -> dict[str, object]:
    response = client.post(
        "/v1/operations/counter-transfer/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                    "quantity": quantity,
                }
            ],
            "notes": "Correction target counter transfer",
        },
    )
    assert response.status_code == 201
    return response.json()


def _dispatch_transfer(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/v1/transfers/dispatch/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "3",
                },
                {
                    "product_id": _get_product_id(SEED_PRODUCT_CAFE_AMERICANO_CODE),
                    "quantity": "1",
                },
            ],
            "notes": "Correction shipment target",
        },
    )
    assert response.status_code == 201
    return response.json()["shipment"]


def test_corrections_bootstrap_returns_active_reasons(client: TestClient) -> None:
    _open_cash_session(client)
    response = client.get(
        f"/v1/corrections/bootstrap?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["branch"]["code"] == "MAIN"
    assert payload["current_open_cash_session"] is not None
    assert payload["correction_operations_allowed"] is True
    assert payload["correction_controls"] == {
        "high_impact_quantity_threshold": "10",
        "high_impact_requires_acknowledgement": True,
    }
    assert [reason["code"] for reason in payload["correction_reasons"]] == [
        "WRONG_QUANTITY",
        "WRONG_PRODUCT",
        "DUPLICATE_CAPTURE",
        "DAMAGED_DURING_HANDLING",
        "COUNT_MISMATCH",
        "WRONG_DESTINATION",
        "OTHER",
    ]
    assert [branch["code"] for branch in payload["destination_branches"]] == [
        SEED_DESTINATION_BRANCH_CODE,
        SEED_ALT_DESTINATION_BRANCH_CODE,
    ]

    with SessionLocal() as session:
        reason_count = session.execute(select(func.count(CorrectionReason.code))).scalar_one()
    assert reason_count == 7


def test_correction_product_search_returns_exact_products(client: TestClient) -> None:
    _open_cash_session(client)
    response = client.get(
        "/v1/corrections/products",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "query": "concha",
        },
        headers=_authorization_header(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workstation_code"] == SEED_WORKSTATION_CODE
    assert any(product["code"] == SEED_PRODUCT_CONCHA_VAN_CODE for product in payload["products"])


def test_correction_search_and_detail_return_correctable_documents(client: TestClient) -> None:
    _open_cash_session(client)
    counter_transfer = _commit_counter_transfer(client)
    _dispatch_transfer(client)

    search_response = client.get(
        "/v1/corrections/search",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "document_type": "COUNTER_TRANSFER",
            "query": "counter transfer",
        },
        headers=_authorization_header(client),
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert [document["id"] for document in search_payload["documents"]] == [counter_transfer["id"]]
    assert search_payload["documents"][0]["folio"].startswith("CTR-")

    detail_response = client.get(
        f"/v1/corrections/{counter_transfer['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["target_document"]["id"] == counter_transfer["id"]
    assert detail_payload["is_correctable"] is True
    assert detail_payload["blocking_reason"] is None
    assert detail_payload["applied_corrections"] == []


def test_correction_commit_keeps_original_document_and_writes_audit_and_outbox(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    counter_transfer = _commit_counter_transfer(client)

    response = client.post(
        "/v1/corrections/commit",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "phase-4a-correction-commit",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "target_document_id": counter_transfer["id"],
            "reason_code": "WRONG_QUANTITY",
            "notes": "Should have been two fewer pieces.",
            "lines": [
                {
                    "target_line_id": counter_transfer["lines"][0]["id"],
                    "product_id": counter_transfer["lines"][0]["product_id"],
                    "delta_quantity": "-2",
                    "notes": "Reduce capture",
                }
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["folio"].startswith("COR-")
    assert payload["target_document_id"] == counter_transfer["id"]
    assert payload["target_document_type"] == "COUNTER_TRANSFER"
    assert payload["reason_code"] == "WRONG_QUANTITY"
    assert payload["lines"][0]["target_line_id"] == counter_transfer["lines"][0]["id"]
    assert Decimal(str(payload["lines"][0]["delta_quantity"])) == Decimal("-2.000")

    detail_response = client.get(
        f"/v1/corrections/{counter_transfer['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert len(detail_payload["applied_corrections"]) == 1
    assert detail_payload["applied_corrections"][0]["id"] == payload["id"]
    assert detail_payload["applied_corrections"][0]["folio"] == payload["folio"]
    assert detail_payload["applied_corrections"][0]["lines"][0]["line_number"] == 1
    assert (
        detail_payload["applied_corrections"][0]["lines"][0]["product_code_snapshot"]
        == SEED_PRODUCT_CONCHA_VAN_CODE
    )
    assert Decimal(
        str(detail_payload["applied_corrections"][0]["lines"][0]["delta_quantity"])
    ) == Decimal("-2.000")

    with SessionLocal() as session:
        target_document = session.execute(
            select(OperationDocument).where(OperationDocument.id == counter_transfer["id"])
        ).scalar_one()
        target_lines = (
            session.execute(
                select(OperationDocumentLine)
                .where(OperationDocumentLine.operation_document_id == target_document.id)
                .order_by(OperationDocumentLine.line_number.asc())
            )
            .scalars()
            .all()
        )
        correction_document = session.execute(
            select(CorrectionDocument).where(CorrectionDocument.id == payload["id"])
        ).scalar_one()
        correction_lines = (
            session.execute(
                select(CorrectionDocumentLine)
                .where(CorrectionDocumentLine.correction_document_id == correction_document.id)
                .order_by(CorrectionDocumentLine.line_number.asc())
            )
            .scalars()
            .all()
        )
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == payload["id"])
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == payload["id"])
        ).scalar_one()

    assert target_document.id == correction_document.target_document_id
    assert Decimal(target_lines[0].quantity) == Decimal("4.000")
    assert Decimal(correction_lines[0].delta_quantity) == Decimal("-2.000")
    assert audit_record.action == "correction.committed"
    assert audit_record.request_id == "phase-4a-correction-commit"
    assert outbox_event.event_name == "correction.committed.v1"


def test_shipment_correction_after_receipt_is_rejected(client: TestClient) -> None:
    _open_cash_session(client)
    shipment = _dispatch_transfer(client)

    first_receive = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
            "lines": [
                {
                    "shipment_line_id": shipment["lines"][0]["id"],
                    "expected_quantity": "3",
                    "received_quantity": "3",
                },
                {
                    "shipment_line_id": shipment["lines"][1]["id"],
                    "expected_quantity": "1",
                    "received_quantity": "1",
                },
            ],
            "notes": "Receipt before correction attempt",
        },
    )
    assert first_receive.status_code == 200

    detail_response = client.get(
        f"/v1/corrections/{shipment['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["is_correctable"] is False
    assert "ya fue recibido" in detail_payload["blocking_reason"]

    commit_response = client.post(
        "/v1/corrections/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "target_document_id": shipment["id"],
            "reason_code": "COUNT_MISMATCH",
            "lines": [
                {
                    "product_id": shipment["lines"][0]["product_id"],
                    "delta_quantity": "-1",
                }
            ],
        },
    )
    assert commit_response.status_code == 409
    assert "ya fue recibido" in commit_response.json()["message"]


def test_correction_commit_supports_wrong_product_delta_composition(client: TestClient) -> None:
    _open_cash_session(client)
    counter_transfer = _commit_counter_transfer(client)
    replacement_product_id = _get_product_id(SEED_PRODUCT_CAFE_AMERICANO_CODE)

    response = client.post(
        "/v1/corrections/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "target_document_id": counter_transfer["id"],
            "reason_code": "WRONG_PRODUCT",
            "notes": "Se capturo el producto equivocado.",
            "lines": [
                {
                    "target_line_id": counter_transfer["lines"][0]["id"],
                    "product_id": counter_transfer["lines"][0]["product_id"],
                    "delta_quantity": "-1",
                },
                {
                    "product_id": replacement_product_id,
                    "delta_quantity": "1",
                },
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert len(payload["lines"]) == 2
    assert payload["lines"][0]["target_line_id"] == counter_transfer["lines"][0]["id"]
    assert payload["lines"][1]["target_line_id"] is None
    assert payload["lines"][1]["product_id"] == replacement_product_id


def test_correction_commit_supports_wrong_destination_for_shipments(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    shipment = _dispatch_transfer(client)
    corrected_destination_branch_id = _get_branch_id(SEED_ALT_DESTINATION_BRANCH_CODE)

    response = client.post(
        "/v1/corrections/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "target_document_id": shipment["id"],
            "reason_code": "WRONG_DESTINATION",
            "corrected_destination_branch_id": corrected_destination_branch_id,
            "notes": "Se capturo una sucursal destino equivocada.",
            "lines": [],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["target_document_id"] == shipment["id"]
    assert payload["correction_type"] == "DESTINATION_ADJUSTMENT"
    assert payload["reason_code"] == "WRONG_DESTINATION"
    assert payload["corrected_destination_branch_id"] == corrected_destination_branch_id
    assert payload["corrected_destination_branch_code"] == SEED_ALT_DESTINATION_BRANCH_CODE
    assert payload["corrected_destination_branch_name"] == "South Branch"
    assert payload["lines"] == []

    detail_response = client.get(
        f"/v1/corrections/{shipment['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert len(detail_payload["applied_corrections"]) == 1
    assert detail_payload["applied_corrections"][0]["id"] == payload["id"]
    assert detail_payload["applied_corrections"][0]["line_count"] == 0
    assert (
        detail_payload["applied_corrections"][0]["corrected_destination_branch_code"]
        == SEED_ALT_DESTINATION_BRANCH_CODE
    )
    assert (
        detail_payload["applied_corrections"][0]["corrected_destination_branch_name"]
        == "South Branch"
    )
    assert detail_payload["applied_corrections"][0]["lines"] == []


def test_correction_history_and_detail_expose_safe_audit_summary(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    counter_transfer = _commit_counter_transfer(client)

    create_response = client.post(
        "/v1/corrections/commit",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "phase-4a-correction-history",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "target_document_id": counter_transfer["id"],
            "reason_code": "WRONG_QUANTITY",
            "notes": "Ajuste auditado para historial.",
            "lines": [
                {
                    "target_line_id": counter_transfer["lines"][0]["id"],
                    "product_id": counter_transfer["lines"][0]["product_id"],
                    "delta_quantity": "-2",
                }
            ],
        },
    )
    assert create_response.status_code == 201
    created_payload = create_response.json()

    history_response = client.get(
        "/v1/corrections/history",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "CURRENT_SHIFT",
            "query": created_payload["folio"],
            "reason_code": "WRONG_QUANTITY",
            "target_document_type": "COUNTER_TRANSFER",
        },
        headers=_authorization_header(client),
    )
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["scope"] == "CURRENT_SHIFT"
    assert history_payload["available_users"][0]["value"]
    assert history_payload["available_document_types"][0]["value"] == "COUNTER_TRANSFER"
    assert history_payload["available_reasons"][0]["value"] == "WRONG_QUANTITY"
    assert len(history_payload["records"]) == 1
    assert history_payload["records"][0]["id"] == created_payload["id"]
    assert history_payload["records"][0]["target_document_id"] == counter_transfer["id"]
    assert history_payload["records"][0]["workstation_code"] == SEED_WORKSTATION_CODE
    assert history_payload["records"][0]["source_branch_code"] == "MAIN"

    history_detail_response = client.get(
        f"/v1/corrections/history/{created_payload['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert history_detail_response.status_code == 200
    history_detail_payload = history_detail_response.json()
    assert history_detail_payload["audit_summary"]["created_by"]["email"] == SEED_USER_EMAIL
    assert (
        history_detail_payload["audit_summary"]["confirmed_by"]["full_name"]
        == "Main Branch Cashier"
    )
    assert history_detail_payload["audit_summary"]["reason_label"] == "Wrong Quantity"
    assert history_detail_payload["audit_summary"]["notes"] == "Ajuste auditado para historial."

    target_detail_response = client.get(
        f"/v1/corrections/{counter_transfer['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert target_detail_response.status_code == 200
    target_detail_payload = target_detail_response.json()
    assert (
        target_detail_payload["applied_corrections"][0]["audit_summary"]["created_by"]["email"]
        == SEED_USER_EMAIL
    )


def test_high_impact_correction_requires_acknowledgement_and_emits_alert_outbox(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    counter_transfer = _commit_counter_transfer(client, quantity="15")

    blocked_response = client.post(
        "/v1/corrections/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "target_document_id": counter_transfer["id"],
            "reason_code": "WRONG_QUANTITY",
            "notes": "High-impact adjustment without acknowledgement.",
            "lines": [
                {
                    "target_line_id": counter_transfer["lines"][0]["id"],
                    "product_id": counter_transfer["lines"][0]["product_id"],
                    "delta_quantity": "-12",
                }
            ],
            "high_impact_acknowledged": False,
        },
    )

    assert blocked_response.status_code == 400
    assert "alto impacto" in blocked_response.json()["message"]

    response = client.post(
        "/v1/corrections/commit",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "phase-4a-correction-high-impact",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "target_document_id": counter_transfer["id"],
            "reason_code": "WRONG_QUANTITY",
            "notes": "High-impact adjustment acknowledged.",
            "lines": [
                {
                    "target_line_id": counter_transfer["lines"][0]["id"],
                    "product_id": counter_transfer["lines"][0]["product_id"],
                    "delta_quantity": "-12",
                }
            ],
            "high_impact_acknowledged": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()

    with SessionLocal() as session:
        audit_records = (
            session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == payload["id"])
                .order_by(AuditLog.occurred_at.asc())
            )
            .scalars()
            .all()
        )
        outbox_events = (
            session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.aggregate_id == payload["id"])
                .order_by(OutboxEvent.occurred_at.asc())
            )
            .scalars()
            .all()
        )

    assert [record.action for record in audit_records] == [
        "correction.committed",
        "correction.high_impact_alert_requested",
    ]
    assert [event.event_name for event in outbox_events] == [
        "correction.committed.v1",
        "correction.high_impact_alert.v1",
    ]
    assert outbox_events[1].payload["notification_target"] == "backoffice"
    assert outbox_events[1].payload["folio"].startswith("COR-")

    history_detail_response = client.get(
        f"/v1/corrections/history/{payload['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert history_detail_response.status_code == 200
    history_detail_payload = history_detail_response.json()
    assert history_detail_payload["audit_summary"]["acknowledged_by"]["email"] == SEED_USER_EMAIL
    assert history_detail_payload["audit_summary"]["backoffice_notification"]["status"] == (
        "PENDING"
    )
