# apps/backend/src/zeromerma_api/services/payment_service.py
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.models.payment import Payment, PaymentMethod
from zeromerma_api.models.sale import Sale, SaleStatus

MONEY = Decimal("0.01")


def money(x: Decimal) -> Decimal:
    """
    Quantize to cents using standard POS rounding.
    """
    return x.quantize(MONEY, rounding=ROUND_HALF_UP)


def to_decimal(value: Decimal | float | int | str) -> Decimal:
    """
    Convert numeric input to Decimal safely.
    """
    return Decimal(str(value))


def require_sale_open(db: Session, sale_id: int) -> Sale:
    """
    Load sale by id and ensure it is OPEN.
    """
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise DomainNotFoundError(
            message=f"Sale {sale_id} not found.",
            details={"sale_id": int(sale_id)},
        )

    if sale.status != SaleStatus.OPEN.value:
        raise DomainConflictError(
            message=f"Sale {sale_id} is not OPEN.",
            details={
                "sale_id": int(sale_id),
                "status": str(sale.status),
            },
        )

    return sale


def compute_paid_amount(db: Session, sale_id: int) -> Decimal:
    """
    Compute SUM(payment.amount) for a given sale.
    """
    stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.sale_id == sale_id)
    val = db.scalar(stmt)
    return money(to_decimal(val or 0))


def validate_method(method: str) -> str:
    """
    Ensure method is one of the allowed PaymentMethod enum values.
    """
    allowed = {m.value for m in PaymentMethod}
    if method not in allowed:
        raise DomainValidationError(
            message=f"Invalid payment method '{method}'.",
            details={"allowed_methods": sorted(allowed)},
        )
    return method


def add_payment(
    db: Session,
    *,
    sale_id: int,
    method: str,
    amount: Decimal | float | int | str,
    reference: str | None = None,
) -> Payment:
    """
    Append a payment to a sale, enforcing the "no overpay" invariant.
    """
    sale = require_sale_open(db, sale_id)

    method = validate_method(method)

    amount_dec = money(to_decimal(amount))
    if amount_dec <= 0:
        raise DomainValidationError(
            message="Payment amount must be greater than zero.",
            details={"amount": str(amount_dec)},
        )

    total_dec = money(to_decimal(sale.total))
    paid_dec = compute_paid_amount(db, sale_id)
    new_paid = money(paid_dec + amount_dec)

    if new_paid > total_dec:
        raise DomainConflictError(
            message="Overpayment is not allowed.",
            details={
                "sale_id": int(sale_id),
                "current_paid": str(paid_dec),
                "adding": str(amount_dec),
                "total": str(total_dec),
            },
        )

    p = Payment(
        sale_id=sale_id,
        method=method,
        amount=amount_dec,
        reference=reference,
    )

    db.add(p)
    db.flush()
    return p


def get_sale_detail(db: Session, sale_id: int) -> dict:
    """
    Load sale with items and payments, and compute paid/balance.
    """
    stmt = select(Sale).where(Sale.id == sale_id).options(selectinload(Sale.items))
    sale = db.scalar(stmt)
    if sale is None:
        raise DomainNotFoundError(
            message=f"Sale {sale_id} not found.",
            details={"sale_id": int(sale_id)},
        )

    pay_stmt = select(Payment).where(Payment.sale_id == sale_id).order_by(Payment.id.asc())
    payments = db.execute(pay_stmt).scalars().all()

    total_dec = money(to_decimal(sale.total))
    paid_dec = money(sum((to_decimal(p.amount) for p in payments), Decimal("0.00")))
    balance_dec = money(total_dec - paid_dec)

    return {
        "id": sale.id,
        "branch_id": sale.branch_id,
        "cash_session_id": sale.cash_session_id,
        "created_by_id": sale.created_by_id,
        "created_at": sale.created_at,
        "updated_at": sale.updated_at,
        "subtotal": sale.subtotal,
        "tax": sale.tax,
        "total": sale.total,
        "status": sale.status,
        "items": sale.items,
        "payments": payments,
        "paid_amount": paid_dec,
        "balance_due": balance_dec,
    }
