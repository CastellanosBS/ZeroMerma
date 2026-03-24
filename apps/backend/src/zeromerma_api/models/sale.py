from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .branch import Branch
    from .cash_session import CashSession
    from .payment import Payment
    from .sale_item import SaleItem
    from .user_account import UserAccount


class SaleStatus(str, Enum):
    """
    Canonical sale lifecycle states for the POS kernel.
    """

    OPEN = "OPEN"
    PAID = "PAID"
    VOIDED = "VOIDED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"


class Sale(Base):
    """
    POS sale header.

    Notes:
    - receipt_snapshot stores the printable ticket captured at checkout time.
    - reversal_snapshot stores the operational evidence of a void/refund.
    """

    __tablename__ = "sale"
    __table_args__ = (
        Index("ix_sale_branch_id", "branch_id"),
        Index("ix_sale_cash_session_id", "cash_session_id"),
        Index("ix_sale_created_by_id", "created_by_id"),
        Index("ix_sale_status", "status"),
        Index("ix_sale_created_at", "created_at"),
        Index("ix_sale_voided_by_id", "voided_by_id"),
        Index("ix_sale_refunded_by_id", "refunded_by_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id", ondelete="RESTRICT"),
        nullable=False,
    )

    cash_session_id: Mapped[int] = mapped_column(
        ForeignKey("cash_session.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        nullable=False,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
        default=Decimal("0.00"),
    )

    tax: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
        default=Decimal("0.00"),
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
        default=Decimal("0.00"),
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'OPEN'"),
        default=SaleStatus.OPEN.value,
    )

    receipt_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Persisted printable receipt payload captured at checkout time.",
    )

    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    voided_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        nullable=True,
    )

    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    refunded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        nullable=True,
    )

    reversal_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    reversal_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Persisted operational evidence for sale void/refund actions.",
    )

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    branch: Mapped["Branch"] = relationship()
    cash_session: Mapped["CashSession"] = relationship()
    created_by: Mapped["UserAccount"] = relationship(
        foreign_keys=[created_by_id],
    )

    voided_by: Mapped["UserAccount | None"] = relationship(
        foreign_keys=[voided_by_id],
    )
    refunded_by: Mapped["UserAccount | None"] = relationship(
        foreign_keys=[refunded_by_id],
    )

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
    )
