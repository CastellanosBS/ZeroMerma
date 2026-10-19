"""Opaque operation identity, independent of authentication and authorization decisions."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4


class SourceApp(StrEnum):
    API = "API"
    POS = "POS"
    BACKOFFICE = "BACKOFFICE"
    SYSTEM = "SYSTEM"
    WORKER = "WORKER"


def normalize_request_id(value: str | None) -> str:
    """Never retain arbitrary client text in the trace envelope."""
    if value is not None and len(value) == 36:
        try:
            parsed = UUID(value)
            if parsed.int and str(parsed) == value.lower():
                return str(parsed)
        except ValueError:
            pass
    return str(uuid4())


@dataclass(frozen=True, slots=True)
class OperationContext:
    source_app: SourceApp
    operation_id: UUID
    correlation_id: UUID
    request_id: str | None = None
    causation_id: UUID | None = None
    actor_id: UUID | None = None
    branch_id: UUID | None = None
    workstation_id: UUID | None = None
    cash_session_id: UUID | None = None
    related_branch_ids: tuple[UUID, ...] = ()
    idempotency_key: UUID | None = None
    operation_code: str | None = None

    @classmethod
    def start(cls, source_app: SourceApp, *, request_id: str | None = None) -> OperationContext:
        identity = uuid4()
        return cls(
            source_app=source_app,
            operation_id=identity,
            correlation_id=identity,
            request_id=request_id,
        )

    @property
    def actor_type(self) -> str:
        if self.actor_id is not None:
            return "USER"
        return "SYSTEM" if self.source_app in {SourceApp.SYSTEM, SourceApp.WORKER} else "ANONYMOUS"

    def log_fields(self) -> dict[str, str | list[str] | None]:
        """An allowlist of identifiers, never business payloads or request headers."""
        return {
            "source_app": self.source_app.value,
            "operation_id": str(self.operation_id),
            "correlation_id": str(self.correlation_id),
            "causation_id": str(self.causation_id) if self.causation_id else None,
            "request_id": self.request_id,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "actor_type": self.actor_type,
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "workstation_id": str(self.workstation_id) if self.workstation_id else None,
            "cash_session_id": str(self.cash_session_id) if self.cash_session_id else None,
            "related_branch_ids": [str(value) for value in self.related_branch_ids],
            "idempotency_key": str(self.idempotency_key) if self.idempotency_key else None,
            "operation_code": self.operation_code,
        }


@dataclass(slots=True)
class RequestOperation:
    """One request-local carrier shared with FastAPI's synchronous dependency threads.

    Only the immutable snapshot is replaced. Each ASGI request owns a separate carrier;
    copying a ContextVar into a worker thread cannot publish state to another request.
    """

    context: OperationContext


request_operation: ContextVar[RequestOperation | None] = ContextVar(
    "zeromerma_request_operation", default=None
)


def current_operation_context() -> OperationContext | None:
    carrier = request_operation.get()
    return carrier.context if carrier is not None else None


def publish_operation_context(context: OperationContext) -> None:
    carrier = request_operation.get()
    if carrier is not None:
        carrier.context = context
