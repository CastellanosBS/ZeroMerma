from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from zeromerma_api.modules.cash.application.command_context import (
    authorize_cash_command,
    resolve_cash_command_context,
)
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.operations.application.schemas import (
    CounterTransferCommitRequest,
    OperationCommitResultView,
    WasteCommitRequest,
)
from zeromerma_api.modules.operations.application.services import OperationsCommandService

OperationCommandCode = Literal["counter-transfer", "waste"]
OPERATION_CODES = {"counter-transfer": "counter_transfer.commit", "waste": "waste.commit"}
RESPONSE_POLICY = ResponsePolicy(snapshot_model=OperationCommitResultView)


class OperationCommitService:
    def __init__(self, command_service: OperationsCommandService | None = None) -> None:
        self._commands = command_service or OperationsCommandService()

    def commit(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CounterTransferCommitRequest | WasteCommitRequest,
        key: UUID,
        request_id: str | None,
    ) -> IdempotencyResult:
        code = "waste" if isinstance(command, WasteCommitRequest) else "counter-transfer"

        def action(current: Session) -> CommandResult:
            owner = execution(current)
            if owner is None or owner.record is None:
                raise IdempotencyBoundaryError("The operation requires an owned reservation.")
            if isinstance(command, WasteCommitRequest):
                result = self._commands.commit_waste_record(
                    current,
                    current_user=current_user,
                    command=command,
                    request_id=request_id,
                    idempotency_key=key,
                    operation_id=owner.record.id,
                )
            else:
                result = self._commands.commit_counter_transfer(
                    current,
                    current_user=current_user,
                    command=command,
                    request_id=request_id,
                    idempotency_key=key,
                    operation_id=owner.record.id,
                )
            return CommandResult(
                status_code=201,
                snapshot=result,
                resource_type="operation_document",
                resource_id=str(result.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=OPERATION_CODES[code],
            payload=command,
            resolve_context=lambda current, _saved: resolve_cash_command_context(
                current,
                current_user=current_user,
                workstation_code=command.workstation_code,
                cash_session_id=command.cash_session_id,
            ),
            authorize=lambda current, context: authorize_cash_command(
                current, current_user, context, "pos.operate"
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
        command_code: OperationCommandCode,
        workstation_code: str,
        cash_session_id: UUID,
    ) -> IdempotencyResult:
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=OPERATION_CODES[command_code],
            resolve_context=lambda current, _saved: resolve_cash_command_context(
                current,
                current_user=current_user,
                workstation_code=workstation_code,
                cash_session_id=cash_session_id,
            ),
            authorize=lambda current, context: authorize_cash_command(
                current, current_user, context, "pos.operate"
            ),
            response_policy=RESPONSE_POLICY,
        )
