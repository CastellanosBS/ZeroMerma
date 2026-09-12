"""Add Phase 4A correction documents and reasons.

Revision ID: 0006_phase_4a_corrections
Revises: 0005_phase_3a_operations
Create Date: 2026-04-09 18:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase_4a_corrections"
down_revision: str | None = "0005_phase_3a_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "correction_reasons",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1000"),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_correction_reasons")),
    )

    op.create_table(
        "correction_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_document_type", sa.String(length=40), nullable=False),
        sa.Column("correction_type", sa.String(length=40), nullable=False),
        sa.Column("source_branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "target_document_type IN ("
            "'COUNTER_TRANSFER', "
            "'WASTE_RECORD', "
            "'BRANCH_TRANSFER_SHIPMENT'"
            ")",
            name="ck_correction_documents_target_document_type_valid",
        ),
        sa.CheckConstraint(
            "correction_type IN ('DELTA_ADJUSTMENT')",
            name="ck_correction_documents_correction_type_valid",
        ),
        sa.CheckConstraint(
            "status IN ('COMMITTED')",
            name="ck_correction_documents_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reason_code"],
            ["correction_reasons.code"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_branch_id"],
            ["branches.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_document_id"],
            ["operation_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workstation_id"],
            ["workstations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_correction_documents")),
    )
    op.create_index(
        "ix_correction_documents_target_document_id",
        "correction_documents",
        ["target_document_id", "committed_at_utc"],
        unique=False,
    )

    op.create_table(
        "correction_document_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correction_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("target_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_class_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_class_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("delta_quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column(
            "unit_of_measure_code",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'EACH'"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "delta_quantity <> 0",
            name="ck_correction_document_lines_delta_quantity_non_zero",
        ),
        sa.ForeignKeyConstraint(
            ["correction_document_id"],
            ["correction_documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_class_id"],
            ["product_classes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["target_line_id"],
            ["operation_document_lines.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_correction_document_lines")),
        sa.UniqueConstraint(
            "correction_document_id",
            "line_number",
            name="uq_correction_document_lines_document_line_number",
        ),
    )
    op.create_index(
        "ix_correction_document_lines_document_id",
        "correction_document_lines",
        ["correction_document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_correction_document_lines_document_id",
        table_name="correction_document_lines",
    )
    op.drop_table("correction_document_lines")

    op.drop_index(
        "ix_correction_documents_target_document_id",
        table_name="correction_documents",
    )
    op.drop_table("correction_documents")

    op.drop_table("correction_reasons")
