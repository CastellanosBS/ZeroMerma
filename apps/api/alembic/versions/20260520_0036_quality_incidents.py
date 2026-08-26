"""Add quality incidents module.

Revision ID: 20260520_0036_incidents
Revises: 20260520_0035_equipment
Create Date: 2026-05-20 23:59:50.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0036_incidents"
down_revision: str | None = "20260520_0035_equipment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quality_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("area_name", sa.String(length=160), nullable=True),
        sa.Column("equipment_name", sa.String(length=160), nullable=True),
        sa.Column("process_name", sa.String(length=160), nullable=True),
        sa.Column("product_reference", sa.String(length=120), nullable=True),
        sa.Column("production_reference", sa.String(length=120), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_reference", sa.String(length=120), nullable=True),
        sa.Column("source_summary", sa.Text(), nullable=True),
        sa.Column("incident_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("operational_impact", sa.Text(), nullable=True),
        sa.Column("food_safety_impact", sa.Boolean(), nullable=False),
        sa.Column("corrective_action", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reported_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_note", sa.Text(), nullable=True),
        sa.Column("has_evidence", sa.Boolean(), nullable=False),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolution_result", sa.String(length=160), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "incident_type IN ('SANITATION_ISSUE', 'CLEANING_NON_COMPLIANCE', "
            "'EQUIPMENT_FAILURE', 'PRODUCTION_ISSUE', 'INVENTORY_ISSUE', "
            "'TRANSFER_ISSUE', 'WASTE_ISSUE', 'SAFETY_ISSUE', 'CUSTOMER_COMPLAINT', "
            "'PROCESS_DEVIATION', 'OTHER')",
            name=op.f("ck_quality_incidents_type_valid"),
        ),
        sa.CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_quality_incidents_risk_level_valid"),
        ),
        sa.CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_quality_incidents_severity_valid"),
        ),
        sa.CheckConstraint(
            "source_type IN ('MANUAL', 'CLEANING_LOG', 'SANITARY_VERIFICATION', "
            "'EQUIPMENT', 'PRODUCTION', 'INVENTORY', 'TRANSFER', 'WASTE_MERMA', "
            "'CUSTOMER_REPORT', 'CORRECTION')",
            name=op.f("ck_quality_incidents_source_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'IN_REVIEW', 'IN_PROGRESS', 'WAITING_ACTION', "
            "'RESOLVED', 'CLOSED', 'CANCELLED')",
            name=op.f("ck_quality_incidents_status_valid"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reported_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folio"),
    )
    op.create_table(
        "quality_incident_follow_ups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("status_change", sa.String(length=32), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["incident_id"], ["quality_incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("quality_incident_follow_ups")
    op.drop_table("quality_incidents")
