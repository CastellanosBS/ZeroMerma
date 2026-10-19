"""Durable admission, external execution without database locks, and evidence application."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import authorization_scope, bind_authorization_scope
from zeromerma_api.db.operation_context import bind_operation_context, get_operation_context
from zeromerma_api.db.transactions import rollback_on_failure
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, CapabilityCode
from zeromerma_api.modules.identity.application.session_services import (
    AUTH_CONTEXT_KEY,
    SessionAuthentication,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.payment_terminal.application.schemas import (
    TerminalBootstrapView,
    TerminalOperationAcknowledgement,
    TerminalOperationRequest,
    TerminalOperationView,
)
from zeromerma_api.modules.payment_terminal.domain.provider import (
    TERMINAL_STATES,
    ExternalPaymentProvider,
    ProviderEvidence,
    ProviderRequest,
    TerminalError,
    next_state,
    opaque_reference,
)
from zeromerma_api.modules.payment_terminal.infrastructure.models import (
    ExternalPaymentEvidence,
    ExternalPaymentOperation,
    PaymentTerminalBinding,
)

_CAPABILITIES: dict[str, CapabilityCode] = {
    "SALE_COLLECTION": "pos.operate",
    "SALE_REFUND": "returns_corrections.manage",
    "ORDER_ADVANCE": "orders.manage",
    "ORDER_SETTLEMENT": "orders.manage",
    "ORDER_REFUND": "orders.cancel",
}


class PaymentTerminalService:
    def __init__(
        self, providers: Mapping[tuple[str, str], ExternalPaymentProvider] | None = None
    ) -> None:
        # There is deliberately no runtime fake, guessed BBVA protocol, or boolean enabling one.
        self._providers = dict(providers or {})
        self._executor = IdempotencyExecutor()

    def bootstrap(self, session: Session, current_user: AuthenticatedUser) -> TerminalBootstrapView:
        if current_user.authorization_surface not in {"POS", "BACKOFFICE"}:
            raise TerminalError(
                "EXTERNAL_PAYMENT_FORBIDDEN", "An explicit audience is required.", 403
            )
        capability: CapabilityCode = (
            "pos.operate" if current_user.authorization_surface == "POS" else "cash_finance.view"
        )
        bind_authorization_scope(
            session,
            user=current_user,
            capabilities=(capability,),
            mutation=False,
            surface=current_user.authorization_surface,
        )
        return TerminalBootstrapView(
            integrated_payments_enabled=False,
            blockers=[
                "BBVA_ADAPTER_NOT_REGISTERED",
                "BBVA_CONTRACT_AND_HARDWARE_EVIDENCE_REQUIRED",
                "BBVA_PCI_GATE_REQUIRED",
            ],
        )

    def _provider(self, code: str, environment: str) -> ExternalPaymentProvider:
        provider = self._providers.get((code, environment))
        if provider is None:
            raise TerminalError(
                "EXTERNAL_PAYMENT_GATE_CLOSED", "No verified provider adapter is registered.", 503
            )
        provider.readiness.validate()
        if (provider.readiness.provider_code, provider.readiness.environment) != (
            code,
            environment,
        ):
            raise TerminalError(
                "EXTERNAL_PAYMENT_GATE_CLOSED", "The provider environment does not match.", 503
            )
        return provider

    def _authorize(
        self, session: Session, user: AuthenticatedUser, entry_id: UUID, *, mutation: bool = True
    ) -> FinancialEntry:
        row = session.execute(
            select(FinancialEntry, FinancialOperation)
            .join(
                FinancialOperation, FinancialOperation.id == FinancialEntry.financial_operation_id
            )
            .where(FinancialEntry.id == entry_id)
            .execution_options(populate_existing=True)
        ).one_or_none()
        if row is None:
            raise TerminalError("EXTERNAL_PAYMENT_NOT_FOUND", "The payment leg was not found.", 404)
        entry, parent = row
        assert isinstance(entry, FinancialEntry)
        capability = _CAPABILITIES.get(parent.kind)
        if capability is None or user.authorization_surface not in {"POS", "BACKOFFICE"}:
            raise TerminalError(
                "EXTERNAL_PAYMENT_FORBIDDEN", "This business effect is not supported.", 403
            )
        current = resolve_authorization(session, user, surface=user.authorization_surface)
        require_branches(current, capability, [entry.branch_id])
        if user.authorization_surface == "POS":
            authentication = session.info.get(AUTH_CONTEXT_KEY)
            if (
                not isinstance(authentication, SessionAuthentication)
                or authentication.record.workstation_id != entry.workstation_id
                or entry.actor_id != user.id
            ):
                raise TerminalError(
                    "EXTERNAL_PAYMENT_FORBIDDEN", "The leg belongs to another POS context.", 403
                )
        # TX1 released its authorization barrier before contacting the provider. Bind
        # a fresh barrier in TX2 as well; a Session's cached scope is not a held lock.
        # An active executor already owns that transaction barrier. Its flushed
        # reservation must stay attached so finalization persists the result.
        if authorization_scope(session) is None or execution(session) is None:
            bind_authorization_scope(
                session,
                user=user,
                capabilities=(capability,),
                mutation=mutation,
                surface=user.authorization_surface,
            )
            scoped_entry = session.get(FinancialEntry, entry_id)
            assert scoped_entry is not None
            return scoped_entry
        return entry

    @staticmethod
    def _lock_session(session: Session, entry: FinancialEntry) -> None:
        cash = session.scalar(
            select(CashSession)
            .where(CashSession.id == entry.cash_session_id)
            .with_for_update(key_share=True)
            .execution_options(populate_existing=True)
        )
        if (
            cash is None
            or cash.branch_id != entry.branch_id
            or cash.workstation_id != entry.workstation_id
            or cash.status != "OPEN"
        ):
            raise TerminalError(
                "CASH_SESSION_CLOSED",
                "External effects cannot post to a closed or mismatched shift.",
            )

    def admit(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: TerminalOperationRequest,
        key: UUID,
    ) -> IdempotencyResult:
        self._authorize(session, current_user, command.financial_entry_id)
        assert current_user.authorization_surface is not None

        def context(current: Session, saved: CommandContext | None) -> CommandContext:
            if saved is not None:
                return saved.model_copy(
                    update={
                        "actor_user_id": current_user.id,
                        "surface": current_user.authorization_surface,
                    }
                )
            entry = self._authorize(current, current_user, command.financial_entry_id)
            assert current_user.authorization_surface is not None
            return CommandContext(
                actor_user_id=current_user.id,
                surface=current_user.authorization_surface,
                branch_id=entry.branch_id,
                workstation_id=entry.workstation_id,
                cash_session_id=entry.cash_session_id,
            )

        def authorize(current: Session, saved: CommandContext) -> None:
            entry = self._authorize(current, current_user, command.financial_entry_id)
            if (entry.branch_id, entry.workstation_id, entry.cash_session_id) != (
                saved.branch_id,
                saved.workstation_id,
                saved.cash_session_id,
            ):
                raise TerminalError(
                    "EXTERNAL_PAYMENT_CONTEXT_CHANGED",
                    "The payment context differs from the admitted intention.",
                )

        def action(current: Session) -> CommandResult:
            entry = current.get(FinancialEntry, command.financial_entry_id)
            assert entry is not None
            self._lock_session(current, entry)
            entry = current.scalar(
                select(FinancialEntry)
                .where(FinancialEntry.id == entry.id)
                .with_for_update(key_share=True)
                .execution_options(populate_existing=True)
            )
            assert entry is not None
            if (
                entry.state != "PENDING"
                or entry.payment_method_code != "CARD"
                or entry.execution_mode != "PROVIDER_INTEGRATED"
            ):
                raise TerminalError(
                    "EXTERNAL_PAYMENT_LEG_INVALID",
                    "Only an unconfirmed integrated CARD leg can be admitted.",
                )
            if current.scalar(
                select(ExternalPaymentOperation.id).where(
                    ExternalPaymentOperation.financial_entry_id == entry.id
                )
            ):
                raise TerminalError(
                    "EXTERNAL_PAYMENT_ALREADY_PENDING",
                    "This leg already has a durable provider intention.",
                )
            binding = current.scalar(
                select(PaymentTerminalBinding)
                .where(PaymentTerminalBinding.id == command.terminal_binding_id)
                .with_for_update(read=True)
            )
            if (
                binding is None
                or not binding.is_active
                or (binding.branch_id, binding.workstation_id)
                != (entry.branch_id, entry.workstation_id)
            ):
                raise TerminalError(
                    "EXTERNAL_PAYMENT_TERMINAL_INVALID",
                    "An active terminal for this station is required.",
                )
            provider = self._provider(binding.provider_code, binding.environment)
            ready = provider.readiness
            if (
                binding.contract_evidence_id,
                binding.hardware_evidence_id,
                binding.certification_evidence_id,
            ) != (
                ready.contract_evidence_id,
                ready.hardware_evidence_id,
                ready.certification_evidence_id,
            ):
                raise TerminalError(
                    "EXTERNAL_PAYMENT_GATE_CLOSED",
                    "Binding approval evidence does not match the registered adapter.",
                )
            opaque_reference(binding.account_reference)
            opaque_reference(binding.terminal_reference)
            operation_type = "REFUND" if entry.direction == "OUT" else "CAPTURE"
            if operation_type == "REFUND":
                self._validate_refund(current, entry, binding, command.original_operation_id)
            elif command.original_operation_id is not None:
                raise TerminalError(
                    "EXTERNAL_PAYMENT_LEG_INVALID", "A capture cannot reference another capture."
                )
            owner = execution(current)
            assert owner is not None and owner.record is not None
            assert entry.workstation_id is not None and entry.cash_session_id is not None
            operation = ExternalPaymentOperation(
                id=uuid4(),
                financial_entry_id=entry.id,
                branch_id=entry.branch_id,
                workstation_id=entry.workstation_id,
                cash_session_id=entry.cash_session_id,
                actor_id=current_user.id,
                terminal_binding_id=binding.id,
                idempotency_record_id=owner.record.id,
                original_operation_id=command.original_operation_id,
                operation_type=operation_type,
                status="CREATED",
                reconciliation_status="PENDING",
                provider_code=binding.provider_code,
                environment=binding.environment,
                account_reference=binding.account_reference,
                terminal_reference=binding.terminal_reference,
                provider_idempotency_key=uuid4(),
                amount=entry.amount,
                currency_code=entry.currency_code,
            )
            current.add(operation)
            current.flush()
            self._event(current, operation, current_user.id, "requested")
            return CommandResult(
                202,
                TerminalOperationAcknowledgement(id=operation.id, financial_entry_id=entry.id),
                "external_payment_operation",
                str(operation.id),
            )

        return self._executor.execute(
            session,
            key=key,
            operation_code="payment_terminal.request",
            payload=command,
            resolve_context=context,
            authorize=authorize,
            action=action,
            response_policy=ResponsePolicy(TerminalOperationAcknowledgement),
        )

    @staticmethod
    def _validate_refund(
        session: Session,
        entry: FinancialEntry,
        binding: PaymentTerminalBinding,
        original_id: UUID | None,
    ) -> None:
        original = session.scalar(
            select(ExternalPaymentOperation)
            .where(ExternalPaymentOperation.id == original_id)
            .with_for_update(key_share=True)
        )
        if (
            original is None
            or original.status != "CAPTURED"
            or (
                original.provider_code,
                original.environment,
                original.account_reference,
                original.branch_id,
                original.currency_code,
            )
            != (
                binding.provider_code,
                binding.environment,
                binding.account_reference,
                entry.branch_id,
                entry.currency_code,
            )
        ):
            raise TerminalError(
                "EXTERNAL_REFUND_ORIGINAL_INVALID",
                "A matching captured provider operation is required.",
            )
        old_entry = session.get(FinancialEntry, original.financial_entry_id)
        assert old_entry is not None
        parent = session.get(FinancialOperation, entry.financial_operation_id)
        old_parent = session.get(FinancialOperation, old_entry.financial_operation_id)
        assert parent is not None and old_parent is not None
        if (parent.subject_type, parent.subject_id) != (
            old_parent.subject_type,
            old_parent.subject_id,
        ):
            raise TerminalError(
                "EXTERNAL_REFUND_ORIGINAL_INVALID",
                "The refund belongs to a different business subject.",
            )
        reserved = session.scalar(
            select(func.coalesce(func.sum(ExternalPaymentOperation.amount), 0)).where(
                ExternalPaymentOperation.original_operation_id == original.id,
                ExternalPaymentOperation.status.not_in(("DECLINED", "FAILED")),
            )
        )
        assert reserved is not None
        if reserved + entry.amount > original.amount:
            raise TerminalError(
                "EXTERNAL_REFUND_EXCEEDS_ELIGIBLE_AMOUNT",
                "The cumulative provider refund exceeds its captured amount.",
            )

    def get(
        self, session: Session, *, current_user: AuthenticatedUser, operation_id: UUID
    ) -> TerminalOperationView:
        operation = session.get(ExternalPaymentOperation, operation_id)
        if operation is None:
            raise TerminalError(
                "EXTERNAL_PAYMENT_NOT_FOUND", "The external operation was not found.", 404
            )
        self._authorize(session, current_user, operation.financial_entry_id, mutation=False)
        operation = session.get(ExternalPaymentOperation, operation_id)
        return TerminalOperationView.model_validate(operation)

    @staticmethod
    def _request(session: Session, operation: ExternalPaymentOperation) -> ProviderRequest:
        original = (
            session.get(ExternalPaymentOperation, operation.original_operation_id)
            if operation.original_operation_id
            else None
        )
        return ProviderRequest(
            operation_id=operation.id,
            provider_idempotency_key=operation.provider_idempotency_key,
            operation_type=operation.operation_type,
            account_reference=operation.account_reference,
            terminal_reference=operation.terminal_reference,
            amount=operation.amount,
            currency_code=operation.currency_code,
            original_provider_operation_id=original.provider_operation_id if original else None,
        )

    @rollback_on_failure
    def dispatch(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        operation_id: UUID,
        reconcile_only: bool = False,
    ) -> TerminalOperationView:
        operation = session.get(ExternalPaymentOperation, operation_id)
        if operation is None:
            raise TerminalError(
                "EXTERNAL_PAYMENT_NOT_FOUND", "The external operation was not found.", 404
            )
        entry = self._authorize(session, current_user, operation.financial_entry_id)
        self._lock_session(session, entry)
        operation = session.scalar(
            select(ExternalPaymentOperation)
            .where(ExternalPaymentOperation.id == operation_id)
            .with_for_update(key_share=True)
            .execution_options(populate_existing=True)
        )
        assert operation is not None
        if operation.status in TERMINAL_STATES:
            view = TerminalOperationView.model_validate(operation)
            session.commit()
            return view
        provider = self._provider(operation.provider_code, operation.environment)
        request = self._request(session, operation)
        send = operation.status == "CREATED" and not reconcile_only
        if send:
            binding = session.scalar(
                select(PaymentTerminalBinding)
                .where(PaymentTerminalBinding.id == operation.terminal_binding_id)
                .with_for_update(read=True)
                .execution_options(populate_existing=True)
            )
            if (
                binding is None
                or not binding.is_active
                or (
                    binding.branch_id,
                    binding.workstation_id,
                    binding.provider_code,
                    binding.environment,
                    binding.account_reference,
                    binding.terminal_reference,
                )
                != (
                    operation.branch_id,
                    operation.workstation_id,
                    operation.provider_code,
                    operation.environment,
                    operation.account_reference,
                    operation.terminal_reference,
                )
            ):
                raise TerminalError(
                    "EXTERNAL_PAYMENT_TERMINAL_INVALID",
                    "The admitted terminal must still be active before the first send.",
                )
            readiness = provider.readiness
            if (
                binding.contract_evidence_id,
                binding.hardware_evidence_id,
                binding.certification_evidence_id,
            ) != (
                readiness.contract_evidence_id,
                readiness.hardware_evidence_id,
                readiness.certification_evidence_id,
            ):
                raise TerminalError(
                    "EXTERNAL_PAYMENT_GATE_CLOSED",
                    "The registered adapter no longer matches the admitted approval evidence.",
                )
            operation.status = "PROCESSING"
            operation.updated_at = datetime.now(UTC)
            entry.state = "PROCESSING"
            self._event(
                session, operation, current_user.id, "processing", previous_status="CREATED"
            )
        session.commit()
        # No lazy ORM access or SQL between this commit and the external call.
        assert not session.in_transaction()
        try:
            evidence = provider.execute(request) if send else provider.query(request)
        except Exception:
            # Never serialize the exception or guess that a network failure means rejection.
            return self._mark_unknown(session, current_user=current_user, operation_id=operation_id)
        return self.apply_evidence(
            session, current_user=current_user, operation_id=operation_id, evidence=evidence
        )

    @rollback_on_failure
    def _mark_unknown(
        self, session: Session, *, current_user: AuthenticatedUser, operation_id: UUID
    ) -> TerminalOperationView:
        operation, entry = self._lock_result(session, current_user, operation_id)
        if operation.status not in TERMINAL_STATES:
            previous_status = operation.status
            operation.status = "UNKNOWN"
            operation.updated_at = datetime.now(UTC)
            entry.state = "UNKNOWN"
            self._event(
                session, operation, current_user.id, "unknown", previous_status=previous_status
            )
        view = TerminalOperationView.model_validate(operation)
        session.commit()
        return view

    def _lock_result(
        self, session: Session, user: AuthenticatedUser, operation_id: UUID
    ) -> tuple[ExternalPaymentOperation, FinancialEntry]:
        operation = session.get(ExternalPaymentOperation, operation_id)
        if operation is None:
            raise TerminalError(
                "EXTERNAL_PAYMENT_NOT_FOUND", "The external operation was not found.", 404
            )
        entry = self._authorize(session, user, operation.financial_entry_id)
        self._lock_session(session, entry)
        operation = session.scalar(
            select(ExternalPaymentOperation)
            .where(ExternalPaymentOperation.id == operation_id)
            .with_for_update(key_share=True)
            .execution_options(populate_existing=True)
        )
        assert operation is not None
        locked_entry = session.scalar(
            select(FinancialEntry)
            .where(FinancialEntry.id == operation.financial_entry_id)
            .with_for_update(key_share=True)
            .execution_options(populate_existing=True)
        )
        assert locked_entry is not None
        return operation, locked_entry

    @rollback_on_failure
    def apply_evidence(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        operation_id: UUID,
        evidence: ProviderEvidence,
    ) -> TerminalOperationView:
        """Internal adapter-only boundary; no HTTP DTO accepts provider success declarations."""
        operation, entry = self._lock_result(session, current_user, operation_id)
        request = self._request(session, operation)
        evidence.validate_for(request)
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "key": str(evidence.provider_idempotency_key),
                    "state": evidence.state.value,
                    "amount": format(evidence.amount, ".2f"),
                    "currency": evidence.currency_code,
                    "account": evidence.account_reference,
                    "terminal": evidence.terminal_reference,
                    "reference": evidence.provider_operation_id,
                    "occurred_at": evidence.occurred_at.astimezone(UTC).isoformat(),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        previous = session.scalar(
            select(ExternalPaymentEvidence).where(
                ExternalPaymentEvidence.provider_code == operation.provider_code,
                ExternalPaymentEvidence.environment == operation.environment,
                ExternalPaymentEvidence.account_reference == operation.account_reference,
                ExternalPaymentEvidence.event_id == evidence.event_id,
            )
        )
        if previous is not None:
            if (
                previous.external_operation_id != operation.id
                or previous.fingerprint != fingerprint
            ):
                raise TerminalError(
                    "EXTERNAL_RECONCILIATION_DISCREPANCY",
                    "A provider event identity was reused with different evidence.",
                )
            view = TerminalOperationView.model_validate(operation)
            session.commit()
            return view
        previous_status = operation.status
        conflicting_state = False
        try:
            status = next_state(operation.status, evidence.state)
        except TerminalError:
            status = operation.status
            conflicting_state = True
        if operation.provider_operation_id is not None and evidence.provider_operation_id not in {
            None,
            operation.provider_operation_id,
        }:
            raise TerminalError(
                "EXTERNAL_RECONCILIATION_DISCREPANCY", "The provider operation identity changed."
            )
        proof = ExternalPaymentEvidence(
            id=uuid4(),
            external_operation_id=operation.id,
            branch_id=operation.branch_id,
            provider_code=operation.provider_code,
            environment=operation.environment,
            account_reference=operation.account_reference,
            event_id=evidence.event_id,
            state=evidence.state.value,
            fingerprint=fingerprint,
            occurred_at=evidence.occurred_at,
        )
        session.add(proof)
        if conflicting_state:
            operation.reconciliation_status = "DISCREPANCY"
            operation.updated_at = datetime.now(UTC)
            self._event(
                session,
                operation,
                current_user.id,
                "discrepancy_detected",
                previous_status=previous_status,
            )
            session.flush()
            view = TerminalOperationView.model_validate(operation)
            session.commit()
            return view
        operation.status = status
        operation.provider_operation_id = (
            evidence.provider_operation_id or operation.provider_operation_id
        )
        operation.updated_at = datetime.now(UTC)
        if entry.state not in {"CONFIRMED", "REJECTED", "CANCELLED"}:
            if status in {"CAPTURED", "REFUNDED"}:
                entry.state = "CONFIRMED"
                entry.confirmed_at = evidence.occurred_at
                entry.resolution_kind = (
                    "PROVIDER_REFUND" if status == "REFUNDED" else "PROVIDER_CAPTURE"
                )
                entry.resolution_reference = proof.id
                operation.reconciliation_status = "MATCHED"
            elif status in {"DECLINED", "FAILED"}:
                entry.state = "REJECTED"
                entry.resolution_kind = "PROVIDER_REJECTION"
                entry.resolution_reference = proof.id
                operation.reconciliation_status = "MATCHED"
            else:
                entry.state = "UNKNOWN" if status == "UNKNOWN" else "PROCESSING"
        self._event(
            session,
            operation,
            current_user.id,
            "evidence_recorded",
            previous_status=previous_status,
        )
        session.flush()
        view = TerminalOperationView.model_validate(operation)
        session.commit()
        return view

    @rollback_on_failure
    def callback(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        operation_id: UUID,
        body: bytes,
        signature: str,
    ) -> TerminalOperationView:
        """A concrete adapter must authenticate callbacks; raw data is never persisted."""
        operation = session.get(ExternalPaymentOperation, operation_id)
        if operation is None:
            raise TerminalError(
                "EXTERNAL_PAYMENT_NOT_FOUND", "The external operation was not found.", 404
            )
        self._authorize(session, current_user, operation.financial_entry_id)
        provider = self._provider(operation.provider_code, operation.environment)
        session.commit()
        if len(body) > 65536:
            raise TerminalError(
                "EXTERNAL_PAYMENT_EVIDENCE_INVALID", "Provider callback is too large.", 413
            )
        try:
            evidence = provider.authenticate_callback(body, signature)
        except Exception:
            raise TerminalError(
                "EXTERNAL_PAYMENT_EVIDENCE_INVALID", "Provider callback authentication failed.", 403
            ) from None
        return self.apply_evidence(
            session, current_user=current_user, operation_id=operation_id, evidence=evidence
        )

    @staticmethod
    def _event(
        session: Session,
        operation: ExternalPaymentOperation,
        actor_id: UUID,
        suffix: str,
        *,
        previous_status: str | None = None,
    ) -> None:
        current_context = get_operation_context(session)
        context = replace(
            current_context,
            correlation_id=operation.idempotency_record_id,
            causation_id=(
                operation.idempotency_record_id
                if current_context.operation_id != operation.idempotency_record_id
                else None
            ),
            operation_code=f"payment_terminal.{suffix}",
            actor_id=actor_id,
            branch_id=operation.branch_id,
            workstation_id=operation.workstation_id,
            cash_session_id=operation.cash_session_id,
        )
        bind_operation_context(session, context)
        metadata = {
            "external_operation_id": str(operation.id),
            "financial_entry_id": str(operation.financial_entry_id),
            "status": operation.status,
            "previous_status": previous_status,
            "amount": format(operation.amount, ".2f"),
            "currency_code": operation.currency_code,
            "provider_code": operation.provider_code,
            "environment": operation.environment,
            "terminal_binding_id": str(operation.terminal_binding_id),
        }
        AuditRecorder().record(
            session,
            actor_id=actor_id,
            action=f"payment_terminal.{suffix}",
            resource_type="external_payment_operation",
            resource_id=str(operation.id),
            branch_id=operation.branch_id,
            request_id=context.request_id,
            metadata=metadata,
        )
        OutboxWriter().append(
            session,
            aggregate_type="external_payment_operation",
            aggregate_id=str(operation.id),
            event_name=f"payment_terminal.{suffix}.v1",
            payload=metadata,
        )
