from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.payments.infrastructure.models import OperationalPaymentCategory


def _login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.json()
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_ADMIN_EMAIL, password=SEED_ADMIN_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def _cashier_headers(client: TestClient) -> dict[str, str]:
    token = _login(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
    return str(product.id)


def _get_category_code(code: str) -> str:
    with SessionLocal() as session:
        category = session.execute(
            select(OperationalPaymentCategory).where(OperationalPaymentCategory.code == code)
        ).scalar_one()
    return str(category.code)


def _open_cash_session(client: TestClient, *, opening_amount: str = "150.00") -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_cashier_headers(client),
        json={
            "opening_amount": opening_amount,
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )
    assert response.status_code == 201, response.json()


def _confirm_direct_sale(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/v1/sales/confirm",
        headers=_cashier_headers(client),
        json={
            "lines": [
                {
                    "capture_mode": "PRODUCT_DIRECT",
                    "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                    "quantity": "1",
                }
            ],
            "payments": [{"payment_method_code": "CASH", "tendered_amount": "100.00"}],
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )
    assert response.status_code == 201, response.json()
    return response.json()


def _commit_return(client: TestClient, *, sale_id: str) -> dict[str, object]:
    source_response = client.get(
        f"/v1/returns/sales/{sale_id}",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_cashier_headers(client),
    )
    assert source_response.status_code == 200, source_response.json()
    line_id = source_response.json()["lines"][0]["id"]

    response = client.post(
        "/v1/returns/commit",
        headers=_cashier_headers(client),
        json={
            "lines": [
                {
                    "disposition_code": "RESTOCK_COUNTER",
                    "original_sale_line_id": line_id,
                    "returned_quantity": "1.000",
                }
            ],
            "original_sale_id": sale_id,
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )
    assert response.status_code == 201, response.json()
    return response.json()


def _create_operational_payment(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/v1/payments",
        headers=_cashier_headers(client),
        json={
            "category_code": _get_category_code("SUPPLIER"),
            "concept": "Compra menor",
            "notes": "Salida de efectivo para flujo.",
            "payee_name": "Proveedor local",
            "payment_method_code": "CASH",
            "total_amount": "25.00",
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )
    assert response.status_code == 201, response.json()
    return response.json()


def _commit_cash_close_with_difference(client: TestClient) -> dict[str, object]:
    summary_response = client.get(
        "/v1/cash-close/summary",
        params={"workstation_code": SEED_WORKSTATION_CODE},
        headers=_cashier_headers(client),
    )
    assert summary_response.status_code == 200, summary_response.json()
    expected_cash = Decimal(str(summary_response.json()["expected_cash_amount"]))
    counted_cash = expected_cash + Decimal("5.00")
    response = client.post(
        "/v1/cash-close/commit",
        headers=_cashier_headers(client),
        json={
            "counter_empty_confirmed": True,
            "counted_payment_methods": [
                {"counted_amount": str(counted_cash), "payment_method_code": "CASH"}
            ],
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()


def _prepare_cash_flow(client: TestClient) -> dict[str, object]:
    _open_cash_session(client)
    sale = _confirm_direct_sale(client)
    payment = _create_operational_payment(client)
    returned = _commit_return(client, sale_id=str(sale["id"]))
    close = _commit_cash_close_with_difference(client)
    return {"close": close, "payment": payment, "return": returned, "sale": sale}


def test_admin_cash_flow_lists_source_movements_metrics_and_trend(client: TestClient) -> None:
    prepared = _prepare_cash_flow(client)
    sale = prepared["sale"]
    headers = _admin_headers(client)

    response = client.get(
        "/v1/admin/cash-flow",
        headers=headers,
        params={
            "branch_id": sale["branch_id"],
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2999-01-01T00:00:00Z",
            "payment_method": "CASH",
        },
    )

    assert response.status_code == 200, response.json()
    payload = response.json()
    assert payload["is_backend_connected"] is True
    source_types = {item["source_type"] for item in payload["items"]}
    assert {"SALE", "RETURN_REFUND", "OPERATIONAL_PAYMENT", "CASH_CUT_DIFFERENCE"}.issubset(
        source_types
    )
    assert Decimal(str(payload["summary"]["inflows_total"])) >= Decimal(str(sale["total_amount"]))
    assert Decimal(str(payload["summary"]["operational_payments_total"])) == Decimal("25.00")
    assert Decimal(str(payload["summary"]["difference_total"])) == Decimal("5.00")
    assert Decimal(str(payload["summary"]["pending_reconciliation_total"])) == Decimal("5.00")
    assert payload["trend"]
    assert payload["filter_options"]["branches"]
    assert payload["filter_options"]["source_types"]

    payment_response = client.get(
        "/v1/admin/cash-flow",
        headers=headers,
        params={"source_type": "OPERATIONAL_PAYMENT"},
    )
    assert payment_response.status_code == 200
    assert payment_response.json()["total"] == 1


def test_admin_cash_flow_detail_links_source_cut_and_reconciliation(client: TestClient) -> None:
    prepared = _prepare_cash_flow(client)
    close_id = str(prepared["close"]["id"])
    headers = _admin_headers(client)

    create_reconciliation_response = client.post(
        "/v1/admin/reconciliation",
        headers=headers,
        json={
            "final_status": "RECONCILED",
            "notes": "Diferencia documentada desde flujo.",
            "reason_code": "CASH_OVER",
            "source_document_id": close_id,
            "source_type": "CASH_CUT",
        },
    )
    assert create_reconciliation_response.status_code == 200, create_reconciliation_response.json()

    list_response = client.get(
        "/v1/admin/cash-flow",
        headers=headers,
        params={
            "reconciliation_state": "RECONCILED",
            "source_type": "CASH_CUT_DIFFERENCE",
        },
    )
    assert list_response.status_code == 200, list_response.json()
    item = list_response.json()["items"][0]

    detail_response = client.get(f"/v1/admin/cash-flow/{item['id']}", headers=headers)

    assert detail_response.status_code == 200, detail_response.json()
    detail = detail_response.json()
    assert detail["overview"]["source_type"] == "CASH_CUT_DIFFERENCE"
    assert detail["reconciliation"]["status"] == "RECONCILED"
    assert detail["source_document_context"]["cash_cut_folio"].startswith("CC-")
    assert detail["financial_classification"]["net_effect"] == "0.00"
    assert any(
        document["document_type"] == "RECONCILIATION" for document in detail["related_documents"]
    )


def test_admin_cash_flow_requires_backoffice_surface(client: TestClient) -> None:
    response = client.get("/v1/admin/cash-flow", headers=_cashier_headers(client))

    assert response.status_code == 403
    assert response.json()["message"] == "Backoffice access is required."
