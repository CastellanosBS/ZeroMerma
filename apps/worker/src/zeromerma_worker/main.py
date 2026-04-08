from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Sequence

from sqlalchemy.exc import SQLAlchemyError

from zeromerma_worker.core.config import WorkerSettings, get_settings
from zeromerma_worker.core.logging import configure_logging
from zeromerma_worker.db.session import create_worker_engine
from zeromerma_worker.outbox.poller import OutboxPoller


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the ZeroMerma outbox worker.")
    parser.add_argument("--once", action="store_true", help="Poll once and exit.")
    parser.add_argument(
        "--skip-db-check",
        action="store_true",
        help="Boot the worker without opening a database connection.",
    )
    return parser


def run_worker(settings: WorkerSettings, *, once: bool, skip_db_check: bool) -> int:
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info(
        "worker_booted",
        extra={
            "environment": settings.environment,
            "poll_interval_seconds": settings.poll_interval_seconds,
            "batch_size": settings.batch_size,
            "skip_db_check": skip_db_check,
        },
    )

    if skip_db_check:
        return 0

    engine = create_worker_engine(settings)
    poller = OutboxPoller(engine=engine, batch_size=settings.batch_size)

    try:
        if once:
            poller.poll_once()
            return 0

        while True:
            poller.poll_once()
            time.sleep(settings.poll_interval_seconds)
    except SQLAlchemyError:
        logger.exception("worker_database_error")
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return run_worker(get_settings(), once=args.once, skip_db_check=args.skip_db_check)


if __name__ == "__main__":
    raise SystemExit(main())
