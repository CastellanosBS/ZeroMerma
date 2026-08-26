from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_DESTINATION_BRANCH_CODE,
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_PRODUCT_CAFE_AMERICANO_CODE,
    SEED_PRODUCT_CLASS_BOLILLO_CODE,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
    WasteReason,
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


def _open_cash_session(client: TestClient, workstation_code: str = SEED_WORKSTATION_CODE) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_authorization_header(client),
        json={
            "workstation_code": workstation_code,
            "opening_amount": "150.00",
        },
    )
    assert response.status_code == 201


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
    return str(product.id)


def _get_product_class_id(code: str) -> str:
    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == code)
        ).scalar_one()
    return str(product_class.id)


def _get_branch_id(code: str) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
    return str(branch.id)


def test_operations_bootstrap_returns_branch_brand_waste_reasons_and_destination_branches(
    client: TestClient,
) -> None:
    response = client.get(
        f"/v1/operations/bootstrap?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["branch"]["code"] == "MAIN"
    assert payload["branch_brand_key"] == "EL_MEJOR_PAN"
    assert [item["code"] for item in payload["waste_reasons"]] == [
        "OLD_COUNTER",
        "DAMAGED",
        "CONTAMINATED",
        "EXPIRED",
        "OTHER",
    ]
    assert payload["waste_reasons"][1]["requires_note"] is True
    assert payload["waste_controls"] == {
        "attachment_evidence_supported": False,
        "high_impact_quantity_threshold": "10",
        "high_impact_requires_acknowledgement": True,
        "high_impact_requires_note": True,
        "stock_validated_source_bucket_codes": ["COUNTER"],
    }
    assert payload["destination_branches"][0]["code"] == SEED_DESTINATION_BRANCH_CODE
    assert payload["destination_branches"][0]["brand_key"] == "MERENNA"


def test_operations_catalog_and_class_products_resolve_exact_products(
    client: TestClient,
) -> None:
    headers = _authorization_header(client)

    catalog_response = client.get(
        "/v1/operations/catalog",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "module": "COUNTER_TRANSFER",
            "query": "concha",
        },
        headers=headers,
    )
    assert catalog_response.status_code == 200
    classes = catalog_response.json()["classes"]
    assert [entry["code"] for entry in classes] == [SEED_PRODUCT_CLASS_PAN_DULCE_CODE]

    class_products_response = client.get(
        f"/v1/operations/classes/{_get_product_class_id(SEED_PRODUCT_CLASS_BOLILLO_CODE)}/products",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "module": "COUNTER_TRANSFER",
            "query": "standard",
        },
        headers=headers,
    )
    assert class_products_response.status_code == 200
    products = class_products_response.json()["products"]
    assert [product["code"] for product in products] == [SEED_PRODUCT_BOLILLO_STD_CODE]


def test_counter_transfer_commit_writes_document_audit_and_outbox(client: TestClient) -> None:
    response = client.post(
        "/v1/operations/counter-transfer/commit",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "phase-3a-counter-transfer",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                    "quantity": "4",
                }
            ],
            "notes": "Restock front counter",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["document_type"] == "COUNTER_TRANSFER"
    assert payload["status"] == "COMMITTED"
    assert payload["source_bucket_code"] == "BACKROOM"
    assert payload["destination_bucket_code"] == "COUNTER"
    assert payload["lines"][0]["product_code_snapshot"] == SEED_PRODUCT_CONCHA_VAN_CODE
    assert Decimal(str(payload["lines"][0]["quantity"])) == Decimal("4")

    with SessionLocal() as session:
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == payload["id"])
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == payload["id"])
        ).scalar_one()

    assert audit_record.action == "counter_transfer.committed"
    assert audit_record.request_id == "phase-3a-counter-transfer"
    assert outbox_event.event_name == "counter_transfer.committed.v1"


