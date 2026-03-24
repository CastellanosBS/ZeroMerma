from __future__ import annotations

from enum import Enum


class PaymentMethod(str, Enum):
    """
    Canonical payment methods recognized across the POS kernel.

    This enum intentionally lives outside the ORM model layer so the same
    vocabulary can be shared by:
    - SQLAlchemy models
    - Pydantic request/response schemas
    - service-layer business rules
    - test fixtures and contract checks

    The goal of this module is to eliminate drift between "raw payments",
    "checkout", "order delivery checkout", and "receipt" payloads.
    """

    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"


PAYMENT_METHOD_VALUES: tuple[str, ...] = tuple(method.value for method in PaymentMethod)
CASH_PAYMENT_METHOD: str = PaymentMethod.CASH.value
NON_CASH_PAYMENT_METHODS: frozenset[str] = frozenset(
    value for value in PAYMENT_METHOD_VALUES if value != CASH_PAYMENT_METHOD
)


def normalize_payment_method(method: PaymentMethod | str) -> str:
    """
    Return the canonical string value for a payment method.

    Rules:
    - enum inputs are converted to their `.value`
    - string inputs are trimmed and uppercased
    - validation is left to the caller because schemas and services surface
      different error types (422 vs domain-level 400/409)
    """
    if isinstance(method, PaymentMethod):
        return method.value

    return str(method).strip().upper()


def is_cash_payment_method(method: PaymentMethod | str) -> bool:
    """
    Return True when the canonical method is CASH.
    """
    return normalize_payment_method(method) == CASH_PAYMENT_METHOD
