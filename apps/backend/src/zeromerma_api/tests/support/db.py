from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def reset_pos_core_tables(session: Session) -> None:
    """
    Hard reset the main transactional/core tables used across POS tests.

    This helper intentionally truncates in dependency-safe order and resets
    identities to keep tests deterministic and easy to reason about.

    Scope:
    - admin/user/branch/role
    - catalog/pricing
    - sales/payments/cash session
    - inventory
    - production
    - customer orders

    Notes:
    - This is appropriate for local/dev DB-backed tests.
    - It assumes the schema already exists (Alembic head applied).
    """
    session.execute(
        text(
            """
            TRUNCATE TABLE
                customer_order_item,
                customer_order,
                product_price,
                payment,
                sale_item,
                sale,
                inventory_movement,
                inventory_balance,
                cash_session,
                production_run,
                user_account,
                role,
                branch,
                product,
                product_category
            RESTART IDENTITY CASCADE
            """
        )
    )
    session.commit()
