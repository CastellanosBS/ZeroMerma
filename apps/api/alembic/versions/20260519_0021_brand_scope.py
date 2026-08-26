"""Add canonical brand scope for branches and product classes.

Revision ID: 20260519_0021_brand_scope
Revises: 20260518_0020_counter_empty
Create Date: 2026-05-19 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260519_0021_brand_scope"
down_revision: str | None = "20260518_0020_counter_empty"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EL_MEJOR_PAN_BRAND_ID = "00000000-0000-4000-8000-000000000101"
MERENNA_BRAND_ID = "00000000-0000-4000-8000-000000000102"


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_brands")),
        sa.UniqueConstraint("code", name=op.f("uq_brands_code")),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO brands (id, code, name, is_active, created_at, updated_at)
            VALUES
              (CAST(:el_mejor_pan_id AS uuid), 'EL_MEJOR_PAN', 'El Mejor Pan', true, now(), now()),
              (CAST(:merenna_id AS uuid), 'MERENNA', 'Merenna', true, now(), now())
            """
        ).bindparams(el_mejor_pan_id=EL_MEJOR_PAN_BRAND_ID, merenna_id=MERENNA_BRAND_ID)
    )

    op.add_column("branches", sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_branches_brand_id_brands"),
        "branches",
        "brands",
        ["brand_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_branches_brand_id"), "branches", ["brand_id"], unique=False)
    op.execute(
        sa.text(
            """
            UPDATE branches
            SET brand_id = CASE
              WHEN code = 'NORTE' THEN CAST(:merenna_id AS uuid)
              ELSE CAST(:el_mejor_pan_id AS uuid)
            END
            """
        ).bindparams(el_mejor_pan_id=EL_MEJOR_PAN_BRAND_ID, merenna_id=MERENNA_BRAND_ID)
    )
    op.alter_column("branches", "brand_id", nullable=False)

    op.add_column("product_classes", sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_product_classes_brand_id_brands"),
        "product_classes",
        "brands",
        ["brand_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_product_classes_brand_id"), "product_classes", ["brand_id"], unique=False)
    op.execute(
        sa.text("UPDATE product_classes SET brand_id = CAST(:brand_id AS uuid)").bindparams(
            brand_id=EL_MEJOR_PAN_BRAND_ID
        )
    )
    op.alter_column("product_classes", "brand_id", nullable=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_product_classes_brand_id"), table_name="product_classes")
    op.drop_constraint(
        op.f("fk_product_classes_brand_id_brands"),
        "product_classes",
        type_="foreignkey",
    )
    op.drop_column("product_classes", "brand_id")

    op.drop_index(op.f("ix_branches_brand_id"), table_name="branches")
    op.drop_constraint(op.f("fk_branches_brand_id_brands"), "branches", type_="foreignkey")
    op.drop_column("branches", "brand_id")

    op.drop_table("brands")
