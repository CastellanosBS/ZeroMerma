"""Add equipment maintenance quality module.

Revision ID: 20260520_0035_equipment
Revises: 20260520_0034_sanitary
Create Date: 2026-05-20 23:59:40.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0035_equipment"
down_revision: str | None = "20260520_0034_sanitary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "equipment_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("equipment_type", sa.String(length=40), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("area_name", sa.String(length=160), nullable=True),
        sa.Column("area_type", sa.String(length=40), nullable=False),
        sa.Column("operational_status", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("serial_number", sa.String(length=120), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("warranty_expires_at", sa.Date(), nullable=True),
        sa.Column("provider_name", sa.String(length=180), nullable=True),
        sa.Column("maintenance_frequency_days", sa.Integer(), nullable=True),
        sa.Column("is_critical", sa.Boolean(), nullable=False),
        sa.Column("food_safety_critical", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("out_of_service_reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "area_type IN ('PRODUCTION', 'REFRIGERATION', 'DISPLAY_COUNTER', 'STORAGE', "
            "'CLEANING_SANITATION', 'OTHER')",
            name=op.f("ck_equipment_assets_area_type_valid"),
        ),
        sa.CheckConstraint(
            "equipment_type IN ('OVEN', 'MIXER', 'REFRIGERATION', 'DISPLAY_CASE', "
            "'SCALE', 'PACKAGING', 'SANITATION', 'OTHER')",
            name=op.f("ck_equipment_assets_type_valid"),
        ),
        sa.CheckConstraint(
            "maintenance_frequency_days IS NULL OR maintenance_frequency_days > 0",
            name=op.f("ck_equipment_assets_frequency_positive"),
        ),
        sa.CheckConstraint(
            "operational_status IN ('OPERATIONAL', 'OUT_OF_SERVICE', "
            "'UNDER_MAINTENANCE', 'RETIRED', 'INACTIVE')",
            name=op.f("ck_equipment_assets_status_valid"),
        ),
        sa.CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_equipment_assets_risk_level_valid"),
        ),
        sa.CheckConstraint(
            "warranty_expires_at IS NULL OR purchase_date IS NULL "
            "OR warranty_expires_at >= purchase_date",
            name=op.f("ck_equipment_assets_warranty_after_purchase"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "equipment_maintenance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("equipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("maintenance_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_name", sa.String(length=180), nullable=True),
        sa.Column("technician_name", sa.String(length=160), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("expected_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("result", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evidence_note", sa.Text(), nullable=True),
        sa.Column("has_evidence", sa.Boolean(), nullable=False),
        sa.Column("related_incident_reference", sa.String(length=80), nullable=True),
        sa.Column("source_document_type", sa.String(length=80), nullable=True),
        sa.Column("source_document_reference", sa.String(length=120), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "cost IS NULL OR cost >= 0",
            name=op.f("ck_equipment_maintenance_records_cost_non_negative"),
        ),
        sa.CheckConstraint(
            "expected_cost IS NULL OR expected_cost >= 0",
            name=op.f("ck_equipment_maintenance_records_expected_cost_non_negative"),
        ),
        sa.CheckConstraint(
            "maintenance_type IN ('PREVENTIVE', 'CORRECTIVE', 'INSPECTION', "
            "'CALIBRATION', 'CLEANING_TECHNICAL')",
            name=op.f("ck_equipment_maintenance_records_type_valid"),
        ),
        sa.CheckConstraint(
            "result IN ('NOT_COMPLETED', 'COMPLETED_SUCCESSFULLY', "
            "'COMPLETED_WITH_OBSERVATIONS', 'FAILED', 'REQUIRES_FOLLOW_UP', 'CANCELLED')",
            name=op.f("ck_equipment_maintenance_records_result_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'PENDING', 'IN_PROGRESS', 'COMPLETED', "
            "'OVERDUE', 'CANCELLED')",
            name=op.f("ck_equipment_maintenance_records_status_valid"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folio"),
    )


def downgrade() -> None:
    op.drop_table("equipment_maintenance_records")
    op.drop_table("equipment_assets")
