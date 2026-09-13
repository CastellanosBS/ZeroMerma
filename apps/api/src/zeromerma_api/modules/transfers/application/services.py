from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.application.access import WorkstationAccessService
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.application.services import CashSessionQueryService
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.application.schemas import (
    OperationCommitLineRequest,
    OperationDocumentView,
    OperationHistoryFilterOptionView,
    OperationHistoryListItemView,
    OperationHistoryScopeView,
)
from zeromerma_api.modules.operations.application.services import (
    OperationsQueryService,
    _build_outbox_lines,
    _resolve_commit_products,
    apply_operation_history_scope_filters,
    get_current_shift_opened_at_for_history_scope,
)
from zeromerma_api.modules.operations.domain.constants import (
    OPERATION_BUCKET_BACKROOM,
    OPERATION_BUCKET_IN_TRANSIT,
    OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
    OPERATION_DOCUMENT_STATUS_RECEIVED,
    OPERATION_DOCUMENT_STATUS_RECEIVED_WITH_VARIANCE,
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
    OPERATION_HISTORY_SCOPE_ALL,
    OPERATION_HISTORY_SCOPE_CURRENT_SHIFT,
    OPERATION_HISTORY_SCOPE_RECENT,
    OPERATION_HISTORY_SCOPE_TODAY,
    OUTBOX_EVENT_TRANSFER_DISPATCHED_V1,
    OUTBOX_EVENT_TRANSFER_RECEIVED_V1,
    VALID_OPERATION_HISTORY_SCOPES,
)
from zeromerma_api.modules.operations.domain.exceptions import (
    OperationDocumentNotFoundError,
)
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.transfers.application.schemas import (
    PendingInboundTransfersResponse,
    PendingInboundTransferView,
    TransferDetailResponse,
    TransferDispatchCommitRequest,
    TransferDispatchHistoryResponse,
    TransferDocumentSummaryView,
    TransferQuantitySummaryView,
    TransferReceiptHistoryResponse,
    TransferReceiveRequest,
)
from zeromerma_api.modules.transfers.domain.exceptions import (
    TransferAlreadyReceivedError,
    TransferNotFoundError,
    TransferValidationError,
)

MAX_TRANSFER_HISTORY_ITEMS = 50


