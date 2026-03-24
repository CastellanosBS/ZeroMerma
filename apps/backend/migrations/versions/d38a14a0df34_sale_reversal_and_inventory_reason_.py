"""add sale reversal audit fields and inventory movement reasons

Revision ID: d38a14a0df34
Revises: b2a23b75d5a3
Create Date: 2026-03-24 00:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d38a14a0df34"
down_revision = "b2a23b75d5a3"
branch_labels = None
depends_on = None


def _drop_inventory_reason_check_if_present() -> None:
    """
    Drop the existing inventory_movement reason CHECK constraint if present.

    Why this helper exists:
    - historical environments may have slightly different auto-generated names
    - the canonical original migration created `ck_inventory_movement_reason`
    - a previous version of this migration attempted to drop the wrong name and
      failed on upgrade

    This helper makes the migration resilient across local DB states while
    still preserving a single final CHECK definition.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_names = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("inventory_movement")
        if constraint.get("name")
    }

    candidate_names = (
        "ck_inventory_movement_reason",
        "ck_inventory_movement_ck_inventory_movement_reason",
    )

    for name in candidate_names:
        if name in existing_names:
            op.drop_constraint(name, "inventory_movement", type_="check")


def upgrade() -> None:
    """
    Add sale reversal audit fields and extend inventory movement reason support.
    """
    op.add_column(
        "sale",
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sale",
        sa.Column("voided_by_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "sale",
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sale",
        sa.Column("refunded_by_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "sale",
        sa.Column("reversal_reason", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "sale",
        sa.Column(
            "reversal_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_sale_voided_by_id_user_account",
        "sale",
        "user_account",
        ["voided_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_sale_refunded_by_id_user_account",
        "sale",
        "user_account",
        ["refunded_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index("ix_sale_voided_by_id", "sale", ["voided_by_id"])
    op.create_index("ix_sale_refunded_by_id", "sale", ["refunded_by_id"])

    _drop_inventory_reason_check_if_present()

    op.create_check_constraint(
        "ck_inventory_movement_reason",
        "inventory_movement",
        "reason IN ("
        "'SALE','SALE_VOID','SALE_REFUND','PURCHASE','ADJUSTMENT',"
        "'PRODUCTION_INPUT','PRODUCTION_OUTPUT',"
        "'TRANSFER_IN','TRANSFER_OUT','OPENING_BALANCE'"
        ")",
    )


def downgrade() -> None:
    """
    Remove reversal audit fields and restore the older movement-reason CHECK.
    """
    _drop_inventory_reason_check_if_present()

    op.create_check_constraint(
        "ck_inventory_movement_reason",
        "inventory_movement",
        "reason IN ("
        "'SALE','PURCHASE','ADJUSTMENT',"
        "'PRODUCTION_INPUT','PRODUCTION_OUTPUT',"
        "'TRANSFER_IN','TRANSFER_OUT','OPENING_BALANCE'"
        ")",
    )

    op.drop_index("ix_sale_refunded_by_id", table_name="sale")
    op.drop_index("ix_sale_voided_by_id", table_name="sale")

    op.drop_constraint(
        "fk_sale_refunded_by_id_user_account",
        "sale",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_sale_voided_by_id_user_account",
        "sale",
        type_="foreignkey",
    )

    op.drop_column("sale", "reversal_snapshot")
    op.drop_column("sale", "reversal_reason")
    op.drop_column("sale", "refunded_by_id")
    op.drop_column("sale", "refunded_at")
    op.drop_column("sale", "voided_by_id")
    op.drop_column("sale", "voided_at")
