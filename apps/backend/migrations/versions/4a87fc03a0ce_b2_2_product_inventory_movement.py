"""B2.2 product + inventory_movement

Revision ID: 4a87fc03a0ce
Revises: 6358fce6b0b4_admin_core_tables
Create Date: 2026-02-05 09:23:14.502428

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "4a87fc03a0ce"
down_revision: str | Sequence[str] | None = "6358fce6b0b4_admin_core_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