class TransferQueryService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        operations_query: OperationsQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._operations_query = operations_query or OperationsQueryService()

    def get_pending_inbound_transfers(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> PendingInboundTransfersResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        source_branch = aliased(Branch, name="source_branch")
        destination_branch = aliased(Branch, name="destination_branch")

        records = (
            session.execute(
                select(
                    OperationDocument.id,
                    OperationDocument.source_branch_id,
                    source_branch.code.label("source_branch_code"),
                    source_branch.name.label("source_branch_name"),
                    OperationDocument.destination_branch_id,
                    destination_branch.code.label("destination_branch_code"),
                    destination_branch.name.label("destination_branch_name"),
                    OperationDocument.workstation_id,
                    Workstation.code.label("workstation_code"),
                    Workstation.name.label("workstation_name"),
                    OperationDocument.status,
                    OperationDocument.created_at_utc,
                    OperationDocument.committed_at_utc,
                    func.count(OperationDocumentLine.id).label("line_count"),
                    func.coalesce(func.sum(OperationDocumentLine.quantity), 0).label(
                        "total_quantity"
                    ),
                )
                .select_from(OperationDocument)
                .join(source_branch, source_branch.id == OperationDocument.source_branch_id)
                .join(
                    destination_branch,
                    destination_branch.id == OperationDocument.destination_branch_id,
                )
                .join(Workstation, Workstation.id == OperationDocument.workstation_id)
                .join(
                    OperationDocumentLine,
                    OperationDocumentLine.operation_document_id == OperationDocument.id,
                )
                .where(
                    OperationDocument.document_type
                    == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
                    OperationDocument.destination_branch_id == context.branch_id,
                    OperationDocument.status == OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
                )
                .group_by(
                    OperationDocument.id,
                    OperationDocument.source_branch_id,
                    source_branch.code,
                    source_branch.name,
                    OperationDocument.destination_branch_id,
                    destination_branch.code,
                    destination_branch.name,
                    OperationDocument.workstation_id,
                    Workstation.code,
                    Workstation.name,
                    OperationDocument.status,
                    OperationDocument.created_at_utc,
                    OperationDocument.committed_at_utc,
                )
                .order_by(
                    OperationDocument.committed_at_utc.asc(),
                    OperationDocument.created_at_utc.asc(),
                    OperationDocument.id.asc(),
                )
                .limit(MAX_TRANSFER_HISTORY_ITEMS)
            )
            .mappings()
            .all()
        )

        return PendingInboundTransfersResponse(
            workstation_code=workstation_code,
            transfers=[
                PendingInboundTransferView(
                    id=record["id"],
                    folio=_build_transfer_folio(
                        OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
                        record["id"],
                    ),
                    source_branch_id=record["source_branch_id"],
                    source_branch_code=record["source_branch_code"],
                    source_branch_name=record["source_branch_name"],
                    destination_branch_id=record["destination_branch_id"],
                    destination_branch_code=record["destination_branch_code"],
                    destination_branch_name=record["destination_branch_name"],
                    workstation_id=record["workstation_id"],
                    workstation_code=record["workstation_code"],
                    workstation_name=record["workstation_name"],
                    status=record["status"],
                    created_at_utc=record["created_at_utc"],
                    committed_at_utc=record["committed_at_utc"],
                    line_count=int(record["line_count"]),
                    expected_total_quantity=record["total_quantity"],
                )
                for record in records
            ],
        )

    def get_transfer_detail(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        transfer_id: uuid.UUID,
    ) -> TransferDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        shipment = session.execute(
            select(OperationDocument).where(
                OperationDocument.id == transfer_id,
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
            )
        ).scalar_one_or_none()
        if shipment is None:
            raise TransferNotFoundError("Transfer shipment was not found.")
        if context.branch_id not in {shipment.source_branch_id, shipment.destination_branch_id}:
            raise TransferNotFoundError("Transfer shipment was not found.")

        receipt = session.execute(
            select(OperationDocument).where(
                OperationDocument.reference_document_id == shipment.id,
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
            )
        ).scalar_one_or_none()
        shipment_view = self._operations_query.get_operation_document(
            session,
            document_id=shipment.id,
        )
        receipt_view = (
            self._operations_query.get_operation_document(session, document_id=receipt.id)
            if receipt is not None
            else None
        )
        return _build_transfer_detail_response(
            shipment=shipment_view,
            receipt=receipt_view,
        )

    def get_outbound_dispatch_history(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        scope: str | None,
        created_by_user_id: uuid.UUID | None,
        destination_branch_id: uuid.UUID | None,
    ) -> TransferDispatchHistoryResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        normalized_scope = _validate_transfer_history_scope(scope)
        destination_branch = aliased(Branch)

        line_stats_subquery = (
            select(
                OperationDocumentLine.operation_document_id.label("document_id"),
                func.count(OperationDocumentLine.id).label("line_count"),
                func.coalesce(func.sum(OperationDocumentLine.quantity), 0).label("total_quantity"),
            )
            .group_by(OperationDocumentLine.operation_document_id)
            .subquery()
        )

        base_statement = (
            select(
                OperationDocument.id,
                OperationDocument.reference_document_id,
                OperationDocument.document_type,
                OperationDocument.status,
                OperationDocument.source_branch_id,
                Branch.code.label("source_branch_code"),
                Branch.name.label("source_branch_name"),
                OperationDocument.destination_branch_id,
                destination_branch.code.label("destination_branch_code"),
                destination_branch.name.label("destination_branch_name"),
                OperationDocument.source_bucket_code,
                OperationDocument.destination_bucket_code,
                OperationDocument.workstation_id,
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                OperationDocument.created_by_user_id,
                User.full_name.label("created_by_user_full_name"),
                OperationDocument.created_at_utc,
                OperationDocument.committed_at_utc,
                func.coalesce(line_stats_subquery.c.line_count, 0).label("line_count"),
                func.coalesce(line_stats_subquery.c.total_quantity, 0).label("total_quantity"),
            )
            .select_from(OperationDocument)
            .join(Branch, Branch.id == OperationDocument.source_branch_id)
            .join(
                destination_branch,
                destination_branch.id == OperationDocument.destination_branch_id,
            )
            .join(Workstation, Workstation.id == OperationDocument.workstation_id)
            .join(User, User.id == OperationDocument.created_by_user_id)
            .outerjoin(
                line_stats_subquery,
                line_stats_subquery.c.document_id == OperationDocument.id,
            )
            .where(
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
                OperationDocument.source_branch_id == context.branch_id,
                OperationDocument.workstation_id == context.workstation_id,
            )
        )
        base_statement = apply_operation_history_scope_filters(
            base_statement,
            normalized_scope=normalized_scope,
            context=context,
            current_shift_opened_at=get_current_shift_opened_at_for_history_scope(
                session,
                cash_session_query=self._cash_session_query,
                normalized_scope=normalized_scope,
                workstation_code=workstation_code,
            ),
        )

        available_user_rows = (
            session.execute(
                base_statement.with_only_columns(
                    OperationDocument.created_by_user_id,
                    User.full_name.label("created_by_user_full_name"),
                )
                .distinct()
                .order_by(User.full_name.asc())
            )
            .mappings()
            .all()
        )
        available_destination_rows = (
            session.execute(
                base_statement.with_only_columns(
                    OperationDocument.destination_branch_id,
                    destination_branch.name.label("destination_branch_name"),
                )
                .distinct()
                .order_by(destination_branch.name.asc())
            )
            .mappings()
            .all()
        )

        filtered_statement = base_statement
        if created_by_user_id is not None:
            filtered_statement = filtered_statement.where(
                OperationDocument.created_by_user_id == created_by_user_id
            )
        if destination_branch_id is not None:
            filtered_statement = filtered_statement.where(
                OperationDocument.destination_branch_id == destination_branch_id
            )

        record_rows = (
            session.execute(
                filtered_statement.order_by(
                    OperationDocument.committed_at_utc.desc().nullslast(),
                    OperationDocument.created_at_utc.desc(),
                    OperationDocument.id.desc(),
                ).limit(MAX_TRANSFER_HISTORY_ITEMS)
            )
            .mappings()
            .all()
        )

        return TransferDispatchHistoryResponse(
            workstation_code=workstation_code,
            scope=normalized_scope,
            created_by_user_id=str(created_by_user_id) if created_by_user_id is not None else None,
            destination_branch_id=(
                str(destination_branch_id) if destination_branch_id is not None else None
            ),
            available_scopes=[
                OperationHistoryScopeView(code=OPERATION_HISTORY_SCOPE_ALL, label="Todos"),
                OperationHistoryScopeView(
                    code=OPERATION_HISTORY_SCOPE_CURRENT_SHIFT,
                    label="Turno actual",
                ),
                OperationHistoryScopeView(code=OPERATION_HISTORY_SCOPE_TODAY, label="Hoy"),
                OperationHistoryScopeView(code=OPERATION_HISTORY_SCOPE_RECENT, label="Recientes"),
            ],
            available_users=[
                OperationHistoryFilterOptionView(
                    value=str(row["created_by_user_id"]),
                    label=row["created_by_user_full_name"],
                )
                for row in available_user_rows
            ],
            available_destination_branches=[
                OperationHistoryFilterOptionView(
                    value=str(row["destination_branch_id"]),
                    label=row["destination_branch_name"],
                )
                for row in available_destination_rows
                if row["destination_branch_id"] is not None
                and row["destination_branch_name"] is not None
            ],
            records=[
                OperationHistoryListItemView(
                    id=row["reference_document_id"] or row["id"],
                    folio=_build_transfer_folio(row["document_type"], row["id"]),
                    document_type=row["document_type"],
                    status=row["status"],
                    source_branch_code=row["source_branch_code"],
                    source_branch_name=row["source_branch_name"],
                    destination_branch_code=row["destination_branch_code"],
                    destination_branch_name=row["destination_branch_name"],
                    source_bucket_code=row["source_bucket_code"],
                    destination_bucket_code=row["destination_bucket_code"],
                    workstation_code=row["workstation_code"],
                    workstation_name=row["workstation_name"],
                    created_by_user_id=row["created_by_user_id"],
                    created_by_user_full_name=row["created_by_user_full_name"],
                    line_count=int(row["line_count"]),
                    total_quantity=row["total_quantity"],
                    created_at_utc=row["created_at_utc"],
                    committed_at_utc=row["committed_at_utc"],
                )
                for row in record_rows
            ],
        )

    def get_inbound_receipt_history(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        scope: str | None,
        created_by_user_id: uuid.UUID | None,
        source_branch_id: uuid.UUID | None,
        status: str | None,
    ) -> TransferReceiptHistoryResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        normalized_scope = _validate_transfer_history_scope(scope)
        normalized_status = (
            status.strip().upper() if status is not None and status.strip() else None
        )
        destination_branch = aliased(Branch)

        line_stats_subquery = (
            select(
                OperationDocumentLine.operation_document_id.label("document_id"),
                func.count(OperationDocumentLine.id).label("line_count"),
                func.coalesce(
                    func.sum(
                        func.coalesce(
                            OperationDocumentLine.received_quantity,
                            OperationDocumentLine.expected_quantity,
                            OperationDocumentLine.quantity,
                        )
                    ),
                    0,
                ).label("total_quantity"),
            )
            .group_by(OperationDocumentLine.operation_document_id)
            .subquery()
        )

        base_statement = (
            select(
                OperationDocument.id,
                OperationDocument.document_type,
                OperationDocument.status,
                OperationDocument.source_branch_id,
                Branch.code.label("source_branch_code"),
                Branch.name.label("source_branch_name"),
                OperationDocument.destination_branch_id,
                destination_branch.code.label("destination_branch_code"),
                destination_branch.name.label("destination_branch_name"),
                OperationDocument.source_bucket_code,
                OperationDocument.destination_bucket_code,
                OperationDocument.workstation_id,
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                OperationDocument.created_by_user_id,
                User.full_name.label("created_by_user_full_name"),
                OperationDocument.created_at_utc,
                OperationDocument.committed_at_utc,
                func.coalesce(line_stats_subquery.c.line_count, 0).label("line_count"),
                func.coalesce(line_stats_subquery.c.total_quantity, 0).label("total_quantity"),
            )
            .select_from(OperationDocument)
            .join(Branch, Branch.id == OperationDocument.source_branch_id)
            .join(
                destination_branch,
                destination_branch.id == OperationDocument.destination_branch_id,
            )
            .join(Workstation, Workstation.id == OperationDocument.workstation_id)
            .join(User, User.id == OperationDocument.created_by_user_id)
            .outerjoin(
                line_stats_subquery,
                line_stats_subquery.c.document_id == OperationDocument.id,
            )
            .where(
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
                OperationDocument.destination_branch_id == context.branch_id,
                OperationDocument.workstation_id == context.workstation_id,
            )
        )
        base_statement = apply_operation_history_scope_filters(
            base_statement,
            normalized_scope=normalized_scope,
            context=context,
            current_shift_opened_at=get_current_shift_opened_at_for_history_scope(
                session,
                cash_session_query=self._cash_session_query,
                normalized_scope=normalized_scope,
                workstation_code=workstation_code,
            ),
        )

        available_user_rows = (
            session.execute(
                base_statement.with_only_columns(
                    OperationDocument.created_by_user_id,
                    User.full_name.label("created_by_user_full_name"),
                )
                .distinct()
                .order_by(User.full_name.asc())
            )
            .mappings()
            .all()
        )
        available_source_rows = (
            session.execute(
                base_statement.with_only_columns(
                    OperationDocument.source_branch_id,
                    Branch.name.label("source_branch_name"),
                )
                .distinct()
                .order_by(Branch.name.asc())
            )
            .mappings()
            .all()
        )
        available_status_rows = (
            session.execute(
                base_statement.with_only_columns(OperationDocument.status)
                .distinct()
                .order_by(OperationDocument.status.asc())
            )
            .scalars()
            .all()
        )

        filtered_statement = base_statement
        if created_by_user_id is not None:
            filtered_statement = filtered_statement.where(
                OperationDocument.created_by_user_id == created_by_user_id
            )
        if source_branch_id is not None:
            filtered_statement = filtered_statement.where(
                OperationDocument.source_branch_id == source_branch_id
            )
        if normalized_status is not None:
            filtered_statement = filtered_statement.where(
                OperationDocument.status == normalized_status
            )

        record_rows = (
            session.execute(
                filtered_statement.order_by(
                    OperationDocument.committed_at_utc.desc().nullslast(),
                    OperationDocument.created_at_utc.desc(),
                    OperationDocument.id.desc(),
                ).limit(MAX_TRANSFER_HISTORY_ITEMS)
            )
            .mappings()
            .all()
        )

        return TransferReceiptHistoryResponse(
            workstation_code=workstation_code,
            scope=normalized_scope,
            created_by_user_id=str(created_by_user_id) if created_by_user_id is not None else None,
            source_branch_id=str(source_branch_id) if source_branch_id is not None else None,
            status=normalized_status,
            available_scopes=[
                OperationHistoryScopeView(code=OPERATION_HISTORY_SCOPE_ALL, label="Todos"),
                OperationHistoryScopeView(
                    code=OPERATION_HISTORY_SCOPE_CURRENT_SHIFT,
                    label="Turno actual",
                ),
                OperationHistoryScopeView(code=OPERATION_HISTORY_SCOPE_TODAY, label="Hoy"),
                OperationHistoryScopeView(code=OPERATION_HISTORY_SCOPE_RECENT, label="Recientes"),
            ],
            available_users=[
                OperationHistoryFilterOptionView(
                    value=str(row["created_by_user_id"]),
                    label=row["created_by_user_full_name"],
                )
                for row in available_user_rows
            ],
            available_source_branches=[
                OperationHistoryFilterOptionView(
                    value=str(row["source_branch_id"]),
                    label=row["source_branch_name"],
                )
                for row in available_source_rows
                if row["source_branch_id"] is not None and row["source_branch_name"] is not None
            ],
            available_statuses=[
                OperationHistoryFilterOptionView(
                    value=status_code,
                    label=_get_transfer_status_label(status_code),
                )
                for status_code in available_status_rows
                if status_code is not None
            ],
            records=[
                OperationHistoryListItemView(
                    id=row["id"],
                    folio=_build_transfer_folio(row["document_type"], row["id"]),
                    document_type=row["document_type"],
                    status=row["status"],
                    source_branch_code=row["source_branch_code"],
                    source_branch_name=row["source_branch_name"],
                    destination_branch_code=row["destination_branch_code"],
                    destination_branch_name=row["destination_branch_name"],
                    source_bucket_code=row["source_bucket_code"],
                    destination_bucket_code=row["destination_bucket_code"],
                    workstation_code=row["workstation_code"],
                    workstation_name=row["workstation_name"],
                    created_by_user_id=row["created_by_user_id"],
                    created_by_user_full_name=row["created_by_user_full_name"],
                    line_count=int(row["line_count"]),
                    total_quantity=row["total_quantity"],
                    created_at_utc=row["created_at_utc"],
                    committed_at_utc=row["committed_at_utc"],
                )
                for row in record_rows
            ],
        )


class TransferCommandService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        operations_query: OperationsQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._operations_query = operations_query or OperationsQueryService()

    def commit_dispatch(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: TransferDispatchCommitRequest,
        request_id: str | None,
    ) -> TransferDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=command.workstation_code,
        )
        if command.destination_branch_id == context.branch_id:
            raise TransferValidationError("Destination branch must differ from the current branch.")

        destination_branch = session.execute(
            select(Branch).where(
                Branch.id == command.destination_branch_id,
                Branch.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if destination_branch is None:
            raise TransferValidationError("Destination branch was not found.")

        resolved_lines = _resolve_commit_products(
            session,
            [
                OperationCommitLineRequest(
                    product_id=line.product_id,
                    quantity=line.quantity,
                    notes=line.notes,
                )
                for line in command.lines
            ],
        )
        committed_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        shipment = OperationDocument(
            document_type=OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
            status=OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
            source_branch_id=context.branch_id,
            destination_branch_id=destination_branch.id,
            source_bucket_code=OPERATION_BUCKET_BACKROOM,
            destination_bucket_code=OPERATION_BUCKET_BACKROOM,
            workstation_id=context.workstation_id,
            created_by_user_id=current_user.id,
            notes=command.notes,
            committed_at_utc=committed_at,
        )

        try:
            session.add(shipment)
            session.flush()
            for line_number, line in enumerate(command.lines, start=1):
                resolved_line = resolved_lines[line.product_id]
                session.add(
                    OperationDocumentLine(
                        operation_document_id=shipment.id,
                        line_number=line_number,
                        product_id=line.product_id,
                        product_code_snapshot=str(resolved_line["product_code"]),
                        product_name_snapshot=str(resolved_line["product_name"]),
                        product_class_id=resolved_line["product_class_id"],
                        product_class_code_snapshot=str(resolved_line["product_class_code"]),
                        product_class_name_snapshot=str(resolved_line["product_class_name"]),
                        quantity=line.quantity,
                        expected_quantity=line.quantity,
                        received_quantity=None,
                        notes=line.notes,
                    )
                )

            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action="transfer.dispatched",
                resource_type="operation_document",
                resource_id=str(shipment.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "document_type": shipment.document_type,
                    "status": shipment.status,
                    "source_branch_code": context.branch_code,
                    "destination_branch_code": destination_branch.code,
                    "source_bucket_code": OPERATION_BUCKET_BACKROOM,
                    "destination_bucket_code": OPERATION_BUCKET_BACKROOM,
                    "workstation_code": context.workstation_code,
                    "line_count": len(command.lines),
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type="transfer",
                aggregate_id=str(shipment.id),
                event_name=OUTBOX_EVENT_TRANSFER_DISPATCHED_V1,
                payload={
                    "document_id": str(shipment.id),
                    "document_type": shipment.document_type,
                    "status": shipment.status,
                    "source_branch_id": str(context.branch_id),
                    "source_branch_code": context.branch_code,
                    "destination_branch_id": str(destination_branch.id),
                    "destination_branch_code": destination_branch.code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "created_by_user_id": str(current_user.id),
                    "created_by_user_email": current_user.email,
                    "notes": command.notes,
                    "committed_at_utc": committed_at.isoformat(),
                    "quantity_summary": {
                        "line_count": len(command.lines),
                        "expected_total_quantity": str(
                            sum((line.quantity for line in command.lines), Decimal("0"))
                        ),
                        "received_total_quantity": None,
                        "has_variance": False,
                        "variance_line_count": 0,
                    },
                    "lines": _build_outbox_lines(
                        [
                            OperationCommitLineRequest(
                                product_id=line.product_id,
                                quantity=line.quantity,
                                notes=line.notes,
                            )
                            for line in command.lines
                        ],
                        resolved_lines,
                    ),
                },
                headers={"request_id": resolved_request_id},
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise TransferValidationError(
                "Transfer dispatch invariants were violated by a concurrent request."
            ) from error

        shipment_view = self._operations_query.get_operation_document(
            session,
            document_id=shipment.id,
        )
        return _build_transfer_detail_response(shipment=shipment_view, receipt=None)

    def receive_transfer(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        transfer_id: uuid.UUID,
        command: TransferReceiveRequest,
        request_id: str | None,
    ) -> TransferDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        shipment = session.execute(
            select(OperationDocument).where(
                OperationDocument.id == transfer_id,
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
            )
        ).scalar_one_or_none()
        if shipment is None:
            raise TransferNotFoundError("Transfer shipment was not found.")
        if shipment.destination_branch_id != context.branch_id:
            raise TransferValidationError(
                "Transfer shipment is not destined to the current branch."
            )
        if shipment.status != OPERATION_DOCUMENT_STATUS_IN_TRANSIT:
            raise TransferAlreadyReceivedError("Transfer shipment is no longer pending receipt.")

        existing_receipt = session.execute(
            select(OperationDocument.id).where(
                OperationDocument.reference_document_id == shipment.id,
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
            )
        ).scalar_one_or_none()
        if existing_receipt is not None:
            raise TransferAlreadyReceivedError("Transfer shipment is no longer pending receipt.")

        shipment_lines = (
            session.execute(
                select(OperationDocumentLine)
                .where(OperationDocumentLine.operation_document_id == shipment.id)
                .order_by(OperationDocumentLine.line_number.asc())
            )
            .scalars()
            .all()
        )
        if len(shipment_lines) == 0:
            raise OperationDocumentNotFoundError("Transfer shipment has no lines.")

        receipt_by_line_id = {line.shipment_line_id: line for line in command.lines}
        if {line.id for line in shipment_lines} != set(receipt_by_line_id):
            raise TransferValidationError(
                "Transfer receipt lines must match the pending shipment lines exactly."
            )

        resolved_request_id = request_id or str(uuid.uuid4())
        committed_at = datetime.now(tz=UTC)
        has_variance = False
        receipt = OperationDocument(
            document_type=OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
            status=OPERATION_DOCUMENT_STATUS_RECEIVED,
            source_branch_id=shipment.source_branch_id,
            destination_branch_id=context.branch_id,
            source_bucket_code=OPERATION_BUCKET_IN_TRANSIT,
            destination_bucket_code=OPERATION_BUCKET_BACKROOM,
            workstation_id=context.workstation_id,
            created_by_user_id=current_user.id,
            notes=command.notes,
            reference_document_id=shipment.id,
            committed_at_utc=committed_at,
        )

        try:
            session.add(receipt)
            session.flush()
            for shipment_line in shipment_lines:
                receipt_line = receipt_by_line_id[shipment_line.id]
                if receipt_line.expected_quantity != shipment_line.quantity:
                    raise TransferValidationError(
                        "Transfer receipt expected quantities must match the pending shipment."
                    )
                if receipt_line.received_quantity != shipment_line.quantity and (
                    receipt_line.variance_reason is None
                    or receipt_line.variance_reason.strip() == ""
                ):
                    raise TransferValidationError(
                        "Variance reason is required when the received quantity "
                        "differs from the shipment."
                    )
                if receipt_line.received_quantity != shipment_line.quantity:
                    has_variance = True
                session.add(
                    OperationDocumentLine(
                        operation_document_id=receipt.id,
                        line_number=shipment_line.line_number,
                        product_id=shipment_line.product_id,
                        product_code_snapshot=shipment_line.product_code_snapshot,
                        product_name_snapshot=shipment_line.product_name_snapshot,
                        product_class_id=shipment_line.product_class_id,
                        product_class_code_snapshot=shipment_line.product_class_code_snapshot,
                        product_class_name_snapshot=shipment_line.product_class_name_snapshot,
                        quantity=shipment_line.quantity,
                        expected_quantity=shipment_line.quantity,
                        received_quantity=receipt_line.received_quantity,
                        variance_reason=receipt_line.variance_reason,
                        notes=receipt_line.notes,
                    )
                )

            receipt.status = (
                OPERATION_DOCUMENT_STATUS_RECEIVED_WITH_VARIANCE
                if has_variance
                else OPERATION_DOCUMENT_STATUS_RECEIVED
            )
            shipment.status = receipt.status

            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action="transfer.received",
                resource_type="operation_document",
                resource_id=str(receipt.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "shipment_id": str(shipment.id),
                    "receipt_id": str(receipt.id),
                    "status": receipt.status,
                    "source_branch_id": str(shipment.source_branch_id),
                    "destination_branch_id": str(context.branch_id),
                    "workstation_code": context.workstation_code,
                    "line_count": len(command.lines),
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type="transfer",
                aggregate_id=str(shipment.id),
                event_name=OUTBOX_EVENT_TRANSFER_RECEIVED_V1,
                payload={
                    "shipment_id": str(shipment.id),
                    "receipt_id": str(receipt.id),
                    "status": receipt.status,
                    "source_branch_id": str(shipment.source_branch_id),
                    "destination_branch_id": str(context.branch_id),
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "received_by_user_id": str(current_user.id),
                    "received_by_user_email": current_user.email,
                    "notes": command.notes,
                    "committed_at_utc": committed_at.isoformat(),
                    "linked_shipment_id": str(shipment.id),
                    "quantity_summary": {
                        "line_count": len(command.lines),
                        "expected_total_quantity": str(
                            sum((line.quantity for line in shipment_lines), Decimal("0"))
                        ),
                        "received_total_quantity": str(
                            sum(
                                (
                                    receipt_by_line_id[line.id].received_quantity
                                    for line in shipment_lines
                                ),
                                Decimal("0"),
                            )
                        ),
                        "has_variance": has_variance,
                        "variance_line_count": sum(
                            1
                            for line in shipment_lines
                            if receipt_by_line_id[line.id].received_quantity != line.quantity
                        ),
                    },
                    "lines": [
                        {
                            "shipment_line_id": str(shipment_line.id),
                            "product_id": str(shipment_line.product_id),
                            "product_code_snapshot": shipment_line.product_code_snapshot,
                            "product_name_snapshot": shipment_line.product_name_snapshot,
                            "product_class_id": str(shipment_line.product_class_id),
                            "product_class_code_snapshot": (
                                shipment_line.product_class_code_snapshot
                            ),
                            "product_class_name_snapshot": (
                                shipment_line.product_class_name_snapshot
                            ),
                            "expected_quantity": str(shipment_line.quantity),
                            "received_quantity": str(
                                receipt_by_line_id[shipment_line.id].received_quantity
                            ),
                            "variance_reason": receipt_by_line_id[shipment_line.id].variance_reason,
                            "notes": receipt_by_line_id[shipment_line.id].notes,
                        }
                        for shipment_line in shipment_lines
                    ],
                },
                headers={"request_id": resolved_request_id},
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise TransferValidationError(
                "Transfer receipt invariants were violated by a concurrent request."
            ) from error

        shipment_view = self._operations_query.get_operation_document(
            session,
            document_id=shipment.id,
        )
        receipt_view = self._operations_query.get_operation_document(
            session,
            document_id=receipt.id,
        )
        return _build_transfer_detail_response(
            shipment=shipment_view,
            receipt=receipt_view,
        )


def _build_transfer_detail_response(
    *,
    shipment: OperationDocumentView,
    receipt: OperationDocumentView | None,
) -> TransferDetailResponse:
    return TransferDetailResponse(
        shipment=shipment,
        shipment_summary=_build_transfer_document_summary(shipment),
        receipt=receipt,
        receipt_summary=(
            _build_transfer_document_summary(receipt) if receipt is not None else None
        ),
    )


def _build_transfer_document_summary(
    document: OperationDocumentView,
) -> TransferDocumentSummaryView:
    expected_total_quantity = Decimal("0")
    received_total_quantity = Decimal("0")
    has_received_quantities = False
    variance_line_count = 0

    for line in document.lines:
        expected_quantity = (
            line.expected_quantity if line.expected_quantity is not None else line.quantity
        )
        expected_total_quantity += expected_quantity
        if line.received_quantity is not None:
            has_received_quantities = True
            received_total_quantity += line.received_quantity
            if line.received_quantity != expected_quantity:
                variance_line_count += 1

    return TransferDocumentSummaryView(
        document_id=document.id,
        folio=_build_transfer_folio(document.document_type, document.id),
        status=document.status,
        committed_at_utc=document.committed_at_utc,
        linked_shipment_id=document.reference_document_id,
        quantity_summary=TransferQuantitySummaryView(
            line_count=len(document.lines),
            expected_total_quantity=expected_total_quantity,
            received_total_quantity=(received_total_quantity if has_received_quantities else None),
            has_variance=variance_line_count > 0,
            variance_line_count=variance_line_count,
        ),
    )


def _build_transfer_folio(document_type: str, document_id: uuid.UUID) -> str:
    prefix = "ENV" if document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT else "REC"
    return f"{prefix}-{str(document_id).split('-', maxsplit=1)[0].upper()}"


def _get_transfer_status_label(status: str) -> str:
    if status == OPERATION_DOCUMENT_STATUS_IN_TRANSIT:
        return "En transito"
    if status == OPERATION_DOCUMENT_STATUS_RECEIVED:
        return "Recibido"
    if status == OPERATION_DOCUMENT_STATUS_RECEIVED_WITH_VARIANCE:
        return "Recibido con diferencia"
    return status


def _validate_transfer_history_scope(scope: str | None) -> str:
    if scope is None or scope.strip() == "":
        return OPERATION_HISTORY_SCOPE_CURRENT_SHIFT

    normalized_scope = scope.strip().upper()
    if normalized_scope not in VALID_OPERATION_HISTORY_SCOPES:
        raise TransferValidationError("History scope is not valid for transfers.")
    return normalized_scope
