from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ALT_DESTINATION_BRANCH_CODE,
    SEED_DESTINATION_BRANCH_CODE,
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_PRODUCT_CAFE_AMERICANO_CODE,
    SEED_PRODUCT_CLASS_BOLILLO_CODE,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.session_services import SessionService
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
    WasteReason,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers
from zeromerma_api.testing.transfer_operators import transfer_cashier_email


def _login(client: TestClient, workstation_code: str = SEED_WORKSTATION_CODE) -> dict[str, str]:
    return login_headers(
        client,
        email=transfer_cashier_email(workstation_code),
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=workstation_code,
    )


def _authorization_header(
    client: TestClient, workstation_code: str = SEED_WORKSTATION_CODE
) -> dict[str, str]:
    return _login(client, workstation_code)


def _open_cash_session(client: TestClient, workstation_code: str = SEED_WORKSTATION_CODE) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers={
            **_authorization_header(client, workstation_code),
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "workstation_code": workstation_code,
            "opening_amount": "150.00",
        },
    )
    assert response.status_code == 201


def _cash_id(workstation_code: str) -> str:
    with SessionLocal() as session:
        cash = session.scalars(
            select(CashSession)
            .join(Workstation, Workstation.id == CashSession.workstation_id)
            .where(Workstation.code == workstation_code, CashSession.status == "OPEN")
        ).one()
        return str(cash.id)


