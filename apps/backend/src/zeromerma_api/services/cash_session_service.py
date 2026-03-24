# apps/backend/src/zeromerma_api/services/cash_session_service.py
# PURPOSE:
#   Business logic for cash sessions (open/close/reconciliation).
#   Keeps routers minimal, deterministic, and aligned with canonical domain errors.

from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainInvariantError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.models.cash_session import CashSession, CashSessionStatus
from zeromerma_api.models.payment import Payment
from zeromerma_api.models.sale import Sale

MONEY = Decimal("0.01")


def utcnow() -> datetime:
    """
    Return a timezone-aware UTC timestamp.

    We prefer explicit UTC at the application layer even if DB defaults exist.
    """
    return datetime.now(timezone.utc)


def to_decimal(value: Decimal | float | int | str) -> Decimal:
    """
    Convert numeric-like input to Decimal safely.
    """
    return Decimal(str(value))


def money(value: Decimal | float | int | str) -> Decimal:
    """
    Normalize money values to NUMERIC(18,2)-style precision.
    """
    return to_decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def get_current_open_session(db: Session, branch_id: int) -> CashSession | None:
    """
    Find the current OPEN cash session for a branch, if any.
    """
    stmt = select(CashSession).where(
        CashSession.branch_id == branch_id,
        CashSession.status == CashSessionStatus.OPEN.value,
    )
    return db.scalar(stmt)


def _empty_payment_totals() -> dict[str, Decimal]:
    """
    Return canonical zero totals for all supported POS payment methods.
    """
    return {
        "CASH": Decimal("0.00"),
        "CARD": Decimal("0.00"),
        "TRANSFER": Decimal("0.00"),
        "OTHER": Decimal("0.00"),
    }


def _sum_session_payment_totals_by_method(
    db: Session,
    *,
    session_id: int,
) -> dict[str, Decimal]:
    """
    Sum recorded payments by method for all sales linked to one cash session.

    Design decision:
    - we reconcile from the immutable payment records tied to sales
    - we do not infer from receipt snapshots
    - we do not require sale status filtering here because the payment ledger
      itself is the authoritative source of collected amounts in the current
      POS scope
    """
    totals = _empty_payment_totals()

    stmt = (
        select(
            Payment.method,
            func.coalesce(func.sum(Payment.amount), 0),
        )
        .join(Sale, Sale.id == Payment.sale_id)
        .where(Sale.cash_session_id == int(session_id))
        .group_by(Payment.method)
    )

    for method, amount in db.execute(stmt).all():
        normalized_method = str(method).strip().upper()
        if normalized_method not in totals:
            raise DomainInvariantError(
                message=(
                    f"Unexpected payment method '{normalized_method}' found while "
                    "reconciling cash session."
                ),
                details={
                    "cash_session_id": int(session_id),
                    "payment_method": normalized_method,
                },
            )
        totals[normalized_method] = money(amount)

    return totals


def _serialize_reconciliation_snapshot(
    *,
    expected_payment_totals: dict[str, Decimal],
    expected_cash: Decimal,
    counted_cash: Decimal,
    counted_card_total: Decimal,
    counted_transfer_total: Decimal,
    counted_other_total: Decimal,
    cash_difference: Decimal,
    non_cash_differences: dict[str, Decimal],
    total_expected_non_cash: Decimal,
    total_counted_non_cash: Decimal,
    total_difference: Decimal,
    assumed_counted_non_cash_methods: list[str],
    note: str | None,
) -> dict[str, Any]:
    """
    Build a JSON-serializable reconciliation snapshot.

    We serialize monetary values as strings so JSONB persistence remains exact
    and the API can safely round-trip them back into Decimal-friendly schemas.
    """
    return {
        "expected_payment_totals_by_method": {
            "cash": str(expected_payment_totals["CASH"]),
            "card": str(expected_payment_totals["CARD"]),
            "transfer": str(expected_payment_totals["TRANSFER"]),
            "other": str(expected_payment_totals["OTHER"]),
        },
        "expected_non_cash_totals_by_method": {
            "card": str(expected_payment_totals["CARD"]),
            "transfer": str(expected_payment_totals["TRANSFER"]),
            "other": str(expected_payment_totals["OTHER"]),
        },
        "counted_non_cash_totals_by_method": {
            "card": str(counted_card_total),
            "transfer": str(counted_transfer_total),
            "other": str(counted_other_total),
        },
        "non_cash_differences_by_method": {
            "card": str(non_cash_differences["CARD"]),
            "transfer": str(non_cash_differences["TRANSFER"]),
            "other": str(non_cash_differences["OTHER"]),
        },
        "expected_cash": str(expected_cash),
        "counted_cash": str(counted_cash),
        "cash_difference": str(cash_difference),
        "total_expected_non_cash": str(total_expected_non_cash),
        "total_counted_non_cash": str(total_counted_non_cash),
        "total_difference": str(total_difference),
        "assumed_counted_non_cash_methods": assumed_counted_non_cash_methods,
        "note": note,
    }


