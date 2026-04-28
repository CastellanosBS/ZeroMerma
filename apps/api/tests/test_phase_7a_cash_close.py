from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_DESTINATION_BRANCH_CODE,
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.cash.domain.constants import CASH_SESSION_STATUS_OPEN
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.cash_close.infrastructure.models import CashSessionClose
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass


def _login(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _authorization_header(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login(client)}"}


def _open_cash_session(
    client: TestClient, *, workstation_code: str = SEED_WORKSTATION_CODE
) -> None:
    response = client.post(
        "/v1/cash-sessions/open",
        headers=_authorization_header(client),
        json={
            "workstation_code": workstation_code,
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


def _get_branch_id(code: str) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
    return str(branch.id)


def _confirm_sale(
    client: TestClient,
    *,
    lines: list[dict[str, str]],
    tendered_amount: str,
) -> None:
    response = client.post(
        "/v1/sales/confirm",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "lines": lines,
            "payments": [
                {
                    "payment_method_code": "CASH",
                    "tendered_amount": tendered_amount,
                }
            ],
        },
    )
    assert response.status_code == 201


def test_cash_close_bootstrap_reports_blockers_and_payment_method_catalog(
    client: TestClient,
) -> None:
    response = client.get(
        f"/v1/cash-close/bootstrap?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_open_cash_session"] is None
    assert payload["can_start_close"] is False
    assert [item["code"] for item in payload["blockers"]] == ["NO_ACTIVE_OPEN_CASH_SESSION"]
    assert [item["payment_method_code"] for item in payload["payment_method_catalog"]] == [
        "CASH",
        "CARD",
        "MIXED",
    ]
    assert payload["baseline_snapshot"]["is_available"] is False
    assert payload["pending_class_capture"]["has_pending_class_capture"] is False


def test_cash_close_summary_aggregates_movements_and_pending_class_capture(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    _confirm_sale(
        client,
        lines=[
            {
                "capture_mode": "CLASS_CAPTURE",
                "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE),
                "quantity": "2",
            }
        ],
        tendered_amount="50.00",
    )
    _confirm_sale(
        client,
        lines=[
            {
                "capture_mode": "PRODUCT_DIRECT",
                "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
                "quantity": "1",
            }
        ],
        tendered_amount="20.00",
    )

    response = client.get(
        f"/v1/cash-close/summary?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cash_session"]["status"] == "OPEN"
    assert Decimal(str(payload["opening_amount"])) == Decimal("150.00")
    assert Decimal(str(payload["total_cash_in"])) == Decimal("42.00")
    assert Decimal(str(payload["total_cash_out"])) == Decimal("0.00")
    assert Decimal(str(payload["expected_cash_amount"])) == Decimal("192.00")
    assert payload["movement_breakdown"] == [
        {
            "movement_type": "SALE_COLLECTION",
            "direction": "IN",
            "currency_code": "MXN",
            "movement_count": 2,
            "total_amount": "42.00",
        }
    ]
    assert payload["pending_class_capture"]["has_pending_class_capture"] is True
    assert payload["pending_class_capture"]["pending_class_capture_classes_count"] == 1
    assert Decimal(
        str(payload["pending_class_capture"]["pending_class_capture_total_quantity"])
    ) == Decimal("2.000")
    assert payload["reconciliation_status"] == "PENDING"
    assert payload["blockers"] == []


def test_cash_close_preview_is_read_only_and_computes_variance_from_payment_method_totals(
    client: TestClient,
) -> None:
    _open_cash_session(client)
    _confirm_sale(
        client,
        lines=[
            {
                "capture_mode": "CLASS_CAPTURE",
                "product_class_id": _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE),
                "quantity": "2",
            }
        ],
        tendered_amount="50.00",
    )

    response = client.post(
        "/v1/cash-close/preview",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "counted_payment_methods": [
                {"payment_method_code": "CASH", "counted_amount": "174.00"},
                {"payment_method_code": "CARD", "counted_amount": "0.00"},
            ],
            "notes": "Manual preview count",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert Decimal(str(payload["expected_cash_amount"])) == Decimal("174.00")
    assert Decimal(str(payload["counted_cash_amount"])) == Decimal("174.00")
    assert Decimal(str(payload["cash_variance_amount"])) == Decimal("0.00")
    assert payload["notes"] == "Manual preview count"
    assert payload["reconciliation_status"] == "PENDING"
    assert payload["blockers"] == []

    with SessionLocal() as session:
        cash_session = session.execute(select(CashSession)).scalar_one()
        close_rows = session.execute(select(CashSessionClose)).scalars().all()

    assert cash_session.status == CASH_SESSION_STATUS_OPEN
    assert cash_session.closed_at is None
    assert close_rows == []


def test_cash_close_preview_rejects_duplicate_payment_methods(client: TestClient) -> None:
    _open_cash_session(client)

    response = client.post(
        "/v1/cash-close/preview",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "counted_payment_methods": [
                {"payment_method_code": "CASH", "counted_amount": "50.00"},
                {"payment_method_code": "CASH", "counted_amount": "75.00"},
            ],
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "No se puede repetir un metodo de pago en el conteo del cierre."
    )


def test_cash_close_summary_exposes_inbound_and_outbound_transfer_warnings(
    client: TestClient,
) -> None:
    _open_cash_session(client)

    outbound_dispatch = client.post(
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
    assert outbound_dispatch.status_code == 201

    inbound_dispatch = client.post(
        "/v1/transfers/dispatch/commit",
        headers=_authorization_header(client),
        json={
            "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
            "destination_branch_id": _get_branch_id("MAIN"),
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "1",
                }
            ],
        },
    )
    assert inbound_dispatch.status_code == 201

    response = client.get(
        f"/v1/cash-close/summary?workstation_code={SEED_WORKSTATION_CODE}",
        headers=_authorization_header(client),
    )

    assert response.status_code == 200
    warning_codes = [item["code"] for item in response.json()["warnings"]]
    assert warning_codes == [
        "PENDING_INBOUND_TRANSFERS",
        "OUTBOUND_TRANSFERS_IN_TRANSIT",
    ]
