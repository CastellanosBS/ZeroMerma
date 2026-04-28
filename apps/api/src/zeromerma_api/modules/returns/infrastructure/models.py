from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zeromerma_api.db.base import Base
from zeromerma_api.modules.returns.domain.constants import (
    RETURN_DISPOSITION_RESTOCK_BACKROOM,
    RETURN_DISPOSITION_RESTOCK_COUNTER,
    RETURN_DISPOSITION_SEND_TO_WASTE,
    RETURN_REFUND_METHOD_CASH,
    RETURN_STATUS_COMMITTED,
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class SaleReturn(Base):
    __tablename__ = "sale_returns"
    __table_args__ = (
        CheckConstraint(
            "status IN ('COMMITTED')",
            name="ck_sale_returns_status_valid",
        ),
        CheckConstraint(
            "refund_method_code IN ('CASH')",
            name="ck_sale_returns_refund_method_valid",
        ),
        CheckConstraint(
            "total_refund_amount >= 0",
            name="ck_sale_returns_total_refund_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workstation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workstations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cash_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cash_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), default=RETURN_STATUS_COMMITTED, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_name: Mapped[str] = mapped_column(String(120), nullable=False)
    refund_method_code: Mapped[str] = mapped_column(
        String(40),
        default=RETURN_REFUND_METHOD_CASH,
        nullable=False,
    )
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN", nullable=False)
    total_refund_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class SaleReturnLine(Base):
    __tablename__ = "sale_return_lines"
    __table_args__ = (
        UniqueConstraint("sale_return_id", "line_number", name="uq_sale_return_lines_line_number"),
        CheckConstraint("returned_quantity > 0", name="ck_sale_return_lines_quantity_positive"),
        CheckConstraint(
            "refund_unit_price >= 0",
            name="ck_sale_return_lines_refund_unit_price_non_negative",
        ),
        CheckConstraint(
            "refund_line_total_amount >= 0",
            name="ck_sale_return_lines_refund_line_total_non_negative",
        ),
        CheckConstraint(
            "disposition_code IN ('RESTOCK_COUNTER', 'RESTOCK_BACKROOM', 'SEND_TO_WASTE')",
            name="ck_sale_return_lines_disposition_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_return_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_returns.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_sale_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_lines.id", ondelete="RESTRICT"),
        nullable=False,
    )
    original_capture_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    original_catalog_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    original_catalog_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    returned_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    returned_product_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    returned_product_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    returned_product_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_classes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    returned_product_class_code_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    returned_product_class_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    returned_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    refund_unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    refund_line_total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    disposition_code: Mapped[str] = mapped_column(
        String(32),
        default=RETURN_DISPOSITION_RESTOCK_COUNTER,
        nullable=False,
    )


_ = (
    RETURN_STATUS_COMMITTED,
    RETURN_REFUND_METHOD_CASH,
    RETURN_DISPOSITION_RESTOCK_COUNTER,
    RETURN_DISPOSITION_RESTOCK_BACKROOM,
    RETURN_DISPOSITION_SEND_TO_WASTE,
)
