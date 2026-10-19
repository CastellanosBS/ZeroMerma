from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.cash.application.command_context import (
    lock_cash_session,
    resolve_cash_command_context,
    validate_cash_command_reference,
)
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, CapabilityCode
from zeromerma_api.modules.identity.application.session_services import auth_error
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument
from zeromerma_api.modules.transfers.application.admin_schemas import (
    AdminTransferCancelRequest,
    AdminTransferCreateRequest,
    AdminTransferDispatchRequest,
    AdminTransferReceiveRequest,
    AdminTransferUpdateRequest,
)
from zeromerma_api.modules.transfers.application.admin_services import AdminTransferService
from zeromerma_api.modules.transfers.application.physical_workflow import resolve as resolve_transit
from zeromerma_api.modules.transfers.application.schemas import (
    AdminTransferResolveRequest,
    PosTransferCommandCode,
    TransferCommandCode,
    TransferCommandResultView,
    TransferDispatchCommitRequest,
    TransferReceiveRequest,
    TransferResolveRequest,
)
from zeromerma_api.modules.transfers.application.services import TransferCommandService
from zeromerma_api.modules.transfers.domain.exceptions import (
    TransferNotFoundError,
    TransferValidationError,
)

TransferAdminCommand = (
    AdminTransferCreateRequest
    | AdminTransferUpdateRequest
    | AdminTransferDispatchRequest
    | AdminTransferReceiveRequest
    | AdminTransferCancelRequest
    | AdminTransferResolveRequest
)
TransferPosCommand = TransferDispatchCommitRequest | TransferReceiveRequest | TransferResolveRequest
TRANSFER_RESPONSE_POLICY = ResponsePolicy(snapshot_model=TransferCommandResultView)


def transfer_capability(code: TransferCommandCode) -> CapabilityCode:
    if code in {"create", "update"}:
        return "transfers.manage"
    return "transfers.cancel" if code == "cancel" else "transfers.execute"


def _branches(session: Session, transfer_id: UUID | None) -> tuple[UUID, UUID]:
    row = session.execute(
        select(OperationDocument.source_branch_id, OperationDocument.destination_branch_id).where(
            OperationDocument.id == transfer_id,
            OperationDocument.document_type == "BRANCH_TRANSFER_SHIPMENT",
        )
    ).one_or_none()
    if row is None or row.destination_branch_id is None:
        raise TransferNotFoundError("Transfer shipment was not found.")
    return row.source_branch_id, row.destination_branch_id


def _authorize(
    session: Session, user: AuthenticatedUser, context: CommandContext, code: TransferCommandCode
) -> None:
    if user.authorization_surface != context.surface or context.branch_id is None:
        raise auth_error(403, "FORBIDDEN", "The transfer surface is not authorized.")
    current = resolve_authorization(session, user, surface=context.surface)
    require_branches(
        current, transfer_capability(code), [context.branch_id, *context.related_branch_ids]
    )
    if code in {"resolve_return", "resolve_waste"}:
        require_branches(
            current,
            "transfers.cancel" if code == "resolve_return" else "waste.manage",
            [context.branch_id, *context.related_branch_ids],
        )
    branch_ids = {context.branch_id, *context.related_branch_ids}
    existing = set(session.scalars(select(Branch.id).where(Branch.id.in_(branch_ids))).all())
    if existing != branch_ids:
        raise TransferValidationError("A transfer branch was not found.")
    if context.surface == "POS":
        validate_cash_command_reference(session, context)


