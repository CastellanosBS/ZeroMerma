from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from zeromerma_api.db.concurrency import (
    CommandConcurrencyConflict,
    is_retryable_transaction_error,
    restore_command_lock_timeout,
    set_command_lock_timeout,
)
from zeromerma_api.modules.idempotency.application.canonicalization import (
    canonical_fingerprint,
    parse_idempotency_key,
)
from zeromerma_api.modules.idempotency.application.context import (
    CommandExecution,
    assert_clean_entry,
    command_execution,
    execution,
    metadata_access,
)
from zeromerma_api.modules.idempotency.application.responses import (
    response_fingerprint,
    safe_snapshot,
    validate_policy,
)
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.domain.constants import IdempotencyStatus
from zeromerma_api.modules.idempotency.domain.exceptions import (
    DeterministicRejection,
    IdempotencyBoundaryError,
    IdempotencyInProgress,
    IdempotencyKeyReused,
    IdempotencyResultUnknown,
)
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord


def _saved_context(record: IdempotencyRecord) -> CommandContext:
    return CommandContext(
        actor_user_id=record.actor_user_id,
        branch_id=record.branch_id,
        workstation_id=record.workstation_id,
        cash_session_id=record.cash_session_id,
        **record.context_data,
    )


def _lookup(session: Session, key: UUID) -> IdempotencyRecord | None:
    with metadata_access(session):
        return session.scalar(
            select(IdempotencyRecord)
            .where(IdempotencyRecord.idempotency_key == key)
            .execution_options(populate_existing=True)
        )


