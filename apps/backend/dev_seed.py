from __future__ import annotations

import json
import logging

from zeromerma_api.scripts.bootstrap_db import bootstrap_database

log = logging.getLogger(__name__)


def main() -> None:
    """
    Backward-compatible dev seed entrypoint.

    Canonical behavior:
      - upgrade to Alembic head
      - seed core admin data
      - seed catalog + inventory snapshot
      - seed one safe sample POS sale when possible
    """
    summary = bootstrap_database(
        profile="dev",
        apply_migrations=True,
        create_sample_sale=True,
    )

    log.info("Dev seed completed successfully.")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
