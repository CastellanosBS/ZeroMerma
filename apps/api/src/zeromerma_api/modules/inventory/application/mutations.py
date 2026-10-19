from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, SessionTransaction

from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)


@dataclass(frozen=True, order=True)
class InventoryBalanceKey:
    branch_id: uuid.UUID
    product_id: uuid.UUID
    location_code: str


class LockedInventoryBalances:
    """Command-local locked rows; never refresh a row after applying a movement."""

    def __init__(
        self,
        session: Session,
        transaction: SessionTransaction,
        balances: dict[InventoryBalanceKey, InventoryBalance],
    ) -> None:
        self._session = session
        self._transaction = transaction
        self._balances = balances

    def balance(self, key: InventoryBalanceKey) -> InventoryBalance:
        if self._session.get_transaction() is not self._transaction:
            raise RuntimeError("Inventory locks belong to the original transaction.")
        return self._balances[key]

    def quantity(self, key: InventoryBalanceKey) -> Decimal:
        return Decimal(self.balance(key).quantity_on_hand)

    def apply_delta(
        self,
        key: InventoryBalanceKey,
        *,
        delta: Decimal,
        movement_type: str,
        unit_of_measure: str,
        source_document_type: str,
        source_document_id: uuid.UUID,
        operator_user_id: uuid.UUID,
        reason: str | None,
        notes: str | None,
        adjustment_id: uuid.UUID | None = None,
        allow_negative: bool = False,
    ) -> InventoryMovement:
        balance = self.balance(key)
        if not delta.is_finite() or delta == 0:
            raise InventoryValidationError("Inventory movement requires a finite nonzero quantity.")
        quantity = Decimal(balance.quantity_on_hand) + delta
        if delta < 0 and quantity < 0 and not allow_negative:
            raise InventoryValidationError("Inventory stock is insufficient.")
        movement = InventoryMovement(
            id=uuid.uuid4(),
            product_id=key.product_id,
            branch_id=key.branch_id,
            location_code=key.location_code,
            movement_type=movement_type,
            direction="IN" if delta > 0 else "OUT",
            quantity=abs(delta),
            unit_of_measure=unit_of_measure,
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            operator_user_id=operator_user_id,
            reason=reason,
            notes=notes,
            adjustment_id=adjustment_id,
            balance_after=quantity,
        )
        balance.quantity_on_hand = quantity
        self._session.add(movement)
        return movement


def lock_inventory_balances(
    session: Session, keys: Iterable[InventoryBalanceKey]
) -> LockedInventoryBalances:
    """Lock the complete write set in branch/product/location order before any stock effects."""
    balances: dict[InventoryBalanceKey, InventoryBalance] = {}
    for key in sorted(set(keys)):
        statement = (
            select(InventoryBalance)
            .where(
                InventoryBalance.branch_id == key.branch_id,
                InventoryBalance.product_id == key.product_id,
                InventoryBalance.location_code == key.location_code,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        balance = session.scalar(statement)
        if balance is None:
            try:
                # ORM inserts retain the branch authorization guard. Only this insert is retried.
                with session.begin_nested():
                    balance = InventoryBalance(
                        product_id=key.product_id,
                        branch_id=key.branch_id,
                        location_code=key.location_code,
                        quantity_on_hand=Decimal(0),
                    )
                    session.add(balance)
                    session.flush()
            except IntegrityError as error:
                if getattr(getattr(error.orig, "diag", None), "constraint_name", None) != (
                    "uq_inventory_balances_product_branch_location"
                ):
                    raise
                balance = session.scalars(statement).one()
        balances[key] = balance
    transaction = session.get_transaction()
    if transaction is None:
        transaction = session.begin()
    return LockedInventoryBalances(session, transaction, balances)
