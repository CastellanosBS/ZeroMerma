"""add_customer_order_model

Revision ID: f359c6d7eb46
Revises: 49e9c4957813
Create Date: 2026-03-23 11:55:55.302046

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f359c6d7eb46"
down_revision: Union[str, Sequence[str], None] = "49e9c4957813"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_order",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "branch_id",
            sa.BigInteger(),
            sa.ForeignKey("branch.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "sent_to_bakery_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "ready_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "delivered_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "canceled_by_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "delivered_sale_id",
            sa.BigInteger(),
            sa.ForeignKey("sale.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'CREATED'"),
        ),
        sa.Column("customer_name", sa.Text(), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("requested_for_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_to_bakery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "subtotal",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "tax",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('CREATED','SENT_TO_BAKERY','READY','DELIVERED','CANCELED')",
            name="ck_customer_order_status_allowed",
        ),
    )

    op.create_index(
        "ix_customer_order_branch_id",
        "customer_order",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_order_status",
        "customer_order",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_customer_order_requested_for_at",
        "customer_order",
        ["requested_for_at"],
        unique=False,
    )
    op.create_index(
        "ix_customer_order_created_at",
        "customer_order",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_customer_order_delivered_sale_id",
        "customer_order",
        ["delivered_sale_id"],
        unique=False,
    )

    op.create_table(
        "customer_order_item",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "customer_order_id",
            sa.BigInteger(),
            sa.ForeignKey("customer_order.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("product.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "qty",
            sa.Numeric(18, 3),
            nullable=False,
        ),
        sa.Column(
            "unit_price_snapshot",
            sa.Numeric(18, 2),
            nullable=False,
        ),
        sa.Column(
            "line_total_snapshot",
            sa.Numeric(18, 2),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_customer_order_item_customer_order_id",
        "customer_order_item",
        ["customer_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_order_item_product_id",
        "customer_order_item",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_order_item_product_id",
        table_name="customer_order_item",
    )
    op.drop_index(
        "ix_customer_order_item_customer_order_id",
        table_name="customer_order_item",
    )
    op.drop_table("customer_order_item")

    op.drop_index(
        "ix_customer_order_delivered_sale_id",
        table_name="customer_order",
    )
    op.drop_index(
        "ix_customer_order_created_at",
        table_name="customer_order",
    )
    op.drop_index(
        "ix_customer_order_requested_for_at",
        table_name="customer_order",
    )
    op.drop_index(
        "ix_customer_order_status",
        table_name="customer_order",
    )
    op.drop_index(
        "ix_customer_order_branch_id",
        table_name="customer_order",
    )
    op.drop_table("customer_order")
