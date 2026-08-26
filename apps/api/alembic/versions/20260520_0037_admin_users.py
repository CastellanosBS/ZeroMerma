"""Add admin user management fields.

Revision ID: 20260520_0037_admin_users
Revises: 20260520_0036_incidents
Create Date: 2026-05-20 00:37:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260520_0037_admin_users"
down_revision: str | None = "20260520_0036_incidents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "allowed_surfaces",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("""'["POS"]'::jsonb"""),
        ),
    )
    op.execute("UPDATE users SET allowed_surfaces = jsonb_build_array(default_surface)")
    op.add_column(
        "users",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("lock_reason", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "password_reset_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("users", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "user_branch_assignments",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_check_constraint(
        "ck_users_allowed_surfaces_array",
        "users",
        "jsonb_typeof(allowed_surfaces) = 'array'",
    )
    op.execute(
        """
        UPDATE user_branch_assignments AS target
        SET is_default = true
        WHERE target.id IN (
          SELECT DISTINCT ON (user_id) id
          FROM user_branch_assignments
          WHERE is_active = true
          ORDER BY user_id, created_at ASC
        )
        """,
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_allowed_surfaces_array", "users", type_="check")
    op.drop_column("user_branch_assignments", "is_default")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "notes")
    op.drop_column("users", "phone")
    op.drop_column("users", "password_reset_required")
    op.drop_column("users", "lock_reason")
    op.drop_column("users", "is_locked")
    op.drop_column("users", "allowed_surfaces")
