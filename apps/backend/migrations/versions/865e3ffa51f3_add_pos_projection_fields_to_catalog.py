"""add_pos_projection_fields_to_catalog

Revision ID: 865e3ffa51f3
Revises: eee458f64e1a
Create Date: 2026-03-22 00:08:23.031608

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "865e3ffa51f3"
down_revision: Union[str, Sequence[str], None] = "eee458f64e1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # product_category: POS projection defaults
    # -------------------------------------------------------------------------
    op.add_column(
        "product_category",
        sa.Column(
            "quick_name",
            sa.Text(),
            nullable=True,
            comment="Short label for POS presentation.",
        ),
    )
    op.add_column(
        "product_category",
        sa.Column(
            "show_in_pos",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether this category is visible in POS bootstrap.",
        ),
    )
    op.add_column(
        "product_category",
        sa.Column(
            "default_pos_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
            comment="Default backend-provided ordering hint for POS presentation.",
        ),
    )

    op.create_index(
        "ix_product_category_show_in_pos",
        "product_category",
        ["show_in_pos"],
        unique=False,
    )
    op.create_index(
        "ix_product_category_default_pos_order",
        "product_category",
        ["default_pos_order"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # product: POS projection defaults
    # -------------------------------------------------------------------------
    op.add_column(
        "product",
        sa.Column(
            "quick_name",
            sa.Text(),
            nullable=True,
            comment="Short label for POS presentation.",
        ),
    )
    op.add_column(
        "product",
        sa.Column(
            "show_in_pos",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether this product is visible in POS bootstrap.",
        ),
    )
    op.add_column(
        "product",
        sa.Column(
            "is_sellable_in_pos",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Explicit sellability flag for POS presentation.",
        ),
    )
    op.add_column(
        "product",
        sa.Column(
            "default_pos_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
            comment="Default backend-provided ordering hint for POS presentation.",
        ),
    )

    op.create_index(
        "ix_product_show_in_pos",
        "product",
        ["show_in_pos"],
        unique=False,
    )
    op.create_index(
        "ix_product_is_sellable_in_pos",
        "product",
        ["is_sellable_in_pos"],
        unique=False,
    )
    op.create_index(
        "ix_product_default_pos_order",
        "product",
        ["default_pos_order"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # Backfill current rows
    # -------------------------------------------------------------------------
    op.execute(
        """
        UPDATE product_category
        SET quick_name = name
        WHERE quick_name IS NULL
        """
    )

    op.execute(
        """
        UPDATE product
        SET quick_name = name
        WHERE quick_name IS NULL
        """
    )

    op.execute(
        """
        UPDATE product
        SET show_in_pos = false,
            is_sellable_in_pos = false
        WHERE is_input = true
        """
    )

    op.execute(
        """
        UPDATE product_category
        SET show_in_pos = false
        WHERE code = 'INGREDIENTS'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_product_default_pos_order", table_name="product")
    op.drop_index("ix_product_is_sellable_in_pos", table_name="product")
    op.drop_index("ix_product_show_in_pos", table_name="product")

    op.drop_index("ix_product_category_default_pos_order", table_name="product_category")
    op.drop_index("ix_product_category_show_in_pos", table_name="product_category")

    op.drop_column("product", "default_pos_order")
    op.drop_column("product", "is_sellable_in_pos")
    op.drop_column("product", "show_in_pos")
    op.drop_column("product", "quick_name")

    op.drop_column("product_category", "default_pos_order")
    op.drop_column("product_category", "show_in_pos")
    op.drop_column("product_category", "quick_name")