def _command_detail(client: TestClient, response: object, workstation: str, kind: str) -> dict:
    document_id = response.json()["id"]
    prefix = "transfers" if kind == "transfer" else "operations"
    detail = client.get(
        f"/v1/{prefix}/{document_id}",
        headers=_authorization_header(client, workstation),
        params={"workstation_code": workstation},
    )
    assert detail.status_code == 200, detail.text
    return detail.json()


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
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    response = client.post(
        "/v1/operations/counter-transfer/commit",
        headers={
            **{
                **_authorization_header(client),
                "X-Request-ID": "3f519c50-62ac-5e42-98b9-b64fd727a453",
            },
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    payload = _command_detail(client, response, SEED_WORKSTATION_CODE, "operation")
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
    assert audit_record.request_id == "3f519c50-62ac-5e42-98b9-b64fd727a453"
    assert outbox_event.event_name == "counter_transfer.committed.v1"


def test_counter_transfer_detail_and_history_return_folio_and_filters(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    commit_response = client.post(
        "/v1/operations/counter-transfer/commit",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    document = _command_detail(client, commit_response, SEED_WORKSTATION_CODE, "operation")

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
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    response = client.post(
        "/v1/operations/waste/commit",
        headers={
            **{
                **_authorization_header(client),
                "X-Request-ID": "3d1f44af-4ef3-5587-8bcf-0afc4a43caaf",
            },
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    payload = _command_detail(client, response, SEED_WORKSTATION_CODE, "operation")
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
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    response = client.post(
        "/v1/operations/waste/commit",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    assert response.json()["message"] == "Operational notes are required for this waste record."


def test_high_impact_waste_requires_acknowledgement_and_emits_alert_outbox(
    client: TestClient,
) -> None:
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    missing_ack_response = client.post(
        "/v1/operations/waste/commit",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
        missing_ack_response.json()["message"]
        == "High-impact waste must be acknowledged before commit."
    )

    response = client.post(
        "/v1/operations/waste/commit",
        headers={
            **{
                **_authorization_header(client),
                "X-Request-ID": "42f4394a-080e-5afe-beb4-cb76a5077f36",
            },
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    payload = _command_detail(client, response, SEED_WORKSTATION_CODE, "operation")

    with SessionLocal() as session:
        audit_records = (
            session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == payload["id"])
                .order_by(AuditLog.action.asc())
            )
            .scalars()
            .all()
        )
        outbox_events = (
            session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.aggregate_id == payload["id"])
                .order_by(OutboxEvent.event_name.asc())
            )
            .scalars()
            .all()
        )

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
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    waste_document = _command_detail(client, commit_response, SEED_WORKSTATION_CODE, "operation")

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
    _open_cash_session(client, SEED_DESTINATION_WORKSTATION_CODE)
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    headers = {
        **_authorization_header(client),
        "X-Request-ID": "46820610-99ec-5fc5-8f0b-72a7c8ff416c",
    }
    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    shipment = _command_detail(client, dispatch_response, SEED_WORKSTATION_CODE, "transfer")[
        "shipment"
    ]
    assert shipment["document_type"] == "BRANCH_TRANSFER_SHIPMENT"
    assert shipment["status"] == "IN_TRANSIT"
    assert shipment["destination_branch_code"] == SEED_DESTINATION_BRANCH_CODE
    assert Decimal(str(shipment["lines"][0]["expected_quantity"])) == Decimal("6.000")
    assert Decimal(str(shipment["lines"][1]["expected_quantity"])) == Decimal("2.000")

    pending_response = client.get(
        "/v1/transfers/inbound/pending",
        params={"workstation_code": SEED_DESTINATION_WORKSTATION_CODE},
        headers=_authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE),
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
        headers=_authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["shipment"]["id"] == shipment["id"]
    assert detail_payload["shipment_summary"]["document_id"] == shipment["id"]
    assert detail_payload["shipment_summary"]["folio"].startswith("ENV-")
    assert Decimal(
        str(detail_payload["shipment_summary"]["quantity_summary"]["expected_total_quantity"])
    ) == Decimal("8.000")
    assert detail_payload["shipment_summary"]["quantity_summary"]["has_variance"] is False
    assert detail_payload["receipts"] == []
    assert detail_payload["receipt_summaries"] == []

    receive_response = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers={
            **{
                **_authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE),
                "X-Request-ID": "e68f39eb-2ffb-5a44-8131-cc6d0803ca77",
            },
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "cash_session_id": _cash_id(SEED_DESTINATION_WORKSTATION_CODE),
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
    receive_payload = _command_detail(
        client, receive_response, SEED_DESTINATION_WORKSTATION_CODE, "transfer"
    )
    assert receive_payload["shipment"]["status"] == "RECEIVED"
    assert receive_payload["receipts"][-1]["document_type"] == "BRANCH_TRANSFER_RECEIPT"
    assert receive_payload["receipts"][-1]["status"] == "RECEIVED"
    assert receive_payload["receipts"][-1]["reference_document_id"] == shipment["id"]
    assert receive_payload["shipment_summary"]["quantity_summary"]["has_variance"] is False
    assert receive_payload["receipt_summaries"][-1]["folio"].startswith("REC-")
    assert receive_payload["receipt_summaries"][-1]["linked_shipment_id"] == shipment["id"]
    assert receive_payload["receipt_summaries"][-1]["quantity_summary"]["has_variance"] is False
    assert Decimal(
        str(receive_payload["receipts"][-1]["lines"][0]["received_quantity"])
    ) == Decimal("6.000")
    assert Decimal(
        str(receive_payload["receipt_summaries"][-1]["quantity_summary"]["received_total_quantity"])
    ) == Decimal("8.000")

    with SessionLocal() as session:
        shipment_record = session.execute(
            select(OperationDocument).where(OperationDocument.id == shipment["id"])
        ).scalar_one()
        receipt_record = session.execute(
            select(OperationDocument).where(
                OperationDocument.reference_document_id == shipment_record.id
            )
        ).scalar_one()
        receipt_lines = (
            session.execute(
                select(OperationDocumentLine).where(
                    OperationDocumentLine.operation_document_id == receipt_record.id
                )
            )
            .scalars()
            .all()
        )
        dispatch_outbox = (
            session.execute(select(OutboxEvent).where(OutboxEvent.aggregate_id == shipment["id"]))
            .scalars()
            .all()
        )
        transfer_audit_records = (
            session.execute(
                select(AuditLog)
                .where(AuditLog.action.in_(["transfer.dispatched", "transfer.received"]))
                .order_by(AuditLog.occurred_at.asc())
            )
            .scalars()
            .all()
        )

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
    assert transfer_audit_records[0].request_id == "46820610-99ec-5fc5-8f0b-72a7c8ff416c"
    assert transfer_audit_records[1].request_id == "e68f39eb-2ffb-5a44-8131-cc6d0803ca77"


def test_transfer_dispatch_history_returns_folio_status_and_filters(client: TestClient) -> None:
    _open_cash_session(client)

    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    shipment = _command_detail(client, dispatch_response, SEED_WORKSTATION_CODE, "transfer")[
        "shipment"
    ]

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
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    _open_cash_session(client, SEED_DESTINATION_WORKSTATION_CODE)

    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    shipment = _command_detail(client, dispatch_response, SEED_WORKSTATION_CODE, "transfer")[
        "shipment"
    ]

    receive_response = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers={
            **_authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE),
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "cash_session_id": _cash_id(SEED_DESTINATION_WORKSTATION_CODE),
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
    receipt = _command_detail(
        client, receive_response, SEED_DESTINATION_WORKSTATION_CODE, "transfer"
    )["receipts"][-1]
    history_response = client.get(
        "/v1/transfers/inbound/history",
        params={
            "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
            "scope": "CURRENT_SHIFT",
            "source_branch_id": _get_branch_id("MAIN"),
            "status": "RECEIVED",
        },
        headers=_authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE),
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
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    response = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    assert response.json()["message"] == "Destination branch must differ from the current branch."


def test_transfer_receive_rejects_already_received_transfer(client: TestClient) -> None:
    _open_cash_session(client, SEED_DESTINATION_WORKSTATION_CODE)
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    shipment = _command_detail(client, dispatch_response, SEED_WORKSTATION_CODE, "transfer")[
        "shipment"
    ]

    first_receive = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers={
            **_authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE),
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "cash_session_id": _cash_id(SEED_DESTINATION_WORKSTATION_CODE),
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
        headers={
            **_authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE),
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "cash_session_id": _cash_id(SEED_DESTINATION_WORKSTATION_CODE),
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
    assert second_receive.json()["message"] == "Transfer shipment is no longer pending receipt."


def test_transfer_receive_with_variance_marks_receipt_and_shipment(client: TestClient) -> None:
    _open_cash_session(client, SEED_DESTINATION_WORKSTATION_CODE)
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    shipment = _command_detail(client, dispatch_response, SEED_WORKSTATION_CODE, "transfer")[
        "shipment"
    ]

    receive_response = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers={
            **{
                **_authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE),
                "X-Request-ID": "b5537665-6d30-5666-846e-e9dc76fa4ad0",
            },
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "cash_session_id": _cash_id(SEED_DESTINATION_WORKSTATION_CODE),
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
    payload = _command_detail(
        client, receive_response, SEED_DESTINATION_WORKSTATION_CODE, "transfer"
    )
    assert payload["shipment"]["status"] == "IN_TRANSIT"
    assert payload["receipts"][-1]["status"] == "RECEIVED_WITH_VARIANCE"
    assert payload["receipt_summaries"][-1]["linked_shipment_id"] == shipment["id"]
    assert payload["receipt_summaries"][-1]["quantity_summary"]["has_variance"] is True
    assert payload["receipt_summaries"][-1]["quantity_summary"]["variance_line_count"] == 1
    assert Decimal(
        str(payload["receipt_summaries"][-1]["quantity_summary"]["expected_total_quantity"])
    ) == Decimal("6.000")
    assert Decimal(
        str(payload["receipt_summaries"][-1]["quantity_summary"]["received_total_quantity"])
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
        outbox_events = (
            session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.aggregate_id == shipment["id"],
                    OutboxEvent.event_name == "transfer.received.v1",
                )
            )
            .scalars()
            .all()
        )
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "transfer.received",
                AuditLog.resource_id == str(receipt_record.id),
            )
        ).scalar_one()

    assert shipment_record.status == "IN_TRANSIT"
    assert receipt_record.status == "RECEIVED_WITH_VARIANCE"
    assert len(outbox_events) == 1
    assert audit_record.request_id == "b5537665-6d30-5666-846e-e9dc76fa4ad0"


def test_transfer_receive_requires_variance_reason_when_quantity_differs(
    client: TestClient,
) -> None:
    _open_cash_session(client, SEED_DESTINATION_WORKSTATION_CODE)
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    dispatch_response = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
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
    shipment = _command_detail(client, dispatch_response, SEED_WORKSTATION_CODE, "transfer")[
        "shipment"
    ]

    receive_response = client.post(
        f"/v1/transfers/{shipment['id']}/receive",
        headers={
            **_authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE),
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "cash_session_id": _cash_id(SEED_DESTINATION_WORKSTATION_CODE),
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
    assert receive_response.json()["message"] == (
        "Variance reason is required when the received quantity differs from the shipment."
    )


@pytest.mark.parametrize(
    "scenario",
    [
        "missing_receipt",
        "changed_workstation",
        "changed_notes",
        "foreign_receipt_workstation",
        "foreign_receipt_branch",
        "committed_receipt",
        "rolled_back_receipt",
        "savepoint_rolled_back_receipt",
        "savepoint_rolled_back_transition",
        "deleted_receipt_after_flush",
        "relinked_receipt_after_flush",
        "changed_receipt_status_after_flush",
    ],
)
def test_pos_transfer_receipt_cannot_bypass_workstation_binding(
    client: TestClient, scenario: str
) -> None:
    _open_cash_session(client, SEED_WORKSTATION_CODE)

    dispatch = client.post(
        "/v1/transfers/dispatch/commit",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "cash_session_id": _cash_id(SEED_WORKSTATION_CODE),
            "workstation_code": SEED_WORKSTATION_CODE,
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
            "lines": [
                {"product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE), "quantity": "1"}
            ],
        },
    )
    assert dispatch.status_code == 201
    shipment_id = UUID(
        _command_detail(client, dispatch, SEED_WORKSTATION_CODE, "transfer")["shipment"]["id"]
    )
    destination_headers = _authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE)
    foreign_branch_id = UUID(_get_branch_id(SEED_ALT_DESTINATION_BRANCH_CODE))

    with SessionLocal() as session:
        audit_count = session.scalar(select(func.count(AuditLog.id)))
        outbox_count = session.scalar(select(func.count(OutboxEvent.id)))
        authentication = SessionService().authenticate(
            session,
            credential=destination_headers["Cookie"].split("=", 1)[1],
            audience="POS",
        )
        bind_authorization_scope(
            session,
            user=authentication.user,
            capabilities=("transfers.execute",),
            mutation=True,
            surface="POS",
        )
        shipment = session.get(OperationDocument, shipment_id)
        assert shipment is not None
        original_workstation_id = shipment.workstation_id
        with pytest.raises(HTTPException) as denied:
            if scenario != "missing_receipt":
                savepoint = (
                    session.begin_nested() if scenario.startswith("savepoint_rolled_back") else None
                )
                receipt = OperationDocument(
                    document_type="BRANCH_TRANSFER_RECEIPT",
                    status="RECEIVED",
                    source_branch_id=shipment.source_branch_id,
                    destination_branch_id=(
                        foreign_branch_id
                        if scenario == "foreign_receipt_branch"
                        else shipment.destination_branch_id
                    ),
                    workstation_id=(
                        shipment.workstation_id
                        if scenario == "foreign_receipt_workstation"
                        else authentication.record.workstation_id
                    ),
                    created_by_user_id=authentication.user.id,
                    reference_document_id=shipment.id,
                )
                session.add(receipt)
                session.flush()
                if scenario == "committed_receipt":
                    session.commit()
                elif scenario == "rolled_back_receipt":
                    session.rollback()
                    shipment = session.get(OperationDocument, shipment_id)
                    assert shipment is not None
                elif savepoint is not None:
                    if scenario == "savepoint_rolled_back_transition":
                        shipment.status = "RECEIVED"
                        session.flush()
                    savepoint.rollback()
            if scenario == "changed_workstation":
                assert authentication.record.workstation_id is not None
                shipment.workstation_id = authentication.record.workstation_id
            elif scenario == "changed_notes":
                shipment.notes = "Unauthorized edit alongside receipt"
            shipment.status = "RECEIVED"
            session.flush()
            if scenario == "deleted_receipt_after_flush":
                session.delete(receipt)
                session.commit()
            elif scenario == "relinked_receipt_after_flush":
                receipt.reference_document_id = None
                session.flush()
            elif scenario == "changed_receipt_status_after_flush":
                receipt.status = "IN_TRANSIT"
                session.commit()
        assert denied.value.status_code == 403
        session.rollback()

    with SessionLocal() as session:
        original = session.get(OperationDocument, shipment_id)
        assert original is not None
        assert original.status == "IN_TRANSIT"
        assert original.workstation_id == original_workstation_id
        assert original.notes is None
        assert session.scalar(select(func.count(AuditLog.id))) == audit_count
        assert session.scalar(select(func.count(OutboxEvent.id))) == outbox_count
        assert session.scalar(
            select(func.count(OperationDocument.id)).where(
                OperationDocument.reference_document_id == shipment_id,
                OperationDocument.document_type == "BRANCH_TRANSFER_RECEIPT",
            )
        ) == (1 if scenario == "committed_receipt" else 0)


def test_pos_transfer_receipt_savepoint_rollback_allows_a_fresh_cause(client: TestClient) -> None:
    headers = _authorization_header(client, SEED_DESTINATION_WORKSTATION_CODE)
    with SessionLocal() as session:
        authentication = SessionService().authenticate(
            session, credential=headers["Cookie"].split("=", 1)[1], audience="POS"
        )
        source = session.scalars(
            select(Workstation).where(Workstation.code == SEED_WORKSTATION_CODE)
        ).one()
        destination = session.get(Workstation, authentication.record.workstation_id)
        assert destination is not None
        shipment = OperationDocument(
            document_type="BRANCH_TRANSFER_SHIPMENT",
            status="IN_TRANSIT",
            source_branch_id=source.branch_id,
            destination_branch_id=destination.branch_id,
            workstation_id=source.id,
            created_by_user_id=authentication.user.id,
        )
        session.add(shipment)
        session.commit()
        shipment_id = shipment.id
        bind_authorization_scope(
            session,
            user=authentication.user,
            capabilities=("transfers.execute",),
            mutation=True,
            surface="POS",
        )
        shipment = session.get(OperationDocument, shipment_id)
        assert shipment is not None
        for roll_back in (True, False):
            savepoint = session.begin_nested() if roll_back else None
            receipt = OperationDocument(
                document_type="BRANCH_TRANSFER_RECEIPT",
                status="RECEIVED",
                source_branch_id=shipment.source_branch_id,
                destination_branch_id=shipment.destination_branch_id,
                workstation_id=authentication.record.workstation_id,
                created_by_user_id=authentication.user.id,
                reference_document_id=shipment.id,
            )
            session.add(receipt)
            session.flush()
            shipment.status = "RECEIVED"
            session.flush()
            if savepoint is not None:
                savepoint.rollback()
                assert shipment.status == "IN_TRANSIT"
        session.commit()
        assert session.get(OperationDocument, shipment_id).status == "RECEIVED"
        assert (
            session.scalar(
                select(func.count(OperationDocument.id)).where(
                    OperationDocument.reference_document_id == shipment_id
                )
            )
            == 1
        )


def test_pos_workstation_binding_checks_expired_original_station_in_same_branch(
    client: TestClient,
) -> None:
    headers = _authorization_header(client)
    with SessionLocal() as session:
        authentication = SessionService().authenticate(
            session, credential=headers["Cookie"].split("=", 1)[1], audience="POS"
        )
        station = session.get(Workstation, authentication.record.workstation_id)
        assert station is not None
        other_station = Workstation(
            code="OTHER-POS-SAME-BRANCH", name="Other station", branch_id=station.branch_id
        )
        session.add(other_station)
        session.flush()
        document = OperationDocument(
            document_type="WASTE_RECORD",
            status="COMMITTED",
            source_branch_id=station.branch_id,
            workstation_id=other_station.id,
            created_by_user_id=authentication.user.id,
        )
        session.add(document)
        session.commit()
        document_id, original_station_id = document.id, other_station.id
        bind_authorization_scope(
            session,
            user=authentication.user,
            capabilities=("pos.operate",),
            mutation=True,
            surface="POS",
        )
        document = session.get(OperationDocument, document_id)
        assert document is not None
        session.expire(document, ["workstation_id"])
        assert authentication.record.workstation_id is not None
        document.workstation_id = authentication.record.workstation_id
        document.notes = "Unauthorized station reassignment"
        with pytest.raises(HTTPException) as denied:
            session.flush()
        assert denied.value.status_code == 403
        session.rollback()
    with SessionLocal() as session:
        original = session.get(OperationDocument, document_id)
        assert original is not None
        assert original.workstation_id == original_station_id
        assert original.notes is None