class IdempotencyExecutor:
    """Own one root transaction, entered before any business write.

    Authentication may already have opened the transaction and flushed safe activity stamps.
    Context, authorization and reference resolvers are read-only. The action may flush and use
    savepoints, but must never commit/rollback the root or perform external effects. Route adoption
    removes service-owned commits explicitly; it does not wrap unchanged committing services.
    """

    def __init__(self, *, lock_timeout_ms: int = 1000, command_lock_timeout_ms: int = 5000) -> None:
        if not 1 <= lock_timeout_ms <= 60000:
            raise ValueError("The key contention timeout must be between 1 and 60000 milliseconds.")
        self.lock_timeout_ms = lock_timeout_ms
        if not 1 <= command_lock_timeout_ms <= 60000:
            raise ValueError("The command lock timeout must be between 1 and 60000 milliseconds.")
        self.command_lock_timeout_ms = command_lock_timeout_ms

    @staticmethod
    def _assert_unowned_entry(session: Session) -> None:
        if execution(session) is not None:
            raise IdempotencyBoundaryError("Nested idempotent commands are not supported.")
        assert_clean_entry(session)

    def recover(
        self,
        session: Session,
        *,
        key: UUID | str,
        operation_code: str,
        resolve_context: Callable[[Session, CommandContext | None], CommandContext],
        authorize: Callable[[Session, CommandContext], None],
        response_policy: ResponsePolicy,
    ) -> IdempotencyResult:
        """Recover an existing result without admitting a command or receiving its body."""
        self._assert_unowned_entry(session)
        parsed_key = parse_idempotency_key(key)
        validate_policy(response_policy)
        owner = CommandExecution(session.get_transaction() or session.begin())
        try:
            with command_execution(session, owner):
                previous_timeout = set_command_lock_timeout(session, self.command_lock_timeout_ms)
                record = _lookup(session, parsed_key)
                if record is None:
                    # A concurrent, uncommitted admission is indistinguishable from absence.
                    raise IdempotencyResultUnknown()
                owner.record = record
                if record.operation_code != operation_code:
                    raise IdempotencyKeyReused()
                saved = _saved_context(record)
                context = resolve_context(session, saved)
                self._assert_transaction(session, owner)
                if canonical_fingerprint(
                    operation_code=operation_code,
                    context=context,
                    payload={},
                    fingerprint_version=record.fingerprint_version,
                ) != canonical_fingerprint(
                    operation_code=operation_code,
                    context=saved,
                    payload={},
                    fingerprint_version=record.fingerprint_version,
                ):
                    raise IdempotencyKeyReused()
                authorize(session, saved)
                self._assert_transaction(session, owner)
                result = self._replay(session, record, response_policy)
                self._assert_transaction(session, owner)
                owner.finalizing = True
                restore_command_lock_timeout(session, previous_timeout)
                session.commit()
                return result
        except BaseException as error:
            session.rollback()
            if is_retryable_transaction_error(error):
                raise CommandConcurrencyConflict() from error
            raise

    def execute(
        self,
        session: Session,
        *,
        key: UUID | str,
        operation_code: str,
        payload: BaseModel | Mapping[str, object],
        resolve_context: Callable[[Session, CommandContext | None], CommandContext],
        authorize: Callable[[Session, CommandContext], None],
        action: Callable[[Session], CommandResult],
        response_policy: ResponsePolicy,
        request_id: str | None = None,
        fingerprint_version: int = 1,
    ) -> IdempotencyResult:
        self._assert_unowned_entry(session)
        parsed_key = parse_idempotency_key(key)
        validate_policy(response_policy)
        transaction = session.get_transaction() or session.begin()
        owner = CommandExecution(transaction)
        try:
            with command_execution(session, owner):
                previous_timeout = set_command_lock_timeout(session, self.command_lock_timeout_ms)
                record = _lookup(session, parsed_key)
                context = resolve_context(session, _saved_context(record) if record else None)
                self._assert_transaction(session, owner)
                fingerprint = canonical_fingerprint(
                    operation_code=operation_code,
                    context=context,
                    payload=payload,
                    fingerprint_version=fingerprint_version,
                )
                inserted = False
                if record is None:
                    authorize(session, context)
                    self._assert_transaction(session, owner)
                    record, inserted = self._reserve(
                        session,
                        key=parsed_key,
                        operation_code=operation_code,
                        context=context,
                        fingerprint=fingerprint,
                        fingerprint_version=fingerprint_version,
                        request_id=request_id,
                    )
                owner.record = record
                if (
                    record.operation_code != operation_code
                    or record.fingerprint_version != fingerprint_version
                    or record.request_fingerprint != fingerprint
                ):
                    raise IdempotencyKeyReused()
                if not inserted:
                    # Revalidate the durable context, including every related branch, on replay.
                    authorize(session, _saved_context(record))
                    result = self._replay(session, record, response_policy)
                    self._assert_transaction(session, owner)
                    owner.finalizing = True
                    restore_command_lock_timeout(session, previous_timeout)
                    session.commit()
                    return result

                rejection = None
                owner.action_running = True
                try:
                    with session.begin_nested():
                        outcome = action(session)
                        self._assert_transaction(session, owner)
                except DeterministicRejection as error:
                    rejection = error
                    outcome = CommandResult(
                        error.status_code, error.snapshot, reference=error.reference
                    )
                finally:
                    owner.action_running = False
                self._assert_transaction(session, owner)
                # Authority may have changed through this command; current authorization is required
                # for ordinary commands. Privileged callers supply their approved lifecycle rule.
                authorize(session, context)
                self._assert_transaction(session, owner)
                self._complete(record, outcome, response_policy, rejection)
                result = self._result(record, record.response_payload, replayed=False)
                owner.finalizing = True
                restore_command_lock_timeout(session, previous_timeout)
                session.commit()
                return result
        except BaseException as error:
            session.rollback()
            if is_retryable_transaction_error(error):
                raise CommandConcurrencyConflict() from error
            raise

    @staticmethod
    def _assert_transaction(session: Session, owner: CommandExecution) -> None:
        if owner.transaction is not session.get_transaction() or not owner.transaction.is_active:
            raise IdempotencyBoundaryError("The callback changed the owned root transaction.")
        if session.new or session.dirty or session.deleted:
            # Domain writes are flushed inside the action savepoint, never by preflight callbacks.
            if not owner.action_running and not owner.finalizing:
                raise IdempotencyBoundaryError(
                    "Context and authorization callbacks must be read-only."
                )

    def _reserve(
        self,
        session: Session,
        *,
        key: UUID,
        operation_code: str,
        context: CommandContext,
        fingerprint: str,
        fingerprint_version: int,
        request_id: str | None,
    ) -> tuple[IdempotencyRecord, bool]:
        now = datetime.now(UTC)
        row_id = uuid4()
        try:
            with session.begin_nested(), metadata_access(session):
                previous_timeout = session.scalar(select(func.current_setting("lock_timeout")))
                session.execute(
                    select(func.set_config("lock_timeout", f"{self.lock_timeout_ms}ms", True))
                )
                inserted_id = session.scalar(
                    insert(IdempotencyRecord)
                    .values(
                        id=row_id,
                        idempotency_key=key,
                        operation_code=operation_code,
                        fingerprint_version=fingerprint_version,
                        request_fingerprint=fingerprint,
                        actor_user_id=context.actor_user_id,
                        branch_id=context.branch_id,
                        workstation_id=context.workstation_id,
                        cash_session_id=context.cash_session_id,
                        context_data={
                            "surface": context.surface,
                            "related_branch_ids": sorted(
                                {str(item) for item in context.related_branch_ids}
                            ),
                        },
                        status=IdempotencyStatus.PROCESSING.value,
                        first_request_id=request_id[:128] if request_id else None,
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_nothing(constraint="uq_idempotency_records_key")
                    .returning(IdempotencyRecord.id)
                )
                session.execute(select(func.set_config("lock_timeout", previous_timeout, True)))
        except DBAPIError as error:
            # Rolling back the claim savepoint also restores its transaction-local setting.
            if getattr(error.orig, "sqlstate", None) == "55P03":
                raise IdempotencyInProgress() from error
            raise
        record = _lookup(session, key)
        if record is None:
            raise IdempotencyBoundaryError(
                "The command reservation was not visible after acquisition."
            )
        return record, inserted_id is not None

    @staticmethod
    def _complete(
        record: IdempotencyRecord,
        outcome: CommandResult,
        policy: ResponsePolicy,
        rejection: DeterministicRejection | None,
    ) -> None:
        if rejection is None and not 200 <= outcome.status_code < 300:
            raise IdempotencyBoundaryError("Successful commands require a successful HTTP status.")
        snapshot = safe_snapshot(
            outcome.snapshot, policy.rejection_model if rejection else policy.snapshot_model
        )
        if rejection and (
            snapshot.get("code") != rejection.code or snapshot.get("message") != rejection.message
        ):
            raise IdempotencyBoundaryError(
                "The rejection snapshot must preserve its explicit safe code/message."
            )
        reference = (
            safe_snapshot(outcome.reference, policy.reference_model)
            if outcome.reference is not None
            else None
        )
        if policy.payload_retention is not None and reference is None:
            raise IdempotencyBoundaryError("An expiring snapshot requires an immutable reference.")
        now = datetime.now(UTC)
        record.status = (
            IdempotencyStatus.REJECTED.value if rejection else IdempotencyStatus.COMPLETED.value
        )
        record.response_status = outcome.status_code
        record.response_schema_version = policy.schema_version
        record.response_payload = snapshot
        record.response_fingerprint = response_fingerprint(snapshot)
        record.response_reference = reference
        record.resource_type, record.resource_id = outcome.resource_type, outcome.resource_id
        record.error_code = rejection.code if rejection else None
        record.completed_at = record.updated_at = now
        record.response_expires_at = (
            now + policy.payload_retention if policy.payload_retention else None
        )

    def _replay(
        self, session: Session, record: IdempotencyRecord, policy: ResponsePolicy
    ) -> IdempotencyResult:
        if record.status == IdempotencyStatus.PROCESSING:
            raise IdempotencyInProgress()
        if record.status == IdempotencyStatus.UNKNOWN:
            raise IdempotencyResultUnknown()
        if record.response_schema_version != policy.schema_version:
            raise IdempotencyBoundaryError(
                "The persisted result requires its declared response schema."
            )
        model = (
            policy.rejection_model
            if record.status == IdempotencyStatus.REJECTED
            else policy.snapshot_model
        )
        if model is None:
            raise IdempotencyBoundaryError("The persisted outcome has no declared response policy.")
        payload = record.response_payload
        if payload is None:
            if (
                policy.restore is None
                or policy.reference_model is None
                or record.response_reference is None
            ):
                raise IdempotencyBoundaryError(
                    "The retained result cannot be reconstructed safely."
                )
            reference = policy.reference_model.model_validate(record.response_reference)
            payload = safe_snapshot(policy.restore(session, reference), model)
        else:
            payload = safe_snapshot(model.model_validate(payload), model)
        return self._result(record, payload, replayed=True)

    @staticmethod
    def _result(
        record: IdempotencyRecord, payload: dict[str, Any] | None, *, replayed: bool
    ) -> IdempotencyResult:
        if payload is None or record.response_status is None:
            raise IdempotencyBoundaryError("A terminal command requires a safe persisted result.")
        if record.response_fingerprint != response_fingerprint(payload):
            raise IdempotencyBoundaryError(
                "The response does not preserve the original logical result."
            )
        message = payload.get("message") if record.error_code else None
        if record.error_code and (
            payload.get("code") != record.error_code or not isinstance(message, str)
        ):
            raise IdempotencyBoundaryError(
                "The rejection snapshot lost its immutable error identity."
            )
        return IdempotencyResult(
            record.id,
            IdempotencyStatus(record.status),
            record.response_status,
            payload,
            replayed,
            record.error_code,
            message if isinstance(message, str) else None,
        )

    def purge_expired_payloads(
        self,
        session: Session,
        *,
        operation_code: str,
        response_policy: ResponsePolicy,
        now: datetime | None = None,
        limit: int = 100,
    ) -> int:
        self._assert_unowned_entry(session)
        owner = CommandExecution(session.get_transaction() or session.begin(), maintenance=True)
        try:
            with command_execution(session, owner):
                count = self._purge_expired_payloads(
                    session,
                    operation_code=operation_code,
                    response_policy=response_policy,
                    now=now,
                    limit=limit,
                )
                self._assert_transaction(session, owner)
                owner.finalizing = True
                session.commit()
                return count
        except BaseException:
            session.rollback()
            raise

    def _purge_expired_payloads(
        self,
        session: Session,
        *,
        operation_code: str,
        response_policy: ResponsePolicy,
        now: datetime | None = None,
        limit: int = 100,
    ) -> int:
        """Retain identity and verify immutable reconstruction before maintenance-only purge."""
        assert_clean_entry(session)
        validate_policy(response_policy)
        if response_policy.restore is None or not 1 <= limit <= 1000:
            raise IdempotencyBoundaryError(
                "Cleanup requires a bounded, reconstructible response policy."
            )
        cutoff = now or datetime.now(UTC)
        with metadata_access(session):
            records = list(
                session.scalars(
                    select(IdempotencyRecord)
                    .where(
                        IdempotencyRecord.operation_code == operation_code,
                        IdempotencyRecord.response_schema_version == response_policy.schema_version,
                        IdempotencyRecord.status.in_(["COMPLETED", "REJECTED"]),
                        IdempotencyRecord.response_payload.is_not(None),
                        IdempotencyRecord.response_reference.is_not(None),
                        IdempotencyRecord.response_expires_at <= cutoff,
                    )
                    .order_by(IdempotencyRecord.response_expires_at, IdempotencyRecord.id)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            )
        for record in records:
            if response_policy.reference_model is None:
                raise IdempotencyBoundaryError("Cleanup requires a declared immutable reference.")
            reference = response_policy.reference_model.model_validate(record.response_reference)
            model = (
                response_policy.rejection_model
                if record.error_code
                else response_policy.snapshot_model
            )
            restored = safe_snapshot(response_policy.restore(session, reference), model)
            if (
                restored != record.response_payload
                or response_fingerprint(restored) != record.response_fingerprint
            ):
                raise IdempotencyBoundaryError(
                    "The reference does not preserve the original logical result."
                )
            with metadata_access(session):
                session.execute(
                    update(IdempotencyRecord)
                    .where(IdempotencyRecord.id == record.id)
                    .values(response_payload=None, updated_at=datetime.now(UTC))
                    .execution_options(synchronize_session=False)
                )
        return len(records)
