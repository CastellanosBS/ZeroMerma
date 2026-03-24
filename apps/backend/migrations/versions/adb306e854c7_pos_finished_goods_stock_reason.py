"""pos_finished_goods_stock_reason

Revision ID: adb306e854c7
Revises: bdd5d0ac6a12
Create Date: 2026-03-24 02:00:31.659244

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "adb306e854c7"
down_revision: Union[str, Sequence[str], None] = "bdd5d0ac6a12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_inventory_reason_check_if_present() -> None:
    """
    Drop only the canonical known inventory_movement reason CHECK names.

    Why raw SQL with IF EXISTS:
    - previous local environments showed unstable/reflected constraint names
    - PostgreSQL safely ignores missing names with IF EXISTS
    - this avoids migration failures caused by phantom/truncated names
    """
    op.execute(
        """
        ALTER TABLE inventory_movement
        DROP CONSTRAINT IF EXISTS ck_inventory_movement_reason
        """
    )
    op.execute(
        """
        ALTER TABLE inventory_movement
        DROP CONSTRAINT IF EXISTS ck_inventory_movement_ck_inventory_movement_reason
        """
    )
    op.execute(
        """
        ALTER TABLE inventory_movement
        DROP CONSTRAINT IF EXISTS ck_inventory_movement_ck_inventory_movement_ck_inventor_dc61
        """
    )


def upgrade() -> None:
    _drop_inventory_reason_check_if_present()

    op.create_check_constraint(
        "ck_inventory_movement_reason",
        "inventory_movement",
        "reason IN ("
        "'SALE','SALE_VOID','SALE_REFUND','POS_FINISHED_GOODS_STOCK_IN',"
        "'PURCHASE','ADJUSTMENT',"
        "'PRODUCTION_INPUT','PRODUCTION_OUTPUT',"
        "'TRANSFER_IN','TRANSFER_OUT','OPENING_BALANCE'"
        ")",
    )


def downgrade() -> None:
    _drop_inventory_reason_check_if_present()

    op.create_check_constraint(
        "ck_inventory_movement_reason",
        "inventory_movement",
        "reason IN ("
        "'SALE','SALE_VOID','SALE_REFUND',"
        "'PURCHASE','ADJUSTMENT',"
        "'PRODUCTION_INPUT','PRODUCTION_OUTPUT',"
        "'TRANSFER_IN','TRANSFER_OUT','OPENING_BALANCE'"
        ")",
    )
