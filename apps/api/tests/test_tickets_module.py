from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from return_fixtures import seed_return_stock
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn
from zeromerma_api.modules.sales.infrastructure.models import Sale
from zeromerma_api.modules.tickets.infrastructure.models import ReceiptSnapshot
from zeromerma_api.testing.idempotency import current_cash_session_id, new_idempotency_key
from zeromerma_api.testing.sessions import login_headers


def _login(client: TestClient) -> dict[str, str]:
    return login_headers(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS")


def _authorization_header(client: TestClient) -> dict[str, str]:
    return _login(client)


def _open_cash_session(client: TestClient) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers={**_authorization_header(client), "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "150.00",
        },
    )
    assert response.status_code == 201


def _get_product_class_id(code: str) -> str:
    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == code)
        ).scalar_one()
    return str(product_class.id)


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
    return str(product.id)


def _confirm_sale(client: TestClient) -> dict[str, object]:
    seed_return_stock()
    headers = _authorization_header(client)
    cash_session_id = current_cash_session_id(
        client, headers=headers, workstation_code=SEED_WORKSTATION_CODE
    )
    headers["Idempotency-Key"] = new_idempotency_key()

    response = client.post(
        "/v1/sales/confirm",
        headers=headers,
        json={
            "cash_session_id": cash_session_id,
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "expected_unit_price": "12.00",
                    "expected_currency_code": "MXN",
                    "capture_mode": "CLASS_CAPTURE",
                    "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE),
                    "quantity": "2",
                },
                {
                    "expected_unit_price": "18.00",
                    "expected_currency_code": "MXN",
                    "capture_mode": "PRODUCT_DIRECT",
                    "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                    "quantity": "1",
                },
            ],
            "payments": [
                {
                    "payment_method_code": "CASH",
                    "tendered_amount": "100.00",
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_tickets_bootstrap_and_current_shift_lookup(client: TestClient) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    headers = _authorization_header(client)

    bootstrap_response = client.get(
        f"/v1/tickets/bootstrap?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )

    assert bootstrap_response.status_code == 200
    bootstrap_payload = bootstrap_response.json()
    assert bootstrap_payload["ticket_lookup_allowed"] is True
    assert bootstrap_payload["default_scope"] == "CURRENT_SHIFT"
    assert bootstrap_payload["current_open_cash_session"] is not None

    list_response = client.get(
        f"/v1/tickets?workstation_code={SEED_WORKSTATION_CODE}&scope=CURRENT_SHIFT",
        headers=headers,
    )

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["scope"] == "CURRENT_SHIFT"
    assert len(list_payload["tickets"]) == 1
    assert list_payload["tickets"][0]["id"] == sale_payload["id"]
    assert Decimal(str(list_payload["tickets"][0]["total_amount"])) == Decimal("42.00")

    folio = str(list_payload["tickets"][0]["folio"])
    search_response = client.get(
        f"/v1/tickets?workstation_code={SEED_WORKSTATION_CODE}&scope=CURRENT_SHIFT&query={folio}",
        headers=headers,
    )

    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert len(search_payload["tickets"]) == 1
    assert search_payload["tickets"][0]["folio"] == folio


def test_ticket_detail_and_reprint_are_available_in_current_branch_context(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    headers = {
        **_authorization_header(client),
        "X-Request-ID": "39c4ca0e-02e9-5df4-915b-2567bcdaea67",
    }

    detail_response = client.get(
        f"/v1/tickets/{sale_payload['id']}?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["folio"].startswith("TCK-")
    assert detail_payload["can_reprint"] is True
    assert len(detail_payload["lines"]) == 2
    assert Decimal(str(detail_payload["total_amount"])) == Decimal("42.00")
    assert detail_payload["payments"][0]["payment_method_code"] == "CASH"

    reprint_response = client.post(
        f"/v1/tickets/{sale_payload['id']}/reprint",
        headers=headers,
        json={"workstation_code": SEED_WORKSTATION_CODE},
    )

    assert reprint_response.status_code == 200
    assert reprint_response.json()["id"] == sale_payload["id"]

    with SessionLocal() as session:
        sale_record = session.execute(
            select(Sale).where(Sale.id == sale_payload["id"])
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "ticket.reprint_requested",
                AuditLog.resource_id == str(sale_record.id),
            )
        ).scalar_one()

    assert audit_record.request_id == "39c4ca0e-02e9-5df4-915b-2567bcdaea67"
    assert audit_record.metadata_["folio"].startswith("TCK-")


def test_ticket_lookup_requires_open_cash_session(client: TestClient) -> None:
    response = client.get(
        f"/v1/tickets?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )

    assert response.status_code == 409
    assert (
        response.json()["message"]
        == "Necesitas una caja abierta en esta estacion para consultar tickets."
    )


def test_ticket_visual_state_updates_after_sale_return(client: TestClient) -> None:
    _open_cash_session(client)
    sale_payload = _confirm_sale(client)
    headers = _authorization_header(client)
    sale_detail_response = client.get(
        f"/v1/returns/sales/{sale_payload['id']}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=headers,
    )
    assert sale_detail_response.status_code == 200
    product_direct_line_id = sale_detail_response.json()["lines"][1]["id"]

    return_headers = {**headers}
    return_cash_session_id = current_cash_session_id(
        client, headers=return_headers, workstation_code=SEED_WORKSTATION_CODE
    )
    return_headers["Idempotency-Key"] = new_idempotency_key()

    return_response = client.post(
        "/v1/returns/commit",
        headers=return_headers,
        json={
            "cash_session_id": return_cash_session_id,
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": product_direct_line_id,
                    "returned_quantity": "1.000",
                    "allocations": [
                        {
                            "exact_product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                            "quantity": "1.000",
                            "disposition_code": "RESTOCK_COUNTER",
                            "restock_safe_acknowledged": True,
                        }
                    ],
                }
            ],
        },
    )
    assert return_response.status_code == 201

    list_response = client.get(
        f"/v1/tickets?workstation_code={SEED_WORKSTATION_CODE}&scope=CURRENT_SHIFT",
        headers=headers,
    )
    assert list_response.status_code == 200
    ticket = list_response.json()["tickets"][0]
    assert ticket["return_status"] == "PARTIALLY_RETURNED"
    assert ticket["return_count"] == 1
    assert Decimal(str(ticket["returned_amount"])) == Decimal("18.00")
    assert ticket["has_returnable_quantity"] is True

    detail_response = client.get(
        f"/v1/tickets/{sale_payload['id']}?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["return_status"] == "PARTIALLY_RETURNED"
    assert detail_payload["return_count"] == 1
    assert Decimal(str(detail_payload["returned_amount"])) == Decimal("18.00")

    with SessionLocal() as session:
        sale_return = session.execute(
            select(SaleReturn).where(SaleReturn.original_sale_id == sale_payload["id"])
        ).scalar_one()

    assert sale_return.reason_code == "WRONG_ITEM"


def test_receipt_is_frozen_when_current_branch_station_and_actor_change(client: TestClient) -> None:
    _open_cash_session(client)
    sale = _confirm_sale(client)
    headers = _authorization_header(client)
    url = f"/v1/tickets/{sale['id']}?workstation_code={SEED_WORKSTATION_CODE}"
    before = client.get(url, headers=headers).json()["receipt"]
    assert before["source_kind"] == "SALE"
    assert before["folio"] == f"TCK-{UUID(sale['id']).hex.upper()}"
    assert before["currency_code"] == "MXN"
    assert before["seller"]["configuration_status"] == "UNCONFIGURED"
    assert before["fiscal_document"] is False
    assert before["provider_receipt"] is False
    with SessionLocal.begin() as session:
        session.get(Branch, UUID(sale["branch_id"])).name = "Renamed branch"
        session.get(Workstation, UUID(sale["workstation_id"])).name = "Renamed station"
        session.get(User, UUID(sale["operator_id"])).full_name = "Renamed actor"
    after = client.get(url, headers=headers)
    assert after.status_code == 200
    assert after.json()["receipt"] == before
    reprint = client.post(
        f"/v1/tickets/{sale['id']}/reprint",
        headers=headers,
        json={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert reprint.status_code == 200
    assert reprint.json()["receipt"] == before


def test_receipt_cannot_be_updated_or_deleted_in_database(client: TestClient) -> None:
    _open_cash_session(client)
    sale = _confirm_sale(client)
    for statement in (
        "UPDATE receipt_snapshots SET document_sha256 = repeat('0',64) WHERE source_id = :id",
        "DELETE FROM receipt_snapshots WHERE source_id = :id",
    ):
        with pytest.raises(DBAPIError, match="Receipt snapshots are immutable"):
            with SessionLocal.begin() as session:
                session.execute(text(statement), {"id": sale["id"]})


def test_receipt_print_request_replay_only_audits_one_physical_intention(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    sale = _confirm_sale(client)
    headers = {**_authorization_header(client), "Idempotency-Key": new_idempotency_key()}
    url = f"/v1/tickets/receipts/SALE/{sale['id']}/print-request"
    payload = {"workstation_code": SEED_WORKSTATION_CODE, "reason": "Customer requested a copy"}
    first = client.post(url, headers=headers, json=payload)
    assert first.status_code == 200, first.text
    replay = client.post(url, headers=headers, json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert replay.json() == first.json()
    assert first.json()["physical_outcome"] == "NOT_CONFIRMED"
    recovered = client.get(
        f"/v1/tickets/receipts/SALE/{sale['id']}/print-requests/"
        f"{headers['Idempotency-Key']}?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json() == first.json()
    with SessionLocal() as session:
        assert session.scalar(select(func.count(Sale.id))) == 1
        assert session.scalar(select(func.count(ReceiptSnapshot.id))) == 1
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.action == "receipt.print_requested",
                    AuditLog.resource_id == sale["id"],
                )
            )
            == 1
        )
    changed = client.post(url, headers=headers, json={**payload, "reason": "Different intention"})
    assert changed.status_code == 409


def test_missing_historical_receipt_is_not_fabricated_on_read_or_reprint(
    client, monkeypatch
) -> None:
    from zeromerma_api.modules.sales.application import services

    monkeypatch.setattr(services, "snapshot_sale", lambda *_args: None)
    _open_cash_session(client)
    sale = _confirm_sale(client)
    headers = _authorization_header(client)
    response = client.get(
        f"/v1/tickets/{sale['id']}?workstation_code={SEED_WORKSTATION_CODE}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["receipt"] is None
    assert response.json()["can_reprint"] is False
    response = client.post(
        f"/v1/tickets/{sale['id']}/reprint",
        headers=headers,
        json={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert response.status_code == 409
    with SessionLocal() as session:
        assert session.scalar(select(func.count(ReceiptSnapshot.id))) == 0
