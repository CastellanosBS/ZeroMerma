"""Add correction destination adjustment support.

Revision ID: 20260416_0015_corr_dest
Revises: 0014_remove_other_payment_method
Create Date: 2026-04-16 18:05:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260416_0015_corr_dest"
down_revision: str | None = "0014_remove_other_payment_method"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "correction_documents",
        sa.Column("corrected_destination_branch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_corr_docs_corr_dest_branch",
        "correction_documents",
        "branches",
        ["corrected_destination_branch_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "ck_correction_documents_correction_type_valid",
        "correction_documents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_correction_documents_correction_type_valid",
        "correction_documents",
        "correction_type IN ('DELTA_ADJUSTMENT', 'DESTINATION_ADJUSTMENT')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_correction_documents_correction_type_valid",
        "correction_documents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_correction_documents_correction_type_valid",
        "correction_documents",
        "correction_type IN ('DELTA_ADJUSTMENT')",
    )

    op.drop_constraint(
        "fk_corr_docs_corr_dest_branch",
        "correction_documents",
        type_="foreignkey",
    )
    op.drop_column("correction_documents", "corrected_destination_branch_id")
