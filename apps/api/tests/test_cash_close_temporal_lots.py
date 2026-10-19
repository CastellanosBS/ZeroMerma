"""Closing selects original-sale lots even when a later receipt expires sooner."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_inventory_core import _run
from test_sale_physical_inventory import _sale, _setup

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.quantities import InventoryLotQuantity
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLot,
    InventoryLotBalance,
    InventoryMovementLotAllocation,
)
from zeromerma_api.modules.inventory.infrastructure.models import InventoryMovement
from zeromerma_api.modules.sales.infrastructure.models import Sale
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key


def test_close_attributes_an_older_lot_before_a_later_receipt_with_earlier_expiry(
    client: TestClient,
) -> None:
    headers, context = _setup(client, stock="2", lots=True, class_sale=True)
    with SessionLocal() as session:
        old_lot_id = session.scalars(
            select(InventoryLotBalance.lot_id).where(
                InventoryLotBalance.branch_id == UUID(context["branch_id"]),
                InventoryLotBalance.product_id == UUID(context["product_id"]),
                InventoryLotBalance.location_code == "COUNTER",
            )
        ).one()
    sold = _sale(client, headers, context, class_sale=True)
    assert sold.status_code == 201, sold.text
    receipt = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**owner_headers(), "Idempotency-Key": new_idempotency_key()},
        json={
            "adjustment_type": "INCREASE",
            "branch_id": context["branch_id"],
            "product_id": context["product_id"],
            "location_code": "COUNTER",
            "quantity": "2",
            "reason": "A documented receipt after the original class sale",
            "lot_code": "LATER-RECEIPT-EARLIER-EXPIRY",
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert receipt.status_code == 201, receipt.text
    with SessionLocal() as session:
        later_lot_id = session.scalars(
            select(InventoryLot.id).where(InventoryLot.lot_code == "LATER-RECEIPT-EARLIER-EXPIRY")
        ).one()
    closed = client.post(
        "/v1/cash-close/commit",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": context["workstation_code"],
            "cash_session_id": context["cash_session_id"],
            "counted_payment_methods": [
                {
                    "payment_method_code": "CASH",
                    "counted_amount": str(Decimal(100) + Decimal(sold.json()["total_amount"])),
                }
            ],
            "counted_product_lines": [
                {
                    "product_id": context["product_id"],
                    "counted_quantity": "2",
                    "lot_counts": [
                        {"lot_id": str(old_lot_id), "counted_quantity": "1"},
                        {"lot_id": str(later_lot_id), "counted_quantity": "1"},
                    ],
                }
            ],
            "manual_reconciliation_overrides": [
                {
                    "product_class_id": context["product_class_id"],
                    "attribution_lines": [
                        {"product_id": context["product_id"], "attributed_quantity": "1"}
                    ],
                    "notes": "One earlier item sold; another later item discarded",
                }
            ],
            "discrepancy_resolutions": [
                {
                    "product_id": context["product_id"],
                    "resolution_type": "CLOSE_WASTE_ADJUSTMENT",
                    "reason_code": "UNREGISTERED_WASTE",
                    "quantity": "1",
                    "notes": "The missing item from the later receipt was discarded",
                }
            ],
        },
    )
    assert closed.status_code == 200, closed.text
    with SessionLocal() as session:
        sale_allocations = session.scalars(
            select(InventoryMovementLotAllocation)
            .join(
                InventoryMovement,
                InventoryMovement.id == InventoryMovementLotAllocation.movement_id,
            )
            .where(InventoryMovement.movement_type == "SALE_CLASS_ATTRIBUTION")
        ).all()
        assert len(sale_allocations) == 1
        assert sale_allocations[0].lot_id == old_lot_id and sale_allocations[0].quantity == 1
        lots = {
            (row.lot_id, row.location_code): row.quantity_on_hand
            for row in session.scalars(select(InventoryLotBalance))
        }
        assert lots[old_lot_id, "COUNTER"] == 1
        assert lots[later_lot_id, "COUNTER"] == 1
        assert lots[later_lot_id, "WASTE"] == 1
        assert lots.get((old_lot_id, "WASTE"), Decimal(0)) == 0


def test_locked_historical_lot_capacity_includes_pending_outflow_and_reservations(
    client: TestClient,
) -> None:
    headers, context = _setup(client, stock="2", lots=True, class_sale=True)
    sold = _sale(client, headers, context, class_sale=True)
    assert sold.status_code == 201, sold.text
    key = InventoryBalanceKey(UUID(context["branch_id"]), UUID(context["product_id"]), "COUNTER")
    with SessionLocal() as session:
        sale = session.get(Sale, UUID(sold.json()["id"]))
        assert sale is not None
        sold_at = sale.confirmed_at
        actor = session.scalars(select(User.id)).first()
        assert actor is not None
        lot_id = session.scalars(
            select(InventoryLotBalance.lot_id).where(
                InventoryLotBalance.branch_id == key.branch_id,
                InventoryLotBalance.product_id == key.product_id,
                InventoryLotBalance.location_code == key.location_code,
            )
        ).one()
    receipt = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**owner_headers(), "Idempotency-Key": new_idempotency_key()},
        json={
            "adjustment_type": "INCREASE",
            "branch_id": context["branch_id"],
            "product_id": context["product_id"],
            "location_code": "COUNTER",
            "quantity": "2",
            "reason": "Later receipt of the same documentary lot",
            "lot_id": str(lot_id),
        },
    )
    assert receipt.status_code == 201, receipt.text

    def action(session: Session) -> list[UUID]:
        balances = lock_inventory_balances(session, [key])
        assert balances.eligible_lot_quantity_at(key, lot_id, sold_at) == 2
        product = session.get(Product, key.product_id)
        assert product is not None
        unit = product.unit_of_measure
        movement = balances.apply_delta(
            key,
            delta=Decimal(-1),
            movement_type="MANUAL_ADJUSTMENT",
            unit_of_measure=unit,
            source_document_type="SYNTHETIC_COUNT",
            source_document_id=uuid4(),
            source_line_id=None,
            causal_effect_code="pending-outflow",
            operator_user_id=actor,
            reason="Pending canonical count evidence",
            notes=None,
            lot_allocations=[InventoryLotQuantity(lot_id, Decimal(1))],
        )
        assert movement in session.new
        assert balances.eligible_lot_quantity_at(key, lot_id, sold_at) == 1
        assert movement in session.new
        reservation = balances.reserve(
            key,
            quantity=Decimal(1),
            unit_of_measure=unit,
            source_document_type="SYNTHETIC_PLAN",
            source_document_id=uuid4(),
            source_line_id=None,
            causal_effect_code="pending-reservation",
            operator_user_id=actor,
        )
        assert balances.eligible_lot_quantity_at(key, lot_id, sold_at) == 0
        assert movement in session.new and reservation in session.new
        return [movement.id, reservation.id]

    _run(key, actor, action)
