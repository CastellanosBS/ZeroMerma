from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .branch import Branch
    from .customer_order_item import CustomerOrderItem
    from .sale import Sale
    from .user_account import UserAccount


class CustomerOrderStatus(str, Enum):
    """
    Canonical lifecycle for customer orders.

    Semantics:
    - CREATED: cashier captured the order
    - SENT_TO_BAKERY: admin released the order to bakers
    - READY: bakers (or admin) marked it ready
    - DELIVERED: front-of-house delivered it from POS
    - CANCELED: order was canceled before delivery
    """

    CREATED = "CREATED"
    SENT_TO_BAKERY = "SENT_TO_BAKERY"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELED = "CANCELED"


class CustomerOrder(Base):
    """
    Customer order header for finished-goods requests.

    Business rules for 2B.1:
    - only existing catalog products
    - only finished goods (is_input = false)
    - creating / sending / marking ready does NOT affect inventory
    - price and total are frozen through snapshot fields in items/header
    - delivered_sale_id is reserved for future linkage to an eventual sale
    """

    __tablename__ = "customer_order"
    __table_args__ = (
        CheckConstraint(
            "status IN ('CREATED','SENT_TO_BAKERY','READY','DELIVERED','CANCELED')",
            name="ck_customer_order_status_allowed",
        ),
        Index("ix_customer_order_branch_id", "branch_id"),
        Index("ix_customer_order_status", "status"),
        Index("ix_customer_order_requested_for_at", "requested_for_at"),
        Index("ix_customer_order_created_at", "created_at"),
        Index("ix_customer_order_delivered_sale_id", "delivered_sale_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        nullable=False,
    )

    sent_to_bakery_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        nullable=True,
    )

    ready_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        nullable=True,
    )

    delivered_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        nullable=True,
    )

    canceled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        nullable=True,
    )

    delivered_sale_id: Mapped[int | None] = mapped_column(
        ForeignKey("sale.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'CREATED'"),
        default=CustomerOrderStatus.CREATED.value,
    )

    customer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    requested_for_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sent_to_bakery_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    branch: Mapped["Branch"] = relationship()
    created_by: Mapped["UserAccount"] = relationship(
        foreign_keys=[created_by_id],
    )
    sent_to_bakery_by: Mapped["UserAccount | None"] = relationship(
        foreign_keys=[sent_to_bakery_by_id],
    )
    ready_by: Mapped["UserAccount | None"] = relationship(
        foreign_keys=[ready_by_id],
    )
    delivered_by: Mapped["UserAccount | None"] = relationship(
        foreign_keys=[delivered_by_id],
    )
    canceled_by: Mapped["UserAccount | None"] = relationship(
        foreign_keys=[canceled_by_id],
    )
    delivered_sale: Mapped["Sale | None"] = relationship(
        foreign_keys=[delivered_sale_id],
    )

    items: Mapped[list["CustomerOrderItem"]] = relationship(
        back_populates="customer_order",
        cascade="all, delete-orphan",
    )
