from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import Select, String, exists, false, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.application.visibility import (
    AuditVisibilityQueryService,
    BackofficeNotificationConfig,
    build_audit_actor_snapshot,
)
from zeromerma_api.modules.branches.application.access import (
    WorkstationAccessService,
    WorkstationContext,
)
from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.cash.application.services import CashSessionQueryService
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.corrections.application.schemas import (
    AppliedCorrectionLineSummaryView,
    AppliedCorrectionSummaryView,
    CorrectionBootstrapResponse,
    CorrectionCommitLineRequest,
    CorrectionCommitRequest,
    CorrectionControlsView,
    CorrectionDocumentLineView,
    CorrectionDocumentView,
    CorrectionHistoryFilterOptionView,
    CorrectionHistoryListItemView,
    CorrectionHistoryScopeView,
    CorrectionProductOptionView,
    CorrectionReasonView,
    CorrectionSearchDocumentView,
    CorrectionSearchResponse,
    CorrectionsHistoryResponse,
    CorrectionsProductsResponse,
    CorrectionTargetDetailResponse,
)
from zeromerma_api.modules.corrections.domain.constants import (
    CORRECTION_REASON_WRONG_DESTINATION,
    CORRECTION_STATUS_COMMITTED,
    CORRECTION_TYPE_DELTA_ADJUSTMENT,
    CORRECTION_TYPE_DESTINATION_ADJUSTMENT,
    OUTBOX_EVENT_CORRECTION_COMMITTED_V1,
    OUTBOX_EVENT_CORRECTION_HIGH_IMPACT_ALERT_V1,
    VALID_CORRECTION_TARGET_DOCUMENT_TYPES,
)
from zeromerma_api.modules.corrections.domain.exceptions import (
    CorrectionConflictError,
    CorrectionIneligibleError,
    CorrectionNotFoundError,
    CorrectionReasonNotFoundError,
    CorrectionValidationError,
)
from zeromerma_api.modules.corrections.infrastructure.models import (
    CorrectionDocument,
    CorrectionDocumentLine,
    CorrectionReason,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.application.schemas import (
    OperationCommitLineRequest,
    TransferDestinationBranchView,
)
from zeromerma_api.modules.operations.application.services import (
    OperationsQueryService,
    _resolve_commit_products,
)
from zeromerma_api.modules.operations.domain.constants import (
    BRANCH_BRAND_MAPPING,
    OPERATION_DOCUMENT_STATUS_COMMITTED,
    OPERATION_DOCUMENT_STATUS_IN_TRANSIT,
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
    OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
    OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
    OPERATION_HISTORY_SCOPE_ALL,
    OPERATION_HISTORY_SCOPE_CURRENT_SHIFT,
    OPERATION_HISTORY_SCOPE_RECENT,
    OPERATION_HISTORY_SCOPE_TODAY,
    VALID_OPERATION_HISTORY_SCOPES,
)
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter

MAX_CORRECTION_SEARCH_RESULTS = 80
MAX_PRODUCT_SEARCH_RESULTS = 24
MAX_CORRECTION_HISTORY_RESULTS = 80


class CorrectionQueryService:
    def __init__(
        self,
        settings: ApiSettings | None = None,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        operations_query: OperationsQueryService | None = None,
        audit_visibility: AuditVisibilityQueryService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._operations_query = operations_query or OperationsQueryService()
        self._audit_visibility = audit_visibility or AuditVisibilityQueryService()

    def get_bootstrap(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> CorrectionBootstrapResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        current_open_cash_session = self._cash_session_query.get_open_session_for_workstation_code(
            session,
            workstation_code=workstation_code,
        )
        local_timestamp = datetime.now(tz=UTC).astimezone(ZoneInfo(context.branch_timezone))
        reason_records = (
            session.execute(
                select(CorrectionReason.code, CorrectionReason.name, CorrectionReason.display_order)
                .where(CorrectionReason.is_active.is_(True))
                .order_by(CorrectionReason.display_order.asc(), CorrectionReason.name.asc())
            )
            .mappings()
            .all()
        )
        destination_branch_records = (
            session.execute(
                select(Branch.id, Branch.code, Branch.name, Branch.timezone)
                .where(Branch.is_active.is_(True), Branch.id != context.branch_id)
                .order_by(Branch.name.asc())
            )
            .mappings()
            .all()
        )

        return CorrectionBootstrapResponse(
            user=current_user,
            branch=BranchSummary(
                id=context.branch_id,
                code=context.branch_code,
                name=context.branch_name,
                timezone=context.branch_timezone,
                is_active=context.branch_is_active,
            ),
            workstation=WorkstationSummary(
                id=context.workstation_id,
                code=context.workstation_code,
                name=context.workstation_name,
                is_active=context.workstation_is_active,
            ),
            local_timestamp=local_timestamp,
            current_open_cash_session=current_open_cash_session,
            branch_brand_key=_get_branch_brand_key(context.branch_code),
            correction_operations_allowed=(
                current_open_cash_session is not None
                and current_open_cash_session.user_id == current_user.id
            ),
            correction_reasons=[
                CorrectionReasonView(
                    code=record["code"],
                    name=record["name"],
                    display_order=record["display_order"],
                )
                for record in reason_records
            ],
            correction_controls=CorrectionControlsView(
                high_impact_quantity_threshold=self._settings.correction_high_impact_quantity_threshold,
                high_impact_requires_acknowledgement=True,
            ),
            destination_branches=[
                TransferDestinationBranchView(
                    id=record["id"],
                    code=record["code"],
                    name=record["name"],
                    timezone=record["timezone"],
                    brand_key=_get_branch_brand_key(record["code"]),
                )
                for record in destination_branch_records
            ],
        )

    def search_documents(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        query: str | None,
        document_type: str | None,
    ) -> CorrectionSearchResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        normalized_query = _normalize_query(query)
        validated_document_type = _validate_document_type(document_type)

        document_record = aliased(OperationDocument)
        source_branch = aliased(Branch)
        destination_branch = aliased(Branch)
        receipt_exists = exists(
            select(OperationDocument.id).where(
                OperationDocument.reference_document_id == document_record.id,
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
            )
        )

        correction_count_subquery = (
            select(func.count(CorrectionDocument.id))
            .where(CorrectionDocument.target_document_id == document_record.id)
            .correlate(document_record)
            .scalar_subquery()
        )
        statement = (
            select(
                document_record.id,
                document_record.document_type,
                document_record.status,
                source_branch.code.label("source_branch_code"),
                source_branch.name.label("source_branch_name"),
                destination_branch.code.label("destination_branch_code"),
                destination_branch.name.label("destination_branch_name"),
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                document_record.committed_at_utc,
                correction_count_subquery.label("correction_count"),
            )
            .select_from(document_record)
            .join(source_branch, source_branch.id == document_record.source_branch_id)
            .outerjoin(
                destination_branch, destination_branch.id == document_record.destination_branch_id
            )
            .join(Workstation, Workstation.id == document_record.workstation_id)
            .where(
                document_record.source_branch_id == context.branch_id,
                document_record.document_type.in_(VALID_CORRECTION_TARGET_DOCUMENT_TYPES),
                or_(
                    (
                        document_record.document_type.in_(
                            [
                                OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
                                OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
                            ]
                        )
                        & (document_record.status == OPERATION_DOCUMENT_STATUS_COMMITTED)
                    ),
                    (
                        document_record.document_type
                        == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT
                    )
                    & (document_record.status == OPERATION_DOCUMENT_STATUS_IN_TRANSIT)
                    & ~receipt_exists,
                ),
            )
            .order_by(
                document_record.committed_at_utc.desc(), document_record.created_at_utc.desc()
            )
        )

        if validated_document_type is not None:
            statement = statement.where(document_record.document_type == validated_document_type)

        if normalized_query is not None:
            pattern = f"%{normalized_query}%"
            folio_document_type, folio_id_prefix = _parse_target_document_folio_query(
                normalized_query
            )
            matching_lines = exists(
                select(OperationDocumentLine.id).where(
                    OperationDocumentLine.operation_document_id == document_record.id,
                    or_(
                        OperationDocumentLine.product_code_snapshot.ilike(pattern),
                        OperationDocumentLine.product_name_snapshot.ilike(pattern),
                        OperationDocumentLine.product_class_code_snapshot.ilike(pattern),
                        OperationDocumentLine.product_class_name_snapshot.ilike(pattern),
                    ),
                )
            )
            statement = statement.where(
                or_(
                    document_record.notes.ilike(pattern),
                    source_branch.code.ilike(pattern),
                    source_branch.name.ilike(pattern),
                    destination_branch.code.ilike(pattern),
                    destination_branch.name.ilike(pattern),
                    Workstation.code.ilike(pattern),
                    Workstation.name.ilike(pattern),
                    document_record.id.cast(String).ilike(pattern),
                    (
                        (document_record.document_type == folio_document_type)
                        & document_record.id.cast(String).ilike(f"{folio_id_prefix}%")
                    )
                    if folio_document_type is not None and folio_id_prefix is not None
                    else false(),
                    matching_lines,
                )
            )

        records = session.execute(statement.limit(MAX_CORRECTION_SEARCH_RESULTS)).mappings().all()
        return CorrectionSearchResponse(
            workstation_code=workstation_code,
            document_type=validated_document_type,
            query=normalized_query,
            documents=[
                CorrectionSearchDocumentView(
                    id=record["id"],
                    folio=_build_target_document_folio(record["document_type"], record["id"]),
                    document_type=record["document_type"],
                    status=record["status"],
                    display_title=_build_document_title(
                        record["document_type"],
                        record["id"],
                    ),
                    source_branch_code=record["source_branch_code"],
                    source_branch_name=record["source_branch_name"],
                    destination_branch_code=record["destination_branch_code"],
                    destination_branch_name=record["destination_branch_name"],
                    workstation_code=record["workstation_code"],
                    workstation_name=record["workstation_name"],
                    committed_at_utc=record["committed_at_utc"],
                    correction_count=int(record["correction_count"]),
                )
                for record in records
            ],
        )

    def get_target_detail(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        target_document_id: uuid.UUID,
    ) -> CorrectionTargetDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        target_document = _get_target_document(
            session,
            target_document_id=target_document_id,
        )
        _ensure_branch_ownership(target_document=target_document, branch_id=context.branch_id)
        target_view = self._operations_query.get_operation_document(
            session,
            document_id=target_document.id,
        )
        is_correctable, blocking_reason = _assess_correction_eligibility(
            session,
            target_document=target_document,
        )
        corrected_destination_branch = aliased(Branch)

        applied_corrections = (
            session.execute(
                select(
                    CorrectionDocument.id,
                    CorrectionDocument.created_by_user_id,
                    CorrectionDocument.reason_code,
                    CorrectionReason.name.label("reason_name"),
                    CorrectionDocument.status,
                    CorrectionDocument.committed_at_utc,
                    User.email.label("created_by_user_email"),
                    User.full_name.label("created_by_user_full_name"),
                    corrected_destination_branch.code.label(
                        "corrected_destination_branch_code"
                    ),
                    corrected_destination_branch.name.label(
                        "corrected_destination_branch_name"
                    ),
                    func.count(CorrectionDocumentLine.id).label("line_count"),
                )
                .select_from(CorrectionDocument)
                .join(CorrectionReason, CorrectionReason.code == CorrectionDocument.reason_code)
                .join(User, User.id == CorrectionDocument.created_by_user_id)
                .outerjoin(
                    corrected_destination_branch,
                    corrected_destination_branch.id
                    == CorrectionDocument.corrected_destination_branch_id,
                )
                .outerjoin(
                    CorrectionDocumentLine,
                    CorrectionDocumentLine.correction_document_id == CorrectionDocument.id,
                )
                .where(CorrectionDocument.target_document_id == target_document.id)
                .group_by(
                    CorrectionDocument.id,
                    CorrectionDocument.created_by_user_id,
                    CorrectionDocument.reason_code,
                    CorrectionReason.name,
                    CorrectionDocument.status,
                    CorrectionDocument.committed_at_utc,
                    User.email,
                    User.full_name,
                    corrected_destination_branch.code,
                    corrected_destination_branch.name,
                )
                .order_by(
                    CorrectionDocument.committed_at_utc.desc(),
                    CorrectionDocument.created_at_utc.desc(),
                )
            )
            .mappings()
            .all()
        )
        correction_ids = [record["id"] for record in applied_corrections]
        line_records_by_correction_id: dict[uuid.UUID, list[AppliedCorrectionLineSummaryView]] = {
            correction_id: [] for correction_id in correction_ids
        }
        if correction_ids:
            line_records = (
                session.execute(
                    select(
                        CorrectionDocumentLine.correction_document_id,
                        CorrectionDocumentLine.line_number,
                        CorrectionDocumentLine.target_line_id,
                        CorrectionDocumentLine.product_code_snapshot,
                        CorrectionDocumentLine.product_name_snapshot,
                        CorrectionDocumentLine.delta_quantity,
                    )
                    .where(CorrectionDocumentLine.correction_document_id.in_(correction_ids))
                    .order_by(
                        CorrectionDocumentLine.correction_document_id.asc(),
                        CorrectionDocumentLine.line_number.asc(),
                    )
                )
                .mappings()
                .all()
            )
            for record in line_records:
                line_records_by_correction_id[record["correction_document_id"]].append(
                    AppliedCorrectionLineSummaryView(
                        line_number=record["line_number"],
                        target_line_id=record["target_line_id"],
                        product_code_snapshot=record["product_code_snapshot"],
                        product_name_snapshot=record["product_name_snapshot"],
                        delta_quantity=record["delta_quantity"],
                    )
                )

        return CorrectionTargetDetailResponse(
            document_title=_build_document_title(target_document.document_type, target_document.id),
            target_document=target_view,
            is_correctable=is_correctable,
            blocking_reason=blocking_reason,
            applied_corrections=[
                AppliedCorrectionSummaryView(
                    id=record["id"],
                    folio=_build_correction_document_folio(record["id"]),
                    reason_code=record["reason_code"],
                    reason_name=record["reason_name"],
                    status=record["status"],
                    committed_at_utc=record["committed_at_utc"],
                    line_count=int(record["line_count"]),
                    corrected_destination_branch_code=record[
                        "corrected_destination_branch_code"
                    ],
                    corrected_destination_branch_name=record[
                        "corrected_destination_branch_name"
                    ],
                    audit_summary=self._audit_visibility.build_summary(
                        session,
                        created_actor=build_audit_actor_snapshot(
                            user_id=record["created_by_user_id"],
                            full_name=record["created_by_user_full_name"],
                            email=record["created_by_user_email"],
                        ),
                        created_at_utc=record["committed_at_utc"],
                        confirmed_at_utc=record["committed_at_utc"],
                        acknowledgement_label="Validacion de alto impacto",
                        reason_label=record["reason_name"],
                        notification_config=BackofficeNotificationConfig(
                            aggregate_id=str(record["id"]),
                            aggregate_type="correction",
                            event_names=(OUTBOX_EVENT_CORRECTION_HIGH_IMPACT_ALERT_V1,),
                            label="Alerta a backoffice",
                        ),
                    ),
                    lines=line_records_by_correction_id.get(record["id"], []),
                )
                for record in applied_corrections
            ],
        )

    def list_correction_history(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        scope: str | None,
        query: str | None,
        created_by_user_id: uuid.UUID | None,
        target_document_type: str | None,
        reason_code: str | None,
    ) -> CorrectionsHistoryResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        current_open_cash_session = _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        normalized_scope = _validate_correction_history_scope(scope)
        normalized_query = _normalize_query(query)
        validated_target_document_type = _validate_history_target_document_type(
            target_document_type
        )
        normalized_reason_code = _normalize_query(reason_code)

        target_document = aliased(OperationDocument)
        source_branch = aliased(Branch)
        workstation = aliased(Workstation)
        line_stats_subquery = (
            select(
                CorrectionDocumentLine.correction_document_id.label("correction_document_id"),
                func.count(CorrectionDocumentLine.id).label("line_count"),
                func.coalesce(func.sum(CorrectionDocumentLine.delta_quantity), 0).label(
                    "net_effect_quantity"
                ),
            )
            .group_by(CorrectionDocumentLine.correction_document_id)
            .subquery()
        )
        base_statement = (
            select(
                CorrectionDocument.id,
                CorrectionDocument.target_document_id,
                target_document.document_type.label("target_document_type"),
                CorrectionDocument.correction_type,
                CorrectionDocument.status,
                CorrectionDocument.created_by_user_id,
                User.full_name.label("created_by_user_full_name"),
                CorrectionDocument.reason_code,
                CorrectionReason.name.label("reason_name"),
                source_branch.code.label("source_branch_code"),
                source_branch.name.label("source_branch_name"),
                workstation.code.label("workstation_code"),
                workstation.name.label("workstation_name"),
                Branch.code.label("corrected_destination_branch_code"),
                Branch.name.label("corrected_destination_branch_name"),
                CorrectionDocument.created_at_utc,
                CorrectionDocument.committed_at_utc,
                func.coalesce(line_stats_subquery.c.line_count, 0).label("line_count"),
                func.coalesce(line_stats_subquery.c.net_effect_quantity, 0).label(
                    "net_effect_quantity"
                ),
            )
            .select_from(CorrectionDocument)
            .join(target_document, target_document.id == CorrectionDocument.target_document_id)
            .join(source_branch, source_branch.id == CorrectionDocument.source_branch_id)
            .join(workstation, workstation.id == CorrectionDocument.workstation_id)
            .join(User, User.id == CorrectionDocument.created_by_user_id)
            .join(CorrectionReason, CorrectionReason.code == CorrectionDocument.reason_code)
            .outerjoin(Branch, Branch.id == CorrectionDocument.corrected_destination_branch_id)
            .outerjoin(
                line_stats_subquery,
                line_stats_subquery.c.correction_document_id == CorrectionDocument.id,
            )
            .where(
                CorrectionDocument.source_branch_id == context.branch_id,
                CorrectionDocument.workstation_id == context.workstation_id,
                CorrectionDocument.status == CORRECTION_STATUS_COMMITTED,
            )
        )
        base_statement = _apply_correction_history_scope_filters(
            base_statement,
            normalized_scope=normalized_scope,
            context=context,
            current_shift_opened_at=current_open_cash_session.opened_at,
        )

        available_user_rows = session.execute(
            base_statement.with_only_columns(
                CorrectionDocument.created_by_user_id,
                User.full_name.label("created_by_user_full_name"),
            )
            .distinct()
            .order_by(User.full_name.asc())
        ).mappings().all()
        available_target_type_rows = session.execute(
            base_statement.with_only_columns(target_document.document_type)
            .distinct()
            .order_by(target_document.document_type.asc())
        ).scalars().all()
        available_reason_rows = session.execute(
            base_statement.with_only_columns(
                CorrectionDocument.reason_code,
                CorrectionReason.name.label("reason_name"),
            )
            .distinct()
            .order_by(CorrectionReason.name.asc(), CorrectionDocument.reason_code.asc())
        ).mappings().all()

        filtered_statement = base_statement
        if created_by_user_id is not None:
            filtered_statement = filtered_statement.where(
                CorrectionDocument.created_by_user_id == created_by_user_id
            )
        if validated_target_document_type is not None:
            filtered_statement = filtered_statement.where(
                target_document.document_type == validated_target_document_type
            )
        if normalized_reason_code is not None:
            filtered_statement = filtered_statement.where(
                CorrectionDocument.reason_code == normalized_reason_code
            )
        if normalized_query is not None:
            pattern = f"%{normalized_query}%"
            filtered_statement = filtered_statement.where(
                or_(
                    CorrectionDocument.id.cast(String).ilike(pattern),
                    func.concat(
                        "COR-", func.substr(CorrectionDocument.id.cast(String), 1, 8)
                    ).ilike(pattern),
                    CorrectionDocument.target_document_id.cast(String).ilike(pattern),
                    User.full_name.ilike(pattern),
                    CorrectionReason.name.ilike(pattern),
                )
            )

        rows = session.execute(
            filtered_statement
            .order_by(
                CorrectionDocument.committed_at_utc.desc().nullslast(),
                CorrectionDocument.created_at_utc.desc(),
            )
            .limit(MAX_CORRECTION_HISTORY_RESULTS)
        ).mappings().all()

        return CorrectionsHistoryResponse(
            workstation_code=workstation_code,
            scope=normalized_scope,
            query=normalized_query,
            created_by_user_id=str(created_by_user_id) if created_by_user_id is not None else None,
            target_document_type=validated_target_document_type,
            reason_code=normalized_reason_code,
            available_scopes=[
                CorrectionHistoryScopeView(code=OPERATION_HISTORY_SCOPE_ALL, label="Todos"),
                CorrectionHistoryScopeView(
                    code=OPERATION_HISTORY_SCOPE_CURRENT_SHIFT,
                    label="Turno actual",
                ),
                CorrectionHistoryScopeView(code=OPERATION_HISTORY_SCOPE_TODAY, label="Hoy"),
                CorrectionHistoryScopeView(code=OPERATION_HISTORY_SCOPE_RECENT, label="Recientes"),
            ],
            available_users=[
                CorrectionHistoryFilterOptionView(
                    value=str(row["created_by_user_id"]),
                    label=row["created_by_user_full_name"],
                )
                for row in available_user_rows
            ],
            available_document_types=[
                CorrectionHistoryFilterOptionView(
                    value=document_type,
                    label=_build_history_document_type_label(document_type),
                )
                for document_type in available_target_type_rows
                if document_type is not None
            ],
            available_reasons=[
                CorrectionHistoryFilterOptionView(
                    value=row["reason_code"],
                    label=row["reason_name"],
                )
                for row in available_reason_rows
                if row["reason_code"] is not None and row["reason_name"] is not None
            ],
            records=[
                CorrectionHistoryListItemView(
                    id=row["id"],
                    folio=_build_correction_document_folio(row["id"]),
                    target_document_id=row["target_document_id"],
                    target_document_folio=_build_target_document_folio(
                        row["target_document_type"],
                        row["target_document_id"],
                    ),
                    target_document_type=row["target_document_type"],
                    correction_type=row["correction_type"],
                    status=row["status"],
                    source_branch_code=row["source_branch_code"],
                    source_branch_name=row["source_branch_name"],
                    workstation_code=row["workstation_code"],
                    workstation_name=row["workstation_name"],
                    created_by_user_id=row["created_by_user_id"],
                    created_by_user_full_name=row["created_by_user_full_name"],
                    reason_code=row["reason_code"],
                    reason_name=row["reason_name"],
                    corrected_destination_branch_code=row["corrected_destination_branch_code"],
                    corrected_destination_branch_name=row["corrected_destination_branch_name"],
                    line_count=int(row["line_count"]),
                    net_effect_quantity=row["net_effect_quantity"],
                    created_at_utc=row["created_at_utc"],
                    committed_at_utc=row["committed_at_utc"],
                )
                for row in rows
            ],
        )

    def get_correction_document(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        correction_id: uuid.UUID,
    ) -> CorrectionDocumentView:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        correction_document = _get_correction_document(
            session,
            correction_id=correction_id,
        )
        _ensure_correction_branch_ownership(
            correction_document=correction_document,
            branch_id=context.branch_id,
        )
        return _build_correction_document_view(
            session,
            correction_document=correction_document,
        )

    def search_products(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        query: str | None,
    ) -> CorrectionsProductsResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        normalized_query = _normalize_query(query)

        statement = (
            select(
                Product.id,
                Product.code,
                Product.name,
                Product.quick_name,
                Product.display_order,
                ProductClass.id.label("product_class_id"),
                ProductClass.code.label("product_class_code"),
                ProductClass.name.label("product_class_name"),
            )
            .select_from(Product)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .where(
                Product.is_active.is_(True),
                ProductClass.is_active.is_(True),
            )
            .order_by(Product.display_order.asc(), Product.name.asc())
            .limit(MAX_PRODUCT_SEARCH_RESULTS)
        )
        if normalized_query is not None:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    Product.code.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.quick_name.ilike(pattern),
                    Product.search_aliases.ilike(pattern),
                    ProductClass.code.ilike(pattern),
                    ProductClass.name.ilike(pattern),
                )
            )

        records = session.execute(statement).mappings().all()
        return CorrectionsProductsResponse(
            workstation_code=workstation_code,
            query=_normalize_optional_string(query),
            products=[
                CorrectionProductOptionView(
                    id=record["id"],
                    code=record["code"],
                    name=record["name"],
                    quick_name=record["quick_name"],
                    product_class_id=record["product_class_id"],
                    product_class_code=record["product_class_code"],
                    product_class_name=record["product_class_name"],
                    display_order=record["display_order"],
                )
                for record in records
            ],
        )


class CorrectionCommandService:
    def __init__(
        self,
        settings: ApiSettings | None = None,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        query_service: CorrectionQueryService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._query_service = query_service or CorrectionQueryService(settings=self._settings)

    def commit_correction(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CorrectionCommitRequest,
        request_id: str | None,
    ) -> CorrectionDocumentView:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=command.workstation_code,
        )
        _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=command.workstation_code,
            context=context,
        )
        target_document = _get_target_document(
            session,
            target_document_id=command.target_document_id,
        )
        _ensure_branch_ownership(target_document=target_document, branch_id=context.branch_id)
        is_correctable, blocking_reason = _assess_correction_eligibility(
            session,
            target_document=target_document,
        )
        if not is_correctable:
            raise CorrectionIneligibleError(
                blocking_reason or "El documento seleccionado ya no se puede corregir."
            )

        reason = session.execute(
            select(CorrectionReason).where(
                CorrectionReason.code == command.reason_code,
                CorrectionReason.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if reason is None:
            raise CorrectionReasonNotFoundError(
                "Selecciona un motivo de correccion valido."
            )

        corrected_destination_branch: Branch | None = None
        if reason.code == CORRECTION_REASON_WRONG_DESTINATION:
            if target_document.document_type != OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT:
                raise CorrectionValidationError(
                    "Solo puedes corregir el destino en envios a sucursal."
                )
            if command.corrected_destination_branch_id is None:
                raise CorrectionValidationError(
                    "Selecciona una sucursal destino para continuar."
                )
            if len(command.lines) > 0:
                raise CorrectionValidationError(
                    "El motivo destino incorrecto no admite ajustes de lineas."
                )
            if command.corrected_destination_branch_id == target_document.destination_branch_id:
                raise CorrectionValidationError(
                    "Selecciona una sucursal distinta al destino actual."
                )
            if command.corrected_destination_branch_id == context.branch_id:
                raise CorrectionValidationError(
                    "La sucursal destino no puede ser la misma sucursal origen."
                )
            corrected_destination_branch = session.execute(
                select(Branch).where(
                    Branch.id == command.corrected_destination_branch_id,
                    Branch.is_active.is_(True),
                )
            ).scalar_one_or_none()
            if corrected_destination_branch is None:
                raise CorrectionValidationError(
                    "Selecciona una sucursal destino valida."
                )
            correction_type = CORRECTION_TYPE_DESTINATION_ADJUSTMENT
            resolved_lines: dict[uuid.UUID, dict[str, object]] = {}
        else:
            if command.corrected_destination_branch_id is not None:
                raise CorrectionValidationError(
                    "Este motivo no permite corregir el destino."
                )
            if len(command.lines) == 0:
                raise CorrectionValidationError(
                    "Agrega al menos una linea al borrador antes de confirmar."
                )
            resolved_lines = _resolve_commit_products(
                session,
                [
                    OperationCommitLineRequest(
                        product_id=line.product_id,
                        quantity=Decimal("1"),
                    )
                    for line in command.lines
                ],
            )
            correction_type = CORRECTION_TYPE_DELTA_ADJUSTMENT
        total_adjusted_quantity = _get_total_adjusted_quantity(command.lines)
        is_high_impact = (
            total_adjusted_quantity
            >= self._settings.correction_high_impact_quantity_threshold
        )
        if is_high_impact and not command.high_impact_acknowledged:
            raise CorrectionValidationError(
                "Confirma el ajuste de alto impacto antes de registrar."
            )
        committed_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        target_lines = (
            session.execute(
                select(OperationDocumentLine)
                .where(OperationDocumentLine.operation_document_id == target_document.id)
                .order_by(OperationDocumentLine.line_number.asc())
            )
            .scalars()
            .all()
        )
        target_line_matches = _index_target_lines_by_product(target_lines)
        target_lines_by_id = {line.id: line for line in target_lines}

        correction_document = CorrectionDocument(
            target_document_id=target_document.id,
            target_document_type=target_document.document_type,
            correction_type=correction_type,
            source_branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            created_by_user_id=current_user.id,
            reason_code=reason.code,
            corrected_destination_branch_id=(
                corrected_destination_branch.id
                if corrected_destination_branch is not None
                else None
            ),
            notes=command.notes,
            status=CORRECTION_STATUS_COMMITTED,
            committed_at_utc=committed_at,
        )

        try:
            session.add(correction_document)
            session.flush()
            correction_folio = _build_correction_document_folio(correction_document.id)
            outbox_lines: list[dict[str, str | None]] = []
            for line_number, line in enumerate(command.lines, start=1):
                resolved_line = resolved_lines[line.product_id]
                target_line_id = _resolve_target_line_id(
                    command_product_id=line.product_id,
                    requested_target_line_id=line.target_line_id,
                    target_line_matches=target_line_matches,
                    target_lines_by_id=target_lines_by_id,
                )
                session.add(
                    CorrectionDocumentLine(
                        correction_document_id=correction_document.id,
                        line_number=line_number,
                        target_line_id=target_line_id,
                        product_id=line.product_id,
                        product_code_snapshot=str(resolved_line["product_code"]),
                        product_name_snapshot=str(resolved_line["product_name"]),
                        product_class_id=resolved_line["product_class_id"],
                        product_class_code_snapshot=str(resolved_line["product_class_code"]),
                        product_class_name_snapshot=str(resolved_line["product_class_name"]),
                        delta_quantity=line.delta_quantity,
                        notes=line.notes,
                    )
                )
                outbox_lines.append(
                    {
                        "line_number": str(line_number),
                        "target_line_id": str(target_line_id)
                        if target_line_id is not None
                        else None,
                        "product_id": str(line.product_id),
                        "product_code_snapshot": str(resolved_line["product_code"]),
                        "product_name_snapshot": str(resolved_line["product_name"]),
                        "product_class_id": str(resolved_line["product_class_id"]),
                        "product_class_code_snapshot": str(resolved_line["product_class_code"]),
                        "product_class_name_snapshot": str(resolved_line["product_class_name"]),
                        "delta_quantity": str(line.delta_quantity),
                        "notes": line.notes,
                    }
                )

            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action="correction.committed",
                resource_type="correction_document",
                resource_id=str(correction_document.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "correction_document_id": str(correction_document.id),
                    "target_document_id": str(target_document.id),
                    "target_document_type": target_document.document_type,
                    "reason_code": reason.code,
                    "corrected_destination_branch_id": (
                        str(corrected_destination_branch.id)
                        if corrected_destination_branch is not None
                        else None
                    ),
                    "corrected_destination_branch_code": (
                        corrected_destination_branch.code
                        if corrected_destination_branch is not None
                        else None
                    ),
                    "folio": correction_folio,
                    "high_impact": is_high_impact,
                    "high_impact_acknowledged": command.high_impact_acknowledged,
                    "high_impact_threshold_quantity": str(
                        self._settings.correction_high_impact_quantity_threshold
                    ),
                    "status": correction_document.status,
                    "total_adjusted_quantity": str(total_adjusted_quantity),
                    "workstation_code": context.workstation_code,
                    "line_count": len(command.lines),
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type="correction",
                aggregate_id=str(correction_document.id),
                event_name=OUTBOX_EVENT_CORRECTION_COMMITTED_V1,
                payload={
                    "correction_document_id": str(correction_document.id),
                    "target_document_id": str(target_document.id),
                    "target_document_type": target_document.document_type,
                    "correction_type": correction_document.correction_type,
                    "status": correction_document.status,
                    "source_branch_id": str(context.branch_id),
                    "source_branch_code": context.branch_code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "created_by_user_id": str(current_user.id),
                    "created_by_user_email": current_user.email,
                    "reason_code": reason.code,
                    "corrected_destination_branch_id": (
                        str(corrected_destination_branch.id)
                        if corrected_destination_branch is not None
                        else None
                    ),
                    "corrected_destination_branch_code": (
                        corrected_destination_branch.code
                        if corrected_destination_branch is not None
                        else None
                    ),
                    "corrected_destination_branch_name": (
                        corrected_destination_branch.name
                        if corrected_destination_branch is not None
                        else None
                    ),
                    "folio": correction_folio,
                    "high_impact": is_high_impact,
                    "high_impact_acknowledged": command.high_impact_acknowledged,
                    "high_impact_threshold_quantity": str(
                        self._settings.correction_high_impact_quantity_threshold
                    ),
                    "notes": command.notes,
                    "committed_at_utc": committed_at.isoformat(),
                    "lines": outbox_lines,
                    "total_adjusted_quantity": str(total_adjusted_quantity),
                },
                headers={"request_id": resolved_request_id},
            )
            if is_high_impact:
                self._audit_recorder.record(
                    session,
                    actor_id=current_user.id,
                    action="correction.high_impact_alert_requested",
                    resource_type="correction_document",
                    resource_id=str(correction_document.id),
                    branch_id=context.branch_id,
                    request_id=resolved_request_id,
                    metadata={
                        "correction_document_id": str(correction_document.id),
                        "folio": correction_folio,
                        "notification_target": "backoffice",
                        "target_document_id": str(target_document.id),
                        "target_document_type": target_document.document_type,
                        "total_adjusted_quantity": str(total_adjusted_quantity),
                    },
                )
                self._outbox_writer.append(
                    session,
                    aggregate_type="correction",
                    aggregate_id=str(correction_document.id),
                    event_name=OUTBOX_EVENT_CORRECTION_HIGH_IMPACT_ALERT_V1,
                    payload={
                        "correction_document_id": str(correction_document.id),
                        "folio": correction_folio,
                        "notification_target": "backoffice",
                        "reason_code": reason.code,
                        "source_branch_code": context.branch_code,
                        "target_document_id": str(target_document.id),
                        "target_document_type": target_document.document_type,
                        "total_adjusted_quantity": str(total_adjusted_quantity),
                        "workstation_code": context.workstation_code,
                    },
                    headers={"request_id": resolved_request_id},
                )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise CorrectionValidationError(
                "No se pudo guardar la correccion por un conflicto de integridad. Intenta de nuevo."
            ) from error

        return _build_correction_document_view(session, correction_document=correction_document)


def _get_target_document(
    session: Session,
    *,
    target_document_id: uuid.UUID,
) -> OperationDocument:
    target_document = session.execute(
        select(OperationDocument).where(OperationDocument.id == target_document_id)
    ).scalar_one_or_none()
    if target_document is None:
        raise CorrectionNotFoundError("El documento original no existe.")
    if target_document.document_type not in VALID_CORRECTION_TARGET_DOCUMENT_TYPES:
        raise CorrectionValidationError(
            "Solo puedes corregir paso a mostrador, merma y envios a sucursal."
        )
    return target_document


def _ensure_branch_ownership(
    *,
    target_document: OperationDocument,
    branch_id: uuid.UUID,
) -> None:
    if target_document.source_branch_id != branch_id:
        raise CorrectionNotFoundError("El documento original no existe en la sucursal actual.")


def _assess_correction_eligibility(
    session: Session,
    *,
    target_document: OperationDocument,
) -> tuple[bool, str | None]:
    if target_document.document_type == OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER:
        if target_document.status != OPERATION_DOCUMENT_STATUS_COMMITTED:
            return (
                False,
                "Solo puedes corregir pasos a mostrador que ya fueron confirmados.",
            )
        return True, None

    if target_document.document_type == OPERATION_DOCUMENT_TYPE_WASTE_RECORD:
        if target_document.status != OPERATION_DOCUMENT_STATUS_COMMITTED:
            return (
                False,
                "Solo puedes corregir registros de merma que ya fueron confirmados.",
            )
        return True, None

    if target_document.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT:
        receipt_exists = session.execute(
            select(OperationDocument.id).where(
                OperationDocument.reference_document_id == target_document.id,
                OperationDocument.document_type == OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_RECEIPT,
            )
        ).scalar_one_or_none()
        if (
            target_document.status != OPERATION_DOCUMENT_STATUS_IN_TRANSIT
            or receipt_exists is not None
        ):
            return (
                False,
                (
                    "Este envio ya fue recibido en la sucursal destino y ya no se puede corregir."
                ),
            )
        return True, None

    return False, "El documento seleccionado no admite correcciones."


def _get_correction_document(
    session: Session,
    *,
    correction_id: uuid.UUID,
) -> CorrectionDocument:
    correction_document = session.execute(
        select(CorrectionDocument).where(CorrectionDocument.id == correction_id)
    ).scalar_one_or_none()
    if correction_document is None:
        raise CorrectionNotFoundError("La correccion solicitada no existe.")
    return correction_document


def _ensure_correction_branch_ownership(
    *,
    correction_document: CorrectionDocument,
    branch_id: uuid.UUID,
) -> None:
    if correction_document.source_branch_id != branch_id:
        raise CorrectionNotFoundError("La correccion solicitada no existe en la sucursal actual.")


def _build_correction_document_view(
    session: Session,
    *,
    correction_document: CorrectionDocument,
) -> CorrectionDocumentView:
    correction_document_id = correction_document.id
    source_branch = aliased(Branch)
    corrected_destination_branch = aliased(Branch)
    record = (
        session.execute(
            select(
                CorrectionDocument.id,
                CorrectionDocument.target_document_id,
                CorrectionDocument.target_document_type,
                CorrectionDocument.correction_type,
                CorrectionDocument.source_branch_id,
                source_branch.code.label("source_branch_code"),
                source_branch.name.label("source_branch_name"),
                CorrectionDocument.workstation_id,
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                CorrectionDocument.created_by_user_id,
                User.email.label("created_by_user_email"),
                User.full_name.label("created_by_user_full_name"),
                CorrectionDocument.reason_code,
                CorrectionReason.name.label("reason_name"),
                CorrectionDocument.corrected_destination_branch_id,
                corrected_destination_branch.code.label(
                    "corrected_destination_branch_code"
                ),
                corrected_destination_branch.name.label(
                    "corrected_destination_branch_name"
                ),
                CorrectionDocument.notes,
                CorrectionDocument.status,
                CorrectionDocument.created_at_utc,
                CorrectionDocument.committed_at_utc,
            )
            .select_from(CorrectionDocument)
            .join(source_branch, source_branch.id == CorrectionDocument.source_branch_id)
            .join(Workstation, Workstation.id == CorrectionDocument.workstation_id)
            .join(User, User.id == CorrectionDocument.created_by_user_id)
            .join(CorrectionReason, CorrectionReason.code == CorrectionDocument.reason_code)
            .outerjoin(
                corrected_destination_branch,
                corrected_destination_branch.id
                == CorrectionDocument.corrected_destination_branch_id,
            )
            .where(CorrectionDocument.id == correction_document_id)
        )
        .mappings()
        .one_or_none()
    )
    if record is None:
        raise CorrectionNotFoundError("La correccion solicitada no existe.")

    line_records = (
        session.execute(
            select(
                CorrectionDocumentLine.id,
                CorrectionDocumentLine.line_number,
                CorrectionDocumentLine.target_line_id,
                CorrectionDocumentLine.product_id,
                CorrectionDocumentLine.product_code_snapshot,
                CorrectionDocumentLine.product_name_snapshot,
                CorrectionDocumentLine.product_class_id,
                CorrectionDocumentLine.product_class_code_snapshot,
                CorrectionDocumentLine.product_class_name_snapshot,
                CorrectionDocumentLine.delta_quantity,
                CorrectionDocumentLine.unit_of_measure_code,
                CorrectionDocumentLine.notes,
            )
            .where(CorrectionDocumentLine.correction_document_id == correction_document_id)
            .order_by(CorrectionDocumentLine.line_number.asc())
        )
        .mappings()
        .all()
    )

    return CorrectionDocumentView(
        id=record["id"],
        folio=_build_correction_document_folio(record["id"]),
        target_document_id=record["target_document_id"],
        target_document_type=record["target_document_type"],
        correction_type=record["correction_type"],
        source_branch_id=record["source_branch_id"],
        source_branch_code=record["source_branch_code"],
        source_branch_name=record["source_branch_name"],
        workstation_id=record["workstation_id"],
        workstation_code=record["workstation_code"],
        workstation_name=record["workstation_name"],
        created_by_user_id=record["created_by_user_id"],
        created_by_user_email=record["created_by_user_email"],
        created_by_user_full_name=record["created_by_user_full_name"],
        reason_code=record["reason_code"],
        reason_name=record["reason_name"],
        corrected_destination_branch_id=record["corrected_destination_branch_id"],
        corrected_destination_branch_code=record["corrected_destination_branch_code"],
        corrected_destination_branch_name=record["corrected_destination_branch_name"],
        notes=record["notes"],
        status=record["status"],
        created_at_utc=record["created_at_utc"],
        committed_at_utc=record["committed_at_utc"],
        audit_summary=AuditVisibilityQueryService().build_summary(
            session,
            created_actor=build_audit_actor_snapshot(
                user_id=record["created_by_user_id"],
                full_name=record["created_by_user_full_name"],
                email=record["created_by_user_email"],
            ),
            created_at_utc=record["created_at_utc"],
            confirmed_at_utc=record["committed_at_utc"],
            acknowledgement_label="Validacion de alto impacto",
            reason_label=record["reason_name"],
            notes=record["notes"],
            notification_config=BackofficeNotificationConfig(
                aggregate_id=str(record["id"]),
                aggregate_type="correction",
                event_names=(OUTBOX_EVENT_CORRECTION_HIGH_IMPACT_ALERT_V1,),
                label="Alerta a backoffice",
            ),
        ),
        lines=[
            CorrectionDocumentLineView(
                id=line["id"],
                line_number=line["line_number"],
                target_line_id=line["target_line_id"],
                product_id=line["product_id"],
                product_code_snapshot=line["product_code_snapshot"],
                product_name_snapshot=line["product_name_snapshot"],
                product_class_id=line["product_class_id"],
                product_class_code_snapshot=line["product_class_code_snapshot"],
                product_class_name_snapshot=line["product_class_name_snapshot"],
                delta_quantity=line["delta_quantity"],
                unit_of_measure_code=line["unit_of_measure_code"],
                notes=line["notes"],
            )
            for line in line_records
        ],
    )


def _build_document_title(document_type: str, document_id: uuid.UUID) -> str:
    label_by_type = {
        OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER: "Paso a mostrador",
        OPERATION_DOCUMENT_TYPE_WASTE_RECORD: "Registro de merma",
        OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT: "Envio a sucursal",
    }
    label = label_by_type.get(document_type, document_type.replace("_", " ").title())
    return f"{label} {str(document_id)[:8]}"


def _build_target_document_folio(document_type: str, document_id: uuid.UUID) -> str:
    prefix = {
        OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER: "CTR",
        OPERATION_DOCUMENT_TYPE_WASTE_RECORD: "WST",
        OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT: "ENV",
    }.get(document_type, "DOC")
    return f"{prefix}-{str(document_id).split('-', maxsplit=1)[0].upper()}"


def _build_correction_document_folio(correction_document_id: uuid.UUID) -> str:
    return f"COR-{str(correction_document_id).split('-', maxsplit=1)[0].upper()}"


def _normalize_query(query: str | None) -> str | None:
    if query is None:
        return None
    normalized_query = query.strip()
    return normalized_query or None


def _parse_target_document_folio_query(
    query: str,
) -> tuple[str | None, str | None]:
    normalized_query = query.strip().upper()
    if "-" not in normalized_query:
        return None, None

    prefix, identifier = normalized_query.split("-", maxsplit=1)
    if not identifier:
        return None, None

    document_type = {
        "CTR": OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
        "WST": OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
        "ENV": OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
    }.get(prefix)
    if document_type is None:
        return None, None

    return document_type, identifier.lower()


def _get_total_adjusted_quantity(lines: Sequence[CorrectionCommitLineRequest]) -> Decimal:
    return sum((abs(line.delta_quantity) for line in lines), start=Decimal("0"))


def _validate_document_type(document_type: str | None) -> str | None:
    if document_type is None:
        return None
    normalized = document_type.strip()
    if normalized == "":
        return None
    if normalized not in VALID_CORRECTION_TARGET_DOCUMENT_TYPES:
        raise CorrectionValidationError(
            "Filtra solo por paso a mostrador, merma o envio a sucursal."
        )
    return normalized


def _validate_correction_history_scope(scope: str | None) -> str:
    normalized_scope = _normalize_query(scope)
    if normalized_scope is None:
        return OPERATION_HISTORY_SCOPE_CURRENT_SHIFT

    scope_code = normalized_scope.upper()
    if scope_code not in VALID_OPERATION_HISTORY_SCOPES:
        raise CorrectionValidationError("El alcance del historial no es valido.")
    return scope_code


def _validate_history_target_document_type(document_type: str | None) -> str | None:
    if document_type is None:
        return None
    normalized = document_type.strip()
    if normalized == "":
        return None
    if normalized not in VALID_CORRECTION_TARGET_DOCUMENT_TYPES:
        raise CorrectionValidationError("El tipo de documento del historial no es valido.")
    return normalized


def _apply_correction_history_scope_filters(
    statement: Select[tuple[object, ...]],
    *,
    normalized_scope: str,
    context: WorkstationContext,
    current_shift_opened_at: datetime,
) -> Select[tuple[object, ...]]:
    if normalized_scope == OPERATION_HISTORY_SCOPE_ALL:
        return statement

    if normalized_scope == OPERATION_HISTORY_SCOPE_CURRENT_SHIFT:
        return statement.where(CorrectionDocument.created_at_utc >= current_shift_opened_at)

    if normalized_scope == OPERATION_HISTORY_SCOPE_TODAY:
        local_now = datetime.now(tz=UTC).astimezone(ZoneInfo(context.branch_timezone))
        local_start = datetime.combine(
            local_now.date(),
            datetime.min.time(),
            tzinfo=ZoneInfo(context.branch_timezone),
        )
        local_end = local_start + timedelta(days=1)
        return statement.where(
            CorrectionDocument.created_at_utc >= local_start.astimezone(UTC),
            CorrectionDocument.created_at_utc < local_end.astimezone(UTC),
        )

    recent_cutoff = datetime.now(tz=UTC) - timedelta(days=30)
    return statement.where(CorrectionDocument.created_at_utc >= recent_cutoff)


def _build_history_document_type_label(document_type: str) -> str:
    return {
        OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER: "Paso a mostrador",
        OPERATION_DOCUMENT_TYPE_WASTE_RECORD: "Merma",
        OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT: "Envio a sucursal",
    }.get(document_type, document_type)


def _index_target_lines_by_product(
    target_lines: Sequence[OperationDocumentLine],
) -> dict[uuid.UUID, list[OperationDocumentLine]]:
    indexed: dict[uuid.UUID, list[OperationDocumentLine]] = {}
    for line in target_lines:
        indexed.setdefault(line.product_id, []).append(line)
    return indexed


def _resolve_target_line_id(
    *,
    command_product_id: uuid.UUID,
    requested_target_line_id: uuid.UUID | None,
    target_line_matches: dict[uuid.UUID, list[OperationDocumentLine]],
    target_lines_by_id: dict[uuid.UUID, OperationDocumentLine],
) -> uuid.UUID | None:
    if requested_target_line_id is not None:
        target_line = target_lines_by_id.get(requested_target_line_id)
        if target_line is None:
            raise CorrectionValidationError(
                "La linea original seleccionada ya no pertenece al documento."
            )
        if target_line.product_id != command_product_id:
            raise CorrectionValidationError(
                "La linea original no coincide con el producto seleccionado para la correccion."
            )
        return requested_target_line_id

    matched_target_lines = target_line_matches.get(command_product_id, [])
    return matched_target_lines[0].id if len(matched_target_lines) == 1 else None


def _get_branch_brand_key(branch_code: str) -> str:
    return BRANCH_BRAND_MAPPING.get(branch_code, "EL_MEJOR_PAN")


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _require_open_cash_session(
    session: Session,
    *,
    cash_session_query: CashSessionQueryService,
    current_user: AuthenticatedUser,
    workstation_code: str,
    context: WorkstationContext,
) -> CashSessionView:
    current_open_cash_session = cash_session_query.get_open_session_for_workstation_code(
        session,
        workstation_code=workstation_code,
    )
    if current_open_cash_session is None:
        raise CorrectionConflictError(
            "Necesitas una caja abierta en esta estacion para trabajar con correcciones."
        )
    if current_open_cash_session.user_id != current_user.id:
        raise CorrectionConflictError(
            "La caja abierta de esta estacion pertenece a otro cajero."
        )
    if (
        current_open_cash_session.branch_id != context.branch_id
        or current_open_cash_session.workstation_id != context.workstation_id
    ):
        raise CorrectionConflictError(
            "La caja abierta no coincide con el contexto actual de la estacion."
        )
    return current_open_cash_session
