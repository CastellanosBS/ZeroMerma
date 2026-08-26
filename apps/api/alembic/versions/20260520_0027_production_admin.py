"""Add production administration.

Revision ID: 20260520_0027_production
Revises: 20260520_0026_transfer_moves
Create Date: 2026-05-20 19:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0027_production"
down_revision: str | None = "20260520_0026_transfer_moves"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "production_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("planned_output_qty", sa.Numeric(12, 3), nullable=False),
        sa.Column("actual_output_qty", sa.Numeric(12, 3), nullable=True),
        sa.Column("variance_qty", sa.Numeric(12, 3), nullable=True),
        sa.Column("variance_percent", sa.Numeric(12, 4), nullable=True),
        sa.Column("planned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("variance_reason", sa.String(length=180), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("actual_output_qty IS NULL OR actual_output_qty >= 0", name="ck_production_batches_actual_output_non_negative"),
        sa.CheckConstraint("planned_output_qty > 0", name="ck_production_batches_planned_output_positive"),
        sa.CheckConstraint("status IN ('DRAFT', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')", name="ck_production_batches_status_valid"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cancelled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["started_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "production_batch_inputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("production_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("required_qty", sa.Numeric(12, 3), nullable=False),
        sa.Column("consumed_qty", sa.Numeric(12, 3), nullable=True),
        sa.Column("available_qty_snapshot", sa.Numeric(12, 3), nullable=True),
        sa.Column("shortage_qty_snapshot", sa.Numeric(12, 3), nullable=True),
        sa.Column("unit_of_measure", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("standard_cost_snapshot", sa.Numeric(12, 4), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("consumed_qty IS NULL OR consumed_qty >= 0", name="ck_production_batch_inputs_consumed_qty_non_negative"),
        sa.CheckConstraint("required_qty > 0", name="ck_production_batch_inputs_required_qty_positive"),
        sa.CheckConstraint("status IN ('available', 'insufficient', 'unavailable')", name="ck_production_batch_inputs_status_valid"),
        sa.ForeignKeyConstraint(["input_product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["production_batch_id"], ["production_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("production_batch_id", "input_product_id", name="uq_production_batch_inputs_batch_product"),
    )
    op.drop_constraint(op.f("ck_inventory_movements_type_valid"), "inventory_movements", type_="check")
    op.create_check_constraint(
        op.f("ck_inventory_movements_type_valid"),
        "inventory_movements",
        "movement_type IN ("
        "'MANUAL_ADJUSTMENT', "
        "'STOCK_COUNT_ADJUSTMENT', "
        "'TRANSFER_DISPATCH', "
        "'TRANSFER_RECEIPT', "
        "'PRODUCTION_CONSUMPTION', "
        "'PRODUCTION_OUTPUT'"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_inventory_movements_type_valid"), "inventory_movements", type_="check")
    op.create_check_constraint(
        op.f("ck_inventory_movements_type_valid"),
        "inventory_movements",
        "movement_type IN ("
        "'MANUAL_ADJUSTMENT', "
        "'STOCK_COUNT_ADJUSTMENT', "
        "'TRANSFER_DISPATCH', "
        "'TRANSFER_RECEIPT'"
        ")",
    )
    op.drop_table("production_batch_inputs")
    op.drop_table("production_batches")
