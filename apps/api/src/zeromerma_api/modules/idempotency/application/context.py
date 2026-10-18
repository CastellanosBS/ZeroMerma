from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import Table, event, inspect
from sqlalchemy.orm import ORMExecuteState, Session, SessionTransaction
from sqlalchemy.sql import visitors
from sqlalchemy.sql.dml import Insert
from sqlalchemy.sql.elements import ClauseElement, TextClause
from sqlalchemy.sql.functions import Function

from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord

_EXECUTION = "zeromerma_idempotent_execution"
_METADATA = "zeromerma_idempotency_metadata"
_PRIOR_WRITES = "zeromerma_idempotency_prior_writes"
_METADATA_TOKEN = object()
_BOUNDARY_INITIALIZATION = "zeromerma_idempotency_boundary_initialization"
_BOUNDARY_TOKEN = object()


@dataclass
class CommandExecution:
    transaction: SessionTransaction
    record: IdempotencyRecord | None = None
    finalizing: bool = False
    action_running: bool = False
    maintenance: bool = False


def execution(session: Session) -> CommandExecution | None:
    value = session.info.get(_EXECUTION)
    return value if isinstance(value, CommandExecution) else None


@contextmanager
def command_execution(session: Session, value: CommandExecution) -> Iterator[None]:
    if execution(session) is not None:
        raise IdempotencyBoundaryError("Nested idempotent commands are not supported.")
    session.info[_EXECUTION] = value
    try:
        yield
    finally:
        session.info.pop(_EXECUTION, None)


@contextmanager
def metadata_access(session: Session) -> Iterator[None]:
    previous = session.info.get(_METADATA)
    session.info[_METADATA] = _METADATA_TOKEN
    try:
        yield
    finally:
        if previous is None:
            session.info.pop(_METADATA, None)
        else:
            session.info[_METADATA] = previous


def metadata_statement_allowed(session: Session, statement: object) -> bool:
    if session.info.get(_METADATA) is not _METADATA_TOKEN or not isinstance(
        statement, ClauseElement
    ):
        return False
    nodes = tuple(visitors.iterate(statement))
    if any(isinstance(node, TextClause) for node in nodes):
        return False
    tables = {node.name for node in nodes if isinstance(node, Table)}
    if tables:
        return tables == {"idempotency_records"}
    functions = {node.name for node in nodes if isinstance(node, Function)}
    return bool(functions) and functions.issubset({"current_setting", "set_config"})


def record_mutation_allowed(session: Session, instance: object) -> bool:
    owner = execution(session)
    return (
        isinstance(instance, IdempotencyRecord)
        and owner is not None
        and owner.record is instance
        and owner.finalizing
        and instance not in session.deleted
    )


@contextmanager
def authorization_boundary_initialization(session: Session) -> Iterator[None]:
    """Permit only the existing singleton's idempotent initialization before admission."""
    previous = session.info.get(_BOUNDARY_INITIALIZATION)
    session.info[_BOUNDARY_INITIALIZATION] = _BOUNDARY_TOKEN
    try:
        yield
    finally:
        if previous is None:
            session.info.pop(_BOUNDARY_INITIALIZATION, None)
        else:
            session.info[_BOUNDARY_INITIALIZATION] = previous


def _is_boundary_initialization(state: ORMExecuteState) -> bool:
    statement = state.statement
    return (
        execution(state.session) is None
        and state.session.info.get(_BOUNDARY_INITIALIZATION) is _BOUNDARY_TOKEN
        and isinstance(statement, Insert)
        and statement.table.name == "identity_privilege_state"
        and statement.compile().params == {"id": 1}
        and not any(isinstance(node, TextClause) for node in visitors.iterate(statement))
    )


def assert_clean_entry(session: Session) -> None:
    if session.new or session.dirty or session.deleted or session.info.get(_PRIOR_WRITES):
        raise IdempotencyBoundaryError(
            "Enter the command before business writes; flush safe authentication activity first."
        )


def _before_flush(session: Session, flush_context: object, instances: object) -> None:
    owner = execution(session)
    for instance in (*session.new, *session.dirty, *session.deleted):
        if isinstance(instance, IdempotencyRecord) and execution(session) is not None:
            if not record_mutation_allowed(session, instance):
                raise IdempotencyBoundaryError("Only the command owner can finalize its record.")
        elif owner is not None and not owner.action_running:
            raise IdempotencyBoundaryError("Authorization and replay callbacks must be read-only.")
        elif owner is None:
            state = inspect(instance)
            changes = {
                attribute.key for attribute in state.attrs if attribute.history.has_changes()
            }
            if not (
                state.mapper.local_table.name == "auth_sessions"
                and state.persistent
                and instance not in session.deleted
                and changes <= {"last_activity_at", "idle_expires_at"}
            ):
                session.info[_PRIOR_WRITES] = True


def _track_statement(state: ORMExecuteState) -> None:
    owner = execution(state.session)
    if (
        owner is not None
        and not owner.action_running
        and isinstance(state.statement, ClauseElement)
        and any(isinstance(node, TextClause) for node in visitors.iterate(state.statement))
    ):
        raise IdempotencyBoundaryError("Read-only callbacks require typed SQL expressions.")
    if state.is_insert or state.is_update or state.is_delete:
        internal = metadata_statement_allowed(state.session, state.statement)
        if owner is not None and not owner.action_running and not internal:
            raise IdempotencyBoundaryError("Authorization and replay callbacks must be read-only.")
        if owner is None and not internal and not _is_boundary_initialization(state):
            state.session.info[_PRIOR_WRITES] = True


def _before_commit(session: Session) -> None:
    owner = execution(session)
    if owner is not None and not session.in_nested_transaction():
        if (
            not owner.finalizing
            or owner.transaction is not session.get_transaction()
            or (
                not owner.maintenance
                and (owner.record is None or owner.record.status not in {"COMPLETED", "REJECTED"})
            )
        ):
            raise IdempotencyBoundaryError("Only the executor can commit a terminal command.")


def _after_transaction_end(session: Session, transaction: SessionTransaction) -> None:
    if transaction.parent is None:
        session.info.pop(_PRIOR_WRITES, None)


def install_transaction_guards() -> None:
    if not event.contains(Session, "before_flush", _before_flush):
        event.listen(Session, "before_flush", _before_flush)
        event.listen(Session, "before_commit", _before_commit)
        event.listen(Session, "after_transaction_end", _after_transaction_end)
        event.listen(Session, "do_orm_execute", _track_statement)


install_transaction_guards()
