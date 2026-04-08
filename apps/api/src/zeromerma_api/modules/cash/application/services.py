from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.application.access import WorkstationAccessService
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.application.schemas import CashSessionView, OpenCashSessionRequest
from zeromerma_api.modules.cash.domain.constants import (
    CASH_SESSION_STATUS_OPEN,
    OUTBOX_EVENT_CASH_SESSION_OPENED_V1,
)
from zeromerma_api.modules.cash.domain.exceptions import CashSessionConflictError
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.application.service import OutboxWriter


class CashSessionQueryService:
    def get_open_session_for_workstation_code(
        self,
        session: Session,
        *,
        workstation_code: str,
    ) -> CashSessionView | None:
        result = session.execute(
            self._base_query().where(
                Workstation.code == workstation_code,
                CashSession.status == CASH_SESSION_STATUS_OPEN,
            )
        ).mappings().one_or_none()
        if result is None:
            return None
        return self._to_view(result)

    def get_session_by_id(self, session: Session, *, cash_session_id: uuid.UUID) -> CashSessionView:
        result = session.execute(
            self._base_query().where(CashSession.id == cash_session_id)
        ).mappings().one()
        return self._to_view(result)

    @staticmethod
    def _base_query() -> Select[tuple[object, ...]]:
        return (
            select(
                CashSession.id,
                CashSession.status,
                CashSession.opening_amount,
                CashSession.opened_at,
                Branch.id.label("branch_id"),
                Branch.code.label("branch_code"),
                Branch.name.label("branch_name"),
                Workstation.id.label("workstation_id"),
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                User.id.label("user_id"),
                User.email.label("user_email"),
                User.full_name.label("user_full_name"),
            )
            .select_from(CashSession)
            .join(Workstation, Workstation.id == CashSession.workstation_id)
            .join(Branch, Branch.id == CashSession.branch_id)
            .join(User, User.id == CashSession.user_id)
        )

    @staticmethod
    def _to_view(record: RowMapping | Mapping[str, Any]) -> CashSessionView:
        return CashSessionView(
            id=record["id"],
            status=record["status"],
            opening_amount=record["opening_amount"],
            opened_at=record["opened_at"],
            branch_id=record["branch_id"],
            branch_code=record["branch_code"],
            branch_name=record["branch_name"],
            workstation_id=record["workstation_id"],
            workstation_code=record["workstation_code"],
            workstation_name=record["workstation_name"],
            user_id=record["user_id"],
            user_email=record["user_email"],
            user_full_name=record["user_full_name"],
        )


class CashSessionCommandService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        query_service: CashSessionQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._query_service = query_service or CashSessionQueryService()

    def open_session(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: OpenCashSessionRequest,
        request_id: str | None,
    ) -> CashSessionView:
        if command.opening_amount < Decimal("0.00"):
            raise CashSessionConflictError("Opening amount must be non-negative.")

        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=command.workstation_code,
        )

        workstation_open_session = session.execute(
            select(CashSession.id).where(
                CashSession.workstation_id == context.workstation_id,
                CashSession.status == CASH_SESSION_STATUS_OPEN,
            )
        ).scalar_one_or_none()
        if workstation_open_session is not None:
            raise CashSessionConflictError(
                f"Workstation {command.workstation_code} already has an open cash session."
            )

        user_open_session = session.execute(
            select(CashSession.id).where(
                CashSession.user_id == current_user.id,
                CashSession.status == CASH_SESSION_STATUS_OPEN,
            )
        ).scalar_one_or_none()
        if user_open_session is not None:
            raise CashSessionConflictError("User already has an open cash session.")

        opened_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        cash_session = CashSession(
            branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            user_id=current_user.id,
            status=CASH_SESSION_STATUS_OPEN,
            opening_amount=command.opening_amount,
            opened_at=opened_at,
        )

        try:
            session.add(cash_session)
            session.flush()

            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action="cash_session.opened",
                resource_type="cash_session",
                resource_id=str(cash_session.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "branch_code": context.branch_code,
                    "workstation_code": context.workstation_code,
                    "opening_amount": str(command.opening_amount),
                    "user_email": current_user.email,
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type="cash_session",
                aggregate_id=str(cash_session.id),
                event_name=OUTBOX_EVENT_CASH_SESSION_OPENED_V1,
                payload={
                    "cash_session_id": str(cash_session.id),
                    "branch_id": str(context.branch_id),
                    "branch_code": context.branch_code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "user_id": str(current_user.id),
                    "user_email": current_user.email,
                    "opening_amount": str(command.opening_amount),
                    "opened_at": opened_at.isoformat(),
                },
                headers={"request_id": resolved_request_id},
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise CashSessionConflictError(
                "Open cash session invariants were violated by a concurrent request."
            ) from error

        return self._query_service.get_session_by_id(session, cash_session_id=cash_session.id)
