from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .branch import Branch
    from .user_account import UserAccount


class CashSessionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELED = "CANCELED"


class CashSession(Base):
    """
    Cash register session for a branch.

    Invariants:
    - At most one OPEN session per branch.
    - Monetary amounts are stored as Decimal-compatible NUMERIC(18,2).
    - expected_cash is persisted at close time.
    - reconciliation_snapshot stores the operational cash-close evidence
      captured when the session is closed.
    """

    __tablename__ = "cash_session"
    __table_args__ = (
        Index("ix_cash_session_opened_at", "opened_at"),
        Index("ix_cash_session_status", "status"),
        Index(
            "uq_cash_session_one_open_per_branch",
            "branch_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    opened_by_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    closed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    opening_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )

    closing_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
        doc="Actual cash counted in drawer at close.",
    )

    expected_cash: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
        doc="System-calculated expected cash at close time.",
    )

    reconciliation_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc=(
            "Persisted reconciliation evidence captured at close time, including "
            "expected payment totals by method, declared non-cash totals, "
            "differences, and optional operator note."
        ),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CashSessionStatus.OPEN.value,
        server_default=text("'OPEN'"),
    )

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    branch: Mapped["Branch"] = relationship()
    opened_by: Mapped["UserAccount"] = relationship(
        foreign_keys=[opened_by_id],
    )
    closed_by: Mapped["UserAccount | None"] = relationship(
        foreign_keys=[closed_by_id],
    )
