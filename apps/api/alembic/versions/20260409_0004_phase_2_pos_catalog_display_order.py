"""Add display order to POS catalog entities.

Revision ID: 0004_phase_2_pos_catalog_order
Revises: 0003_phase_2a_pos_sales
Create Date: 2026-04-09 00:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_phase_2_pos_catalog_order"
down_revision: str | None = "0003_phase_2a_pos_sales"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_classes",
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1000"),
    )
    op.add_column(
        "products",
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1000"),
    )

    op.execute("UPDATE product_classes SET display_order = 10 WHERE code = 'PAN-DULCE'")
    op.execute("UPDATE product_classes SET display_order = 20 WHERE code = 'BOLILLO'")
    op.execute("UPDATE product_classes SET display_order = 30 WHERE code = 'TELERA'")
    op.execute("UPDATE product_classes SET display_order = 110 WHERE code = 'BEBIDAS'")
    op.execute("UPDATE product_classes SET display_order = 120 WHERE code = 'PASTELES'")

    op.execute("UPDATE products SET display_order = 10 WHERE code = 'COCA-355'")
    op.execute("UPDATE products SET display_order = 20 WHERE code = 'CAFE-AMERICANO'")
    op.execute("UPDATE products SET display_order = 10 WHERE code = 'PASTEL-CHOC-IND'")
    op.execute("UPDATE products SET display_order = 20 WHERE code = 'REBANADA-TRES-LECHES'")

    op.alter_column("product_classes", "display_order", server_default=None)
    op.alter_column("products", "display_order", server_default=None)


def downgrade() -> None:
    op.drop_column("products", "display_order")
    op.drop_column("product_classes", "display_order")
