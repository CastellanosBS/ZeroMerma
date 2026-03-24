from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainInvariantError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.models.inventory_movement import InventoryMovement, MovementReason
from zeromerma_api.models.payment import Payment
from zeromerma_api.models.sale import Sale, SaleStatus
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.services.inventory_balance_service import (
    atomic_increment_on_hand,
    ensure_balance_row,
)
from zeromerma_api.services.payment_service import money, to_decimal, validate_method

QTY_PLACES = Decimal("0.001")


def utcnow() -> datetime:
    """
    Return timezone-aware UTC now.
    """
    return datetime.now(timezone.utc)


def qty(value: Decimal | float | int | str) -> Decimal:
    """
    Quantize quantity to NUMERIC(18,3)-compatible precision.
    """
    return Decimal(str(value)).quantize(QTY_PLACES, rounding=ROUND_HALF_UP)


def _require_user(db: Session, *, user_id: int) -> UserAccount:
    user = db.get(UserAccount, int(user_id))
    if user is None:
        raise DomainNotFoundError(
            message=f"User {user_id} not found.",
            details={"user_id": int(user_id)},
        )
    return user


def _require_sale_with_relations(db: Session, *, sale_id: int) -> Sale:
    stmt = (
        select(Sale)
        .where(Sale.id == int(sale_id))
        .options(selectinload(Sale.items), selectinload(Sale.payments))
    )
    sale = db.scalar(stmt)
    if sale is None:
        raise DomainNotFoundError(
            message=f"Sale {sale_id} not found.",
            details={"sale_id": int(sale_id)},
        )
    return sale


def _restore_sale_inventory(
    db: Session,
    *,
    sale: Sale,
    actor_user_id: int,
    reason: MovementReason,
    note: str,
) -> list[dict[str, str | int]]:
    """
    Restore stock for all sale items and append matching ledger movements.
    """
    restored_lines: list[dict[str, str | int]] = []

    for item in sale.items:
        restore_qty = qty(item.qty)

        ensure_balance_row(
            db,
            branch_id=int(sale.branch_id),
            product_id=int(item.product_id),
        )
        atomic_increment_on_hand(
            db,
            branch_id=int(sale.branch_id),
            product_id=int(item.product_id),
            amount=restore_qty,
        )

        movement = InventoryMovement(
            branch_id=int(sale.branch_id),
            product_id=int(item.product_id),
            qty=float(restore_qty),
            reason=reason.value,
            ref_type="SALE",
            ref_id=int(sale.id),
            note=note,
            created_by_id=int(actor_user_id),
        )
        db.add(movement)

        restored_lines.append(
            {
                "product_id": int(item.product_id),
                "qty": str(restore_qty),
            }
        )

    db.flush()
    return restored_lines


def void_sale(
    db: Session,
    *,
    sale_id: int,
    actor_user_id: int,
    reason: str,
) -> dict[str, Any]:
    """
    Void one OPEN unpaid sale.

    Rules:
    - sale must be OPEN
    - sale must not have any recorded payments
    - inventory is restored
    - status becomes VOIDED
    """
    _require_user(db, user_id=int(actor_user_id))
    sale = _require_sale_with_relations(db, sale_id=int(sale_id))

    if sale.status != SaleStatus.OPEN.value:
        raise DomainConflictError(
            message=f"Sale {sale_id} cannot be voided from status {sale.status}.",
            details={
                "sale_id": int(sale.id),
                "status": str(sale.status),
                "required_status": SaleStatus.OPEN.value,
            },
        )

    if sale.payments:
        raise DomainConflictError(
            message="Cannot void a sale that already has payments.",
            details={
                "sale_id": int(sale.id),
                "payment_count": len(sale.payments),
            },
        )

    normalized_reason = reason.strip()
    if not normalized_reason:
        raise DomainValidationError(
            message="Void reason must not be blank.",
            details={"reason": reason},
        )

    reversal_note = f"SALE VOID | sale_id={int(sale.id)} | reason={normalized_reason}"
    restored_lines = _restore_sale_inventory(
        db,
        sale=sale,
        actor_user_id=int(actor_user_id),
        reason=MovementReason.SALE_VOID,
        note=reversal_note,
    )

    when = utcnow()
    snapshot = {
        "kind": "VOID",
        "sale_id": int(sale.id),
        "status_before": SaleStatus.OPEN.value,
        "restocked_items": restored_lines,
        "payment_reversal": "NONE",
        "reason": normalized_reason,
        "performed_by_id": int(actor_user_id),
        "performed_at": when.isoformat(),
    }

    sale.status = SaleStatus.VOIDED.value
    sale.voided_at = when
    sale.voided_by_id = int(actor_user_id)
    sale.reversal_reason = normalized_reason
    sale.reversal_snapshot = snapshot

    db.flush()

    return {
        "sale_id": int(sale.id),
        "status": sale.status,
        "reversal_kind": "VOID",
        "branch_id": int(sale.branch_id),
        "cash_session_id": int(sale.cash_session_id),
        "voided_at": sale.voided_at,
        "voided_by_id": sale.voided_by_id,
        "refunded_at": sale.refunded_at,
        "refunded_by_id": sale.refunded_by_id,
        "reversal_reason": sale.reversal_reason,
        "total": money(to_decimal(sale.total)),
        "reversal_snapshot": snapshot,
    }


