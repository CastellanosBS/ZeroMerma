"""Create Phase 1A identity, branch, workstation, and cash session schema.

Revision ID: 0002_phase_1a_core_identity_cash
Revises: 0001_foundation_schema
Create Date: 2026-04-08 00:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase_1a_core_identity_cash"
down_revision: str | None = "0001_foundation_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_branches")),
        sa.UniqueConstraint("code", name=op.f("uq_branches_code")),
    )

    op.create_table(
        "workstations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workstations")),
        sa.UniqueConstraint("code", name=op.f("uq_workstations_code")),
    )
    op.create_index(op.f("ix_workstations_branch_id"), "workstations", ["branch_id"], unique=False)

    op.create_table(
        "user_branch_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_branch_assignments")),
        sa.UniqueConstraint("user_id", "branch_id", name="uq_user_branch_assignments_user_branch"),
    )
    op.create_index(
        "ix_user_branch_assignments_active_lookup",
        "user_branch_assignments",
        ["user_id", "branch_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "cash_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("opening_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("opening_amount >= 0", name="ck_cash_sessions_opening_amount_non_negative"),
        sa.CheckConstraint(
            "status IN ('OPEN', 'CLOSED')",
            name="ck_cash_sessions_status_valid",
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_sessions")),
    )
    op.create_index(
        "ix_cash_sessions_open_workstation",
        "cash_sessions",
        ["workstation_id"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
    )
    op.create_index(
        "ix_cash_sessions_open_user",
        "cash_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
    )
    op.create_index(
        "ix_cash_sessions_current_lookup",
        "cash_sessions",
        ["status", "workstation_id", "user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cash_sessions_current_lookup", table_name="cash_sessions")
    op.drop_index("ix_cash_sessions_open_user", table_name="cash_sessions")
    op.drop_index("ix_cash_sessions_open_workstation", table_name="cash_sessions")
    op.drop_table("cash_sessions")

    op.drop_index("ix_user_branch_assignments_active_lookup", table_name="user_branch_assignments")
    op.drop_table("user_branch_assignments")

    op.drop_index(op.f("ix_workstations_branch_id"), table_name="workstations")
    op.drop_table("workstations")

    op.drop_table("branches")
    op.drop_table("users")
