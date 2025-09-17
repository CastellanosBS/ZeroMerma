"""baseline

Revision ID: 96c3be99bda4
Revises:
Create Date: 2025-09-16 21:20:49.077788

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "96c3be99bda4"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
