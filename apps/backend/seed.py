from __future__ import annotations

import argparse
import json
import logging

from zeromerma_api.scripts.bootstrap_db import bootstrap_database

log = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Canonical ZeroMerma DB bootstrap runner.")
    parser.add_argument(
        "--profile",
        choices=["core", "dev", "inventory-fixture"],
        default="core",
        help="Bootstrap profile to apply.",
    )
    parser.add_argument(
        "--skip-migrate",
        action="store_true",
        help="Do not run Alembic upgrade head before seeding.",
    )
    parser.add_argument(
        "--sample-sale",
        choices=["auto", "yes", "no"],
        default="auto",
        help="Only relevant for profile=dev. Controls whether to seed one sample POS sale.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.sample_sale == "auto":
        create_sample_sale = None
    elif args.sample_sale == "yes":
        create_sample_sale = True
    else:
        create_sample_sale = False

    summary = bootstrap_database(
        profile=args.profile,
        apply_migrations=not args.skip_migrate,
        create_sample_sale=create_sample_sale,
    )

    log.info("Bootstrap completed successfully.")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
