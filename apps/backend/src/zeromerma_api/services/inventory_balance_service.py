# apps/backend/src/zeromerma_api/services/inventory_balance_service.py
# PURPOSE:
#   Operational inventory snapshot helpers:
#     - Ensure a balance row exists for (branch_id, product_id)
#     - Atomic decrement to prevent oversell under concurrency
#
# IMPORTANT:
#   These functions must be called inside the same DB transaction
#   as sale creation, so rollback reverses everything.

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

QTY_PLACES = Decimal("0.001")


def to_decimal(value: float | int | str) -> Decimal:
    """
    Safe Decimal conversion to avoid float artifacts.
    """
    return Decimal(str(value))


def qty(value: Decimal) -> Decimal:
    """
    Quantize quantity to 3 decimals to match NUMERIC(18,3).
    """
    return value.quantize(QTY_PLACES, rounding=ROUND_HALF_UP)


def ensure_balance_row(db: Session, *, branch_id: int, product_id: int) -> None:
    """
    Ensure inventory_balance has a row for this (branch_id, product_id).

    We do INSERT ... ON CONFLICT DO NOTHING so:
      - first time we see a product/branch pair, we create it with zeros
      - if it already exists, no error and no change

    This is safe under concurrency.
    """
    db.execute(
        text(
            """
            INSERT INTO inventory_balance (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES (:b, :p, 0, 0, now(), now())
            ON CONFLICT (branch_id, product_id) DO NOTHING
            """
        ),
        {"b": int(branch_id), "p": int(product_id)},
    )


def atomic_decrement_on_hand(
    db: Session, *, branch_id: int, product_id: int, amount: Decimal
) -> Decimal:
    """
    Atomically decrement on_hand if sufficient stock exists.

    Returns:
      new_on_hand (Decimal)

    Raises:
      ValueError if insufficient stock

    Concurrency behavior:
      - Postgres will lock the row during UPDATE.
      - Two transactions decrementing the same row will serialize safely.
    """
    amount = qty(amount)
    if amount <= 0:
        raise ValueError("Decrement amount must be > 0.")

    row = db.execute(
        text(
            """
            UPDATE inventory_balance
            SET on_hand = on_hand - :q,
                updated_at = now()
            WHERE branch_id = :b
              AND product_id = :p
              AND on_hand >= :q
            RETURNING on_hand
            """
        ),
        {"b": int(branch_id), "p": int(product_id), "q": float(amount)},
    ).fetchone()

    if row is None:
        raise ValueError(
            f"Insufficient stock for product_id={product_id} in branch_id={branch_id}: "
            f"required={amount}."
        )

    return qty(to_decimal(row[0]))
