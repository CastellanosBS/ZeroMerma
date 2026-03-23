from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from zeromerma_api.scripts.bootstrap_db import (
    ensure_core_seed,
    ensure_dev_catalog_and_inventory,
    ensure_inventory_fixture,
    ensure_sample_pos_transaction,
)

SeedProfile = Literal["core", "dev", "inventory-fixture"]


def run_all(
    db: Session,
    *,
    profile: SeedProfile = "core",
    create_sample_sale: bool | None = None,
) -> dict[str, object]:
    """
    Backward-compatible package-level seeder used by older tests.

    This function preserves the historical contract expected by:
        from zeromerma_api.scripts.seed import run_all

    Important:
    - It does NOT create/close the SQLAlchemy session.
    - It does NOT run Alembic migrations.
    - It does NOT commit/rollback.
    - The caller owns the transaction boundary.

    Profiles:
      - core:
          roles + MAIN branch + admin/cashier users
      - dev:
          core + catalog + opening balances + snapshot rebuild
          optionally creates one sample POS sale/payment when possible
      - inventory-fixture:
          core + deterministic inventory fixture

    Returns:
        Summary dictionary describing what was ensured/seeded.
    """
    summary: dict[str, object] = {
        "profile": profile,
    }

    core = ensure_core_seed(db)
    summary["core"] = core

    branch_id = int(core["branch_id"])
    admin_user_id = int(core["admin_user_id"])

    if profile == "dev":
        dev_info = ensure_dev_catalog_and_inventory(
            db,
            branch_id=branch_id,
            created_by_id=admin_user_id,
        )
        summary["dev"] = dev_info

        should_create_sample = True if create_sample_sale is None else bool(create_sample_sale)
        if should_create_sample:
            sample_info = ensure_sample_pos_transaction(
                db,
                branch_id=branch_id,
                created_by_id=admin_user_id,
            )
            summary["sample_sale"] = sample_info

    elif profile == "inventory-fixture":
        fixture_info = ensure_inventory_fixture(
            db,
            branch_id=branch_id,
            created_by_id=admin_user_id,
        )
        summary["inventory_fixture"] = fixture_info

    return summary


def run_core(db: Session) -> dict[str, object]:
    """
    Convenience wrapper for the minimum operable seed.
    """
    return run_all(db, profile="core")


def run_dev(
    db: Session,
    *,
    create_sample_sale: bool = True,
) -> dict[str, object]:
    """
    Convenience wrapper for the richer development seed.
    """
    return run_all(
        db,
        profile="dev",
        create_sample_sale=create_sample_sale,
    )


def run_inventory_fixture(db: Session) -> dict[str, object]:
    """
    Convenience wrapper for deterministic inventory endpoint fixtures.
    """
    return run_all(db, profile="inventory-fixture")
