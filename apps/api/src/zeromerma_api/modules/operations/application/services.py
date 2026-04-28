from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import cast
from zoneinfo import ZoneInfo

from sqlalchemy import Select, func, or_, select
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
from zeromerma_api.modules.branches.application.schemas import WorkstationSummary
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.application.services import CashSessionQueryService
from zeromerma_api.modules.catalog.domain.exceptions import (
    ProductClassNotFoundError,
    ProductNotFoundError,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.application.schemas import (
    CounterTransferCommitRequest,
    OperationBranchSummary,
    OperationCommitLineRequest,
    OperationDocumentLineView,
    OperationDocumentView,
    OperationHistoryFilterOptionView,
    OperationHistoryListItemView,
    OperationHistoryResponse,
    OperationHistoryScopeView,
    OperationsBootstrapResponse,
    OperationsCatalogClassView,
    OperationsCatalogProductView,
    OperationsCatalogResponse,
    OperationsClassProductsResponse,
    TransferDestinationBranchView,
    WasteCommitRequest,
    WasteControlsView,
    WasteReasonView,
)
from zeromerma_api.modules.operations.domain.constants import (
    BRANCH_BRAND_MAPPING,
    OPERATION_BUCKET_BACKROOM,
    OPERATION_BUCKET_COUNTER,
    OPERATION_BUCKET_WASTE,
    OPERATION_DOCUMENT_STATUS_COMMITTED,
    OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
    OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
    OPERATION_HISTORY_SCOPE_CURRENT_SHIFT,
    OPERATION_HISTORY_SCOPE_RECENT,
    OPERATION_HISTORY_SCOPE_TODAY,
    OUTBOX_EVENT_COUNTER_TRANSFER_COMMITTED_V1,
    OUTBOX_EVENT_WASTE_RECORD_COMMITTED_V1,
    OUTBOX_EVENT_WASTE_RECORD_HIGH_IMPACT_ALERT_V1,
    VALID_OPERATION_DOCUMENT_TYPES,
    VALID_OPERATION_HISTORY_SCOPES,
    VALID_OPERATION_MODULES,
    WASTE_REASON_CODES_REQUIRING_NOTE,
    WASTE_STOCK_VALIDATED_SOURCE_BUCKET_CODES,
)
from zeromerma_api.modules.operations.domain.exceptions import (
    OperationDocumentNotFoundError,
    OperationValidationError,
    WasteReasonNotFoundError,
)
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
    WasteReason,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter

MAX_OPERATION_HISTORY_ITEMS = 50


class OperationsQueryService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        settings: ApiSettings | None = None,
        audit_visibility: AuditVisibilityQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._settings = settings or get_settings()
        self._audit_visibility = audit_visibility or AuditVisibilityQueryService()

    def get_bootstrap(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> OperationsBootstrapResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        local_timestamp = datetime.now(tz=UTC).astimezone(ZoneInfo(context.branch_timezone))

        waste_reason_records = session.execute(
            select(WasteReason.code, WasteReason.name, WasteReason.display_order)
            .where(WasteReason.is_active.is_(True))
            .order_by(WasteReason.display_order.asc(), WasteReason.name.asc())
        ).mappings().all()
        destination_branch_records = session.execute(
            select(Branch.id, Branch.code, Branch.name, Branch.timezone)
            .where(Branch.is_active.is_(True), Branch.id != context.branch_id)
            .order_by(Branch.name.asc())
        ).mappings().all()
        branch_brand_key = _get_branch_brand_key(context.branch_code)

        return OperationsBootstrapResponse(
            user=current_user,
            branch=OperationBranchSummary(
                id=context.branch_id,
                code=context.branch_code,
                name=context.branch_name,
                timezone=context.branch_timezone,
                is_active=context.branch_is_active,
                brand_key=branch_brand_key,
            ),
            workstation=WorkstationSummary(
                id=context.workstation_id,
                code=context.workstation_code,
                name=context.workstation_name,
                is_active=context.workstation_is_active,
            ),
            local_timestamp=local_timestamp,
            branch_brand_key=branch_brand_key,
            waste_reasons=[
                WasteReasonView(
                    code=record["code"],
                    name=record["name"],
                    display_order=record["display_order"],
                    requires_note=record["code"] in WASTE_REASON_CODES_REQUIRING_NOTE,
                )
                for record in waste_reason_records
            ],
            waste_controls=WasteControlsView(
                attachment_evidence_supported=False,
                high_impact_quantity_threshold=self._settings.waste_high_impact_quantity_threshold,
                high_impact_requires_acknowledgement=True,
                high_impact_requires_note=True,
                stock_validated_source_bucket_codes=sorted(
                    WASTE_STOCK_VALIDATED_SOURCE_BUCKET_CODES
                ),
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

    def get_catalog(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        module: str,
        query: str | None,
    ) -> OperationsCatalogResponse:
        self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        validated_module = _validate_module(module)
        normalized_query = _normalize_query(query)
        product_count_subquery = (
            select(func.count(Product.id))
            .where(
                Product.product_class_id == ProductClass.id,
                Product.is_active.is_(True),
                Product.is_sellable.is_(True),
            )
            .correlate(ProductClass)
            .scalar_subquery()
        )

        statement = (
            select(
                ProductClass.id,
                ProductClass.code,
                ProductClass.name,
                ProductClass.quick_name,
                ProductClass.display_order,
                product_count_subquery.label("product_count"),
            )
            .where(
                ProductClass.is_active.is_(True),
                ProductClass.is_sellable.is_(True),
                product_count_subquery > 0,
            )
            .order_by(ProductClass.display_order.asc(), ProductClass.name.asc())
        )
        if normalized_query is not None:
            pattern = f"%{normalized_query}%"
            matching_products = (
                select(Product.id)
                .where(
                    Product.product_class_id == ProductClass.id,
                    Product.is_active.is_(True),
                    Product.is_sellable.is_(True),
                    or_(
                        Product.code.ilike(pattern),
                        Product.name.ilike(pattern),
                        Product.quick_name.ilike(pattern),
                        Product.search_aliases.ilike(pattern),
                    ),
                )
                .exists()
            )
            statement = statement.where(
                or_(
                    ProductClass.code.ilike(pattern),
                    ProductClass.name.ilike(pattern),
                    ProductClass.quick_name.ilike(pattern),
                    ProductClass.search_aliases.ilike(pattern),
                    matching_products,
                )
            )

        records = session.execute(statement).mappings().all()
        return OperationsCatalogResponse(
            workstation_code=workstation_code,
            module=validated_module,
            query=normalized_query,
            classes=[
                OperationsCatalogClassView(
                    id=record["id"],
                    code=record["code"],
                    name=record["name"],
                    quick_name=record["quick_name"],
                    display_order=record["display_order"],
                    product_count=int(record["product_count"]),
                )
                for record in records
            ],
        )

    def get_class_products(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        class_id: uuid.UUID,
        module: str,
        query: str | None,
    ) -> OperationsClassProductsResponse:
        self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        validated_module = _validate_module(module)
        normalized_query = _normalize_query(query)
        product_class = session.execute(
            select(ProductClass).where(
                ProductClass.id == class_id,
                ProductClass.is_active.is_(True),
                ProductClass.is_sellable.is_(True),
            )
        ).scalar_one_or_none()
        if product_class is None:
            raise ProductClassNotFoundError("Product class was not found.")

        statement = (
            select(
                Product.id,
                Product.code,
                Product.name,
                Product.quick_name,
                Product.display_order,
                Product.unit_price,
                Product.currency_code,
            )
            .where(
                Product.product_class_id == class_id,
                Product.is_active.is_(True),
                Product.is_sellable.is_(True),
            )
            .order_by(Product.display_order.asc(), Product.name.asc())
        )
        if normalized_query is not None:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    Product.code.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.quick_name.ilike(pattern),
                    Product.search_aliases.ilike(pattern),
                )
            )

        product_records = session.execute(statement).mappings().all()
        return OperationsClassProductsResponse(
            class_id=product_class.id,
            class_code=product_class.code,
            class_name=product_class.name,
            module=validated_module,
            query=normalized_query,
            products=[
                OperationsCatalogProductView(
                    id=record["id"],
                    code=record["code"],
                    name=record["name"],
                    quick_name=record["quick_name"],
                    display_order=record["display_order"],
                    unit_price=record["unit_price"],
                    currency_code=record["currency_code"],
                )
                for record in product_records
            ],
        )

    def list_operation_history(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        document_type: str,
        scope: str | None,
        created_by_user_id: uuid.UUID | None,
        reason_code: str | None,
        product_id: uuid.UUID | None,
        source_bucket_code: str | None,
        destination_bucket_code: str | None,
    ) -> OperationHistoryResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        normalized_document_type = _validate_document_type(document_type)
        normalized_scope = _validate_history_scope(scope)

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
                OperationDocument.document_type,
                OperationDocument.status,
                OperationDocument.source_branch_id,
                Branch.code.label("source_branch_code"),
                Branch.name.label("source_branch_name"),
                OperationDocument.destination_branch_id,
                OperationDocument.source_bucket_code,
                OperationDocument.destination_bucket_code,
                OperationDocument.workstation_id,
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                OperationDocument.created_by_user_id,
                User.full_name.label("created_by_user_full_name"),
                OperationDocument.reason_code,
                WasteReason.name.label("reason_name"),
                OperationDocument.created_at_utc,
                OperationDocument.committed_at_utc,
                func.coalesce(line_stats_subquery.c.line_count, 0).label("line_count"),
                func.coalesce(line_stats_subquery.c.total_quantity, 0).label("total_quantity"),
            )
            .select_from(OperationDocument)
            .join(Branch, Branch.id == OperationDocument.source_branch_id)
            .join(Workstation, Workstation.id == OperationDocument.workstation_id)
            .join(User, User.id == OperationDocument.created_by_user_id)
            .outerjoin(WasteReason, WasteReason.code == OperationDocument.reason_code)
            .outerjoin(
                line_stats_subquery,
                line_stats_subquery.c.document_id == OperationDocument.id,
            )
            .where(
                OperationDocument.document_type == normalized_document_type,
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

        available_user_rows = session.execute(
            base_statement.with_only_columns(
                OperationDocument.created_by_user_id,
                User.full_name.label("created_by_user_full_name"),
            )
            .distinct()
            .order_by(User.full_name.asc())
        ).mappings().all()
        available_source_bucket_rows = session.execute(
            base_statement.with_only_columns(OperationDocument.source_bucket_code)
            .distinct()
            .order_by(OperationDocument.source_bucket_code.asc())
        ).scalars().all()
        available_destination_bucket_rows = session.execute(
            base_statement.with_only_columns(OperationDocument.destination_bucket_code)
            .distinct()
            .order_by(OperationDocument.destination_bucket_code.asc())
        ).scalars().all()
        available_reason_rows = session.execute(
            base_statement.with_only_columns(
                OperationDocument.reason_code,
                WasteReason.name.label("reason_name"),
            )
            .where(OperationDocument.reason_code.is_not(None))
            .distinct()
            .order_by(WasteReason.name.asc(), OperationDocument.reason_code.asc())
        ).mappings().all()
        available_product_rows = session.execute(
            apply_operation_history_scope_filters(
                cast(
                    Select[tuple[object, ...]],
                    select(
                        OperationDocumentLine.product_id,
                        Product.code.label("product_code"),
                        Product.name.label("product_name"),
                    )
                    .select_from(OperationDocumentLine)
                    .join(
                        OperationDocument,
                        OperationDocument.id == OperationDocumentLine.operation_document_id,
                    )
                    .join(Product, Product.id == OperationDocumentLine.product_id)
                    .where(
                        OperationDocument.document_type == normalized_document_type,
                        OperationDocument.source_branch_id == context.branch_id,
                        OperationDocument.workstation_id == context.workstation_id,
                    ),
                ),
                normalized_scope=normalized_scope,
                context=context,
                current_shift_opened_at=get_current_shift_opened_at_for_history_scope(
                    session,
                    cash_session_query=self._cash_session_query,
                    normalized_scope=normalized_scope,
                    workstation_code=workstation_code,
                ),
            )
            .distinct()
            .order_by(Product.name.asc(), Product.code.asc())
        ).mappings().all()

        filtered_statement = base_statement
        if created_by_user_id is not None:
            filtered_statement = filtered_statement.where(
                OperationDocument.created_by_user_id == created_by_user_id
            )
        if reason_code is not None:
            filtered_statement = filtered_statement.where(
                OperationDocument.reason_code == reason_code
            )
        if product_id is not None:
            filtered_statement = filtered_statement.where(
                OperationDocument.id.in_(
                    select(OperationDocumentLine.operation_document_id).where(
                        OperationDocumentLine.product_id == product_id
                    )
                )
            )
        if source_bucket_code is not None:
            filtered_statement = filtered_statement.where(
                OperationDocument.source_bucket_code == source_bucket_code
            )
        if destination_bucket_code is not None:
            filtered_statement = filtered_statement.where(
                OperationDocument.destination_bucket_code == destination_bucket_code
            )

        destination_branch = aliased(Branch)
        record_rows = session.execute(
            filtered_statement.outerjoin(
                destination_branch,
                destination_branch.id == OperationDocument.destination_branch_id,
            )
            .add_columns(
                destination_branch.code.label("destination_branch_code"),
                destination_branch.name.label("destination_branch_name"),
            )
            .order_by(
                OperationDocument.committed_at_utc.desc().nullslast(),
                OperationDocument.created_at_utc.desc(),
            )
            .limit(MAX_OPERATION_HISTORY_ITEMS)
        ).mappings().all()

        return OperationHistoryResponse(
            workstation_code=workstation_code,
            document_type=normalized_document_type,
            scope=normalized_scope,
            created_by_user_id=str(created_by_user_id) if created_by_user_id is not None else None,
            reason_code=reason_code,
            product_id=str(product_id) if product_id is not None else None,
            source_bucket_code=source_bucket_code,
            destination_bucket_code=destination_bucket_code,
            available_scopes=[
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
            available_reasons=[
                OperationHistoryFilterOptionView(
                    value=row["reason_code"],
                    label=row["reason_name"] or row["reason_code"],
                )
                for row in available_reason_rows
                if row["reason_code"] is not None
            ],
            available_products=[
                OperationHistoryFilterOptionView(
                    value=str(row["product_id"]),
                    label=f"{row['product_code']} · {row['product_name']}",
                )
                for row in available_product_rows
            ],
            available_source_buckets=[
                OperationHistoryFilterOptionView(
                    value=value,
                    label=value,
                )
                for value in available_source_bucket_rows
                if value is not None
            ],
            available_destination_buckets=[
                OperationHistoryFilterOptionView(
                    value=value,
                    label=value,
                )
                for value in available_destination_bucket_rows
                if value is not None
            ],
            records=[
                OperationHistoryListItemView(
                    id=row["id"],
                    folio=_build_operation_document_folio(
                        row["document_type"],
                        row["id"],
                    ),
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
                    reason_code=row["reason_code"],
                    reason_name=row["reason_name"],
                    line_count=int(row["line_count"]),
                    total_quantity=row["total_quantity"],
                    created_at_utc=row["created_at_utc"],
                    committed_at_utc=row["committed_at_utc"],
                )
                for row in record_rows
            ],
        )

    def get_operation_document_for_workstation(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        document_id: uuid.UUID,
    ) -> OperationDocumentView:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        document = self.get_operation_document(session, document_id=document_id)
        if document.workstation_id != context.workstation_id:
            raise OperationDocumentNotFoundError("Operation document was not found.")
        if document.source_branch_id != context.branch_id and (
            document.destination_branch_id != context.branch_id
        ):
            raise OperationDocumentNotFoundError("Operation document was not found.")
        return document

    def get_operation_document(
        self,
        session: Session,
        *,
        document_id: uuid.UUID,
    ) -> OperationDocumentView:
        source_branch = aliased(Branch)
        destination_branch = aliased(Branch)
        record = session.execute(
            select(
                OperationDocument.id,
                OperationDocument.document_type,
                OperationDocument.status,
                OperationDocument.source_branch_id,
                source_branch.code.label("source_branch_code"),
                source_branch.name.label("source_branch_name"),
                OperationDocument.destination_branch_id,
                destination_branch.code.label("destination_branch_code"),
                destination_branch.name.label("destination_branch_name"),
                OperationDocument.source_bucket_code,
                OperationDocument.destination_bucket_code,
                OperationDocument.workstation_id,
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                OperationDocument.created_by_user_id,
                User.email.label("created_by_user_email"),
                User.full_name.label("created_by_user_full_name"),
                OperationDocument.reason_code,
                WasteReason.name.label("reason_name"),
                OperationDocument.notes,
                OperationDocument.reference_document_id,
                OperationDocument.created_at_utc,
                OperationDocument.committed_at_utc,
            )
            .select_from(OperationDocument)
            .join(source_branch, source_branch.id == OperationDocument.source_branch_id)
            .outerjoin(
                destination_branch,
                destination_branch.id == OperationDocument.destination_branch_id,
            )
            .join(Workstation, Workstation.id == OperationDocument.workstation_id)
            .join(User, User.id == OperationDocument.created_by_user_id)
            .outerjoin(WasteReason, WasteReason.code == OperationDocument.reason_code)
            .where(OperationDocument.id == document_id)
        ).mappings().one_or_none()
        if record is None:
            raise OperationDocumentNotFoundError("Operation document was not found.")

        line_records = session.execute(
            select(
                OperationDocumentLine.id,
                OperationDocumentLine.line_number,
                OperationDocumentLine.product_id,
                OperationDocumentLine.product_code_snapshot,
                OperationDocumentLine.product_name_snapshot,
                OperationDocumentLine.product_class_id,
                OperationDocumentLine.product_class_code_snapshot,
                OperationDocumentLine.product_class_name_snapshot,
                OperationDocumentLine.quantity,
                OperationDocumentLine.expected_quantity,
                OperationDocumentLine.received_quantity,
                OperationDocumentLine.unit_of_measure_code,
                OperationDocumentLine.variance_reason,
                OperationDocumentLine.notes,
            )
            .where(OperationDocumentLine.operation_document_id == document_id)
            .order_by(OperationDocumentLine.line_number.asc())
        ).mappings().all()

        return OperationDocumentView(
            id=record["id"],
            folio=_build_operation_document_folio(record["document_type"], record["id"]),
            document_type=record["document_type"],
            status=record["status"],
            source_branch_id=record["source_branch_id"],
            source_branch_code=record["source_branch_code"],
            source_branch_name=record["source_branch_name"],
            destination_branch_id=record["destination_branch_id"],
            destination_branch_code=record["destination_branch_code"],
            destination_branch_name=record["destination_branch_name"],
            source_bucket_code=record["source_bucket_code"],
            destination_bucket_code=record["destination_bucket_code"],
            workstation_id=record["workstation_id"],
            workstation_code=record["workstation_code"],
            workstation_name=record["workstation_name"],
            created_by_user_id=record["created_by_user_id"],
            created_by_user_email=record["created_by_user_email"],
            created_by_user_full_name=record["created_by_user_full_name"],
            reason_code=record["reason_code"],
            reason_name=record["reason_name"],
            notes=record["notes"],
            reference_document_id=record["reference_document_id"],
            created_at_utc=record["created_at_utc"],
            committed_at_utc=record["committed_at_utc"],
            audit_summary=self._audit_visibility.build_summary(
                session,
                created_actor=build_audit_actor_snapshot(
                    user_id=record["created_by_user_id"],
                    full_name=record["created_by_user_full_name"],
                    email=record["created_by_user_email"],
                ),
                created_at_utc=record["created_at_utc"],
                confirmed_at_utc=record["committed_at_utc"],
                acknowledgement_label=(
                    "Validacion de alto impacto"
                    if record["document_type"] == OPERATION_DOCUMENT_TYPE_WASTE_RECORD
                    else None
                ),
                reason_label=record["reason_name"] or record["reason_code"],
                notes=record["notes"],
                notification_config=(
                    BackofficeNotificationConfig(
                        aggregate_id=str(record["id"]),
                        aggregate_type="operation_document",
                        event_names=(OUTBOX_EVENT_WASTE_RECORD_HIGH_IMPACT_ALERT_V1,),
                        label="Alerta a backoffice",
                    )
                    if record["document_type"] == OPERATION_DOCUMENT_TYPE_WASTE_RECORD
                    else None
                ),
            ),
            lines=[
                OperationDocumentLineView(
                    id=line["id"],
                    line_number=line["line_number"],
                    product_id=line["product_id"],
                    product_code_snapshot=line["product_code_snapshot"],
                    product_name_snapshot=line["product_name_snapshot"],
                    product_class_id=line["product_class_id"],
                    product_class_code_snapshot=line["product_class_code_snapshot"],
                    product_class_name_snapshot=line["product_class_name_snapshot"],
                    quantity=line["quantity"],
                    expected_quantity=line["expected_quantity"],
                    received_quantity=line["received_quantity"],
                    unit_of_measure_code=line["unit_of_measure_code"],
                    variance_reason=line["variance_reason"],
                    notes=line["notes"],
                )
                for line in line_records
            ],
        )


class OperationsCommandService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        query_service: OperationsQueryService | None = None,
        settings: ApiSettings | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._query_service = query_service or OperationsQueryService()
        self._settings = settings or get_settings()

    def commit_counter_transfer(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CounterTransferCommitRequest,
        request_id: str | None,
    ) -> OperationDocumentView:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=command.workstation_code,
        )
        resolved_lines = _resolve_commit_products(session, command.lines)
        committed_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        document = OperationDocument(
            document_type=OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
            status=OPERATION_DOCUMENT_STATUS_COMMITTED,
            source_branch_id=context.branch_id,
            destination_branch_id=None,
            source_bucket_code=OPERATION_BUCKET_BACKROOM,
            destination_bucket_code=OPERATION_BUCKET_COUNTER,
            workstation_id=context.workstation_id,
            created_by_user_id=current_user.id,
            notes=command.notes,
            committed_at_utc=committed_at,
        )

        try:
            session.add(document)
            session.flush()
            _append_operation_lines(
                session,
                document_id=document.id,
                lines=command.lines,
                resolved_lines=resolved_lines,
            )
            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action="counter_transfer.committed",
                resource_type="operation_document",
                resource_id=str(document.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "document_type": document.document_type,
                    "status": document.status,
                    "source_branch_code": context.branch_code,
                    "source_bucket_code": OPERATION_BUCKET_BACKROOM,
                    "destination_bucket_code": OPERATION_BUCKET_COUNTER,
                    "workstation_code": context.workstation_code,
                    "line_count": len(command.lines),
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type="operation_document",
                aggregate_id=str(document.id),
                event_name=OUTBOX_EVENT_COUNTER_TRANSFER_COMMITTED_V1,
                payload={
                    "document_id": str(document.id),
                    "document_type": document.document_type,
                    "status": document.status,
                    "source_branch_id": str(context.branch_id),
                    "source_branch_code": context.branch_code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "created_by_user_id": str(current_user.id),
                    "created_by_user_email": current_user.email,
                    "notes": command.notes,
                    "committed_at_utc": committed_at.isoformat(),
                    "lines": _build_outbox_lines(command.lines, resolved_lines),
                },
                headers={"request_id": resolved_request_id},
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise OperationValidationError(
                "Counter transfer invariants were violated by a concurrent request."
            ) from error

        return self._query_service.get_operation_document(session, document_id=document.id)

    def commit_waste_record(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: WasteCommitRequest,
        request_id: str | None,
    ) -> OperationDocumentView:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=command.workstation_code,
        )
        if command.source_bucket_code not in {OPERATION_BUCKET_BACKROOM, OPERATION_BUCKET_COUNTER}:
            raise OperationValidationError("Waste source bucket must be BACKROOM or COUNTER.")

        waste_reason = session.execute(
            select(WasteReason).where(
                WasteReason.code == command.reason_code,
                WasteReason.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if waste_reason is None:
            raise WasteReasonNotFoundError(
                f"Waste reason {command.reason_code} is not available."
            )

        resolved_lines = _resolve_commit_products(session, command.lines)
        total_quantity = _sum_operation_commit_quantities(command.lines)
        is_high_impact = total_quantity > self._settings.waste_high_impact_quantity_threshold
        notes_required = (
            waste_reason.code in WASTE_REASON_CODES_REQUIRING_NOTE or is_high_impact
        )
        if notes_required and not _has_meaningful_text(command.notes):
            raise OperationValidationError(
                "Operational notes are required for this waste record."
            )
        if is_high_impact and not command.high_impact_acknowledged:
            raise OperationValidationError(
                "High-impact waste must be acknowledged before commit."
            )
        committed_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        document = OperationDocument(
            document_type=OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
            status=OPERATION_DOCUMENT_STATUS_COMMITTED,
            source_branch_id=context.branch_id,
            destination_branch_id=None,
            source_bucket_code=command.source_bucket_code,
            destination_bucket_code=OPERATION_BUCKET_WASTE,
            workstation_id=context.workstation_id,
            created_by_user_id=current_user.id,
            reason_code=waste_reason.code,
            notes=command.notes,
            committed_at_utc=committed_at,
        )

        try:
            session.add(document)
            session.flush()
            _append_operation_lines(
                session,
                document_id=document.id,
                lines=command.lines,
                resolved_lines=resolved_lines,
            )
            document_folio = _build_operation_document_folio(document.document_type, document.id)
            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action="waste_record.committed",
                resource_type="operation_document",
                resource_id=str(document.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "document_type": document.document_type,
                    "status": document.status,
                    "source_branch_code": context.branch_code,
                    "source_bucket_code": command.source_bucket_code,
                    "destination_bucket_code": OPERATION_BUCKET_WASTE,
                    "workstation_code": context.workstation_code,
                    "reason_code": waste_reason.code,
                    "line_count": len(command.lines),
                    "notes_required": notes_required,
                    "high_impact": is_high_impact,
                    "high_impact_threshold_quantity": str(
                        self._settings.waste_high_impact_quantity_threshold
                    ),
                    "high_impact_acknowledged": command.high_impact_acknowledged,
                    "total_quantity": str(total_quantity),
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type="operation_document",
                aggregate_id=str(document.id),
                event_name=OUTBOX_EVENT_WASTE_RECORD_COMMITTED_V1,
                payload={
                    "document_id": str(document.id),
                    "document_type": document.document_type,
                    "status": document.status,
                    "source_branch_id": str(context.branch_id),
                    "source_branch_code": context.branch_code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "created_by_user_id": str(current_user.id),
                    "created_by_user_email": current_user.email,
                    "reason_code": waste_reason.code,
                    "high_impact": is_high_impact,
                    "high_impact_threshold_quantity": str(
                        self._settings.waste_high_impact_quantity_threshold
                    ),
                    "high_impact_acknowledged": command.high_impact_acknowledged,
                    "notes": command.notes,
                    "committed_at_utc": committed_at.isoformat(),
                    "total_quantity": str(total_quantity),
                    "lines": _build_outbox_lines(command.lines, resolved_lines),
                },
                headers={"request_id": resolved_request_id},
            )
            if is_high_impact:
                self._audit_recorder.record(
                    session,
                    actor_id=current_user.id,
                    action="waste_record.high_impact_alert_requested",
                    resource_type="operation_document",
                    resource_id=str(document.id),
                    branch_id=context.branch_id,
                    request_id=resolved_request_id,
                    metadata={
                        "document_type": document.document_type,
                        "folio": document_folio,
                        "reason_code": waste_reason.code,
                        "source_bucket_code": command.source_bucket_code,
                        "notification_target": "backoffice",
                        "threshold_quantity": str(
                            self._settings.waste_high_impact_quantity_threshold
                        ),
                        "total_quantity": str(total_quantity),
                    },
                )
                self._outbox_writer.append(
                    session,
                    aggregate_type="operation_document",
                    aggregate_id=str(document.id),
                    event_name=OUTBOX_EVENT_WASTE_RECORD_HIGH_IMPACT_ALERT_V1,
                    payload={
                        "document_id": str(document.id),
                        "folio": document_folio,
                        "document_type": document.document_type,
                        "status": document.status,
                        "source_branch_id": str(context.branch_id),
                        "source_branch_code": context.branch_code,
                        "workstation_id": str(context.workstation_id),
                        "workstation_code": context.workstation_code,
                        "created_by_user_id": str(current_user.id),
                        "created_by_user_email": current_user.email,
                        "reason_code": waste_reason.code,
                        "source_bucket_code": command.source_bucket_code,
                        "notification_target": "backoffice",
                        "notes": command.notes,
                        "threshold_quantity": str(
                            self._settings.waste_high_impact_quantity_threshold
                        ),
                        "total_quantity": str(total_quantity),
                        "committed_at_utc": committed_at.isoformat(),
                        "lines": _build_outbox_lines(command.lines, resolved_lines),
                    },
                    headers={"request_id": resolved_request_id},
                )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise OperationValidationError(
                "Waste record invariants were violated by a concurrent request."
            ) from error

        return self._query_service.get_operation_document(session, document_id=document.id)


def _append_operation_lines(
    session: Session,
    *,
    document_id: uuid.UUID,
    lines: list[OperationCommitLineRequest],
    resolved_lines: dict[uuid.UUID, dict[str, object]],
) -> None:
    for line_number, line in enumerate(lines, start=1):
        resolved_line = resolved_lines[line.product_id]
        session.add(
            OperationDocumentLine(
                operation_document_id=document_id,
                line_number=line_number,
                product_id=line.product_id,
                product_code_snapshot=str(resolved_line["product_code"]),
                product_name_snapshot=str(resolved_line["product_name"]),
                product_class_id=resolved_line["product_class_id"],
                product_class_code_snapshot=str(resolved_line["product_class_code"]),
                product_class_name_snapshot=str(resolved_line["product_class_name"]),
                quantity=line.quantity,
                expected_quantity=None,
                received_quantity=None,
                notes=line.notes,
            )
        )


def _build_outbox_lines(
    lines: list[OperationCommitLineRequest],
    resolved_lines: dict[uuid.UUID, dict[str, object]],
) -> list[dict[str, str | None]]:
    payload_lines: list[dict[str, str | None]] = []
    for line_number, line in enumerate(lines, start=1):
        resolved_line = resolved_lines[line.product_id]
        payload_lines.append(
            {
                "line_number": str(line_number),
                "product_id": str(line.product_id),
                "product_code_snapshot": str(resolved_line["product_code"]),
                "product_name_snapshot": str(resolved_line["product_name"]),
                "product_class_id": str(resolved_line["product_class_id"]),
                "product_class_code_snapshot": str(resolved_line["product_class_code"]),
                "product_class_name_snapshot": str(resolved_line["product_class_name"]),
                "quantity": str(line.quantity),
                "notes": line.notes,
            }
        )
    return payload_lines


def _sum_operation_commit_quantities(lines: list[OperationCommitLineRequest]) -> Decimal:
    return sum((line.quantity for line in lines), start=Decimal("0"))


def _has_meaningful_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _resolve_commit_products(
    session: Session,
    lines: list[OperationCommitLineRequest],
) -> dict[uuid.UUID, dict[str, object]]:
    if len(lines) == 0:
        raise OperationValidationError("Operation document must contain at least one line.")

    product_ids = {line.product_id for line in lines}
    records = session.execute(
        select(
            Product.id,
            Product.code.label("product_code"),
            Product.name.label("product_name"),
            Product.product_class_id,
            ProductClass.code.label("product_class_code"),
            ProductClass.name.label("product_class_name"),
        )
        .select_from(Product)
        .join(ProductClass, ProductClass.id == Product.product_class_id)
        .where(
            Product.id.in_(product_ids),
            Product.is_active.is_(True),
            Product.is_sellable.is_(True),
            ProductClass.is_active.is_(True),
            ProductClass.is_sellable.is_(True),
        )
    ).mappings().all()
    resolved = {record["id"]: dict(record) for record in records}
    for product_id in product_ids:
        if product_id not in resolved:
            raise ProductNotFoundError(f"Product {product_id} was not found.")
    return resolved


def _normalize_query(query: str | None) -> str | None:
    if query is None:
        return None
    stripped_query = query.strip()
    if stripped_query == "":
        return None
    return stripped_query


def _validate_module(module: str) -> str:
    normalized_module = module.strip()
    if normalized_module not in VALID_OPERATION_MODULES:
        raise OperationValidationError(
            "Module must be one of COUNTER_TRANSFER, WASTE_RECORD, "
            "BRANCH_TRANSFER_SHIPMENT, or BRANCH_TRANSFER_RECEIPT."
        )
    return normalized_module


def _validate_document_type(document_type: str) -> str:
    normalized_document_type = document_type.strip()
    if normalized_document_type not in VALID_OPERATION_DOCUMENT_TYPES:
        raise OperationValidationError("Document type is not valid for operations history.")
    return normalized_document_type


def _validate_history_scope(scope: str | None) -> str:
    normalized_scope = _normalize_query(scope)
    if normalized_scope is None:
        return OPERATION_HISTORY_SCOPE_CURRENT_SHIFT
    scope_code = normalized_scope.upper()
    if scope_code not in VALID_OPERATION_HISTORY_SCOPES:
        raise OperationValidationError("History scope is not valid for operations.")
    return scope_code


def get_current_shift_opened_at_for_history_scope(
    session: Session,
    *,
    cash_session_query: CashSessionQueryService,
    normalized_scope: str,
    workstation_code: str,
) -> datetime | None:
    if normalized_scope != OPERATION_HISTORY_SCOPE_CURRENT_SHIFT:
        return None
    current_open_session = cash_session_query.get_open_session_for_workstation_code(
        session,
        workstation_code=workstation_code,
    )
    if current_open_session is None:
        raise OperationValidationError(
            "An open cash session is required to query operations for the current shift."
        )
    return current_open_session.opened_at


def apply_operation_history_scope_filters(
    statement: Select[tuple[object, ...]],
    *,
    normalized_scope: str,
    context: WorkstationContext,
    current_shift_opened_at: datetime | None,
) -> Select[tuple[object, ...]]:
    if normalized_scope == OPERATION_HISTORY_SCOPE_CURRENT_SHIFT:
        assert current_shift_opened_at is not None
        return statement.where(OperationDocument.created_at_utc >= current_shift_opened_at)

    if normalized_scope == OPERATION_HISTORY_SCOPE_TODAY:
        branch_timezone = ZoneInfo(context.branch_timezone)
        local_now = datetime.now(tz=UTC).astimezone(branch_timezone)
        local_start = datetime.combine(local_now.date(), time.min, tzinfo=branch_timezone)
        local_end = local_start + timedelta(days=1)
        return statement.where(
            OperationDocument.created_at_utc >= local_start.astimezone(UTC),
            OperationDocument.created_at_utc < local_end.astimezone(UTC),
        )

    recent_cutoff = datetime.now(tz=UTC) - timedelta(days=30)
    return statement.where(OperationDocument.created_at_utc >= recent_cutoff)


def _build_operation_document_folio(document_type: str, document_id: uuid.UUID) -> str:
    prefix = {
        "COUNTER_TRANSFER": "CTR",
        "WASTE_RECORD": "WST",
        "BRANCH_TRANSFER_SHIPMENT": "ENV",
        "BRANCH_TRANSFER_RECEIPT": "REC",
        "CLOSE_COUNTER_ADJUSTMENT": "CCA",
        "CLOSE_WASTE_ADJUSTMENT": "CWA",
    }.get(document_type, "DOC")
    return f"{prefix}-{str(document_id).split('-', maxsplit=1)[0].upper()}"


def _get_branch_brand_key(branch_code: str) -> str | None:
    return BRANCH_BRAND_MAPPING.get(branch_code)
