"""Add Phase 3A operational documents and waste reasons.

Revision ID: 0005_phase_3a_operations
Revises: 0004_phase_2_pos_catalog_order
Create Date: 2026-04-09 12:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase_3a_operations"
down_revision: str | None = "0004_phase_2_pos_catalog_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "waste_reasons",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1000"),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_waste_reasons")),
    )

    op.create_table(
        "operation_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_bucket_code", sa.String(length=32), nullable=True),
        sa.Column("destination_bucket_code", sa.String(length=32), nullable=True),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reference_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "document_type IN ("
            "'COUNTER_TRANSFER', "
            "'WASTE_RECORD', "
            "'BRANCH_TRANSFER_SHIPMENT', "
            "'BRANCH_TRANSFER_RECEIPT'"
            ")",
            name="ck_operation_documents_document_type_valid",
        ),
        sa.CheckConstraint(
            "status IN ("
            "'DRAFT', "
            "'COMMITTED', "
            "'IN_TRANSIT', "
            "'RECEIVED', "
            "'RECEIVED_WITH_VARIANCE', "
            "'CANCELLED'"
            ")",
            name="ck_operation_documents_status_valid",
        ),
        sa.CheckConstraint(
            "source_bucket_code IS NULL OR "
            "source_bucket_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_operation_documents_source_bucket_valid",
        ),
        sa.CheckConstraint(
            "destination_bucket_code IS NULL OR "
            "destination_bucket_code IN ('BACKROOM', 'COUNTER', 'IN_TRANSIT', 'WASTE')",
            name="ck_operation_documents_destination_bucket_valid",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["destination_branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reason_code"], ["waste_reasons.code"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["reference_document_id"],
            ["operation_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["source_branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operation_documents")),
    )
    op.create_index(
        "ix_operation_documents_type_status",
        "operation_documents",
        ["document_type", "status", "committed_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_operation_documents_destination_branch",
        "operation_documents",
        ["destination_branch_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_operation_documents_reference_document_id",
        "operation_documents",
        ["reference_document_id"],
        unique=False,
    )

    op.create_table(
        "operation_document_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("product_class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_class_code_snapshot", sa.String(length=64), nullable=False),
        sa.Column("product_class_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("expected_quantity", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("received_quantity", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column(
            "unit_of_measure_code",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'EACH'"),
        ),
        sa.Column("variance_reason", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_operation_document_lines_quantity_positive"),
        sa.CheckConstraint(
            "expected_quantity IS NULL OR expected_quantity > 0",
            name="ck_operation_document_lines_expected_quantity_positive",
        ),
        sa.CheckConstraint(
            "received_quantity IS NULL OR received_quantity >= 0",
            name="ck_operation_document_lines_received_quantity_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["operation_document_id"],
            ["operation_documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_class_id"], ["product_classes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operation_document_lines")),
        sa.UniqueConstraint(
            "operation_document_id",
            "line_number",
            name="uq_operation_document_lines_document_line_number",
        ),
    )
    op.create_index(
        "ix_operation_document_lines_document_id",
        "operation_document_lines",
        ["operation_document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_operation_document_lines_document_id", table_name="operation_document_lines")
    op.drop_table("operation_document_lines")

    op.drop_index(
        "ix_operation_documents_reference_document_id",
        table_name="operation_documents",
    )
    op.drop_index("ix_operation_documents_destination_branch", table_name="operation_documents")
    op.drop_index("ix_operation_documents_type_status", table_name="operation_documents")
    op.drop_table("operation_documents")

    op.drop_table("waste_reasons")
