from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn
from zeromerma_api.modules.sales.infrastructure.models import Sale


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
    response = client.post(
        "/v1/sales/confirm",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {
                    "capture_mode": "CLASS_CAPTURE",
                    "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE),
                    "quantity": "2",
                },
                {
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
        "X-Request-ID": "tickets-reprint-request",
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
                AuditLog.action == "ticket.reprinted",
                AuditLog.resource_id == str(sale_record.id),
            )
        ).scalar_one()

    assert audit_record.request_id == "tickets-reprint-request"
    assert audit_record.metadata_["folio"].startswith("TCK-")


def test_ticket_lookup_requires_open_cash_session(client: TestClient) -> None:
    response = client.get(
        f"/v1/tickets?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
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

    return_response = client.post(
        "/v1/returns/commit",
        headers=headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_payload["id"],
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": product_direct_line_id,
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
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
