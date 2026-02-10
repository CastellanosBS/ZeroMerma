# apps/backend/src/zeromerma_api/models/cash_session.py
# PURPOSE: Represent a POS "cash session" (register session) per branch.
#          A branch typically has at most ONE open session at a time.
#          Sales will later reference a cash_session to enforce operational flow.

from __future__ import (
    annotations,
)  # Postpone evaluation of type hints (helps avoid import cycles).

from datetime import datetime  # We store open/close timestamps for auditing.
from enum import Enum  # We'll model session status as a constrained set of values.
from typing import (
    TYPE_CHECKING,
    Optional,
)  # Optional for nullable fields; TYPE_CHECKING avoids runtime cycles.

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)  # SQLAlchemy column types and DB expressions.
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)  # SQLAlchemy 2.0 typed ORM mapping tools.

from .base import (
    Base,
    created_at_col,
    updated_at_col,
)  # The single Declarative Base shared across your entire model layer.

# TYPE_CHECKING imports are ONLY for editors/type-checkers.
# They are NOT executed at runtime, which prevents circular imports.

if TYPE_CHECKING:
    from .branch import Branch
    from .user_account import UserAccount


class CashSessionStatus(str, Enum):
    """
    Allowed session statuses.
    Stored in DB as strings for simplicity and easy debugging.
    """

    OPEN = "OPEN"  # Session is active; sales are allowed.
    CLOSED = "CLOSED"  # Session is finished; sales should not be created under it.
    CANCELED = "CANCELED"  # Optional future use (e.g., session opened by mistake).


class CashSession(Base):
    """
    CashSession is the cashier/register lifecycle per branch:
      - opened_at/opening_amount recorded when opening the register
      - closed_at/closing_amount recorded when closing it
      - opened_by_id/closed_by_id for accountability
    """

    __tablename__ = "cash_session"  # Explicit table name; stable and predictable.

    # Primary key: BIGINT for plenty of headroom and consistent style with other tables.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Branch scope: a session belongs to exactly one branch (NOT NULL).
    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branch.id", ondelete="RESTRICT"
        ),  # RESTRICT: do not allow deleting branch with history.
        index=True,  # Index: we filter by branch frequently.
        nullable=False,
    )

    # Who opened the session (NOT NULL) — accountability.
    opened_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "user_account.id", ondelete="RESTRICT"
        ),  # Restrict: don't delete users with history by default.
        index=True,
        nullable=False,
    )

    # Who closed the session (nullable until closed).
    closed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "user_account.id", ondelete="SET NULL"
        ),  # If a user is removed, keep session but clear pointer.
        index=True,
        nullable=True,
    )

    # When the session was opened: DB-side timestamp.
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),  # DB sets time at insert; consistent across services.
    )

    # When the session was closed: NULL while status is OPEN.
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Currency fields as NUMERIC(18,2) to avoid floating precision errors.
    opening_amount: Mapped[float] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    closing_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    # Status stored as short string (OPEN/CLOSED/CANCELED).
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="OPEN",  # Default: an inserted session starts open unless stated otherwise.
    )

    # Standard audit timestamps (optional but useful for consistency and debugging).
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    # ORM relationships (not required, but improves developer ergonomics).
    branch: Mapped["Branch"] = (
        relationship()
    )  # We can add back_populates later if you want it bidirectional.
    opened_by: Mapped["UserAccount"] = relationship(foreign_keys=[opened_by_id])
    closed_by: Mapped[Optional["UserAccount"]] = relationship(
        foreign_keys=[closed_by_id]
    )
