# apps/backend/src/zeromerma_api/services/production_service.py
# PURPOSE:
#   Production stub service:
#     - Create a production_run header
#     - Consume inputs via inventory_balance decrement + ledger movements
#     - Produce outputs via inventory_balance increment + ledger movements
#
# DESIGN:
#   - Single DB transaction:
#       if any step fails -> rollback everything (no partial inventory writes).
#   - Enforces product semantics:
#       inputs must have is_input = TRUE
#       outputs must have is_input = FALSE
#
# ERROR CONTRACT:
#   - LookupError -> missing product(s)
#   - ValueError  -> business rule violation (insufficient stock / wrong product type)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

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

    Returns:
      dict[product_id] -> is_input
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
        raise LookupError(f"Some products do not exist: {missing}")

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
    for it in raw_items:
        pid = int(it["product_id"])
        q_raw = to_decimal(it["qty"])
        q_norm = qty(q_raw)

        if q_norm <= 0:
            raise ValueError("All quantities must be > 0.")

        items.append(ProductionItem(product_id=pid, qty=q_norm))

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

    Steps (single transaction):
      1) Normalize inputs/outputs quantities
      2) Validate product semantics:
           - inputs: is_input must be TRUE
           - outputs: is_input must be FALSE
      3) Insert production_run header -> get run_id
      4) Snapshot updates:
           - decrement inputs (must not go negative)
           - increment outputs
      5) Ledger inserts:
           - PRODUCTION_INPUT  (negative qty)
           - PRODUCTION_OUTPUT (positive qty)

    Returns:
      dict with run_id and counts.
    """
    in_items = _normalize_items(inputs)
    out_items = _normalize_items(outputs)

    if not in_items:
        raise ValueError("Production run must include at least 1 input item.")
    if not out_items:
        raise ValueError("Production run must include at least 1 output item.")

    all_ids = [x.product_id for x in in_items] + [x.product_id for x in out_items]
    flags = _load_product_flags(db, product_ids=all_ids)

    # Enforce semantics
    bad_inputs = sorted(x.product_id for x in in_items if flags.get(x.product_id) is not True)
    if bad_inputs:
        raise ValueError(
            "Invalid inputs: expected is_input=true for input items. " f"product_ids={bad_inputs}."
        )

    bad_outputs = sorted(x.product_id for x in out_items if flags.get(x.product_id) is True)
    if bad_outputs:
        raise ValueError(
            "Invalid outputs: expected is_input=false for output items. "
            f"product_ids={bad_outputs}."
        )

    # (1) Create header
    run_row = db.execute(
        text(
            """
            INSERT INTO production_run (branch_id, created_by_id, note, created_at, updated_at)
            VALUES (:b, :u, :note, now(), now())
            RETURNING id
            """
        ),
        {"b": int(branch_id), "u": int(created_by_id), "note": note},
    ).fetchone()

    if run_row is None:
        raise RuntimeError("Failed to create production_run header unexpectedly.")

    run_id = int(run_row[0])

    # (2) Snapshot updates + ledger inserts
    # Inputs: decrement + ledger negative
    for it in in_items:
        ensure_balance_row(db, branch_id=branch_id, product_id=it.product_id)
        atomic_decrement_on_hand(db, branch_id=branch_id, product_id=it.product_id, amount=it.qty)

        db.execute(
            text(
                """
                INSERT INTO inventory_movement
                  (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id,
                    created_at, updated_at)
                VALUES
                  (:b, :p, :q, 'PRODUCTION_INPUT', 'PRODUCTION_RUN', :rid, :note, :u, now(), now())
                """
            ),
            {
                "b": int(branch_id),
                "p": int(it.product_id),
                "q": float(qty(it.qty)) * -1.0,
                "rid": int(run_id),
                "note": note,
                "u": int(created_by_id),
            },
        )

    # Outputs: increment + ledger positive
    for it in out_items:
        ensure_balance_row(db, branch_id=branch_id, product_id=it.product_id)
        atomic_increment_on_hand(db, branch_id=branch_id, product_id=it.product_id, amount=it.qty)

        db.execute(
            text(
                """
                INSERT INTO inventory_movement
                  (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id,
                    created_at, updated_at)
                VALUES
                  (:b, :p, :q, 'PRODUCTION_OUTPUT', 'PRODUCTION_RUN', :rid, :note, :u, now(), now())
                """
            ),
            {
                "b": int(branch_id),
                "p": int(it.product_id),
                "q": float(qty(it.qty)),
                "rid": int(run_id),
                "note": note,
                "u": int(created_by_id),
            },
        )

    return {
        "id": run_id,
        "branch_id": int(branch_id),
        "created_by_id": int(created_by_id),
        "inputs_count": len(in_items),
        "outputs_count": len(out_items),
    }