def test_counter_transfer_detail_and_history_return_folio_and_filters(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    commit_response = client.post(
        "/v1/operations/counter-transfer/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                    "quantity": "3",
                }
            ],
        },
    )
    assert commit_response.status_code == 201
    document = commit_response.json()

    detail_response = client.get(
        f"/v1/operations/{document['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == document["id"]
    assert detail_payload["folio"].startswith("CTR-")
    assert detail_payload["workstation_code"] == SEED_WORKSTATION_CODE
    assert detail_payload["lines"][0]["product_code_snapshot"] == SEED_PRODUCT_CONCHA_VAN_CODE

    history_response = client.get(
        "/v1/operations/history",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "document_type": "COUNTER_TRANSFER",
            "scope": "CURRENT_SHIFT",
            "created_by_user_id": detail_payload["created_by_user_id"],
            "source_bucket_code": "BACKROOM",
            "destination_bucket_code": "COUNTER",
        },
        headers=_authorization_header(client),
    )
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["scope"] == "CURRENT_SHIFT"
    assert history_payload["records"][0]["id"] == document["id"]
    assert history_payload["records"][0]["folio"] == detail_payload["folio"]
    assert history_payload["records"][0]["line_count"] == 1
    assert Decimal(str(history_payload["records"][0]["total_quantity"])) == Decimal("3.000")
    assert history_payload["available_scopes"] == [
        {"code": "ALL", "label": "Todos"},
        {"code": "CURRENT_SHIFT", "label": "Turno actual"},
        {"code": "TODAY", "label": "Hoy"},
        {"code": "RECENT", "label": "Recientes"},
    ]
    assert history_payload["available_users"][0]["label"] == "Main Branch Cashier"
    assert history_payload["available_source_buckets"] == [
        {"value": "BACKROOM", "label": "BACKROOM"}
    ]
    assert history_payload["available_destination_buckets"] == [
        {"value": "COUNTER", "label": "COUNTER"}
    ]

    all_history_response = client.get(
        "/v1/operations/history",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "document_type": "COUNTER_TRANSFER",
            "scope": "ALL",
            "created_by_user_id": detail_payload["created_by_user_id"],
            "source_bucket_code": "BACKROOM",
            "destination_bucket_code": "COUNTER",
        },
        headers=_authorization_header(client),
    )
    assert all_history_response.status_code == 200
    all_history_payload = all_history_response.json()
    assert all_history_payload["scope"] == "ALL"
    assert any(record["id"] == document["id"] for record in all_history_payload["records"])


def test_waste_commit_requires_exact_product_and_reason_and_writes_audit_and_outbox(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/operations/waste/commit",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "phase-3a-waste",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "source_bucket_code": "COUNTER",
            "reason_code": "DAMAGED",
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "2",
                    "notes": "Tray drop",
                }
            ],
            "notes": "Morning waste review",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["document_type"] == "WASTE_RECORD"
    assert payload["status"] == "COMMITTED"
    assert payload["source_bucket_code"] == "COUNTER"
    assert payload["destination_bucket_code"] == "WASTE"
    assert payload["reason_code"] == "DAMAGED"

    with SessionLocal() as session:
        waste_reason = session.execute(
            select(WasteReason).where(WasteReason.code == payload["reason_code"])
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == payload["id"])
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == payload["id"])
        ).scalar_one()

    assert waste_reason.name == "Damaged"
    assert audit_record.action == "waste_record.committed"
    assert outbox_event.event_name == "waste_record.committed.v1"


def test_waste_commit_requires_operational_notes_for_sensitive_reasons(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/operations/waste/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "source_bucket_code": "COUNTER",
            "reason_code": "DAMAGED",
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "1",
                }
            ],
            "notes": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Operational notes are required for this waste record."


def test_high_impact_waste_requires_acknowledgement_and_emits_alert_outbox(
    client: TestClient,
) -> None:
    missing_ack_response = client.post(
        "/v1/operations/waste/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "source_bucket_code": "COUNTER",
            "reason_code": "OLD_COUNTER",
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "12",
                }
            ],
            "notes": "Large front-counter waste batch.",
            "high_impact_acknowledged": False,
        },
    )

    assert missing_ack_response.status_code == 400
    assert (
        missing_ack_response.json()["detail"]
        == "High-impact waste must be acknowledged before commit."
    )

    response = client.post(
        "/v1/operations/waste/commit",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "phase-3a-waste-high-impact",
        },
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "source_bucket_code": "COUNTER",
            "reason_code": "OLD_COUNTER",
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "12",
                }
            ],
            "notes": "Large front-counter waste batch.",
            "high_impact_acknowledged": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()

    with SessionLocal() as session:
        audit_records = session.execute(
            select(AuditLog)
            .where(AuditLog.resource_id == payload["id"])
            .order_by(AuditLog.action.asc())
        ).scalars().all()
        outbox_events = session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.aggregate_id == payload["id"])
            .order_by(OutboxEvent.event_name.asc())
        ).scalars().all()

    assert [record.action for record in audit_records] == [
        "waste_record.committed",
        "waste_record.high_impact_alert_requested",
    ]
    assert [event.event_name for event in outbox_events] == [
        "waste_record.committed.v1",
        "waste_record.high_impact_alert.v1",
    ]
    assert outbox_events[1].payload["notification_target"] == "backoffice"
    assert outbox_events[1].payload["folio"].startswith("WST-")


