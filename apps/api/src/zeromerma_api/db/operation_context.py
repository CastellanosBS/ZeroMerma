"""Transaction-local propagation to ORM trace writers and PostgreSQL audit triggers."""

from __future__ import annotations

import json

from sqlalchemy import Connection, event, func, select
from sqlalchemy.orm import Session, SessionTransaction

from zeromerma_api.core.operation_context import (
    OperationContext,
    SourceApp,
    current_operation_context,
    publish_operation_context,
)

_CONTEXT = "zeromerma_operation_context"
_SAVEPOINTS = "zeromerma_operation_savepoints"
_CONNECTION = "zeromerma_operation_connection"


def _apply(connection: Connection, context: OperationContext) -> None:
    if connection.dialect.name != "postgresql":
        return
    values = context.log_fields()
    connection.execute(
        select(
            *(
                func.set_config(
                    f"zeromerma.{key}",
                    json.dumps(value) if isinstance(value, list) else value or "",
                    True,
                )
                for key, value in values.items()
            )
        )
    )


def get_operation_context(session: Session) -> OperationContext:
    context = session.info.get(_CONTEXT)
    if not isinstance(context, OperationContext):
        context = current_operation_context() or OperationContext.start(SourceApp.SYSTEM)
        bind_operation_context(session, context)
    return context


def bind_operation_context(session: Session, context: OperationContext) -> None:
    """Bind provenance only. This does not grant capabilities or choose commit ownership."""
    session.info[_CONTEXT] = context
    publish_operation_context(context)
    if session.in_transaction():
        _apply(session.connection(), context)


def _after_begin(session: Session, transaction: SessionTransaction, connection: Connection) -> None:
    session.info[_CONNECTION] = connection
    context = session.info.get(_CONTEXT)
    if not isinstance(context, OperationContext):
        context = current_operation_context() or OperationContext.start(SourceApp.SYSTEM)
        session.info[_CONTEXT] = context
    _apply(connection, context)


def _after_transaction_end(session: Session, transaction: SessionTransaction) -> None:
    if transaction.parent is None:
        session.info.pop(_CONTEXT, None)
        session.info.pop(_SAVEPOINTS, None)
        session.info.pop(_CONNECTION, None)


def _after_transaction_create(session: Session, transaction: SessionTransaction) -> None:
    if transaction.nested:
        context = session.info.get(_CONTEXT)
        if not isinstance(context, OperationContext):
            context = current_operation_context() or OperationContext.start(SourceApp.SYSTEM)
            session.info[_CONTEXT] = context
        session.info.setdefault(_SAVEPOINTS, {})[transaction] = context


def _after_commit(session: Session) -> None:
    transaction = session.get_nested_transaction()
    if transaction is not None:
        session.info.get(_SAVEPOINTS, {}).pop(transaction, None)


def _after_soft_rollback(session: Session, previous_transaction: SessionTransaction) -> None:
    if not previous_transaction.nested:
        return
    snapshots = session.info.get(_SAVEPOINTS, {})
    if previous_transaction not in snapshots:
        return
    context = snapshots.pop(previous_transaction)
    if isinstance(context, OperationContext):
        # A lazily acquired connection may have materialized its root transaction only
        # after the snapshot changed. Synchronize that case as well as ordinary SET LOCAL.
        session.info[_CONTEXT] = context
        publish_operation_context(context)
        connection = session.info.get(_CONNECTION)
        if (
            isinstance(connection, Connection)
            and not connection.closed
            and not connection.invalidated
            and connection.in_transaction()
        ):
            # Session's nested context manager is still unwinding at this callback.
            # Use its live owned connection only: an invalidated connection cannot
            # restore GUCs, and reconnecting would mask the original database failure.
            _apply(connection, context)
    else:
        session.info.pop(_CONTEXT, None)


event.listen(Session, "after_begin", _after_begin)
event.listen(Session, "after_transaction_end", _after_transaction_end)
event.listen(Session, "after_transaction_create", _after_transaction_create)
event.listen(Session, "after_commit", _after_commit)
event.listen(Session, "after_soft_rollback", _after_soft_rollback)
