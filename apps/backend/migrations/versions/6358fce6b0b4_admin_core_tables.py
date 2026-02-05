# apps/backend/migrations/versions/6358fce6b0b4_admin_core_tables.py
# ^ Replace XXXXX... with the actual filename Alembic created; keep this header.

from __future__ import annotations  # modern typing of annotations

import sqlalchemy as sa  # SQLAlchemy namespace for column types, defaults, etc.
from alembic import op  # Alembic 'operations' module to emit DDL

# --- Alembic revision identifiers (auto-filled by 'alembic revision'); KEEP THEM SYNCED ---
revision = "6358fce6b0b4_admin_core_tables"  # Alembic puts a unique id here; do not change arbitrarily
down_revision = (
    "96c3be99bda4"  # previous migration id; Alembic fills this based on your head
)
branch_labels = None  # we don't use alembic branches in this project
depends_on = None  # no dependency on parallel revisions


def upgrade() -> None:
    """
    Apply schema changes FORWARD:
      1) Create 'branch'
      2) Create 'role'
      3) Create 'user_account' (with FKs to branch/role)
      4) Add indices/uniques
    """
    # 1) Create 'branch' table (stores physical locations)
    op.create_table(
        "branch",  # table name in snake_case
        # BIGINT primary key with autoincrement; plenty of headroom for many branches
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        # Short, human-stable code for references on labels/configs (e.g., "MAIN", "NORTH-01")
        sa.Column("code", sa.String(length=16), nullable=False),
        # Display name; Text to avoid length constraints (you can trim in UI)
        sa.Column("name", sa.Text(), nullable=False),
        # Active flag; server_default true so inserts default to active even if app forgets to send it
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        # Audit timestamps; TIMESTAMPTZ (timezone aware) with DB-side default 'now()'
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
        # Optional: a table-level COMMENT visible in psql and DB tools (Postgres supports this)
        comment="Physical store / location",
    )

    # Add a UNIQUE constraint on branch.code (unique index will be created implicitly)
    op.create_unique_constraint("uq_branch_code", "branch", ["code"])

    # 2) Create 'role' table (RBAC roles)
    op.create_table(
        "role",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        # Stable code like 'ADMIN', 'CASHIER', 'BAKER'
        sa.Column("code", sa.String(length=32), nullable=False),
        # Human-readable label (UI)
        sa.Column("name", sa.Text(), nullable=False),
        # Audit timestamps with server-side defaults
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

    # Unique constraint on role.code
    op.create_unique_constraint("uq_role_code", "role", ["code"])

    # 3) Create 'user_account' table (employees/users)
    op.create_table(
        "user_account",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        # Foreign keys to branch and role (NOT NULL because every user must have both).
        # We set 'ondelete=RESTRICT' to prevent deleting a branch/role if users exist.
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
        # Unique login identity (case-sensitive by default; enforce lowercase at app level if desired).
        sa.Column("email", sa.String(length=255), nullable=False),
        # Full display name for UI/reports
        sa.Column("full_name", sa.Text(), nullable=False),
        # Password hash (nullable for system/service/SSO accounts)
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        # Soft-activity flag
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        # Audit timestamps with server-side defaults
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

    # Unique constraint on email (prevents duplicate identities)
    op.create_unique_constraint("uq_user_account_email", "user_account", ["email"])

    # Add indexes on FK columns for faster joins/filters
    op.create_index("ix_user_account_branch_id", "user_account", ["branch_id"])
    op.create_index("ix_user_account_role_id", "user_account", ["role_id"])


def downgrade() -> None:
    """
    Revert schema changes BACKWARD:
      Drop indices/uniques (if needed), then tables in dependency order.
    """
    # Drop indexes created explicitly (constraints will be dropped with table)
    op.drop_index("ix_user_account_role_id", table_name="user_account")
    op.drop_index("ix_user_account_branch_id", table_name="user_account")

    # Drop unique constraints explicitly created (optional; dropping table also drops them)
    op.drop_constraint("uq_user_account_email", "user_account", type_="unique")
    op.drop_constraint("uq_role_code", "role", type_="unique")
    op.drop_constraint("uq_branch_code", "branch", type_="unique")

    # Drop tables in reverse dependency order: user_account → role → branch
    op.drop_table("user_account")
    op.drop_table("role")
    op.drop_table("branch")