def test_waste_history_returns_reason_and_product_filters(client: TestClient) -> None:
    _open_cash_session(client)

    commit_response = client.post(
        "/v1/operations/waste/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "source_bucket_code": "COUNTER",
            "reason_code": "DAMAGED",
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "2",
                }
            ],
            "notes": "History validation waste",
        },
    )
    assert commit_response.status_code == 201
    waste_document = commit_response.json()

    history_response = client.get(
        "/v1/operations/history",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "document_type": "WASTE_RECORD",
            "scope": "CURRENT_SHIFT",
            "created_by_user_id": waste_document["created_by_user_id"],
            "reason_code": "DAMAGED",
            "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
            "source_bucket_code": "COUNTER",
            "destination_bucket_code": "WASTE",
        },
        headers=_authorization_header(client),
    )

    assert history_response.status_code == 200
    payload = history_response.json()
    assert payload["scope"] == "CURRENT_SHIFT"
    assert payload["reason_code"] == "DAMAGED"
    assert payload["product_id"] == _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE)
    assert payload["records"][0]["id"] == waste_document["id"]
    assert payload["records"][0]["folio"].startswith("WST-")
    assert payload["records"][0]["reason_code"] == "DAMAGED"
    assert payload["records"][0]["reason_name"] == "Damaged"
    assert payload["available_reasons"][0] == {"value": "DAMAGED", "label": "Damaged"}
    assert payload["available_products"][0]["value"] == _get_product_id(
        SEED_PRODUCT_BOLILLO_STD_CODE
    )
    assert payload["available_products"][0]["label"].startswith(SEED_PRODUCT_BOLILLO_STD_CODE)


def test_transfer_dispatch_pending_detail_and_receive_work_end_to_end(client: TestClient) -> None:
    headers = {
        **_authorization_header(client),
        "X-Request-ID": "phase-3a-transfer-dispatch",
    }
    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers=headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "6",
                },
                {
                    "product_id": _get_product_id(SEED_PRODUCT_CAFE_AMERICANO_CODE),
                    "quantity": "2",
                },
            ],
            "notes": "Dispatch to north branch",
        },
    )

    assert dispatch_response.status_code == 201
    shipment = dispatch_response.json()["shipment"]
    assert shipment["document_type"] == "BRANCH_TRANSFER_SHIPMENT"
    assert shipment["status"] == "IN_TRANSIT"
    assert shipment["destination_branch_code"] == SEED_DESTINATION_BRANCH_CODE
    assert Decimal(str(shipment["lines"][0]["expected_quantity"])) == Decimal("6.000")
    assert Decimal(str(shipment["lines"][1]["expected_quantity"])) == Decimal("2.000")

    pending_response = client.get(
        "/v1/transfers/inbound/pending",
        params={"workstation_code": SEED_DESTINATION_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert pending_response.status_code == 200
    pending_payload = pending_response.json()
    assert pending_payload["transfers"][0]["id"] == shipment["id"]
    assert pending_payload["transfers"][0]["folio"].startswith("ENV-")
    assert Decimal(str(pending_payload["transfers"][0]["expected_total_quantity"])) == Decimal(
        "8.000"
    )

    detail_response = client.get(
        f"/v1/transfers/{shipment['id']}",
        params={"workstation_code": SEED_DESTINATION_WORKSTATION_CODE},
        headers=_authorization_header(client),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["shipment"]["id"] == shipment["id"]
    assert detail_payload["shipment_summary"]["document_id"] == shipment["id"]
    assert detail_payload["shipment_summary"]["folio"].startswith("ENV-")
    assert (
        Decimal(
            str(detail_payload["shipment_summary"]["quantity_summary"]["expected_total_quantity"])
        )
        == Decimal("8.000")
    )
    assert detail_payload["shipment_summary"]["quantity_summary"]["has_variance"] is False
    assert detail_payload["receipt"] is None
    assert detail_payload["receipt_summary"] is None

    receive_response = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "phase-3a-transfer-receive",
        },
        json={
            "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
            "lines": [
                {
                    "shipment_line_id": shipment["lines"][0]["id"],
                    "expected_quantity": "6",
                    "received_quantity": "6",
                },
                {
                    "shipment_line_id": shipment["lines"][1]["id"],
                    "expected_quantity": "2",
                    "received_quantity": "2",
                },
            ],
            "notes": "Received in full",
        },
    )
    assert receive_response.status_code == 200
    receive_payload = receive_response.json()
    assert receive_payload["shipment"]["status"] == "RECEIVED"
    assert receive_payload["receipt"]["document_type"] == "BRANCH_TRANSFER_RECEIPT"
    assert receive_payload["receipt"]["status"] == "RECEIVED"
    assert receive_payload["receipt"]["reference_document_id"] == shipment["id"]
    assert receive_payload["shipment_summary"]["quantity_summary"]["has_variance"] is False
    assert receive_payload["receipt_summary"]["folio"].startswith("REC-")
    assert receive_payload["receipt_summary"]["linked_shipment_id"] == shipment["id"]
    assert receive_payload["receipt_summary"]["quantity_summary"]["has_variance"] is False
    assert Decimal(str(receive_payload["receipt"]["lines"][0]["received_quantity"])) == Decimal(
        "6.000"
    )
    assert (
        Decimal(
            str(receive_payload["receipt_summary"]["quantity_summary"]["received_total_quantity"])
        )
        == Decimal("8.000")
    )

    with SessionLocal() as session:
        shipment_record = session.execute(
            select(OperationDocument).where(OperationDocument.id == shipment["id"])
        ).scalar_one()
        receipt_record = session.execute(
            select(OperationDocument).where(
                OperationDocument.reference_document_id == shipment_record.id
            )
        ).scalar_one()
        receipt_lines = session.execute(
            select(OperationDocumentLine).where(
                OperationDocumentLine.operation_document_id == receipt_record.id
            )
        ).scalars().all()
        dispatch_outbox = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == shipment["id"])
        ).scalars().all()
        transfer_audit_records = session.execute(
            select(AuditLog)
            .where(AuditLog.action.in_(["transfer.dispatched", "transfer.received"]))
            .order_by(AuditLog.occurred_at.asc())
        ).scalars().all()

    assert shipment_record.status == "RECEIVED"
    assert receipt_record.status == "RECEIVED"
    assert len(receipt_lines) == 2
    assert {event.event_name for event in dispatch_outbox} == {
        "transfer.dispatched.v1",
        "transfer.received.v1",
    }
    assert [record.action for record in transfer_audit_records] == [
        "transfer.dispatched",
        "transfer.received",
    ]
    assert transfer_audit_records[0].request_id == "phase-3a-transfer-dispatch"
    assert transfer_audit_records[1].request_id == "phase-3a-transfer-receive"


