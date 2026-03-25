"""admin roles description and active flag

Revision ID: 088962cc9b26
Revises: adb306e854c7
Create Date: 2026-03-24 19:44:17.224904

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "088962cc9b26"
down_revision: Union[str, Sequence[str], None] = "adb306e854c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "role",
        sa.Column("description", sa.Text(), nullable=True),
    )

    op.add_column(
        "role",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    op.create_index(
        "ix_role_is_active",
        "role",
        ["is_active"],
        unique=False,
    )

    # Remove the server default after backfilling existing rows.
    op.alter_column("role", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_role_is_active", table_name="role")
    op.drop_column("role", "is_active")
    op.drop_column("role", "description")
