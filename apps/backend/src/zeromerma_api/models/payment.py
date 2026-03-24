# apps/backend/src/zeromerma_api/models/payment.py
"""
Immutable payment records attached to a sale.

A sale can have many payments at the data-model level. The service layer
decides whether partial payments, overpayments, or future refund flows are
allowed for a given API contract.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .sale import Sale


class Payment(Base):
    """
    Immutable payment event.

    Important:
    - `method` is stored as the canonical string representation of
      `PaymentMethod`.
    - `reference` is optional metadata for card/transfer authorization codes,
      external transaction identifiers, or operator-entered notes.
    """

    __tablename__ = "payment"
    __table_args__ = (
        Index("ix_payment_created_at", "created_at"),
        Index("ix_payment_method", "method"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sale.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    method: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        doc="Canonical payment method string from PaymentMethod.",
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    reference: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sale: Mapped["Sale"] = relationship(back_populates="payments")
