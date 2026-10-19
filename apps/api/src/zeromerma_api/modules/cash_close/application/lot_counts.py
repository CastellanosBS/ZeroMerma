"""A physical count identifies lots; a class attribution cannot erase counted goods."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.cash_close.application.schemas import (
    CashCloseCountedProductLineRequest,
    CashCloseLotCountView,
    CashCloseReconciliationProductView,
)
from zeromerma_api.modules.cash_close.domain.exceptions import CashCloseConflictError
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    LockedInventoryBalances,
)
from zeromerma_api.modules.inventory.domain.quantities import InventoryLotQuantity
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLot,
    InventoryLotBalance,
)


def decorate_count_lots(
    session: Session,
    branch_id: UUID,
    views: list[CashCloseReconciliationProductView],
) -> list[CashCloseReconciliationProductView]:
    for view in views:
        product = session.get(Product, view.product_id)
        if product is None or not product.lot_tracking_enabled:
            continue
        view.lot_tracking_enabled = True
        view.lots = [
            CashCloseLotCountView(
                lot_id=lot.id,
                lot_code=lot.lot_code,
                expires_at=lot.expires_at,
                expected_quantity=balance.quantity_on_hand,
                reserved_quantity=balance.quantity_reserved,
            )
            for lot, balance in session.execute(
                select(InventoryLot, InventoryLotBalance)
                .join(InventoryLotBalance, InventoryLotBalance.lot_id == InventoryLot.id)
                .where(
                    InventoryLotBalance.branch_id == branch_id,
                    InventoryLotBalance.product_id == view.product_id,
                    InventoryLotBalance.location_code == "COUNTER",
                )
                .order_by(InventoryLot.expires_at.asc().nulls_last(), InventoryLot.id)
            )
        ]
    return views


class CountedLots:
    def __init__(
        self,
        session: Session,
        branch_id: UUID,
        lines: Sequence[CashCloseCountedProductLineRequest],
    ) -> None:
        self.session = session
        self.branch_id = branch_id
        self.counts: dict[UUID, dict[UUID, Decimal]] = {}
        for line in lines:
            product = session.get(Product, line.product_id)
            if product is None:
                raise CashCloseConflictError("The counted product no longer exists.")
            if not product.lot_tracking_enabled:
                if line.lot_counts:
                    raise CashCloseConflictError("Lot counts require a lot-tracked product.")
                continue
            if line.counted_quantity > 0 and not line.lot_counts:
                raise CashCloseConflictError("Count each physical lot before closing this product.")
            counts = {row.lot_id: row.counted_quantity for row in line.lot_counts}
            for lot_id in counts:
                lot = session.get(InventoryLot, lot_id)
                if lot is None or lot.product_id != line.product_id or lot.unidentified:
                    raise CashCloseConflictError("The counted lot lacks valid product identity.")
            self.counts[line.product_id] = counts

    def rows(self, product_id: UUID) -> list[tuple[InventoryLot, InventoryLotBalance]]:
        return [
            (lot, balance)
            for lot, balance in self.session.execute(
                select(InventoryLot, InventoryLotBalance)
                .join(InventoryLotBalance, InventoryLotBalance.lot_id == InventoryLot.id)
                .where(
                    InventoryLotBalance.branch_id == self.branch_id,
                    InventoryLotBalance.product_id == product_id,
                    InventoryLotBalance.location_code == "COUNTER",
                )
                .order_by(InventoryLot.expires_at.asc().nulls_last(), InventoryLot.id)
            )
        ]

    def snapshot(self, product_id: UUID) -> list[dict[str, str]]:
        product = self.session.get(Product, product_id)
        if product is None or not product.lot_tracking_enabled:
            return []
        counts = self.counts.get(product_id, {})
        actual = {lot.id: (lot, balance) for lot, balance in self.rows(product_id)}
        lot_ids = set(counts) | set(actual)
        return [
            {
                "lot_id": str(lot_id),
                "counted_quantity": str(counts.get(lot_id, Decimal(0))),
                "expected_quantity": str(actual[lot_id][1].quantity_on_hand)
                if lot_id in actual
                else "0",
                "reserved_quantity": str(actual[lot_id][1].quantity_reserved)
                if lot_id in actual
                else "0",
            }
            for lot_id in sorted(lot_ids, key=str)
        ]

    def attribute(
        self,
        product_id: UUID,
        quantity: Decimal,
        sold_at: datetime,
        *,
        balances: LockedInventoryBalances,
    ) -> list[InventoryLotQuantity] | None:
        product = self.session.get(Product, product_id)
        if product is None or not product.lot_tracking_enabled:
            return None
        counts = self.counts.get(product_id, {})
        selected = []
        pending = quantity
        for lot, balance in self.rows(product_id):
            if lot.unidentified or (lot.expires_at is not None and lot.expires_at <= sold_at):
                continue
            deficit = max(Decimal(0), balance.quantity_on_hand - counts.get(lot.id, Decimal(0)))
            eligible = balances.eligible_lot_quantity_at(
                InventoryBalanceKey(self.branch_id, product_id, "COUNTER"), lot.id, sold_at
            )
            take = min(pending, deficit, eligible)
            if take > 0:
                selected.append(InventoryLotQuantity(lot.id, take))
                pending -= take
            if not pending:
                break
        if pending:
            raise CashCloseConflictError(
                "Counted lots cannot explain this class sale's physical quantity."
            )
        return selected

    def discrepancy(self, product_id: UUID, delta: Decimal) -> list[InventoryLotQuantity] | None:
        product = self.session.get(Product, product_id)
        if product is None or not product.lot_tracking_enabled:
            return None
        actual = {lot.id: balance.quantity_on_hand for lot, balance in self.rows(product_id)}
        counted = self.counts.get(product_id, {})
        selected = []
        for lot_id in sorted(set(actual) | set(counted), key=str):
            difference = counted.get(lot_id, Decimal(0)) - actual.get(lot_id, Decimal(0))
            if difference == 0:
                continue
            if (difference > 0) != (delta > 0):
                raise CashCloseConflictError(
                    "Mixed lot differences require explicit inventory reconciliation "
                    "before closing."
                )
            selected.append(InventoryLotQuantity(lot_id, abs(difference)))
        if sum((row.quantity for row in selected), Decimal(0)) != abs(delta):
            raise CashCloseConflictError(
                "The physical lot count does not reconcile with the closing adjustment."
            )
        return selected

    def verify(self, product_ids: Sequence[UUID]) -> None:
        for product_id in product_ids:
            product = self.session.get(Product, product_id)
            if product is None or not product.lot_tracking_enabled:
                continue
            actual = {lot.id: balance.quantity_on_hand for lot, balance in self.rows(product_id)}
            counted = self.counts.get(product_id, {})
            if any(
                actual.get(lot_id, Decimal(0)) != counted.get(lot_id, Decimal(0))
                for lot_id in set(actual) | set(counted)
            ):
                raise CashCloseConflictError("The remaining lots differ from the physical count.")

    def validate_projection(self, product_id: UUID, attributed_quantity: Decimal) -> None:
        """Reject incompatible lot counts without mutating a preview's stock projections."""
        product = self.session.get(Product, product_id)
        if product is None or not product.lot_tracking_enabled:
            return
        counts = self.counts.get(product_id, {})
        pending = attributed_quantity
        differences = []
        known = set()
        for lot, balance in self.rows(product_id):
            known.add(lot.id)
            counted = counts.get(lot.id, Decimal(0))
            if counted < balance.quantity_reserved:
                raise CashCloseConflictError(
                    "The count is below reserved stock. Resolve the affected reservation first."
                )
            deficit = max(Decimal(0), balance.quantity_on_hand - counted)
            take = min(pending, deficit)
            pending -= take
            differences.append(counted - (balance.quantity_on_hand - take))
        if pending:
            raise CashCloseConflictError("The counted lots cannot explain the class attribution.")
        differences.extend(count for lot_id, count in counts.items() if lot_id not in known)
        if any(value < 0 for value in differences) and any(value > 0 for value in differences):
            raise CashCloseConflictError(
                "Mixed lot differences require explicit inventory reconciliation before closing."
            )


def historical_count_lots(
    session: Session, snapshot: list[dict[str, str]]
) -> list[CashCloseLotCountView]:
    result = []
    for row in snapshot:
        lot = session.get(InventoryLot, UUID(row["lot_id"]))
        if lot is None:
            raise CashCloseConflictError("The immutable counted lot identity is missing.")
        result.append(
            CashCloseLotCountView(
                lot_id=lot.id,
                lot_code=lot.lot_code,
                expires_at=lot.expires_at,
                expected_quantity=Decimal(row["expected_quantity"]),
                reserved_quantity=Decimal(row["reserved_quantity"]),
                counted_quantity=Decimal(row["counted_quantity"]),
            )
        )
    return result
