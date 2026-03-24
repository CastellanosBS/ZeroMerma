# apps/backend/src/zeromerma_api/services/production_service.py
# PURPOSE:
#   Production service:
#     - create a production_run header
#     - consume inputs via inventory_balance decrement + ledger movements
#     - produce outputs via inventory_balance increment + ledger movements
#
# DESIGN:
#   - single DB transaction:
#       if any step fails -> rollback everything (no partial inventory writes)
#   - enforces product semantics:
#       inputs must have is_input = TRUE
#       outputs must have is_input = FALSE

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainInvariantError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.services.inventory_balance_service import (
    atomic_decrement_on_hand,
    atomic_increment_on_hand,
    ensure_balance_row,
    qty,
    to_decimal,
)


@dataclass(frozen=True)
class ProductionItem:
    """
    One line in a production run.

    qty must be positive.
    """

    product_id: int
    qty: Decimal


def _load_product_flags(db: Session, *, product_ids: list[int]) -> dict[int, bool]:
    """
    Load is_input flag for each product id.
    """
    if not product_ids:
        return {}

    rows = db.execute(
        text(
            """
            SELECT id, is_input
            FROM product
            WHERE id = ANY(CAST(:ids AS BIGINT[]))
            """
        ),
        {"ids": [int(x) for x in product_ids]},
    ).fetchall()

    found = {int(r[0]) for r in rows}
    missing = sorted(set(int(x) for x in product_ids) - found)
    if missing:
        raise DomainNotFoundError(
            message="Some products do not exist.",
            details={"missing_product_ids": missing},
        )

    return {int(r[0]): bool(r[1]) for r in rows}


def _normalize_items(raw_items: list[dict[str, Any]]) -> list[ProductionItem]:
    """
    Normalize request payload items:
    - cast product_id to int
    - cast qty to Decimal
    - quantize qty to NUMERIC(18,3) semantics
    - validate qty > 0
    """
    items: list[ProductionItem] = []
    for item in raw_items:
        product_id = int(item["product_id"])
        raw_qty = to_decimal(item["qty"])
        normalized_qty = qty(raw_qty)

        if normalized_qty <= 0:
            raise DomainValidationError(
                message="All production quantities must be greater than zero.",
                details={
                    "product_id": product_id,
                    "qty": str(normalized_qty),
                },
            )

        items.append(
            ProductionItem(product_id=product_id, qty=normalized_qty),
        )

    return items


def create_production_run(
    db: Session,
    *,
    branch_id: int,
    created_by_id: int,
    inputs: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    note: str | None = None,
) -> dict[str, Any]:
    """
    Create a production run and all its side effects.

    Domain contract:
    - missing products              -> DomainNotFoundError
    - missing inputs/outputs        -> DomainValidationError
    - invalid product semantics     -> DomainConflictError
    - insufficient stock            -> DomainConflictError
    - impossible header anomaly     -> DomainInvariantError
    """
    input_items = _normalize_items(inputs)
    output_items = _normalize_items(outputs)

    if not input_items:
        raise DomainValidationError(
            message="Production run must include at least 1 input item.",
            details={"inputs": []},
        )

    if not output_items:
        raise DomainValidationError(
            message="Production run must include at least 1 output item.",
            details={"outputs": []},
        )

    all_ids = [item.product_id for item in input_items] + [item.product_id for item in output_items]
    flags = _load_product_flags(db, product_ids=all_ids)

    bad_inputs = sorted(
        item.product_id for item in input_items if flags.get(item.product_id) is not True
    )
    if bad_inputs:
        raise DomainConflictError(
            message="Invalid inputs: expected is_input=true for input items.",
            details={"invalid_input_product_ids": bad_inputs},
        )

    bad_outputs = sorted(
        item.product_id for item in output_items if flags.get(item.product_id) is True
    )
    if bad_outputs:
        raise DomainConflictError(
            message="Invalid outputs: expected is_input=false for output items.",
            details={"invalid_output_product_ids": bad_outputs},
        )

    run_row = db.execute(
        text(
            """
            INSERT INTO production_run
                (branch_id, created_by_id, note, created_at, updated_at)
            VALUES
                (:b, :u, :note, now(), now())
            RETURNING id
            """
        ),
        {"b": int(branch_id), "u": int(created_by_id), "note": note},
    ).fetchone()

    if run_row is None:
        raise DomainInvariantError(
            message="Failed to create production_run header unexpectedly.",
            details={
                "branch_id": int(branch_id),
                "created_by_id": int(created_by_id),
            },
        )

    run_id = int(run_row[0])

    for item in input_items:
        ensure_balance_row(db, branch_id=branch_id, product_id=item.product_id)
        atomic_decrement_on_hand(
            db,
            branch_id=branch_id,
            product_id=item.product_id,
            amount=item.qty,
        )

        db.execute(
            text(
                """
                INSERT INTO inventory_movement
                    (
                        branch_id,
                        product_id,
                        qty,
                        reason,
                        ref_type,
                        ref_id,
                        note,
                        created_by_id,
                        created_at,
                        updated_at
                    )
                VALUES
                    (
                        :b,
                        :p,
                        :q,
                        'PRODUCTION_INPUT',
                        'PRODUCTION_RUN',
                        :rid,
                        :note,
                        :u,
                        now(),
                        now()
                    )
                """
            ),
            {
                "b": int(branch_id),
                "p": int(item.product_id),
                "q": float(qty(item.qty)) * -1.0,
                "rid": int(run_id),
                "note": note,
                "u": int(created_by_id),
            },
        )

    for item in output_items:
        ensure_balance_row(db, branch_id=branch_id, product_id=item.product_id)
        atomic_increment_on_hand(
            db,
            branch_id=branch_id,
            product_id=item.product_id,
            amount=item.qty,
        )

        db.execute(
            text(
                """
                INSERT INTO inventory_movement
                    (
                        branch_id,
                        product_id,
                        qty,
                        reason,
                        ref_type,
                        ref_id,
                        note,
                        created_by_id,
                        created_at,
                        updated_at
                    )
                VALUES
                    (
                        :b,
                        :p,
                        :q,
                        'PRODUCTION_OUTPUT',
                        'PRODUCTION_RUN',
                        :rid,
                        :note,
                        :u,
                        now(),
                        now()
                    )
                """
            ),
            {
                "b": int(branch_id),
                "p": int(item.product_id),
                "q": float(qty(item.qty)),
                "rid": int(run_id),
                "note": note,
                "u": int(created_by_id),
            },
        )

    return {
        "id": run_id,
        "branch_id": int(branch_id),
        "created_by_id": int(created_by_id),
        "inputs_count": len(input_items),
        "outputs_count": len(output_items),
    }
