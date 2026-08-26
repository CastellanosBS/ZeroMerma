"""Add cleaning log quality module.

Revision ID: 20260520_0033_cleaning_logs
Revises: 20260520_0032_fin_recon
Create Date: 2026-05-20 23:59:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0033_cleaning_logs"
down_revision: str | None = "20260520_0032_fin_recon"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cleaning_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("area_type", sa.String(length=40), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("cleaning_type", sa.String(length=40), nullable=False),
        sa.Column("method_summary", sa.Text(), nullable=True),
        sa.Column("required_tools", sa.Text(), nullable=True),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("requires_evidence", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "area_type IN ('PRODUCTION_AREA', 'COUNTER_DISPLAY', 'STORAGE', 'RESTROOM', "
            "'CUSTOMER_AREA', 'EQUIPMENT', 'EXTERIOR', 'OTHER')",
            name=op.f("ck_cleaning_templates_area_type_valid"),
        ),
        sa.CheckConstraint(
            "cleaning_type IN ('ROUTINE', 'DEEP_CLEANING', 'EQUIPMENT', 'SANITATION', "
            "'SPILL_RESPONSE', 'OTHER')",
            name=op.f("ck_cleaning_templates_type_valid"),
        ),
        sa.CheckConstraint(
            "estimated_duration_minutes IS NULL OR estimated_duration_minutes >= 0",
            name=op.f("ck_cleaning_templates_duration_non_negative"),
        ),
        sa.CheckConstraint(
            "frequency IN ('PER_SHIFT', 'DAILY', 'WEEKLY', 'MONTHLY', 'AS_NEEDED')",
            name=op.f("ck_cleaning_templates_frequency_valid"),
        ),
        sa.CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_cleaning_templates_risk_level_valid"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "cleaning_template_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["cleaning_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "template_id",
            "display_order",
            name=op.f("uq_cleaning_template_items_template_order"),
        ),
    )
    op.create_table(
        "cleaning_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("area_name", sa.String(length=160), nullable=False),
        sa.Column("area_type", sa.String(length=40), nullable=False),
        sa.Column("equipment_name", sa.String(length=160), nullable=True),
        sa.Column("task_template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_name", sa.String(length=160), nullable=False),
        sa.Column("cleaning_type", sa.String(length=40), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("shift_code", sa.String(length=32), nullable=False),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("issue_notes", sa.Text(), nullable=True),
        sa.Column("evidence_note", sa.Text(), nullable=True),
        sa.Column("has_evidence", sa.Boolean(), nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "area_type IN ('PRODUCTION_AREA', 'COUNTER_DISPLAY', 'STORAGE', 'RESTROOM', "
            "'CUSTOMER_AREA', 'EQUIPMENT', 'EXTERIOR', 'OTHER')",
            name=op.f("ck_cleaning_logs_area_type_valid"),
        ),
        sa.CheckConstraint(
            "cleaning_type IN ('ROUTINE', 'DEEP_CLEANING', 'EQUIPMENT', 'SANITATION', "
            "'SPILL_RESPONSE', 'OTHER')",
            name=op.f("ck_cleaning_logs_type_valid"),
        ),
        sa.CheckConstraint(
            "frequency IS NULL OR frequency IN ('PER_SHIFT', 'DAILY', 'WEEKLY', 'MONTHLY', "
            "'AS_NEEDED')",
            name=op.f("ck_cleaning_logs_frequency_valid"),
        ),
        sa.CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_cleaning_logs_risk_level_valid"),
        ),
        sa.CheckConstraint(
            "shift_code IN ('MORNING', 'AFTERNOON', 'NIGHT', 'MIXED')",
            name=op.f("ck_cleaning_logs_shift_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'MISSED', "
            "'CANCELLED', 'REQUIRES_REVIEW')",
            name=op.f("ck_cleaning_logs_status_valid"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_template_id"], ["cleaning_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folio"),
    )
    op.create_table(
        "cleaning_log_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cleaning_log_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("label", sa.String(length=240), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cleaning_log_id"], ["cleaning_logs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_item_id"], ["cleaning_template_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cleaning_log_id",
            "display_order",
            name=op.f("uq_cleaning_log_checklist_items_log_order"),
        ),
    )


def downgrade() -> None:
    op.drop_table("cleaning_log_checklist_items")
    op.drop_table("cleaning_logs")
    op.drop_table("cleaning_template_items")
    op.drop_table("cleaning_templates")
