# apps/backend/src/zeromerma_api/models/inventory_movement.py
# PURPOSE: Single source of truth for stock changes (ledger).
#          Each row is an immutable movement (positive or negative).
#          Current stock is computed as SUM(qty) GROUP BY (branch_id, product_id).

from __future__ import (
    annotations,
)  # Postpone annotation evaluation -> fewer import cycles.

from datetime import datetime  # Audit timestamps.
from enum import Enum  # Python-level constraint for allowed reasons.
from typing import TYPE_CHECKING  # Optional fields & type-only imports.

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Numeric,
    String,
    Text,
)  # Core column/constraint types.
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)  # SQLAlchemy 2.0 ORM API.

from .base import (
    Base,
    created_at_col,
    updated_at_col,
)  # Shared Declarative Base for coherent metadata.

# TYPE_CHECKING imports give editors/types checkers class info without runtime imports (avoid cycles).
if TYPE_CHECKING:
    pass


class MovementReason(str, Enum):
    """
    Allowed movement reasons. We store them as STRINGs in the DB for flexibility.
    We'll also add a DB CHECK constraint in the migration to enforce the set.
    Positive qty = stock inflow; negative qty = stock outflow.
    """

    SALE = "SALE"  # Customer sale: finished goods OUT (negative qty).
    PURCHASE = "PURCHASE"  # Supplier purchase: goods IN (positive qty).
    ADJUSTMENT = "ADJUSTMENT"  # Manual correction: could be + or -.
    PRODUCTION_INPUT = (
        "PRODUCTION_INPUT"  # Consumed input for production: OUT (negative qty).
    )
    PRODUCTION_OUTPUT = (
        "PRODUCTION_OUTPUT"  # Produced finished goods: IN (positive qty).
    )
    TRANSFER_IN = "TRANSFER_IN"  # Branch transfer inbound: IN (positive qty).
    TRANSFER_OUT = "TRANSFER_OUT"  # Branch transfer outbound: OUT (negative qty).
    OPENING_BALANCE = "OPENING_BALANCE"  # Initial stock: IN (usually positive).


class InventoryMovement(Base):
    """
    One immutable stock movement (the ledger row).

    - 'branch_id' (FK): stock is always branch-scoped.
    - 'product_id' (FK): which item moved.
    - 'qty' (NUMERIC(18,3)): signed quantity (>= 0 for inflows; < 0 for outflows).
    - 'reason' (String): one of MovementReason values (validated in app; enforced via DB CHECK in migration).
    - 'ref_type' / 'ref_id': traceability to the generating document (SALE, PURCHASE, etc.).
    - 'note': optional comment.
    - 'created_by_id' (FK): attribution (nullable until auth is wired end-to-end).
    - Audit timestamps: DB-side defaults.
    """

    __tablename__ = "inventory_movement"

    # BIGINT PK: simple joins, ample range.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign keys: we RESTRICT deletes on branch/product to preserve history;
    # created_by can be SET NULL if a user is removed.
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    # Signed quantity. NUMERIC(18,3) covers grams and fractional pieces precisely.
    qty: Mapped[float] = mapped_column(Numeric(18, 3), nullable=False)

    # Reason: store the Enum's value as a DB string. Keep it short for indexing.
    reason: Mapped[str] = mapped_column(String(32), nullable=False)

    # Traceability to source document (e.g., SALE 123, PURCHASE 456).
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Optional human note (counts, shrinkage note, etc.).
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Attribution (nullable for system tasks/legacy backfills).
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Audit timestamps (DB-side now()).
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    # Relationships
    # String target avoids importing Product at runtime (prevents circular import).
    product = relationship("Product", back_populates="movements")