class TransferCommandServiceWrapper:
    def execute_pos(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: PosTransferCommandCode,
        command: TransferPosCommand,
        key: UUID,
        request_id: str | None,
        transfer_id: UUID | None = None,
    ) -> IdempotencyResult:
        if isinstance(command, TransferResolveRequest) and command_code != (
            "resolve_return" if command.kind == "RETURN_TO_ORIGIN" else "resolve_waste"
        ):
            raise IdempotencyBoundaryError("The resolution kind does not match its command.")
        if (command_code == "dispatch") != isinstance(command, TransferDispatchCommitRequest) or (
            command_code == "dispatch"
        ) != (transfer_id is None):
            raise IdempotencyBoundaryError("The transfer command does not match its operation.")

        def context(current: Session, saved: CommandContext | None) -> CommandContext:
            base = resolve_cash_command_context(
                current,
                current_user=current_user,
                workstation_code=command.workstation_code,
                cash_session_id=command.cash_session_id,
            )
            related = (
                saved.related_branch_ids
                if saved
                else (
                    (command.destination_branch_id,)
                    if isinstance(command, TransferDispatchCommitRequest)
                    else _branches(current, transfer_id)
                )
            )
            return CommandContext(
                actor_user_id=base.actor_user_id,
                surface="POS",
                branch_id=base.branch_id,
                workstation_id=base.workstation_id,
                cash_session_id=base.cash_session_id,
                related_branch_ids=tuple(sorted(set(related) - {base.branch_id}, key=str)),
            )

        def action(current: Session) -> CommandResult:
            base = resolve_cash_command_context(
                current,
                current_user=current_user,
                workstation_code=command.workstation_code,
                cash_session_id=command.cash_session_id,
            )
            if base.workstation_id is None or base.branch_id is None:
                raise IdempotencyBoundaryError("A POS transfer requires its workstation.")
            lock_cash_session(
                current,
                current_user=current_user,
                workstation_id=base.workstation_id,
                branch_id=base.branch_id,
                cash_session_id=command.cash_session_id,
            )
            service = TransferCommandService()
            if isinstance(command, TransferDispatchCommitRequest):
                result = service.commit_dispatch(
                    current, current_user=current_user, command=command, request_id=request_id
                )
            else:
                if transfer_id is None:
                    raise IdempotencyBoundaryError("A receipt requires its shipment.")
                if isinstance(command, TransferResolveRequest):
                    result = resolve_transit(
                        current,
                        transfer_id=transfer_id,
                        user=current_user,
                        command=command,
                        request_id=request_id,
                    )
                    return CommandResult(
                        200, result, resource_type="transfer", resource_id=str(result.id)
                    )
                result = service.receive_transfer(
                    current,
                    current_user=current_user,
                    workstation_code=command.workstation_code,
                    transfer_id=transfer_id,
                    command=command,
                    request_id=request_id,
                )
            return CommandResult(
                201 if command_code == "dispatch" else 200,
                result,
                resource_type="transfer",
                resource_id=str(result.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=f"transfer.{command_code}",
            payload={"transfer_id": transfer_id, "command": command},
            resolve_context=context,
            authorize=lambda current, saved: _authorize(current, current_user, saved, command_code),
            action=action,
            response_policy=TRANSFER_RESPONSE_POLICY,
            request_id=request_id,
        )

    def execute_admin(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: TransferCommandCode,
        command: TransferAdminCommand,
        key: UUID,
        request_id: str | None,
        transfer_id: UUID | None = None,
    ) -> IdempotencyResult:
        if isinstance(command, AdminTransferResolveRequest) and command_code != (
            "resolve_return" if command.kind == "RETURN_TO_ORIGIN" else "resolve_waste"
        ):
            raise IdempotencyBoundaryError("The resolution kind does not match its command.")
        types = {
            "create": AdminTransferCreateRequest,
            "update": AdminTransferUpdateRequest,
            "dispatch": AdminTransferDispatchRequest,
            "receive": AdminTransferReceiveRequest,
            "cancel": AdminTransferCancelRequest,
            "resolve_return": AdminTransferResolveRequest,
            "resolve_waste": AdminTransferResolveRequest,
        }
        if type(command) is not types[command_code] or (command_code == "create") != (
            transfer_id is None
        ):
            raise IdempotencyBoundaryError("The transfer command does not match its operation.")

        def context(current: Session, saved: CommandContext | None) -> CommandContext:
            if saved:
                origin, related = saved.branch_id, saved.related_branch_ids
            else:
                origin, destination = (
                    (command.origin_branch_id, command.destination_branch_id)
                    if isinstance(command, AdminTransferCreateRequest)
                    else _branches(current, transfer_id)
                )
                branches = {destination}
                if isinstance(command, AdminTransferUpdateRequest):
                    branches.update(
                        value
                        for value in (command.origin_branch_id, command.destination_branch_id)
                        if value is not None
                    )
                related = tuple(sorted(branches - {origin}, key=str))
            return CommandContext(
                actor_user_id=current_user.id,
                surface="BACKOFFICE",
                branch_id=origin,
                related_branch_ids=related,
            )

        def action(current: Session) -> CommandResult:
            service = AdminTransferService()
            if isinstance(command, AdminTransferCreateRequest):
                result = service.create_transfer(
                    current, current_user=current_user, command=command, request_id=request_id
                )
            else:
                if transfer_id is None:
                    raise IdempotencyBoundaryError("The command requires its shipment.")
                if isinstance(command, AdminTransferUpdateRequest):
                    result = service.update_transfer(
                        current,
                        current_user=current_user,
                        transfer_id=transfer_id,
                        command=command,
                        request_id=request_id,
                    )
                elif isinstance(command, AdminTransferDispatchRequest):
                    result = service.dispatch_transfer(
                        current,
                        current_user=current_user,
                        transfer_id=transfer_id,
                        command=command,
                        request_id=request_id,
                    )
                elif isinstance(command, AdminTransferResolveRequest):
                    result = resolve_transit(
                        current,
                        transfer_id=transfer_id,
                        user=current_user,
                        command=command,
                        request_id=request_id,
                    )
                elif isinstance(command, AdminTransferReceiveRequest):
                    result = service.receive_transfer(
                        current,
                        current_user=current_user,
                        transfer_id=transfer_id,
                        command=command,
                        request_id=request_id,
                    )
                else:
                    result = service.cancel_transfer(
                        current,
                        current_user=current_user,
                        transfer_id=transfer_id,
                        command=command,
                        request_id=request_id,
                    )
            return CommandResult(
                201 if command_code == "create" else 200,
                result,
                resource_type="transfer",
                resource_id=str(result.id),
            )

        payload = (
            command.model_dump(exclude_unset=True)
            if isinstance(command, AdminTransferUpdateRequest)
            else command
        )
        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=f"transfer.{command_code}",
            payload={"transfer_id": transfer_id, "command": payload},
            resolve_context=context,
            authorize=lambda current, saved: _authorize(current, current_user, saved, command_code),
            action=action,
            response_policy=TRANSFER_RESPONSE_POLICY,
            request_id=request_id,
        )

    def recover_pos(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: PosTransferCommandCode,
        key: UUID,
        workstation_code: str,
        cash_session_id: UUID,
    ) -> IdempotencyResult:
        def context(current: Session, saved: CommandContext | None) -> CommandContext:
            base = resolve_cash_command_context(
                current,
                current_user=current_user,
                workstation_code=workstation_code,
                cash_session_id=cash_session_id,
            )
            return CommandContext(
                actor_user_id=base.actor_user_id,
                surface="POS",
                branch_id=base.branch_id,
                workstation_id=base.workstation_id,
                cash_session_id=cash_session_id,
                related_branch_ids=saved.related_branch_ids if saved else (),
            )

        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=f"transfer.{command_code}",
            resolve_context=context,
            authorize=lambda current, saved: _authorize(current, current_user, saved, command_code),
            response_policy=TRANSFER_RESPONSE_POLICY,
        )

    def recover_admin(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command_code: TransferCommandCode,
        key: UUID,
        branch_id: UUID,
    ) -> IdempotencyResult:
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=f"transfer.{command_code}",
            resolve_context=lambda current, saved: CommandContext(
                actor_user_id=current_user.id,
                surface="BACKOFFICE",
                branch_id=branch_id,
                related_branch_ids=saved.related_branch_ids if saved else (),
            ),
            authorize=lambda current, saved: _authorize(current, current_user, saved, command_code),
            response_policy=TRANSFER_RESPONSE_POLICY,
        )
