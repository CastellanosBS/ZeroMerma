"""add_customer_order_model

Revision ID: 335c336469da
Revises: f359c6d7eb46
Create Date: 2026-03-23 13:26:18.272703

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "335c336469da"
down_revision: Union[str, Sequence[str], None] = "f359c6d7eb46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
