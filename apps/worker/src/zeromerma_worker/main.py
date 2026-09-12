from __future__ import annotations

import argparse
import logging
import signal
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from threading import Event, current_thread, main_thread
from types import FrameType

from pydantic import ValidationError
from sqlalchemy import Engine
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


@contextmanager
def _shutdown_signals(stop_requested: Event) -> Iterator[None]:
    """Wake polling waits on process termination and restore the caller's handlers."""
    if current_thread() is not main_thread():
        yield
        return

    def request_shutdown(signum: int, frame: FrameType | None) -> None:
        stop_requested.set()

    previous_handlers = {
        signum: signal.signal(signum, request_shutdown)
        for signum in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        yield
    finally:
        for signum, previous_handler in previous_handlers.items():
            signal.signal(signum, previous_handler)


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
        logger.info("worker_stopped", extra={"reason": "database_check_skipped"})
        return 0

    engine: Engine | None = None
    stop_requested = Event()
    stop_reason = "unexpected_error"

    try:
        engine = create_worker_engine(settings)
        poller = OutboxPoller(engine=engine, batch_size=settings.batch_size)
        with _shutdown_signals(stop_requested):
            while not stop_requested.is_set():
                poller.poll_once()
                if once:
                    break
                stop_requested.wait(settings.poll_interval_seconds)
        stop_reason = "poll_once_completed" if once else "shutdown_requested"
        return 0
    except KeyboardInterrupt:
        stop_reason = "keyboard_interrupt"
        return 0
    except SQLAlchemyError as error:
        stop_reason = "database_error"
        # Driver exception text can contain credentials or operational SQL/payloads.
        logger.error("worker_database_error", extra={"error_type": type(error).__name__})
        return 1
    finally:
        if engine is not None:
            engine.dispose()
        logger.info("worker_stopped", extra={"reason": stop_reason})


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        settings = get_settings()
    except ValidationError as error:
        configure_logging("ERROR")
        logging.getLogger(__name__).error(
            "worker_configuration_error",
            extra={"fields": [".".join(map(str, item["loc"])) for item in error.errors()]},
        )
        return 2
    return run_worker(settings, once=args.once, skip_db_check=args.skip_db_check)


if __name__ == "__main__":
    raise SystemExit(main())
