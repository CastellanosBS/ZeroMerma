"""create product and inventory movement (neutralized)

Revision ID: 8e1d77af65e2
Revises: 4a87fc03a0ce
Create Date: 2026-02-05

NOTE
----
This revision originally duplicated creation of `product` and `inventory_movement`
which are already created in 4a87fc03a0ce.

It caused fresh database upgrades to fail with:
  psycopg.errors.DuplicateTable: relation "product" already exists

We intentionally neutralize this migration to preserve a linear history while
making `alembic upgrade head` deterministic from an empty DB.

If later we truly need schema changes that were originally placed here, we will
create a NEW migration with only the required ALTER statements.
"""

from __future__ import annotations

# Alembic revision identifiers
revision = "8e1d77af65e2"
down_revision = "4a87fc03a0ce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Intentionally no-op (see module docstring).
    pass


def downgrade() -> None:
    # Intentionally no-op.
    pass
