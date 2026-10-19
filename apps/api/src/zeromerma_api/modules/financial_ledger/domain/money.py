from __future__ import annotations

from collections.abc import Callable
from decimal import ROUND_HALF_UP, Context, Decimal, InvalidOperation, localcontext
from functools import wraps

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
MAX_AMOUNT = Decimal("9999999999.99")
CURRENCY = "MXN"


class FinancialModelError(ValueError):
    """An admitted financial fact does not satisfy the canonical model."""


def financial_calculation[**P, T](function: Callable[P, T]) -> Callable[P, T]:
    """Use deterministic decimal arithmetic independently of the caller's context."""

    @wraps(function)
    def calculate(*args: P.args, **kwargs: P.kwargs) -> T:
        with localcontext(Context(prec=28, rounding=ROUND_HALF_UP)):
            return function(*args, **kwargs)

    return calculate


def quantize_money(value: Decimal) -> Decimal:
    """Round a calculation explicitly; binary floats are never monetary input."""
    if not isinstance(value, Decimal) or not value.is_finite():
        raise FinancialModelError("Money requires a finite Decimal.")
    if value.copy_abs() >= Decimal("10000000000"):
        raise FinancialModelError("The monetary value exceeds Numeric(12, 2).")
    try:
        with localcontext(Context(prec=28, rounding=ROUND_HALF_UP)):
            result = value.quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation as error:
        raise FinancialModelError("The monetary value cannot be rounded safely.") from error
    if result.copy_abs() > MAX_AMOUNT:
        raise FinancialModelError("The monetary value exceeds Numeric(12, 2).")
    return result


def require_money(value: Decimal, *, positive: bool = False) -> Decimal:
    """Validate persisted amounts before PostgreSQL can silently round their scale."""
    rounded = quantize_money(value)
    if rounded != value:
        raise FinancialModelError("Persisted money must already have cent precision.")
    if value < ZERO or (positive and value == ZERO):
        raise FinancialModelError("The monetary amount has an invalid sign.")
    return rounded


def require_currency(currency_code: str) -> None:
    if currency_code != CURRENCY:
        raise FinancialModelError("The current financial model supports MXN without FX.")
