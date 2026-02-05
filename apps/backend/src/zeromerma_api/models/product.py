# apps/backend/src/zeromerma_api/models/product.py
# PURPOSE: Minimal product master so the inventory ledger can reference products.
#          Keep it intentionally small for MVP; we can add UoM, price history, etc. later.

from __future__ import (
    annotations,
)  # Defer evaluation of type hints -> fewer import cycles.

from datetime import datetime  # Timestamp type used in audit fields.
from typing import TYPE_CHECKING  # Type hints for optional fields & relationships.

from sqlalchemy import BigInteger, Boolean, String, Text  # Column types + DB defaults.
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)  # SQLAlchemy 2.0 typed ORM API.

from .base import (
    Base,
    created_at_col,
    updated_at_col,
)  # Single Declarative Base shared by all models.

# NOTE: We'll reference InventoryMovement only by string in 'relationship' to avoid runtime cycles.
#       TYPE_CHECKING lets the editor know about the class for autocompletion without importing at runtime.
if TYPE_CHECKING:
    from .inventory_movement import InventoryMovement


class Product(Base):
    """
    Minimal product definition for inventory control.

    - 'sku' (optional): a short unique code for barcodes/labels. We enforce UNIQUE at the DB level.
    - 'name': human-friendly name, free text.
    - 'is_active': soft flag for retiring products without deleting history.
    - Timestamps: DB-side defaults for auditability.
    """

    __tablename__ = "product"

    # BIGINT PK: plenty of headroom; predictable, simple FK joins.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Optional SKU: some items may not have codes initially. UNIQUE + index for fast lookup.
    sku: Mapped[str | None] = mapped_column(
        String(32), unique=True, index=True, nullable=True
    )

    # Free-text name; we avoid arbitrary length caps here.
    name: Mapped[str] = mapped_column(Text)

    # Operational toggle. Default True so new products are active by default.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Audit fields with DB-side defaults.
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    # Reverse relation: one product -> many inventory movements.
    # The string target avoids importing InventoryMovement at runtime (prevents cycles).
    movements: Mapped[list[InventoryMovement]] = relationship(back_populates="product")
