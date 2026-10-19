from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.cash.application.command_context import (
    authorize_cash_command,
    resolve_cash_command_context,
)
from zeromerma_api.modules.corrections.application.schemas import (
    CorrectionCommitRequest,
    CorrectionCommitResultView,
)
from zeromerma_api.modules.corrections.application.services import CorrectionCommandService
from zeromerma_api.modules.corrections.domain.exceptions import CorrectionNotFoundError
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument

OPERATION_CODE = "correction.commit"
RESPONSE_POLICY = ResponsePolicy(snapshot_model=CorrectionCommitResultView)


class CorrectionCommitService:
    def __init__(self, command_service: CorrectionCommandService | None = None) -> None:
        self._commands = command_service or CorrectionCommandService()

    def commit(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CorrectionCommitRequest,
        key: UUID,
        request_id: str | None,
    ) -> IdempotencyResult:
        def resolve_context(current: Session, saved: CommandContext | None) -> CommandContext:
            context = resolve_cash_command_context(
                current,
                current_user=current_user,
                workstation_code=command.workstation_code,
                cash_session_id=command.cash_session_id,
            )
            if saved is not None:
                return context.model_copy(update={"related_branch_ids": saved.related_branch_ids})
            target = current.execute(
                select(
                    OperationDocument.source_branch_id, OperationDocument.destination_branch_id
                ).where(OperationDocument.id == command.target_document_id)
            ).one_or_none()
            if target is None:
                raise CorrectionNotFoundError("The original document was not found.")
            branches = {
                target.source_branch_id,
                target.destination_branch_id,
                command.corrected_destination_branch_id,
            } - {None, context.branch_id}
            return context.model_copy(
                update={"related_branch_ids": tuple(sorted(branches, key=str))}
            )

        def action(current: Session) -> CommandResult:
            owner = execution(current)
            if owner is None or owner.record is None:
                raise IdempotencyBoundaryError("The command requires an owned reservation.")
            result = self._commands.commit_correction(
                current,
                current_user=current_user,
                command=command,
                idempotency_key=key,
                operation_id=owner.record.id,
                request_id=request_id,
            )
            return CommandResult(
                status_code=201,
                snapshot=result,
                resource_type="correction_document",
                resource_id=str(result.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=OPERATION_CODE,
            payload=command,
            resolve_context=resolve_context,
            authorize=lambda current, context: authorize_cash_command(
                current, current_user, context, "returns_corrections.manage"
            ),
            action=action,
            response_policy=RESPONSE_POLICY,
            request_id=request_id,
        )

    def recover(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        key: UUID,
        workstation_code: str,
        cash_session_id: UUID,
    ) -> IdempotencyResult:
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=OPERATION_CODE,
            resolve_context=lambda current, saved: resolve_cash_command_context(
                current,
                current_user=current_user,
                workstation_code=workstation_code,
                cash_session_id=cash_session_id,
            ).model_copy(update={"related_branch_ids": saved.related_branch_ids if saved else ()}),
            authorize=lambda current, context: authorize_cash_command(
                current, current_user, context, "returns_corrections.manage"
            ),
            response_policy=RESPONSE_POLICY,
        )
