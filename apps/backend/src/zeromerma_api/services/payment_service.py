# apps/backend/src/zeromerma_api/services/payment_service.py
# PURPOSE:
#   Payment business logic:
#     - append payment records to a sale
#     - enforce "no overpay" invariant
#     - compute paid_amount and balance_due

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from zeromerma_api.models.payment import Payment, PaymentMethod
from zeromerma_api.models.sale import Sale, SaleStatus

MONEY = Decimal("0.01")


def money(x: Decimal) -> Decimal:
    """
    Quantize to cents using standard POS rounding.
    """
    return x.quantize(MONEY, rounding=ROUND_HALF_UP)


def to_decimal(value: float | int | str) -> Decimal:
    """
    Convert numeric input to Decimal safely (avoid float artifacts).
    """
    return Decimal(str(value))


def require_sale_open(db: Session, sale_id: int) -> Sale:
    """
    Load sale by id and ensure it is OPEN.

    Raises:
      - LookupError: sale doesn't exist
      - ValueError: sale isn't OPEN
    """
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise LookupError(f"Sale {sale_id} not found.")

    if sale.status != SaleStatus.OPEN.value:
        raise ValueError(f"Sale {sale_id} is not OPEN (status={sale.status}).")

    return sale


def compute_paid_amount(db: Session, sale_id: int) -> Decimal:
    """
    Compute sum(payment.amount) for a given sale.

    We compute at query-time (ledger approach).
    """
    stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.sale_id == sale_id
    )
    val = db.scalar(stmt)
    return money(to_decimal(val or 0))


def validate_method(method: str) -> str:
    """
    Ensure method is one of the allowed PaymentMethod enum values.
    Stored as string in DB, but we validate for integrity.
    """
    allowed = {m.value for m in PaymentMethod}
    if method not in allowed:
        raise ValueError(
            f"Invalid payment method '{method}'. Allowed: {sorted(allowed)}"
        )
    return method


def add_payment(
    db: Session,
    *,
    sale_id: int,
    method: str,
    amount: float,
    reference: str | None = None,
) -> Payment:
    """
    Append a payment to a sale, enforcing "no overpay".

    Rules:
      - sale must exist and be OPEN
      - method must be allowed
      - amount must be > 0 (schema already enforces, but we re-check at domain layer)
      - paid_amount + amount <= sale.total
    """
    sale = require_sale_open(db, sale_id)

    method = validate_method(method)

    amount_dec = money(to_decimal(amount))
    if amount_dec <= 0:
        raise ValueError("Payment amount must be > 0.")

    total_dec = money(to_decimal(sale.total))
    paid_dec = compute_paid_amount(db, sale_id)

    new_paid = money(paid_dec + amount_dec)

    if new_paid > total_dec:
        # Overpay policy: reject with conflict
        raise ValueError(
            f"Overpayment: current paid={paid_dec}, adding={amount_dec}, total={total_dec}."
        )

    p = Payment(
        sale_id=sale_id,
        method=method,
        amount=float(amount_dec),
        reference=reference,
    )

    db.add(p)
    db.flush()  # ensure p.id exists before returning
    return p


def get_sale_detail(db: Session, sale_id: int) -> dict:
    """
    Load sale with items and payments, and compute paid/balance.

    Returns a dict that matches SaleDetailOut fields.
    """
    # Load sale with its items (selectinload avoids N+1 queries).
    stmt = select(Sale).where(Sale.id == sale_id).options(selectinload(Sale.items))
    sale = db.scalar(stmt)
    if sale is None:
        raise LookupError(f"Sale {sale_id} not found.")

    # Load payments separately (also selectin style, simple query).
    pay_stmt = (
        select(Payment).where(Payment.sale_id == sale_id).order_by(Payment.id.asc())
    )
    payments = db.execute(pay_stmt).scalars().all()

    total_dec = money(to_decimal(sale.total))
    paid_dec = money(sum((to_decimal(p.amount) for p in payments), Decimal("0.00")))
    balance_dec = money(total_dec - paid_dec)

    # Return a dict so router can respond with SaleDetailOut cleanly.
    return {
        "id": sale.id,
        "branch_id": sale.branch_id,
        "cash_session_id": sale.cash_session_id,
        "created_by_id": sale.created_by_id,
        "subtotal": float(sale.subtotal),
        "tax": float(sale.tax),
        "total": float(sale.total),
        "status": sale.status,
        "items": sale.items,  # Pydantic orm_mode will serialize
        "payments": payments,  # Pydantic orm_mode will serialize
        "paid_amount": float(paid_dec),
        "balance_due": float(balance_dec),
    }
