"""Failure cleanup for explicit transaction owners; this module never commits."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from typing import Concatenate, cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@contextmanager
def rollback_on_error(session: Session) -> Iterator[None]:
    """Revert unfinished work before an error leaves its owner, including cancellation."""
    try:
        yield
    except BaseException:
        session.rollback()
        raise


def rollback_on_failure[Service, Result, **P](
    method: Callable[Concatenate[Service, Session, P], Result],
) -> Callable[Concatenate[Service, Session, P], Result]:
    """Keep a service's explicit commits while making failed calls safe to reuse."""

    @wraps(method)
    def guarded(service: Service, session: Session, *args: P.args, **kwargs: P.kwargs) -> Result:
        with rollback_on_error(session):
            return method(service, session, *args, **kwargs)

    return cast(Callable[Concatenate[Service, Session, P], Result], guarded)


def is_unique_violation(error: IntegrityError, *constraints: str) -> bool:
    """Translate only the named business constraint, never unrelated trace failures."""
    return (
        getattr(error.orig, "sqlstate", None) == "23505"
        and getattr(getattr(error.orig, "diag", None), "constraint_name", None) in constraints
    )
