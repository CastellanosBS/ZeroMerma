"""Sale, class attribution, closing and return physical effects in disposable PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.financial_ledger.infrastructure.models import FinancialOperation
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.infrastructure.attribution_models import (
    ClassInventoryObligation,
)
from zeromerma_api.modules.inventory.infrastructure.lot_models import InventoryLotBalance
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn
from zeromerma_api.modules.sales.infrastructure.models import Sale, SaleLine
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.inventory import seed_test_inventory
from zeromerma_api.testing.sessions import login_headers


def _setup(
    client: TestClient, *, stock: str = "4", lots: bool = False, class_sale: bool = False
) -> tuple[dict[str, str], dict[str, Any]]:
    with SessionLocal() as session:
        station = session.scalar(
            select(Workstation).where(Workstation.code == SEED_WORKSTATION_CODE)
        )
        actor = session.scalar(select(User.id).where(User.email == SEED_USER_EMAIL))
        product = session.scalar(
            select(Product).where(
                Product.code
                == (SEED_PRODUCT_CONCHA_VAN_CODE if class_sale else SEED_PRODUCT_COCA_355_CODE)
            )
        )
        assert station and actor and product
        product.lot_tracking_enabled = lots
        product.expiry_required = lots
        identity = {
            "branch_id": str(station.branch_id),
            "product_id": str(product.id),
            "product_class_id": str(product.product_class_id),
        }
        session.commit()
        if Decimal(stock):
            seed_test_inventory(
                session,
                branch_id=station.branch_id,
                actor_user_id=actor,
                product_quantities={product.id: Decimal(stock)},
                location_code="COUNTER",
                fixture_reference="sale-physical-acceptance",
                unit_cost=Decimal("3"),
            )
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    response = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "100.00"},
    )
    assert response.status_code == 201, response.text
    return headers, {
        **identity,
        "cash_session_id": response.json()["id"],
        "workstation_code": SEED_WORKSTATION_CODE,
    }


def _sale(
    client: TestClient,
    headers: dict[str, str],
    context: dict[str, Any],
    *,
    quantity: str = "1",
    class_sale: bool = False,
    key: str | None = None,
) -> Any:
    line = {
        "capture_mode": "CLASS_CAPTURE" if class_sale else "PRODUCT_DIRECT",
        "quantity": quantity,
        "product_class_id" if class_sale else "product_id": context[
            "product_class_id" if class_sale else "product_id"
        ],
    }
    return client.post(
        "/v1/sales/confirm",
        headers={**headers, "Idempotency-Key": key or new_idempotency_key()},
        json={
            "cash_session_id": context["cash_session_id"],
            "workstation_code": context["workstation_code"],
            "lines": [line],
            "payments": [{"payment_method_code": "CASH", "tendered_amount": "100.00"}],
        },
    )


def _quantity(context: dict[str, Any], location: str = "COUNTER") -> Decimal:
    with SessionLocal() as session:
        return session.scalar(
            select(InventoryBalance.quantity_on_hand).where(
                InventoryBalance.branch_id == UUID(context["branch_id"]),
                InventoryBalance.product_id == UUID(context["product_id"]),
                InventoryBalance.location_code == location,
            )
        ) or Decimal(0)


def _line(sale_id: str) -> str:
    with SessionLocal() as session:
        return str(session.scalar(select(SaleLine.id).where(SaleLine.sale_id == UUID(sale_id))))


def _return(
    client: TestClient,
    headers: dict[str, str],
    context: dict[str, Any],
    sale_id: str,
    allocations: list[dict[str, Any]],
    *,
    key: str | None = None,
) -> Any:
    lookup = client.get(
        f"/v1/returns/sales/{sale_id}",
        headers=headers,
        params={"workstation_code": context["workstation_code"]},
    )
    assert lookup.status_code == 200, lookup.text
    return client.post(
        "/v1/returns/commit",
        headers={**headers, "Idempotency-Key": key or new_idempotency_key()},
        json={
            "cash_session_id": context["cash_session_id"],
            "workstation_code": context["workstation_code"],
            "original_sale_id": sale_id,
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "notes": "Inspected synthetic acceptance",
            "lines": [
                {
                    "original_sale_line_id": _line(sale_id),
                    "returned_quantity": str(
                        sum((Decimal(a["quantity"]) for a in allocations), Decimal(0))
                    ),
                    "allocations": [
                        {"exact_product_id": context["product_id"], **a} for a in allocations
                    ],
                }
            ],
        },
    )


def test_direct_sale_debits_once_and_freezes_weighted_cost(client: TestClient) -> None:
    headers, context = _setup(client)
    key = new_idempotency_key()
    first = _sale(client, headers, context, quantity="2", key=key)
    assert first.status_code == 201, first.text
    replay = _sale(client, headers, context, quantity="2", key=key)
    assert replay.json() == first.json() and replay.headers["Idempotency-Replayed"] == "true"
    assert _quantity(context) == Decimal(2)
    with SessionLocal() as session:
        movement = session.scalars(
            select(InventoryMovement).where(InventoryMovement.movement_type == "SALE_DIRECT")
        ).one()
        assert movement.total_cost == Decimal(6) and movement.source_line_id == UUID(
            _line(first.json()["id"])
        )


def test_two_sales_compete_for_last_stock_without_duplicate_finance(client: TestClient) -> None:
    headers, context = _setup(client, stock="1")
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: _sale(client, headers, context), range(2)))
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert _quantity(context) == 0
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Sale)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(FinancialOperation)
                .where(FinancialOperation.source_type == "SALE")
            )
            == 1
        )


def test_rejected_sale_leaves_no_sale_or_physical_effect(client: TestClient) -> None:
    headers, context = _setup(client, stock="1")
    response = _sale(client, headers, context, quantity="2")
    assert response.status_code == 409, response.text
    assert _quantity(context) == 1
    with SessionLocal() as session:
        assert session.scalar(select(Sale.id)) is None
        assert (
            session.scalar(
                select(InventoryMovement.id).where(InventoryMovement.movement_type == "SALE_DIRECT")
            )
            is None
        )


def test_class_partial_attribution_and_close_consume_only_remaining_quantity(
    client: TestClient,
) -> None:
    headers, context = _setup(client, class_sale=True)
    sale = _sale(client, headers, context, quantity="2", class_sale=True)
    assert sale.status_code == 201, sale.text
    assert _quantity(context) == 4
    sale_id = sale.json()["id"]
    command = {
        "workstation_code": context["workstation_code"],
        "cash_session_id": context["cash_session_id"],
        "lines": [
            {"sale_line_id": _line(sale_id), "product_id": context["product_id"], "quantity": "1"}
        ],
    }
    key = new_idempotency_key()
    first = client.post(
        f"/v1/sales/{sale_id}/attribute-inventory",
        headers={**headers, "Idempotency-Key": key},
        json=command,
    )
    assert first.status_code == 200, first.text
    assert (
        client.post(
            f"/v1/sales/{sale_id}/attribute-inventory",
            headers={**headers, "Idempotency-Key": key},
            json=command,
        ).json()
        == first.json()
    )
    assert _quantity(context) == 3
    close = client.post(
        "/v1/cash-close/commit",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": context["workstation_code"],
            "cash_session_id": context["cash_session_id"],
            "counted_payment_methods": [
                {
                    "payment_method_code": "CASH",
                    "counted_amount": str(Decimal(100) + Decimal(sale.json()["total_amount"])),
                }
            ],
            "counted_product_lines": [
                {"product_id": context["product_id"], "counted_quantity": "2"}
            ],
        },
    )
    assert close.status_code == 200, close.text
    assert _quantity(context) == 2
    with SessionLocal() as session:
        obligation = session.scalars(select(ClassInventoryObligation)).one()
        assert obligation.status == "FULFILLED" and obligation.attributed_quantity == 2


def test_split_return_refunds_once_with_separate_physical_allocations(client: TestClient) -> None:
    headers, context = _setup(client)
    sale = _sale(client, headers, context, quantity="2")
    assert sale.status_code == 201, sale.text
    allocations = [
        {
            "quantity": "0.5",
            "disposition_code": "RESTOCK_COUNTER",
            "restock_safe_acknowledged": True,
        },
        {"quantity": "0.5", "disposition_code": "QUARANTINE"},
        {"quantity": "1", "disposition_code": "SEND_TO_WASTE"},
    ]
    key = new_idempotency_key()
    returned = _return(client, headers, context, sale.json()["id"], allocations, key=key)
    assert returned.status_code == 201, returned.text
    assert (
        _return(client, headers, context, sale.json()["id"], allocations, key=key).json()
        == returned.json()
    )
    assert _quantity(context) == Decimal("2.5")
    assert _quantity(context, "QUARANTINE") == Decimal("0.5")
    assert _quantity(context, "WASTE") == 1
    assert (
        _return(
            client,
            headers,
            context,
            sale.json()["id"],
            [{"quantity": "1", "disposition_code": "QUARANTINE"}],
        ).status_code
        == 409
    )
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(SaleReturn)) == 1


def test_tracked_return_requires_inspection_and_original_lot_for_restock(
    client: TestClient,
) -> None:
    headers, context = _setup(client, lots=True)
    sale = _sale(client, headers, context)
    assert sale.status_code == 201, sale.text
    rejected = _return(
        client,
        headers,
        context,
        sale.json()["id"],
        [
            {
                "quantity": "1",
                "disposition_code": "RESTOCK_COUNTER",
                "restock_safe_acknowledged": True,
            }
        ],
    )
    assert rejected.status_code in {400, 409}, rejected.text
    returned = _return(
        client,
        headers,
        context,
        sale.json()["id"],
        [{"quantity": "1", "disposition_code": "QUARANTINE"}],
    )
    assert returned.status_code == 201, returned.text
    admin = owner_headers()
    with SessionLocal() as session:
        lot_id = session.scalar(
            select(InventoryLotBalance.lot_id).where(
                InventoryLotBalance.location_code == "QUARANTINE"
            )
        )
    released = client.post(
        "/v1/admin/inventory-dispositions",
        headers={**admin, "Idempotency-Key": new_idempotency_key()},
        json={
            "branch_id": context["branch_id"],
            "product_id": context["product_id"],
            "kind": "QUARANTINE_RELEASE",
            "destination": "COUNTER",
            "quantity": "1",
            "lot_id": str(lot_id),
            "inspection_passed": True,
            "reason": "Synthetic inspection",
        },
    )
    assert released.status_code == 409, released.text
    assert _quantity(context, "QUARANTINE") == 1


def test_return_physical_compensation_preserves_refund_and_entitlement(client: TestClient) -> None:
    headers, context = _setup(client)
    sale = _sale(client, headers, context)
    returned = _return(
        client,
        headers,
        context,
        sale.json()["id"],
        [
            {
                "quantity": "1",
                "disposition_code": "RESTOCK_COUNTER",
                "restock_safe_acknowledged": True,
            }
        ],
    )
    assert returned.status_code == 201, returned.text
    allocation_id = returned.json()["lines"][0]["allocations"][0]["id"]
    admin = owner_headers()
    command = {
        "branch_id": context["branch_id"],
        "product_id": context["product_id"],
        "kind": "RETURN_CORRECTION",
        "destination": "QUARANTINE",
        "quantity": "1",
        "return_allocation_id": allocation_id,
        "reason": "Quality finding after receipt",
    }
    key = new_idempotency_key()
    response = client.post(
        "/v1/admin/inventory-dispositions", headers={**admin, "Idempotency-Key": key}, json=command
    )
    assert response.status_code == 201, response.text
    assert (
        client.post(
            "/v1/admin/inventory-dispositions",
            headers={**admin, "Idempotency-Key": key},
            json=command,
        ).json()
        == response.json()
    )
    assert (
        client.post(
            "/v1/admin/inventory-dispositions",
            headers={**admin, "Idempotency-Key": new_idempotency_key()},
            json=command,
        ).status_code
        == 409
    )
    assert _quantity(context) == 3 and _quantity(context, "QUARANTINE") == 1
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(SaleReturn)) == 1
        assert session.get(SaleReturn, UUID(returned.json()["id"])).total_refund_amount == Decimal(
            returned.json()["total_refund_amount"]
        )


def test_class_close_requires_lot_count_and_preserves_counted_lot(client: TestClient) -> None:
    headers, context = _setup(client, class_sale=True, lots=True)
    sale = _sale(client, headers, context, quantity="2", class_sale=True)
    assert sale.status_code == 201, sale.text
    with SessionLocal() as session:
        lot_id = session.scalar(
            select(InventoryLotBalance.lot_id).where(
                InventoryLotBalance.product_id == UUID(context["product_id"]),
                InventoryLotBalance.location_code == "COUNTER",
            )
        )
    command = {
        "workstation_code": context["workstation_code"],
        "cash_session_id": context["cash_session_id"],
        "counted_payment_methods": [
            {
                "payment_method_code": "CASH",
                "counted_amount": str(Decimal(100) + Decimal(sale.json()["total_amount"])),
            }
        ],
        "counted_product_lines": [{"product_id": context["product_id"], "counted_quantity": "2"}],
    }
    rejected = client.post(
        "/v1/cash-close/commit",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json=command,
    )
    assert rejected.status_code in {400, 409}, rejected.text
    assert _quantity(context) == 4
    command["counted_product_lines"][0]["lot_counts"] = [
        {"lot_id": str(lot_id), "counted_quantity": "2"}
    ]
    closed = client.post(
        "/v1/cash-close/commit",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json=command,
    )
    assert closed.status_code == 200, closed.text
    assert _quantity(context) == 2
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    detail = client.get(f"/v1/cash-close/{closed.json()['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    counted = next(
        row
        for row in detail.json()["counted_product_lines"]
        if row["product_id"] == context["product_id"]
    )
    assert counted["lot_tracking_enabled"]
    assert counted["lots"][0]["lot_id"] == str(lot_id)
    assert Decimal(counted["lots"][0]["counted_quantity"]) == 2
    assert Decimal(counted["lots"][0]["expected_quantity"]) == 4
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(InventoryLotBalance.quantity_on_hand).where(
                    InventoryLotBalance.lot_id == lot_id,
                    InventoryLotBalance.location_code == "COUNTER",
                )
            )
            == 2
        )


def test_waste_correction_moves_actual_goods_to_quarantine_without_restock(
    client: TestClient,
) -> None:
    headers, context = _setup(client, lots=True)
    with SessionLocal() as session:
        source_lot_id = session.scalar(
            select(InventoryLotBalance.lot_id).where(
                InventoryLotBalance.product_id == UUID(context["product_id"]),
                InventoryLotBalance.location_code == "COUNTER",
            )
        )
    waste = client.post(
        "/v1/operations/waste/commit",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": context["workstation_code"],
            "cash_session_id": context["cash_session_id"],
            "source_bucket_code": "COUNTER",
            "reason_code": "DAMAGED",
            "notes": "Inspected damaged goods",
            "lines": [
                {"product_id": context["product_id"], "quantity": "2", "lot_id": str(source_lot_id)}
            ],
        },
    )
    assert waste.status_code == 201, waste.text
    assert _quantity(context) == 2 and _quantity(context, "WASTE") == 2
    command = {
        "workstation_code": context["workstation_code"],
        "cash_session_id": context["cash_session_id"],
        "target_document_id": waste.json()["id"],
        "reason_code": "WRONG_QUANTITY",
        "notes": "One item needs quality inspection",
        "lines": [{"product_id": context["product_id"], "delta_quantity": "-1"}],
    }
    key = new_idempotency_key()
    corrected = client.post(
        "/v1/corrections/commit", headers={**headers, "Idempotency-Key": key}, json=command
    )
    assert corrected.status_code == 201, corrected.text
    assert (
        client.post(
            "/v1/corrections/commit", headers={**headers, "Idempotency-Key": key}, json=command
        ).json()
        == corrected.json()
    )
    assert _quantity(context) == 2
    assert _quantity(context, "WASTE") == 1 and _quantity(context, "QUARANTINE") == 1
    admin = owner_headers()
    with SessionLocal() as session:
        lot_id = session.scalar(
            select(InventoryLotBalance.lot_id).where(
                InventoryLotBalance.location_code == "QUARANTINE"
            )
        )
    released = client.post(
        "/v1/admin/inventory-dispositions",
        headers={**admin, "Idempotency-Key": new_idempotency_key()},
        json={
            "branch_id": context["branch_id"],
            "product_id": context["product_id"],
            "kind": "QUARANTINE_RELEASE",
            "destination": "COUNTER",
            "quantity": "1",
            "lot_id": str(lot_id),
            "inspection_passed": True,
            "reason": "Quality inspection passed",
        },
    )
    assert released.status_code == 201, released.text
    assert _quantity(context) == 3 and _quantity(context, "QUARANTINE") == 0


def test_unknown_cost_return_preserves_unknown_valuation(client: TestClient) -> None:
    headers, context = _setup(client, stock="0")
    with SessionLocal() as session:
        actor = session.scalar(select(User.id).where(User.email == SEED_USER_EMAIL))
        assert actor
        seed_test_inventory(
            session,
            branch_id=UUID(context["branch_id"]),
            actor_user_id=actor,
            product_quantities={UUID(context["product_id"]): Decimal(1)},
            location_code="COUNTER",
            fixture_reference="unknown-cost-return",
        )
    sale = _sale(client, headers, context)
    assert sale.status_code == 201, sale.text
    returned = _return(
        client,
        headers,
        context,
        sale.json()["id"],
        [{"quantity": "1", "disposition_code": "QUARANTINE"}],
    )
    assert returned.status_code == 201, returned.text
    with SessionLocal() as session:
        movement = session.scalars(
            select(InventoryMovement).where(InventoryMovement.movement_type == "RETURN_QUARANTINE")
        ).one()
        assert movement.total_cost is None and movement.cost_evidence_reference is None


def test_partial_returns_preserve_exact_original_weighted_value(client: TestClient) -> None:
    headers, context = _setup(client, stock="0")
    with SessionLocal() as session:
        actor = session.scalar(select(User.id).where(User.email == SEED_USER_EMAIL))
        assert actor
        for quantity, cost in [(Decimal(1), Decimal(4)), (Decimal(2), Decimal(3))]:
            seed_test_inventory(
                session,
                branch_id=UUID(context["branch_id"]),
                actor_user_id=actor,
                product_quantities={UUID(context["product_id"]): quantity},
                location_code="COUNTER",
                fixture_reference="fractional-weighted-return",
                unit_cost=cost,
            )
    sale = _sale(client, headers, context, quantity="3")
    assert sale.status_code == 201, sale.text
    for _ in range(3):
        returned = _return(
            client,
            headers,
            context,
            sale.json()["id"],
            [
                {"quantity": "1", "disposition_code": "QUARANTINE"},
            ],
        )
        assert returned.status_code == 201, returned.text
    with SessionLocal() as session:
        facts = session.scalars(
            select(InventoryMovement).where(InventoryMovement.movement_type == "RETURN_QUARANTINE")
        ).all()
        assert len(facts) == 3
        assert sum((fact.total_cost for fact in facts), Decimal(0)) == Decimal(10)
        assert session.scalar(
            select(InventoryBalance.inventory_value).where(
                InventoryBalance.product_id == UUID(context["product_id"]),
                InventoryBalance.location_code == "QUARANTINE",
            )
        ) == Decimal(10)


def test_waste_requires_selected_lot_and_does_not_discard_earlier_lot(client: TestClient) -> None:
    headers, context = _setup(client, lots=True)
    admin = owner_headers()
    incoming = client.post(
        "/v1/admin/inventory/adjustments",
        headers={
            **admin,
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "adjustment_type": "INCREASE",
            "branch_id": context["branch_id"],
            "product_id": context["product_id"],
            "location_code": "COUNTER",
            "quantity": "2",
            "reason": "Distinct later physical lot",
            "lot_code": "DAMAGED-LATER",
            "expires_at": (datetime.now(UTC) + timedelta(days=60)).isoformat(),
            "unit_cost": "3",
            "cost_evidence_reference": "synthetic-delivery",
        },
    )
    assert incoming.status_code == 201, incoming.text
    choices = client.get(
        "/v1/admin/waste/stock",
        headers=admin,
        params={
            "branch_id": context["branch_id"],
            "product_id": context["product_id"],
            "location_code": "COUNTER",
        },
    )
    assert choices.status_code == 200, choices.text
    lot = next(row for row in choices.json()["lots"] if row["lot_code"] == "DAMAGED-LATER")
    earlier = next(row for row in choices.json()["lots"] if row["lot_id"] != lot["lot_id"])
    preview = client.post(
        "/v1/cash-close/preview",
        headers=headers,
        json={
            "workstation_code": context["workstation_code"],
            "cash_session_id": context["cash_session_id"],
            "counted_payment_methods": [{"payment_method_code": "CASH", "counted_amount": "100"}],
            "counted_product_lines": [
                {
                    "product_id": context["product_id"],
                    "counted_quantity": "6",
                    "lot_counts": [
                        {"lot_id": earlier["lot_id"], "counted_quantity": "3"},
                        {"lot_id": lot["lot_id"], "counted_quantity": "3"},
                    ],
                }
            ],
        },
    )
    assert preview.status_code == 200, preview.text
    assert "LOT_COUNT_MISMATCH" in {row["code"] for row in preview.json()["blockers"]}
    assert _quantity(context) == 6
    command = {
        "workstation_code": context["workstation_code"],
        "cash_session_id": context["cash_session_id"],
        "source_bucket_code": "COUNTER",
        "reason_code": "DAMAGED",
        "notes": "Physical damaged lot",
        "lines": [{"product_id": context["product_id"], "quantity": "1"}],
    }
    rejected = client.post(
        "/v1/operations/waste/commit",
        headers={
            **headers,
            "Idempotency-Key": new_idempotency_key(),
        },
        json=command,
    )
    assert rejected.status_code == 409, rejected.text
    assert _quantity(context) == 6
    command["lines"][0]["lot_id"] = lot["lot_id"]
    accepted = client.post(
        "/v1/operations/waste/commit",
        headers={
            **headers,
            "Idempotency-Key": new_idempotency_key(),
        },
        json=command,
    )
    assert accepted.status_code == 201, accepted.text
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(InventoryLotBalance.quantity_on_hand).where(
                    InventoryLotBalance.lot_id == UUID(lot["lot_id"]),
                    InventoryLotBalance.location_code == "COUNTER",
                )
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.sum(InventoryLotBalance.quantity_on_hand)).where(
                    InventoryLotBalance.product_id == UUID(context["product_id"]),
                    InventoryLotBalance.lot_id != UUID(lot["lot_id"]),
                    InventoryLotBalance.location_code == "COUNTER",
                )
            )
            == 4
        )
    corrected = client.post(
        "/v1/corrections/commit",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": context["workstation_code"],
            "cash_session_id": context["cash_session_id"],
            "target_document_id": accepted.json()["id"],
            "reason_code": "WRONG_QUANTITY",
            "notes": "A second damaged item from the same physical lot",
            "lines": [{"product_id": context["product_id"], "delta_quantity": "1"}],
        },
    )
    assert corrected.status_code == 201, corrected.text
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(InventoryLotBalance.quantity_on_hand).where(
                    InventoryLotBalance.lot_id == UUID(lot["lot_id"]),
                    InventoryLotBalance.location_code == "COUNTER",
                )
            )
            == 0
        )
        assert (
            session.scalar(
                select(InventoryLotBalance.quantity_on_hand).where(
                    InventoryLotBalance.lot_id == UUID(lot["lot_id"]),
                    InventoryLotBalance.location_code == "WASTE",
                )
            )
            == 2
        )
    assert _quantity(context) == 4


@pytest.mark.parametrize("lots", [False, True])
def test_return_choices_exclude_receipts_after_original_class_sale(
    client: TestClient, lots: bool
) -> None:
    headers, context = _setup(client, stock="1", class_sale=True, lots=lots)
    sale = _sale(client, headers, context, quantity="2", class_sale=True)
    assert sale.status_code == 201, sale.text
    with SessionLocal() as session:
        actor = session.scalar(select(User.id).where(User.email == SEED_USER_EMAIL))
        assert actor
        seed_test_inventory(
            session,
            branch_id=UUID(context["branch_id"]),
            actor_user_id=actor,
            product_quantities={UUID(context["product_id"]): Decimal(100)},
            location_code="COUNTER",
            fixture_reference="receipt-after-original-sale",
            unit_cost=Decimal(3),
        )
    lookup = client.get(
        f"/v1/returns/sales/{sale.json()['id']}",
        headers=headers,
        params={"workstation_code": context["workstation_code"]},
    )
    assert lookup.status_code == 200, lookup.text
    options = [
        row
        for row in lookup.json()["lines"][0]["physical_options"]
        if row["product_id"] == context["product_id"]
    ]
    assert sum((Decimal(row["remaining_quantity"]) for row in options), Decimal(0)) == 1
    rejected = _return(
        client,
        headers,
        context,
        sale.json()["id"],
        [{"quantity": "2", "disposition_code": "QUARANTINE", "lot_id": options[0]["lot_id"]}],
    )
    assert rejected.status_code == 409, rejected.text
    assert _quantity(context) == 101
    assert _quantity(context, "QUARANTINE") == 0
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(SaleReturn)) == 0


def test_returns_across_lots_preserve_the_entire_original_value(client: TestClient) -> None:
    headers, context = _setup(client, stock="0", lots=True)
    with SessionLocal() as session:
        actor = session.scalar(select(User.id).where(User.email == SEED_USER_EMAIL))
        assert actor
        for index, cost in enumerate(["0.25", "0.25", "0.50"]):
            seed_test_inventory(
                session,
                branch_id=UUID(context["branch_id"]),
                actor_user_id=actor,
                product_quantities={UUID(context["product_id"]): Decimal(1)},
                location_code="COUNTER",
                fixture_reference=f"fractional-cost-lot-{index}",
                unit_cost=Decimal(cost),
            )
        lot_ids = list(
            session.scalars(
                select(InventoryLotBalance.lot_id)
                .where(
                    InventoryLotBalance.product_id == UUID(context["product_id"]),
                    InventoryLotBalance.location_code == "COUNTER",
                )
                .order_by(InventoryLotBalance.lot_id.desc())
            )
        )
    sale = _sale(client, headers, context, quantity="3")
    assert sale.status_code == 201, sale.text
    for lot_id in lot_ids:
        returned = _return(
            client,
            headers,
            context,
            sale.json()["id"],
            [
                {
                    "quantity": "1",
                    "disposition_code": "QUARANTINE",
                    "lot_id": str(lot_id),
                }
            ],
        )
        assert returned.status_code == 201, returned.text
    with SessionLocal() as session:
        returned_costs = list(
            session.scalars(
                select(InventoryMovement.total_cost).where(
                    InventoryMovement.movement_type == "RETURN_QUARANTINE",
                )
            )
        )
        assert sorted(returned_costs) == [
            Decimal("0.33333333"),
            Decimal("0.33333333"),
            Decimal("0.33333334"),
        ]
        assert sum(returned_costs, Decimal(0)) == Decimal(1)
        assert session.scalar(
            select(InventoryBalance.inventory_value).where(
                InventoryBalance.product_id == UUID(context["product_id"]),
                InventoryBalance.location_code == "QUARANTINE",
            )
        ) == Decimal(1)