def refund_sale(
    db: Session,
    *,
    sale_id: int,
    actor_user_id: int,
    reason: str,
) -> dict[str, Any]:
    """
    Fully refund one PAID sale.

    Rules:
    - sale must be PAID
    - no prior negative refund payments may exist
    - refund is full only in this block
    - negative payment rows mirror the original positive payments
    - inventory is restored
    - status becomes REFUNDED
    """
    _require_user(db, user_id=int(actor_user_id))
    sale = _require_sale_with_relations(db, sale_id=int(sale_id))

    if sale.status != SaleStatus.PAID.value:
        raise DomainConflictError(
            message=f"Sale {sale_id} cannot be refunded from status {sale.status}.",
            details={
                "sale_id": int(sale.id),
                "status": str(sale.status),
                "required_status": SaleStatus.PAID.value,
            },
        )

    normalized_reason = reason.strip()
    if not normalized_reason:
        raise DomainValidationError(
            message="Refund reason must not be blank.",
            details={"reason": reason},
        )

    positive_payments = [p for p in sale.payments if to_decimal(p.amount) > 0]
    negative_payments = [p for p in sale.payments if to_decimal(p.amount) < 0]

    if negative_payments:
        raise DomainConflictError(
            message="Sale already has refund/reversal payment lines.",
            details={
                "sale_id": int(sale.id),
                "negative_payment_count": len(negative_payments),
            },
        )

    if not positive_payments:
        raise DomainInvariantError(
            message="Paid sale has no positive payment lines to mirror for refund.",
            details={"sale_id": int(sale.id)},
        )

    total_positive = money(sum((to_decimal(p.amount) for p in positive_payments), Decimal("0.00")))
    sale_total = money(to_decimal(sale.total))
    if total_positive != sale_total:
        raise DomainConflictError(
            message="Only fully settled sales can be refunded in this block.",
            details={
                "sale_id": int(sale.id),
                "sale_total": str(sale_total),
                "positive_payments_total": str(total_positive),
            },
        )

    mirrored_refund_lines: list[dict[str, str | int]] = []
    for original_payment in positive_payments:
        method = validate_method(str(original_payment.method))
        refund_payment = Payment(
            sale_id=int(sale.id),
            method=method,
            amount=money(to_decimal(original_payment.amount) * Decimal("-1")),
            reference=f"REFUND:{int(sale.id)}:{int(original_payment.id)}",
        )
        db.add(refund_payment)
        db.flush()

        mirrored_refund_lines.append(
            {
                "original_payment_id": int(original_payment.id),
                "refund_payment_id": int(refund_payment.id),
                "method": method,
                "amount": str(money(abs(to_decimal(original_payment.amount)))),
            }
        )

    reversal_note = f"SALE REFUND | sale_id={int(sale.id)} | reason={normalized_reason}"
    restored_lines = _restore_sale_inventory(
        db,
        sale=sale,
        actor_user_id=int(actor_user_id),
        reason=MovementReason.SALE_REFUND,
        note=reversal_note,
    )

    when = utcnow()
    snapshot = {
        "kind": "REFUND",
        "sale_id": int(sale.id),
        "status_before": SaleStatus.PAID.value,
        "restocked_items": restored_lines,
        "mirrored_refund_payments": mirrored_refund_lines,
        "reason": normalized_reason,
        "performed_by_id": int(actor_user_id),
        "performed_at": when.isoformat(),
    }

    sale.status = SaleStatus.REFUNDED.value
    sale.refunded_at = when
    sale.refunded_by_id = int(actor_user_id)
    sale.reversal_reason = normalized_reason
    sale.reversal_snapshot = snapshot

    db.flush()

    return {
        "sale_id": int(sale.id),
        "status": sale.status,
        "reversal_kind": "REFUND",
        "branch_id": int(sale.branch_id),
        "cash_session_id": int(sale.cash_session_id),
        "voided_at": sale.voided_at,
        "voided_by_id": sale.voided_by_id,
        "refunded_at": sale.refunded_at,
        "refunded_by_id": sale.refunded_by_id,
        "reversal_reason": sale.reversal_reason,
        "total": sale_total,
        "reversal_snapshot": snapshot,
    }
