"""pos_audit_event_table

Revision ID: bdd5d0ac6a12
Revises: d38a14a0df34
Create Date: 2026-03-24 00:50:54.335874

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bdd5d0ac6a12"
down_revision: Union[str, Sequence[str], None] = "d38a14a0df34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pos_audit_event",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "branch_id",
            sa.BigInteger(),
            sa.ForeignKey("branch.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.BigInteger(),
            sa.ForeignKey("user_account.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
    )

    op.create_index("ix_pos_audit_event_branch_id", "pos_audit_event", ["branch_id"])
    op.create_index(
        "ix_pos_audit_event_actor_user_id",
        "pos_audit_event",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_pos_audit_event_entity",
        "pos_audit_event",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_pos_audit_event_event_type",
        "pos_audit_event",
        ["event_type"],
    )
    op.create_index(
        "ix_pos_audit_event_occurred_at",
        "pos_audit_event",
        ["occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pos_audit_event_occurred_at", table_name="pos_audit_event")
    op.drop_index("ix_pos_audit_event_event_type", table_name="pos_audit_event")
    op.drop_index("ix_pos_audit_event_entity", table_name="pos_audit_event")
    op.drop_index("ix_pos_audit_event_actor_user_id", table_name="pos_audit_event")
    op.drop_index("ix_pos_audit_event_branch_id", table_name="pos_audit_event")
    op.drop_table("pos_audit_event")
