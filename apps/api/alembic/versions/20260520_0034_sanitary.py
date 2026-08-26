"""Add sanitary verification quality module.

Revision ID: 20260520_0034_sanitary_verifications
Revises: 20260520_0033_cleaning_logs
Create Date: 2026-05-20 23:59:30.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0034_sanitary"
down_revision: str | None = "20260520_0033_cleaning_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sanitary_verification_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("area_type", sa.String(length=40), nullable=False),
        sa.Column("process_type", sa.String(length=40), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("pass_threshold_percent", sa.Integer(), nullable=False),
        sa.Column("requires_evidence_on_failure", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "area_type IN ('PRODUCTION_AREA', 'COUNTER_DISPLAY', 'STORAGE', 'RESTROOM', "
            "'CUSTOMER_AREA', 'EQUIPMENT', 'EXTERIOR', 'OTHER')",
            name=op.f("ck_sanitary_verification_templates_area_type_valid"),
        ),
        sa.CheckConstraint(
            "frequency IN ('PER_SHIFT', 'DAILY', 'WEEKLY', 'MONTHLY', 'AS_NEEDED')",
            name=op.f("ck_sanitary_verification_templates_frequency_valid"),
        ),
        sa.CheckConstraint(
            "pass_threshold_percent >= 0 AND pass_threshold_percent <= 100",
            name=op.f("ck_sanitary_verification_templates_threshold_valid"),
        ),
        sa.CheckConstraint(
            "process_type IN ('STORAGE', 'PRODUCTION', 'DISPLAY', 'EQUIPMENT', "
            "'SANITATION', 'OTHER')",
            name=op.f("ck_sanitary_verification_templates_process_type_valid"),
        ),
        sa.CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_sanitary_verification_templates_risk_level_valid"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "sanitary_verification_template_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expected_standard", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("evidence_required_on_failure", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_sanitary_verification_template_items_risk_level_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["sanitary_verification_templates.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "template_id",
            "display_order",
            name=op.f("uq_sanitary_verification_template_items_template_order"),
        ),
    )
    op.create_table(
        "sanitary_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("area_name", sa.String(length=160), nullable=False),
        sa.Column("area_type", sa.String(length=40), nullable=False),
        sa.Column("equipment_name", sa.String(length=160), nullable=True),
        sa.Column("process_name", sa.String(length=160), nullable=True),
        sa.Column("process_type", sa.String(length=40), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("template_name", sa.String(length=160), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("inspector_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("findings_notes", sa.Text(), nullable=True),
        sa.Column("evidence_note", sa.Text(), nullable=True),
        sa.Column("has_evidence", sa.Boolean(), nullable=False),
        sa.Column("has_incident", sa.Boolean(), nullable=False),
        sa.Column("incident_reference", sa.String(length=80), nullable=True),
        sa.Column("follow_up_required", sa.Boolean(), nullable=False),
        sa.Column("follow_up_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("passed_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("not_applicable_count", sa.Integer(), nullable=False),
        sa.Column("checklist_total_count", sa.Integer(), nullable=False),
        sa.Column("score_percent", sa.Integer(), nullable=True),
        sa.Column("max_score", sa.Integer(), nullable=True),
        sa.Column("pass_threshold_percent", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "area_type IN ('PRODUCTION_AREA', 'COUNTER_DISPLAY', 'STORAGE', 'RESTROOM', "
            "'CUSTOMER_AREA', 'EQUIPMENT', 'EXTERIOR', 'OTHER')",
            name=op.f("ck_sanitary_verifications_area_type_valid"),
        ),
        sa.CheckConstraint(
            "process_type IN ('STORAGE', 'PRODUCTION', 'DISPLAY', 'EQUIPMENT', "
            "'SANITATION', 'OTHER')",
            name=op.f("ck_sanitary_verifications_process_type_valid"),
        ),
        sa.CheckConstraint(
            "result IN ('NOT_EVALUATED', 'PASSED', 'FAILED', 'PARTIAL')",
            name=op.f("ck_sanitary_verifications_result_valid"),
        ),
        sa.CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_sanitary_verifications_risk_level_valid"),
        ),
        sa.CheckConstraint(
            "score_percent IS NULL OR (score_percent >= 0 AND score_percent <= 100)",
            name=op.f("ck_sanitary_verifications_score_percent_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'PENDING', 'IN_PROGRESS', 'COMPLETED', "
            "'CANCELLED', 'REQUIRES_FOLLOW_UP')",
            name=op.f("ck_sanitary_verifications_status_valid"),
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inspector_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["sanitary_verification_templates.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folio"),
    )
    op.create_table(
        "sanitary_verification_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("label", sa.String(length=240), nullable=False),
        sa.Column("expected_standard", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("evidence_required_on_failure", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "result IN ('PENDING', 'PASSED', 'FAILED', 'NOT_APPLICABLE')",
            name=op.f("ck_sanitary_verification_checklist_items_result_valid"),
        ),
        sa.CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_sanitary_verification_checklist_items_risk_level_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["template_item_id"],
            ["sanitary_verification_template_items.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["verification_id"],
            ["sanitary_verifications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "verification_id",
            "display_order",
            name=op.f("uq_sanitary_verification_checklist_items_verification_order"),
        ),
    )


def downgrade() -> None:
    op.drop_table("sanitary_verification_checklist_items")
    op.drop_table("sanitary_verifications")
    op.drop_table("sanitary_verification_template_items")
    op.drop_table("sanitary_verification_templates")
