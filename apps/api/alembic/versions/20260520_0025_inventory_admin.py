"""Add inventory balances, movements, and adjustments.

Revision ID: 20260520_0025_inventory_admin
Revises: 20260520_0024_branch_admin
Create Date: 2026-05-20 17:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0025_inventory_admin"
down_revision: str | None = "20260520_0024_branch_admin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_products_product_kind_valid", "products", type_="check")
    op.create_check_constraint(
        "ck_products_product_kind_valid",
        "products",
        "product_kind IN ('FINISHED_GOOD', 'RAW_MATERIAL', 'CONSUMABLE', 'DISPOSABLE')",
    )

    op.create_table(
        "inventory_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_code", sa.String(length=32), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(12, 3), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "location_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name=op.f("ck_inventory_balances_location_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name=op.f("fk_inventory_balances_branch_id_branches"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_inventory_balances_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_balances")),
        sa.UniqueConstraint(
            "product_id",
            "branch_id",
            "location_code",
            name="uq_inventory_balances_product_branch_location",
        ),
    )
    op.create_index(op.f("ix_inventory_balances_branch_id"), "inventory_balances", ["branch_id"], unique=False)
    op.create_index(op.f("ix_inventory_balances_product_id"), "inventory_balances", ["product_id"], unique=False)

    op.create_table(
        "inventory_adjustments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_code", sa.String(length=32), nullable=False),
        sa.Column("adjustment_type", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("previous_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("new_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("reason", sa.String(length=160), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "location_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name=op.f("ck_inventory_adjustments_location_valid"),
        ),
        sa.CheckConstraint(
            "adjustment_type IN ('INCREASE', 'DECREASE', 'SET_COUNTED')",
            name=op.f("ck_inventory_adjustments_type_valid"),
        ),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_inventory_adjustments_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name=op.f("fk_inventory_adjustments_branch_id_branches"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_inventory_adjustments_created_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_inventory_adjustments_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_adjustments")),
    )
    op.create_index(op.f("ix_inventory_adjustments_branch_id"), "inventory_adjustments", ["branch_id"], unique=False)
    op.create_index(
        op.f("ix_inventory_adjustments_product_id"),
        "inventory_adjustments",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_code", sa.String(length=32), nullable=False),
        sa.Column("movement_type", sa.String(length=40), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_of_measure", sa.String(length=32), nullable=False),
        sa.Column("source_document_type", sa.String(length=64), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("adjustment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operator_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("balance_after", sa.Numeric(12, 3), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "location_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name=op.f("ck_inventory_movements_location_valid"),
        ),
        sa.CheckConstraint(
            "movement_type IN ('MANUAL_ADJUSTMENT', 'STOCK_COUNT_ADJUSTMENT')",
            name=op.f("ck_inventory_movements_type_valid"),
        ),
        sa.CheckConstraint("direction IN ('IN', 'OUT')", name=op.f("ck_inventory_movements_direction_valid")),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_inventory_movements_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["adjustment_id"],
            ["inventory_adjustments.id"],
            name=op.f("fk_inventory_movements_adjustment_id_inventory_adjustments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name=op.f("fk_inventory_movements_branch_id_branches"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["operator_user_id"],
            ["users.id"],
            name=op.f("fk_inventory_movements_operator_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_inventory_movements_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_movements")),
    )
    op.create_index(op.f("ix_inventory_movements_branch_id"), "inventory_movements", ["branch_id"], unique=False)
    op.create_index(op.f("ix_inventory_movements_product_id"), "inventory_movements", ["product_id"], unique=False)
    op.create_index(op.f("ix_inventory_movements_occurred_at"), "inventory_movements", ["occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inventory_movements_occurred_at"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_product_id"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_branch_id"), table_name="inventory_movements")
    op.drop_table("inventory_movements")

    op.drop_index(op.f("ix_inventory_adjustments_product_id"), table_name="inventory_adjustments")
    op.drop_index(op.f("ix_inventory_adjustments_branch_id"), table_name="inventory_adjustments")
    op.drop_table("inventory_adjustments")

    op.drop_index(op.f("ix_inventory_balances_product_id"), table_name="inventory_balances")
    op.drop_index(op.f("ix_inventory_balances_branch_id"), table_name="inventory_balances")
    op.drop_table("inventory_balances")

    op.drop_constraint("ck_products_product_kind_valid", "products", type_="check")
    op.create_check_constraint(
        "ck_products_product_kind_valid",
        "products",
        "product_kind IN ('FINISHED_GOOD', 'RAW_MATERIAL')",
    )