def test_transfer_dispatch_history_returns_folio_status_and_filters(client: TestClient) -> None:
    _open_cash_session(client)

    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "3",
                }
            ],
            "notes": "History validation shipment",
        },
    )
    assert dispatch_response.status_code == 201
    shipment = dispatch_response.json()["shipment"]

    history_response = client.get(
        "/v1/transfers/outbound/history",
        params={
            "workstation_code": SEED_WORKSTATION_CODE,
            "scope": "CURRENT_SHIFT",
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
        },
        headers=_authorization_header(client),
    )

    assert history_response.status_code == 200
    payload = history_response.json()
    assert payload["scope"] == "CURRENT_SHIFT"
    assert payload["available_destination_branches"][0]["label"] == "North Branch"
    assert payload["records"][0]["id"] == shipment["id"]
    assert payload["records"][0]["folio"].startswith("ENV-")
    assert payload["records"][0]["status"] == "IN_TRANSIT"
    assert payload["records"][0]["destination_branch_code"] == SEED_DESTINATION_BRANCH_CODE
    assert Decimal(str(payload["records"][0]["total_quantity"])) == Decimal("3.000")


def test_transfer_inbound_history_returns_folio_status_and_filters(client: TestClient) -> None:
    _open_cash_session(client, SEED_DESTINATION_WORKSTATION_CODE)

    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "2",
                }
            ],
        },
    )
    assert dispatch_response.status_code == 201
    shipment = dispatch_response.json()["shipment"]

    receive_response = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
            "lines": [
                {
                    "shipment_line_id": shipment["lines"][0]["id"],
                    "expected_quantity": "2",
                    "received_quantity": "2",
                }
            ],
        },
    )
    assert receive_response.status_code == 200
    receipt = receive_response.json()["receipt"]
    history_response = client.get(
        "/v1/transfers/inbound/history",
        params={
            "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
            "scope": "CURRENT_SHIFT",
            "source_branch_id": _get_branch_id("MAIN"),
            "status": "RECEIVED",
        },
        headers=_authorization_header(client),
    )

    assert history_response.status_code == 200
    payload = history_response.json()
    assert payload["scope"] == "CURRENT_SHIFT"
    assert payload["source_branch_id"] == _get_branch_id("MAIN")
    assert payload["status"] == "RECEIVED"
    assert payload["available_source_branches"][0]["label"] == "Main Branch"
    assert payload["available_statuses"][0]["value"] == "RECEIVED"
    assert payload["records"][0]["id"] == receipt["id"]
    assert payload["records"][0]["folio"].startswith("REC-")
    assert payload["records"][0]["status"] == "RECEIVED"
    assert payload["records"][0]["source_branch_code"] == "MAIN"
    assert Decimal(str(payload["records"][0]["total_quantity"])) == Decimal("2.000")


