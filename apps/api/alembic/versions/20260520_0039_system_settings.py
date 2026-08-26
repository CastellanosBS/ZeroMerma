"""Add system settings.

Revision ID: 20260520_0039_system_settings
Revises: 20260520_0038_roles_permissions
Create Date: 2026-05-20 00:39:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0039_system_settings"
down_revision: str | None = "20260520_0038_roles_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=140), nullable=False),
        sa.Column("scope", sa.String(length=40), nullable=False),
        sa.Column("scope_id", sa.String(length=80), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "key",
            "scope",
            "scope_id",
            name="uq_system_settings_key_scope_scope_id",
        ),
    )
    op.create_table(
        "system_setting_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("setting_key", sa.String(length=140), nullable=False),
        sa.Column("scope", sa.String(length=40), nullable=False),
        sa.Column("scope_id", sa.String(length=80), nullable=False),
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_system_setting_history_setting_key",
        "system_setting_history",
        ["setting_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_system_setting_history_setting_key", table_name="system_setting_history")
    op.drop_table("system_setting_history")
    op.drop_table("system_settings")