def open_cash_session(
    db: Session,
    *,
    branch_id: int,
    opened_by_id: int,
    opening_amount: Decimal | float | int | str,
) -> CashSession:
    """
    Open a new cash session for a branch.

    Rules:
      - Only one OPEN session per branch.
      - opening_amount must be >= 0.
      - The INSERT must remain transactional.
      - Concurrent opens are prevented by the DB unique partial index.
    """
    opening_amount_dec = money(opening_amount)
    if opening_amount_dec < 0:
        raise DomainValidationError(
            message="Opening amount must be greater than or equal to zero.",
            details={"opening_amount": str(opening_amount_dec)},
        )

    existing = get_current_open_session(db, branch_id)
    if existing is not None:
        raise DomainConflictError(
            message=f"Branch {branch_id} already has an OPEN cash session.",
            details={
                "branch_id": int(branch_id),
                "cash_session_id": int(existing.id),
                "status": str(existing.status),
            },
        )

    cs = CashSession(
        branch_id=branch_id,
        opened_by_id=opened_by_id,
        opening_amount=opening_amount_dec,
        status=CashSessionStatus.OPEN.value,
        opened_at=utcnow(),
    )

    db.add(cs)

    try:
        db.flush()
    except IntegrityError as e:
        raise DomainConflictError(
            message="Cash session already open for this branch.",
            details={"branch_id": int(branch_id)},
        ) from e

    return cs


def close_cash_session(
    db: Session,
    *,
    session_id: int,
    closed_by_id: int,
    closing_amount: Decimal | float | int | str,
    counted_card_total: Decimal | float | int | str | None = None,
    counted_transfer_total: Decimal | float | int | str | None = None,
    counted_other_total: Decimal | float | int | str | None = None,
    note: str | None = None,
) -> CashSession:
    """
    Close an OPEN cash session and persist reconciliation evidence.

    Semantics:
    - closing_amount is the real counted cash in drawer
    - expected_cash = opening_amount + total recorded CASH payments in session
    - non-cash expected totals are derived from recorded payments in the session
    - non-cash counted totals are optional; when omitted, they default to the
      expected totals and the assumption is recorded in the snapshot

    Persisted fields on close:
      * status = CLOSED
      * closed_at
      * closed_by_id
      * closing_amount
      * expected_cash
      * reconciliation_snapshot
    """
    closing_amount_dec = money(closing_amount)
    if closing_amount_dec < 0:
        raise DomainValidationError(
            message="Closing amount must be greater than or equal to zero.",
            details={"closing_amount": str(closing_amount_dec)},
        )

    cs = db.get(CashSession, session_id)
    if cs is None:
        raise DomainNotFoundError(
            message=f"Cash session {session_id} not found.",
            details={"cash_session_id": int(session_id)},
        )

    if cs.status != CashSessionStatus.OPEN.value:
        raise DomainConflictError(
            message=f"Cash session {session_id} is not OPEN.",
            details={
                "cash_session_id": int(session_id),
                "status": str(cs.status),
            },
        )

    expected_payment_totals = _sum_session_payment_totals_by_method(
        db,
        session_id=int(session_id),
    )

    expected_cash = money(cs.opening_amount or 0) + expected_payment_totals["CASH"]
    expected_cash = money(expected_cash)

    assumed_counted_non_cash_methods: list[str] = []

    if counted_card_total is None:
        counted_card_dec = expected_payment_totals["CARD"]
        if counted_card_dec > 0:
            assumed_counted_non_cash_methods.append("CARD")
    else:
        counted_card_dec = money(counted_card_total)

    if counted_transfer_total is None:
        counted_transfer_dec = expected_payment_totals["TRANSFER"]
        if counted_transfer_dec > 0:
            assumed_counted_non_cash_methods.append("TRANSFER")
    else:
        counted_transfer_dec = money(counted_transfer_total)

    if counted_other_total is None:
        counted_other_dec = expected_payment_totals["OTHER"]
        if counted_other_dec > 0:
            assumed_counted_non_cash_methods.append("OTHER")
    else:
        counted_other_dec = money(counted_other_total)

    for method_name, value in {
        "counted_card_total": counted_card_dec,
        "counted_transfer_total": counted_transfer_dec,
        "counted_other_total": counted_other_dec,
    }.items():
        if value < 0:
            raise DomainValidationError(
                message=f"{method_name} must be greater than or equal to zero.",
                details={method_name: str(value)},
            )

    cash_difference = money(closing_amount_dec - expected_cash)

    non_cash_differences = {
        "CARD": money(counted_card_dec - expected_payment_totals["CARD"]),
        "TRANSFER": money(counted_transfer_dec - expected_payment_totals["TRANSFER"]),
        "OTHER": money(counted_other_dec - expected_payment_totals["OTHER"]),
    }

    total_expected_non_cash = money(
        expected_payment_totals["CARD"]
        + expected_payment_totals["TRANSFER"]
        + expected_payment_totals["OTHER"]
    )

    total_counted_non_cash = money(counted_card_dec + counted_transfer_dec + counted_other_dec)

    total_difference = money(
        cash_difference
        + non_cash_differences["CARD"]
        + non_cash_differences["TRANSFER"]
        + non_cash_differences["OTHER"]
    )

    normalized_note = note.strip() if note is not None else None
    if normalized_note == "":
        normalized_note = None

    cs.status = CashSessionStatus.CLOSED.value
    cs.closed_at = utcnow()
    cs.closed_by_id = int(closed_by_id)
    cs.closing_amount = closing_amount_dec
    cs.expected_cash = expected_cash
    cs.reconciliation_snapshot = _serialize_reconciliation_snapshot(
        expected_payment_totals=expected_payment_totals,
        expected_cash=expected_cash,
        counted_cash=closing_amount_dec,
        counted_card_total=counted_card_dec,
        counted_transfer_total=counted_transfer_dec,
        counted_other_total=counted_other_dec,
        cash_difference=cash_difference,
        non_cash_differences=non_cash_differences,
        total_expected_non_cash=total_expected_non_cash,
        total_counted_non_cash=total_counted_non_cash,
        total_difference=total_difference,
        assumed_counted_non_cash_methods=assumed_counted_non_cash_methods,
        note=normalized_note,
    )

    db.flush()
    return cs
