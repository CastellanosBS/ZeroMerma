"""admin_core_tables

Revision ID: 6358fce6b0b4
Revises: 96c3be99bda4
Create Date: 2025-09-16

Creates:
- branch
- role
- user_account
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# --- Alembic revision identifiers ---
revision = "6358fce6b0b4"
down_revision = "96c3be99bda4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) branch: physical store / location
    op.create_table(
        "branch",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        comment="Physical store / location",
    )
    op.create_unique_constraint("uq_branch_code", "branch", ["code"])

    # 2) role: RBAC roles
    op.create_table(
        "role",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        comment="Role-based access control entry",
    )
    op.create_unique_constraint("uq_role_code", "role", ["code"])

    # 3) user_account: app users / employees
    op.create_table(
        "user_account",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column(
            "branch_id",
            sa.BigInteger(),
            sa.ForeignKey("branch.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.BigInteger(),
            sa.ForeignKey("role.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        comment="Application user / employee",
    )
    op.create_unique_constraint("uq_user_account_email", "user_account", ["email"])
    op.create_index("ix_user_account_branch_id", "user_account", ["branch_id"])
    op.create_index("ix_user_account_role_id", "user_account", ["role_id"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_user_account_role_id", table_name="user_account")
    op.drop_index("ix_user_account_branch_id", table_name="user_account")

    # Drop constraints (optional; dropping tables would also drop them)
    op.drop_constraint("uq_user_account_email", "user_account", type_="unique")
    op.drop_constraint("uq_role_code", "role", type_="unique")
    op.drop_constraint("uq_branch_code", "branch", type_="unique")

    # Drop tables in reverse dependency order
    op.drop_table("user_account")
    op.drop_table("role")
    op.drop_table("branch")
