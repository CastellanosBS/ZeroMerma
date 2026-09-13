from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.testing.authorization import owner_headers


def _login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    return owner_headers()


def _cashier_headers(client: TestClient) -> dict[str, str]:
    return {
        "Authorization": "Bearer "
        + _login(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    }


def _open_cash_session(client: TestClient) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_cashier_headers(client),
        json={"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "150.00"},
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
        headers=_cashier_headers(client),
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
            "payments": [{"payment_method_code": "CASH", "tendered_amount": "100.00"}],
        },
    )
    assert response.status_code == 201
    return response.json()


def _commit_return(client: TestClient, sale_id: str) -> dict[str, object]:
    sale_detail = client.get(
        f"/v1/returns/sales/{sale_id}",
        headers=_cashier_headers(client),
        params={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert sale_detail.status_code == 200
    direct_line = next(
        line for line in sale_detail.json()["lines"] if line["capture_mode"] == "PRODUCT_DIRECT"
    )
    response = client.post(
        "/v1/returns/commit",
        headers=_cashier_headers(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "original_sale_id": sale_id,
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "notes": "Consulta Backoffice",
            "lines": [
                {
                    "original_sale_line_id": direct_line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def _commit_counter_transfer(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/v1/operations/counter-transfer/commit",
        headers=_cashier_headers(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": [
                {"product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE), "quantity": "4"}
            ],
            "notes": "Documento para correccion admin",
        },
    )
    assert response.status_code == 201
    return response.json()


def _commit_correction(client: TestClient, target: dict[str, object]) -> dict[str, object]:
    line = target["lines"][0]
    response = client.post(
        "/v1/corrections/commit",
        headers=_cashier_headers(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "target_document_id": target["id"],
            "reason_code": "WRONG_QUANTITY",
            "notes": "Ajuste consultado por Backoffice",
            "lines": [
                {
                    "target_line_id": line["id"],
                    "product_id": line["product_id"],
                    "delta_quantity": "-1",
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_admin_returns_list_and_detail_use_real_return_records(client: TestClient) -> None:
    _open_cash_session(client)
    sale = _confirm_sale(client)
    sale_return = _commit_return(client, str(sale["id"]))
    headers = _admin_headers(client)

    list_response = client.get(
        "/v1/admin/returns-corrections/returns",
        headers=headers,
        params={"search": sale_return["folio"], "refund_method": "CASH", "status": "COMMITTED"},
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["is_backend_connected"] is True
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == sale_return["id"]
    assert payload["items"][0]["original_ticket_folio"].startswith("TCK-")
    assert Decimal(str(payload["metrics"]["refunded_amount"])) == Decimal("18.00")
    assert payload["filter_options"]["branches"]
    assert payload["filter_options"]["refund_methods"][0]["id"] == "CASH"

    detail_response = client.get(
        f"/v1/admin/returns-corrections/returns/{sale_return['id']}",
        headers=headers,
    )

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["overview"]["folio"] == sale_return["folio"]
    assert detail["original_ticket"]["folio"].startswith("TCK-")
    assert detail["refund_impact"]["cash_impact_amount"] == "18.00"
    assert detail["returned_lines"][0]["product_name"]
    assert detail["related_documents"][0]["document_type"] == "ticket"
    assert detail["available_actions"]["can_create_from_backoffice"] is False


def test_admin_corrections_list_and_detail_use_real_correction_records(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    target = _commit_counter_transfer(client)
    correction = _commit_correction(client, target)
    headers = _admin_headers(client)

    list_response = client.get(
        "/v1/admin/returns-corrections/corrections",
        headers=headers,
        params={
            "search": correction["folio"],
            "target_document_type": "COUNTER_TRANSFER",
            "net_effect": "NEGATIVE",
            "status": "COMMITTED",
        },
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == correction["id"]
    assert payload["items"][0]["original_document_folio"].startswith("CTR-")
    assert payload["items"][0]["net_effect"] == "NEGATIVE"
    assert payload["filter_options"]["target_document_types"]
    assert payload["filter_options"]["reasons"]

    detail_response = client.get(
        f"/v1/admin/returns-corrections/corrections/{correction['id']}",
        headers=headers,
    )

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["overview"]["folio"] == correction["folio"]
    assert detail["original_document"]["folio"].startswith("CTR-")
    assert detail["affected_lines"][0]["original_quantity"] == "4.000"
    assert detail["affected_lines"][0]["corrected_quantity"] == "3.000"
    assert detail["reason_notes"]["reason_code"] == "WRONG_QUANTITY"
    assert detail["net_effect"]["cash_effect"] == "Sin impacto directo de caja"
    assert detail["available_actions"]["can_create_from_backoffice"] is False


def test_admin_returns_corrections_require_backoffice_surface(client: TestClient) -> None:
    cashier_headers = _cashier_headers(client)

    returns_response = client.get(
        "/v1/admin/returns-corrections/returns",
        headers=cashier_headers,
    )
    corrections_response = client.get(
        "/v1/admin/returns-corrections/corrections",
        headers=cashier_headers,
    )

    assert returns_response.status_code == 403
    assert corrections_response.status_code == 403
    assert returns_response.json()["message"] == "This application surface is not authorized."
