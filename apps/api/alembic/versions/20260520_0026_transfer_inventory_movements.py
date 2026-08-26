"""Allow transfer inventory movement types.

Revision ID: 20260520_0026_transfer_moves
Revises: 20260520_0025_inventory_admin
Create Date: 2026-05-20 18:20:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260520_0026_transfer_moves"
down_revision: str | None = "20260520_0025_inventory_admin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_constraint(op.f("ck_inventory_movements_type_valid"), "inventory_movements", type_="check")
    op.create_check_constraint(
        op.f("ck_inventory_movements_type_valid"),
        "inventory_movements",
        "movement_type IN ('MANUAL_ADJUSTMENT', 'STOCK_COUNT_ADJUSTMENT')",
    )
