"""Audit a physical print intention independently of its immutable economic source."""

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.cash.application.command_context import (
    authorize_cash_command,
    resolve_cash_command_context,
)
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyError
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, CapabilityCode
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.tickets.application.receipt_schemas import OperationalReceiptView
from zeromerma_api.modules.tickets.application.receipts import read_receipt

ReceiptKind = Literal["SALE", "ORDER_PAYMENT", "RETURN"]
CAPABILITIES: dict[ReceiptKind, CapabilityCode] = {
    "SALE": "pos.operate",
    "ORDER_PAYMENT": "orders.manage",
    "RETURN": "returns_corrections.manage",
}


class ReceiptPrintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workstation_code: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=3, max_length=240)


class ReceiptPrintCommand(ReceiptPrintRequest):
    source_kind: ReceiptKind
    source_id: UUID


class ReceiptPrintAcknowledgement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    receipt: OperationalReceiptView
    print_command_id: UUID
    physical_outcome: Literal["NOT_CONFIRMED"] = "NOT_CONFIRMED"


def request_receipt_print(
    session: Session,
    *,
    current_user: AuthenticatedUser,
    command: ReceiptPrintCommand,
    key: UUID,
    request_id: str | None,
) -> IdempotencyResult:
    def resolve(current: Session, saved: CommandContext | None) -> CommandContext:
        return resolve_cash_command_context(
            current,
            current_user=current_user,
            workstation_code=command.workstation_code,
            cash_session_id=None,
        )

    def authorize(current: Session, context: CommandContext) -> None:
        authorize_cash_command(current, current_user, context, CAPABILITIES[command.source_kind])
        receipt = read_receipt(current, command.source_kind, command.source_id)
        if receipt is None or receipt.context.branch_id != context.branch_id:
            raise IdempotencyError(
                "RECEIPT_NOT_FOUND", 404, "The receipt was not found in this branch."
            )

    def action(current: Session) -> CommandResult:
        context = resolve(current, None)
        receipt = read_receipt(current, command.source_kind, command.source_id)
        assert receipt is not None
        command_id = uuid4()
        metadata = {
            "source_kind": command.source_kind,
            "source_id": str(command.source_id),
            "print_command_id": str(command_id),
            "physical_outcome": "NOT_CONFIRMED",
            "reason": command.reason,
        }
        AuditRecorder().record(
            current,
            actor_id=current_user.id,
            branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            request_id=request_id,
            action="receipt.print_requested",
            resource_type="receipt",
            resource_id=str(command.source_id),
            metadata=metadata,
        )
        OutboxWriter().append(
            current,
            aggregate_type="receipt",
            aggregate_id=str(command.source_id),
            event_name="receipt.print_requested.v1",
            actor_id=current_user.id,
            branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            payload={key: value for key, value in metadata.items() if key != "reason"},
        )
        return CommandResult(
            200,
            ReceiptPrintAcknowledgement(receipt=receipt, print_command_id=command_id),
            "receipt",
            str(command.source_id),
        )

    return IdempotencyExecutor().execute(
        session,
        key=key,
        operation_code="receipt.print_request",
        payload=command,
        resolve_context=resolve,
        authorize=authorize,
        action=action,
        response_policy=ResponsePolicy(ReceiptPrintAcknowledgement),
        request_id=request_id,
    )


def recover_receipt_print(
    session: Session,
    *,
    current_user: AuthenticatedUser,
    source_kind: ReceiptKind,
    source_id: UUID,
    workstation_code: str,
    key: UUID,
) -> IdempotencyResult:
    def resolve(current: Session, saved: CommandContext | None) -> CommandContext:
        return resolve_cash_command_context(
            current,
            current_user=current_user,
            workstation_code=workstation_code,
            cash_session_id=None,
        )

    def authorize(current: Session, context: CommandContext) -> None:
        authorize_cash_command(current, current_user, context, CAPABILITIES[source_kind])
        receipt = read_receipt(current, source_kind, source_id)
        if receipt is None or receipt.context.branch_id != context.branch_id:
            raise IdempotencyError(
                "RECEIPT_NOT_FOUND", 404, "The receipt was not found in this branch."
            )

    result = IdempotencyExecutor().recover(
        session,
        key=key,
        operation_code="receipt.print_request",
        resolve_context=resolve,
        authorize=authorize,
        response_policy=ResponsePolicy(ReceiptPrintAcknowledgement),
    )
    if result.status_code == 200:
        document = ReceiptPrintAcknowledgement.model_validate(result.payload).receipt
        if document.source_kind != source_kind or document.source_id != source_id:
            raise IdempotencyError(
                "IDEMPOTENCY_KEY_REUSED", 409, "This print request belongs to another receipt."
            )
    return result
