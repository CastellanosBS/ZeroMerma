from __future__ import annotations

import json
import logging

from zeromerma_api.scripts.bootstrap_db import bootstrap_database

log = logging.getLogger(__name__)


def main() -> None:
    """
    Backward-compatible inventory fixture entrypoint.

    Creates a deterministic fixture suitable for inventory endpoint demos/tests:
      - one branch / users / roles
      - one sellable product
      - +10 OPENING_BALANCE
      - -3 SALE
      - inventory_balance rebuilt from ledger
    """
    summary = bootstrap_database(
        profile="inventory-fixture",
        apply_migrations=True,
        create_sample_sale=False,
    )

    log.info("Inventory fixture seed completed successfully.")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
