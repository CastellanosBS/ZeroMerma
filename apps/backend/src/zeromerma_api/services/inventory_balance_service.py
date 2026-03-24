# apps/backend/src/zeromerma_api/services/inventory_balance_service.py
# PURPOSE:
#   Operational inventory snapshot helpers:
#     - Ensure a balance row exists for (branch_id, product_id)
#     - Atomic decrement to prevent oversell under concurrency
#
# IMPORTANT:
#   These functions must be called inside the same DB transaction
#   as sale creation / production, so rollback reverses everything.

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainInvariantError,
    DomainValidationError,
)

QTY_PLACES = Decimal("0.001")


def to_decimal(value: Decimal | float | int | str) -> Decimal:
    """
    Convert numeric-like input to Decimal safely.
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
            INSERT INTO inventory_balance
                (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES
                (:b, :p, 0, 0, now(), now())
            ON CONFLICT (branch_id, product_id) DO NOTHING
            """
        ),
        {"b": int(branch_id), "p": int(product_id)},
    )


def atomic_decrement_on_hand(
    db: Session,
    *,
    branch_id: int,
    product_id: int,
    amount: Decimal,
) -> Decimal:
    """
    Atomically decrement on_hand if sufficient stock exists.

    Returns:
      new_on_hand (Decimal)

    Domain contract:
    - amount <= 0         -> DomainValidationError
    - insufficient stock  -> DomainConflictError

    Concurrency behavior:
    - Postgres locks the row during UPDATE.
    - Two transactions decrementing the same row serialize safely.
    """
    amount = qty(amount)
    if amount <= 0:
        raise DomainValidationError(
            message="Decrement amount must be greater than zero.",
            details={"amount": str(amount)},
        )

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
        raise DomainConflictError(
            message="Insufficient stock for inventory decrement.",
            details={
                "branch_id": int(branch_id),
                "product_id": int(product_id),
                "required_qty": str(amount),
            },
        )

    return qty(to_decimal(row[0]))


def bootstrap_inventory_balance_from_ledger(db: Session, *, branch_id: int) -> int:
    """
    Build or rebuild inventory_balance rows for a branch using the inventory_movement ledger.

    What it does:
      1) Aggregate movements by (branch_id, product_id): SUM(qty)
      2) Upsert into inventory_balance:
         - on_hand = aggregated sum
         - reserved = 0 (for now; reserved logic comes later)
         - updated_at = now()

    Why we need this:
      - deterministic dev seeding
      - recovery tool if snapshot ever drifts in development
    """
    result = db.execute(
        text(
            """
            WITH agg AS (
                SELECT
                    branch_id,
                    product_id,
                    COALESCE(SUM(qty), 0) AS on_hand
                FROM inventory_movement
                WHERE branch_id = :b
                GROUP BY branch_id, product_id
            )
            INSERT INTO inventory_balance
                (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            SELECT
                agg.branch_id,
                agg.product_id,
                agg.on_hand,
                0,
                now(),
                now()
            FROM agg
            ON CONFLICT (branch_id, product_id)
            DO UPDATE SET
                on_hand = EXCLUDED.on_hand,
                reserved = EXCLUDED.reserved,
                updated_at = now()
            """
        ),
        {"b": int(branch_id)},
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


def atomic_increment_on_hand(
    db: Session,
    *,
    branch_id: int,
    product_id: int,
    amount: Decimal,
) -> Decimal:
    """
    Atomically increment on_hand by amount.

    Domain contract:
    - amount <= 0         -> DomainValidationError
    - impossible missing row after ensure -> DomainInvariantError
    """
    amount = qty(amount)
    if amount <= 0:
        raise DomainValidationError(
            message="Increment amount must be greater than zero.",
            details={"amount": str(amount)},
        )

    ensure_balance_row(db, branch_id=branch_id, product_id=product_id)

    row = db.execute(
        text(
            """
            UPDATE inventory_balance
            SET on_hand = on_hand + :q,
                updated_at = now()
            WHERE branch_id = :b
              AND product_id = :p
            RETURNING on_hand
            """
        ),
        {"b": int(branch_id), "p": int(product_id), "q": float(amount)},
    ).fetchone()

    if row is None:
        raise DomainInvariantError(
            message="Failed to increment inventory balance row unexpectedly.",
            details={
                "branch_id": int(branch_id),
                "product_id": int(product_id),
            },
        )

    return qty(to_decimal(row[0]))
