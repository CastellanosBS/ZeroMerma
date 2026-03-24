from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .branch import Branch
    from .user_account import UserAccount


class PosAuditEvent(Base):
    """
    Immutable operational audit event for the POS kernel.

    This table is intentionally generic enough to store audit records for:
    - cash session operations
    - checkouts
    - order delivery through checkout
    - sale void/refund reversals

    Conventions:
    - entity_type identifies the aggregate/document kind (SALE, CASH_SESSION, etc.)
    - entity_id points to the specific aggregate instance
    - event_type identifies the concrete operational event
    - payload stores structured evidence as JSONB
    """

    __tablename__ = "pos_audit_event"
    __table_args__ = (
        Index("ix_pos_audit_event_branch_id", "branch_id"),
        Index("ix_pos_audit_event_actor_user_id", "actor_user_id"),
        Index("ix_pos_audit_event_entity", "entity_type", "entity_id"),
        Index("ix_pos_audit_event_event_type", "event_type"),
        Index("ix_pos_audit_event_occurred_at", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    entity_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        default=dict,
    )

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    branch: Mapped["Branch"] = relationship()
    actor_user: Mapped["UserAccount | None"] = relationship()
