"""Authorize device intentions after business commit; adapters never decide economics."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.cash.application.command_context import (
    authorize_cash_command,
    resolve_cash_command_context,
)
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.hardware.application.schemas import (
    HardwareBindingView,
    HardwareBootstrapView,
    HardwareCommandAcknowledgement,
    HardwareCommandRequest,
)
from zeromerma_api.modules.hardware.domain.commands import DeviceCommand, sign_device_command
from zeromerma_api.modules.hardware.infrastructure.models import (
    HardwareCommandIntent,
    HardwareDeviceBinding,
)
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyError
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, CapabilityCode
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.tickets.application.print_requests import CAPABILITIES
from zeromerma_api.modules.tickets.application.receipts import read_receipt


@dataclass(frozen=True)
class VerifiedHardwareRegistration:
    adapter_code: str
    adapter_version: str
    certification_evidence_id: UUID
    environment: str
    origin: str
    pairing_key: bytes = field(repr=False)


class HardwareService:
    def __init__(
        self, registrations: Mapping[UUID, VerifiedHardwareRegistration] | None = None
    ) -> None:
        # No runtime test driver or guessed device protocol. A certified installation
        # must register its private pairing material and exact binding evidence.
        self._registrations = dict(registrations or {})

    def _registration(self, binding: HardwareDeviceBinding) -> VerifiedHardwareRegistration:
        record = self._registrations.get(binding.id)
        if (
            record is None
            or not binding.is_active
            or (
                record.adapter_code,
                record.adapter_version,
                record.certification_evidence_id,
                record.environment,
                record.origin,
            )
            != (
                binding.adapter_code,
                binding.adapter_version,
                binding.certification_evidence_id,
                binding.environment,
                binding.origin,
            )
            or not binding.certification_evidence_id.int
            or len(record.pairing_key) < 32
        ):
            raise IdempotencyError(
                "HARDWARE_GATE_CLOSED", 503, "No verified device registration is available."
            )
        return record

    def bootstrap(
        self, session: Session, user: AuthenticatedUser, workstation_code: str
    ) -> HardwareBootstrapView:
        context = resolve_cash_command_context(
            session, current_user=user, workstation_code=workstation_code, cash_session_id=None
        )
        authorize_cash_command(session, user, context, "pos.operate")
        bindings = session.scalars(
            select(HardwareDeviceBinding).where(
                HardwareDeviceBinding.workstation_id == context.workstation_id,
                HardwareDeviceBinding.branch_id == context.branch_id,
            )
        )
        devices = []
        for binding in bindings:
            try:
                self._registration(binding)
                enabled = True
            except IdempotencyError:
                enabled = False
            devices.append(
                HardwareBindingView.model_validate(
                    {
                        "id": binding.id,
                        "kind": binding.kind,
                        "enabled": enabled,
                        "support_status": "REGISTERED" if enabled else "PENDING_VALIDATION",
                    }
                )
            )
        assert context.workstation_id is not None and context.branch_id is not None
        return HardwareBootstrapView(
            workstation_id=context.workstation_id,
            branch_id=context.branch_id,
            devices=devices,
            blockers=[]
            if any(item.enabled for item in devices)
            else ["CERTIFIED_DEVICE_AND_PAIRING_REQUIRED"],
        )

    def _capability(self, session: Session, command: HardwareCommandRequest) -> CapabilityCode:
        if command.kind == "PRINT":
            assert command.receipt_source_kind is not None
            return CAPABILITIES[command.receipt_source_kind]
        parent = session.scalar(
            select(FinancialOperation)
            .join(
                FinancialEntry,
                FinancialEntry.financial_operation_id == FinancialOperation.id,
            )
            .where(FinancialEntry.id == command.cash_entry_id)
        )
        if parent is None:
            raise IdempotencyError("HARDWARE_CAUSE_NOT_FOUND", 404, "The cash cause was not found.")
        if parent.kind in {"SALE_REFUND", "REFUND_SETTLEMENT"}:
            return "returns_corrections.manage"
        if parent.kind in {"ORDER_ADVANCE", "ORDER_SETTLEMENT"}:
            return "orders.manage"
        if parent.kind == "ORDER_REFUND":
            return "orders.cancel"
        if parent.kind not in {
            "SALE_COLLECTION",
            "OPERATIONAL_PAYMENT",
            "OPERATIONAL_CHARGE",
            "CASH_OPENING",
        }:
            raise IdempotencyError(
                "HARDWARE_CAUSE_UNSUPPORTED", 409, "This cash cause cannot open the drawer."
            )
        return "pos.operate"

    def admit(
        self,
        session: Session,
        *,
        user: AuthenticatedUser,
        command: HardwareCommandRequest,
        key: UUID,
        request_id: str | None,
    ) -> IdempotencyResult:
        capability = self._capability(session, command)
        bind_authorization_scope(
            session, user=user, capabilities=(capability,), mutation=True, surface="POS"
        )

        def resolve(current: Session, saved: CommandContext | None) -> CommandContext:
            return resolve_cash_command_context(
                current,
                current_user=user,
                workstation_code=command.workstation_code,
                cash_session_id=None,
            )

        def authorize(current: Session, context: CommandContext) -> None:
            authorize_cash_command(current, user, context, capability)

        def action(current: Session) -> CommandResult:
            context = resolve(current, None)
            binding = current.scalar(
                select(HardwareDeviceBinding)
                .where(
                    HardwareDeviceBinding.id == command.binding_id,
                    HardwareDeviceBinding.branch_id == context.branch_id,
                    HardwareDeviceBinding.workstation_id == context.workstation_id,
                )
                .with_for_update(read=True)
            )
            if binding is None or binding.kind != (
                "PRINTER" if command.kind == "PRINT" else "DRAWER"
            ):
                raise IdempotencyError(
                    "HARDWARE_BINDING_INVALID", 409, "The device belongs to another context."
                )
            registration = self._registration(binding)
            receipt = None
            if command.kind == "PRINT":
                assert (
                    command.receipt_source_kind is not None
                    and command.receipt_source_id is not None
                )
                receipt = read_receipt(
                    current, command.receipt_source_kind, command.receipt_source_id
                )
                if receipt is None or receipt.context.branch_id != context.branch_id:
                    raise IdempotencyError(
                        "RECEIPT_NOT_FOUND", 404, "The immutable receipt was not found."
                    )
            else:
                entry = current.scalar(
                    select(FinancialEntry)
                    .where(
                        FinancialEntry.id == command.cash_entry_id,
                    )
                    .with_for_update(key_share=True)
                )
                if (
                    entry is None
                    or entry.payment_method_code != "CASH"
                    or entry.state != "CONFIRMED"
                    or entry.amount <= 0
                    or (
                        entry.branch_id,
                        entry.workstation_id,
                        entry.actor_id,
                    )
                    != (context.branch_id, context.workstation_id, user.id)
                ):
                    raise IdempotencyError(
                        "HARDWARE_CASH_CAUSE_INVALID",
                        409,
                        "An owned confirmed cash effect is required.",
                    )
                existing = current.scalar(
                    select(HardwareCommandIntent).where(
                        HardwareCommandIntent.cash_entry_id == command.cash_entry_id,
                    )
                )
                if existing is not None:
                    if existing.binding_id != binding.id:
                        raise IdempotencyError(
                            "HARDWARE_CASH_ALREADY_ASSIGNED",
                            409,
                            "The cash cause already has its device intention.",
                        )
                    value = DeviceCommand.model_validate(existing.command)
                    return CommandResult(
                        200,
                        HardwareCommandAcknowledgement(
                            command_id=existing.id,
                            grant=sign_device_command(value, registration.pairing_key),
                        ),
                        "hardware_command",
                        str(existing.id),
                    )
            value = DeviceCommand.model_validate(
                {
                    "id": uuid4(),
                    "kind": command.kind,
                    "branch_id": context.branch_id,
                    "workstation_id": context.workstation_id,
                    "device_id": binding.id,
                    "binding_version": binding.version,
                    "environment": binding.environment,
                    "origin": binding.origin,
                    "receipt": receipt,
                    "cash_entry_id": command.cash_entry_id,
                }
            )
            current.add(
                HardwareCommandIntent(
                    id=value.id,
                    branch_id=value.branch_id,
                    workstation_id=value.workstation_id,
                    actor_id=user.id,
                    binding_id=binding.id,
                    cash_entry_id=command.cash_entry_id,
                    command=value.model_dump(mode="json"),
                )
            )
            metadata = {
                "command_id": str(value.id),
                "kind": value.kind,
                "binding_id": str(binding.id),
                "physical_outcome": "NOT_CONFIRMED",
            }
            AuditRecorder().record(
                current,
                actor_id=user.id,
                branch_id=context.branch_id,
                workstation_id=context.workstation_id,
                request_id=request_id,
                action="hardware.command_requested",
                resource_type="hardware_command",
                resource_id=str(value.id),
                metadata=metadata,
            )
            OutboxWriter().append(
                current,
                aggregate_type="hardware_command",
                aggregate_id=str(value.id),
                event_name="hardware.command_requested.v1",
                actor_id=user.id,
                branch_id=context.branch_id,
                workstation_id=context.workstation_id,
                payload=metadata,
            )
            return CommandResult(
                200,
                HardwareCommandAcknowledgement(
                    command_id=value.id,
                    grant=sign_device_command(value, registration.pairing_key),
                ),
                "hardware_command",
                str(value.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code="hardware.command_request",
            payload=command,
            resolve_context=resolve,
            authorize=authorize,
            action=action,
            response_policy=ResponsePolicy(HardwareCommandAcknowledgement),
            request_id=request_id,
        )

    def recover(
        self, session: Session, *, user: AuthenticatedUser, key: UUID, workstation_code: str
    ) -> IdempotencyResult:
        def resolve(current: Session, saved: CommandContext | None) -> CommandContext:
            return resolve_cash_command_context(
                current, current_user=user, workstation_code=workstation_code, cash_session_id=None
            )

        def authorize(current: Session, context: CommandContext) -> None:
            authorize_cash_command(current, user, context, "pos.operate")
            record = current.scalar(
                select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == key)
            )
            if record is not None and record.resource_id is not None:
                self.renew_authorization(
                    current,
                    user=user,
                    command_id=UUID(record.resource_id),
                    workstation_code=workstation_code,
                )

        result = IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code="hardware.command_request",
            resolve_context=resolve,
            authorize=authorize,
            response_policy=ResponsePolicy(HardwareCommandAcknowledgement),
        )
        if result.status_code == 200:
            original = HardwareCommandAcknowledgement.model_validate(result.payload)
            renewed = self.renew_authorization(
                session,
                user=user,
                command_id=original.command_id,
                workstation_code=workstation_code,
            )
            return replace(result, payload=renewed.model_dump(mode="json"))
        return result

    def renew_authorization(
        self,
        session: Session,
        *,
        user: AuthenticatedUser,
        command_id: UUID,
        workstation_code: str,
    ) -> HardwareCommandAcknowledgement:
        context = resolve_cash_command_context(
            session, current_user=user, workstation_code=workstation_code, cash_session_id=None
        )
        record = session.get(HardwareCommandIntent, command_id)
        if record is None or (record.actor_id, record.branch_id, record.workstation_id) != (
            user.id,
            context.branch_id,
            context.workstation_id,
        ):
            raise IdempotencyError(
                "HARDWARE_COMMAND_NOT_FOUND", 404, "The local command was not found."
            )
        value = DeviceCommand.model_validate(record.command)
        request = HardwareCommandRequest(
            workstation_code=workstation_code,
            binding_id=record.binding_id,
            kind=value.kind,
            cash_entry_id=value.cash_entry_id,
            receipt_source_kind=value.receipt.source_kind if value.receipt is not None else None,
            receipt_source_id=value.receipt.source_id if value.receipt is not None else None,
        )
        authorize_cash_command(session, user, context, self._capability(session, request))
        binding = session.get(HardwareDeviceBinding, record.binding_id)
        if (
            binding is None
            or binding.version != value.binding_version
            or (
                binding.branch_id,
                binding.workstation_id,
                binding.environment,
                binding.origin,
            )
            != (value.branch_id, value.workstation_id, value.environment, value.origin)
        ):
            raise IdempotencyError(
                "HARDWARE_BINDING_CHANGED", 409, "The admitted device binding has changed."
            )
        registration = self._registration(binding)
        return HardwareCommandAcknowledgement(
            command_id=value.id,
            grant=sign_device_command(value, registration.pairing_key),
        )