def test_transfer_dispatch_rejects_same_branch_destination(client: TestClient) -> None:
    response = client.post(
        "/v1/transfers/dispatch/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "destination_branch_id": _get_branch_id("MAIN"),
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "1",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Destination branch must differ from the current branch."


def test_transfer_receive_rejects_already_received_transfer(client: TestClient) -> None:
    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "1",
                }
            ],
        },
    )
    assert dispatch_response.status_code == 201
    shipment = dispatch_response.json()["shipment"]

    first_receive = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
            "lines": [
                {
                    "shipment_line_id": shipment["lines"][0]["id"],
                    "expected_quantity": "1",
                    "received_quantity": "1",
                }
            ],
        },
    )
    assert first_receive.status_code == 200

    second_receive = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
            "lines": [
                {
                    "shipment_line_id": shipment["lines"][0]["id"],
                    "expected_quantity": "1",
                    "received_quantity": "1",
                }
            ],
        },
    )
    assert second_receive.status_code == 409
    assert second_receive.json()["detail"] == "Transfer shipment is no longer pending receipt."


def test_transfer_receive_with_variance_marks_receipt_and_shipment(client: TestClient) -> None:
    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "4",
                },
                {
                    "product_id": _get_product_id(SEED_PRODUCT_CAFE_AMERICANO_CODE),
                    "quantity": "2",
                },
            ],
            "notes": "Variance validation shipment",
        },
    )
    assert dispatch_response.status_code == 201
    shipment = dispatch_response.json()["shipment"]

    receive_response = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers={
            **_authorization_header(client),
            "X-Request-ID": "phase-3c-transfer-variance",
        },
        json={
            "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
            "lines": [
                {
                    "shipment_line_id": shipment["lines"][0]["id"],
                    "expected_quantity": "4",
                    "received_quantity": "3",
                    "variance_reason": "One unit missing on arrival",
                },
                {
                    "shipment_line_id": shipment["lines"][1]["id"],
                    "expected_quantity": "2",
                    "received_quantity": "2",
                },
            ],
            "notes": "Received with shortage",
        },
    )

    assert receive_response.status_code == 200
    payload = receive_response.json()
    assert payload["shipment"]["status"] == "RECEIVED_WITH_VARIANCE"
    assert payload["receipt"]["status"] == "RECEIVED_WITH_VARIANCE"
    assert payload["receipt_summary"]["linked_shipment_id"] == shipment["id"]
    assert payload["receipt_summary"]["quantity_summary"]["has_variance"] is True
    assert payload["receipt_summary"]["quantity_summary"]["variance_line_count"] == 1
    assert Decimal(
        str(payload["receipt_summary"]["quantity_summary"]["expected_total_quantity"])
    ) == Decimal("6.000")
    assert Decimal(
        str(payload["receipt_summary"]["quantity_summary"]["received_total_quantity"])
    ) == Decimal("5.000")

    with SessionLocal() as session:
        shipment_record = session.execute(
            select(OperationDocument).where(OperationDocument.id == shipment["id"])
        ).scalar_one()
        receipt_record = session.execute(
            select(OperationDocument).where(
                OperationDocument.reference_document_id == shipment_record.id
            )
        ).scalar_one()
        outbox_events = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == shipment["id"],
                OutboxEvent.event_name == "transfer.received.v1",
            )
        ).scalars().all()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "transfer.received",
                AuditLog.resource_id == str(receipt_record.id),
            )
        ).scalar_one()

    assert shipment_record.status == "RECEIVED_WITH_VARIANCE"
    assert receipt_record.status == "RECEIVED_WITH_VARIANCE"
    assert len(outbox_events) == 1
    assert audit_record.request_id == "phase-3c-transfer-variance"


def test_transfer_receive_requires_variance_reason_when_quantity_differs(
    client: TestClient,
) -> None:
    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "4",
                }
            ],
        },
    )
    assert dispatch_response.status_code == 201
    shipment = dispatch_response.json()["shipment"]

    receive_response = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
            "lines": [
                {
                    "shipment_line_id": shipment["lines"][0]["id"],
                    "expected_quantity": "4",
                    "received_quantity": "3",
                }
            ],
        },
    )

    assert receive_response.status_code == 400
    assert receive_response.json()["detail"] == (
        "Variance reason is required when the received quantity differs from the shipment."
    )
