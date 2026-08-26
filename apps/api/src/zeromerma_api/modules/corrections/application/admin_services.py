from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from typing import cast as type_cast

from sqlalchemy import Select, String, and_, case, cast, exists, func, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session, aliased

from zeromerma_api.modules.audit.application.visibility import (
    AuditVisibilityQueryService,
    BackofficeNotificationConfig,
    build_audit_actor_snapshot,
)
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.corrections.application.admin_schemas import (
    AdminCorrectionAffectedLineView,
    AdminCorrectionAvailableActionsView,
    AdminCorrectionDetailView,
    AdminCorrectionFilterOptionsView,
    AdminCorrectionListItemView,
    AdminCorrectionMetricsView,
    AdminCorrectionNetEffectView,
    AdminCorrectionOriginalDocumentView,
    AdminCorrectionOverviewView,
    AdminCorrectionReasonNotesView,
    AdminCorrectionRelatedDocumentView,
    AdminCorrectionsBackendContractView,
    AdminCorrectionsListResponse,
    AdminReturnCorrectionFilterOptionView,
)
from zeromerma_api.modules.corrections.domain.constants import (
    CORRECTION_STATUS_COMMITTED,
    CORRECTION_TYPE_DELTA_ADJUSTMENT,
    CORRECTION_TYPE_DESTINATION_ADJUSTMENT,
    OUTBOX_EVENT_CORRECTION_HIGH_IMPACT_ALERT_V1,
    VALID_CORRECTION_TARGET_DOCUMENT_TYPES,
)
from zeromerma_api.modules.corrections.domain.exceptions import (
    CorrectionNotFoundError,
    CorrectionValidationError,
)
from zeromerma_api.modules.corrections.infrastructure.models import (
    CorrectionDocument,
    CorrectionDocumentLine,
    CorrectionReason,
)
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.domain.constants import (
    OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT,
    OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER,
    OPERATION_DOCUMENT_TYPE_WASTE_RECORD,
)
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)

ADMIN_CORRECTION_PAGE_SIZE_MAX = 100
ZERO_QUANTITY = Decimal("0.000")
ZERO_MONEY = Decimal("0.00")
NET_EFFECT_POSITIVE = "POSITIVE"
NET_EFFECT_NEGATIVE = "NEGATIVE"
NET_EFFECT_NEUTRAL = "NEUTRAL"


class AdminCorrectionsService:
    def __init__(self, audit_visibility: AuditVisibilityQueryService | None = None) -> None:
        self._audit_visibility = audit_visibility or AuditVisibilityQueryService()

    def list_corrections(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        correction_type: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        net_effect: str | None,
        operator_id: uuid.UUID | None,
        page: int,
        page_size: int,
        reason_code: str | None,
        search: str | None,
        status_filter: str | None,
        target_document_type: str | None,
    ) -> AdminCorrectionsListResponse:
        resolved_page = max(page, 1)
        resolved_page_size = min(max(page_size, 1), ADMIN_CORRECTION_PAGE_SIZE_MAX)
        conditions = _build_correction_conditions(
            branch_id=branch_id,
            correction_type=correction_type,
            date_from=date_from,
            date_to=date_to,
            net_effect=net_effect,
            operator_id=operator_id,
            reason_code=reason_code,
            search=search,
            status_filter=status_filter,
            target_document_type=target_document_type,
        )
        base_statement = _build_correction_base_statement(conditions)
        total = int(
            session.execute(
                select(func.count()).select_from(base_statement.order_by(None).subquery())
            ).scalar_one()
        )
        rows = session.execute(
            base_statement.order_by(
                CorrectionDocument.created_at_utc.desc(),
                CorrectionDocument.id.desc(),
            )
            .limit(resolved_page_size)
            .offset((resolved_page - 1) * resolved_page_size)
        ).mappings().all()
        return AdminCorrectionsListResponse(
            backend_contract=_backend_contract(),
            filter_options=_build_filter_options(session),
            is_backend_connected=True,
            items=[_map_correction_list_item(row) for row in rows],
            metrics=_build_metrics(session, conditions),
            page=resolved_page,
            page_size=resolved_page_size,
            total=total,
        )

    def get_correction_detail(
        self,
        session: Session,
        *,
        correction_id: uuid.UUID,
    ) -> AdminCorrectionDetailView:
        _get_correction_record(session, correction_id=correction_id)
        source_branch = aliased(Branch)
        target_branch = aliased(Branch)
        target_workstation = aliased(Workstation)
        target_user = aliased(User)
        row = session.execute(
            select(
                CorrectionDocument.id,
                CorrectionDocument.target_document_id,
                CorrectionDocument.target_document_type,
                CorrectionDocument.correction_type,
                CorrectionDocument.source_branch_id,
                source_branch.name.label("source_branch_name"),
                CorrectionDocument.workstation_id,
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                CorrectionDocument.created_by_user_id,
                User.email.label("operator_email"),
                User.full_name.label("operator_name"),
                CorrectionDocument.reason_code,
                CorrectionReason.name.label("reason_name"),
                CorrectionDocument.notes,
                CorrectionDocument.status,
                CorrectionDocument.created_at_utc,
                CorrectionDocument.committed_at_utc,
                OperationDocument.status.label("target_status"),
                OperationDocument.created_at_utc.label("target_created_at"),
                OperationDocument.committed_at_utc.label("target_committed_at"),
                OperationDocument.created_by_user_id.label("target_created_by_user_id"),
                target_user.full_name.label("target_operator_name"),
                target_branch.name.label("target_branch_name"),
                target_workstation.name.label("target_workstation_name"),
            )
            .select_from(CorrectionDocument)
            .join(source_branch, source_branch.id == CorrectionDocument.source_branch_id)
            .join(Workstation, Workstation.id == CorrectionDocument.workstation_id)
            .join(User, User.id == CorrectionDocument.created_by_user_id)
            .join(CorrectionReason, CorrectionReason.code == CorrectionDocument.reason_code)
            .join(OperationDocument, OperationDocument.id == CorrectionDocument.target_document_id)
            .join(target_branch, target_branch.id == OperationDocument.source_branch_id)
            .join(target_workstation, target_workstation.id == OperationDocument.workstation_id)
            .join(target_user, target_user.id == OperationDocument.created_by_user_id)
            .where(CorrectionDocument.id == correction_id)
        ).mappings().one()

        line_rows = session.execute(
            select(
                CorrectionDocumentLine.id,
                CorrectionDocumentLine.target_line_id,
                CorrectionDocumentLine.product_code_snapshot,
                CorrectionDocumentLine.product_name_snapshot,
                CorrectionDocumentLine.product_class_code_snapshot,
                CorrectionDocumentLine.product_class_name_snapshot,
                CorrectionDocumentLine.delta_quantity,
                CorrectionDocumentLine.unit_of_measure_code,
                CorrectionDocumentLine.notes,
                OperationDocumentLine.quantity.label("original_quantity"),
            )
            .select_from(CorrectionDocumentLine)
            .outerjoin(
                OperationDocumentLine,
                OperationDocumentLine.id == CorrectionDocumentLine.target_line_id,
            )
            .where(CorrectionDocumentLine.correction_document_id == correction_id)
            .order_by(CorrectionDocumentLine.line_number.asc())
        ).mappings().all()
        total_units_affected = _sum_abs(line["delta_quantity"] for line in line_rows)
        net_effect_quantity = sum(
            (type_cast(Decimal, line["delta_quantity"]) for line in line_rows),
            ZERO_QUANTITY,
        )
        audit_summary = self._audit_visibility.build_summary(
            session,
            created_actor=build_audit_actor_snapshot(
                user_id=type_cast(uuid.UUID, row["created_by_user_id"]),
                full_name=type_cast(str, row["operator_name"]),
                email=type_cast(str | None, row["operator_email"]),
            ),
            created_at_utc=type_cast(datetime, row["created_at_utc"]),
            confirmed_at_utc=type_cast(datetime | None, row["committed_at_utc"]),
            acknowledgement_label="Validacion de alto impacto",
            reason_label=type_cast(str, row["reason_name"]),
            notes=type_cast(str | None, row["notes"]),
            notification_config=BackofficeNotificationConfig(
                aggregate_id=str(correction_id),
                aggregate_type="correction",
                event_names=(OUTBOX_EVENT_CORRECTION_HIGH_IMPACT_ALERT_V1,),
                label="Alerta a backoffice",
            ),
        )
        net_effect_label = _net_effect_label(net_effect_quantity)

        return AdminCorrectionDetailView(
            affected_lines=[
                _map_affected_line(line)
                for line in line_rows
            ],
            available_actions=AdminCorrectionAvailableActionsView(
                creation_note=(
                    "Las correcciones nuevas requieren caja/workstation operativo y se registran desde el flujo de ajustes."
                )
            ),
            backend_contract=_backend_contract(),
            net_effect=AdminCorrectionNetEffectView(
                total_units_affected=total_units_affected,
                total_amount_affected=None,
                inventory_effect="Ajuste operativo de productos",
                cash_effect="Sin impacto directo de caja",
                net_effect=net_effect_label,
            ),
            original_document=AdminCorrectionOriginalDocumentView(
                id=type_cast(uuid.UUID, row["target_document_id"]),
                folio=_build_target_document_folio(
                    type_cast(str, row["target_document_type"]),
                    type_cast(uuid.UUID, row["target_document_id"]),
                ),
                document_type=type_cast(str, row["target_document_type"]),
                status=type_cast(str, row["target_status"]),
                occurred_at=type_cast(datetime | None, row["target_committed_at"])
                or type_cast(datetime, row["target_created_at"]),
                operator_name=type_cast(str, row["target_operator_name"]),
                branch_name=type_cast(str, row["target_branch_name"]),
                workstation_name=type_cast(str, row["target_workstation_name"]),
                route_hint=_route_hint_for_document_type(type_cast(str, row["target_document_type"])),
            ),
            overview=AdminCorrectionOverviewView(
                id=type_cast(uuid.UUID, row["id"]),
                folio=_build_correction_folio(type_cast(uuid.UUID, row["id"])),
                status=type_cast(str, row["status"]),
                created_at=type_cast(datetime, row["created_at_utc"]),
                committed_at=type_cast(datetime | None, row["committed_at_utc"]),
                operator_id=type_cast(uuid.UUID, row["created_by_user_id"]),
                operator_name=type_cast(str, row["operator_name"]),
                branch_id=type_cast(uuid.UUID, row["source_branch_id"]),
                branch_name=type_cast(str, row["source_branch_name"]),
                workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
                workstation_name=type_cast(str, row["workstation_name"]),
                workstation_code=type_cast(str, row["workstation_code"]),
                correction_type=type_cast(str, row["correction_type"]),
                original_document_id=type_cast(uuid.UUID, row["target_document_id"]),
                original_document_folio=_build_target_document_folio(
                    type_cast(str, row["target_document_type"]),
                    type_cast(uuid.UUID, row["target_document_id"]),
                ),
                original_document_type=type_cast(str, row["target_document_type"]),
                net_effect=net_effect_label,
                net_effect_quantity=net_effect_quantity,
                total_units_affected=total_units_affected,
            ),
            reason_notes=AdminCorrectionReasonNotesView(
                reason_code=type_cast(str, row["reason_code"]),
                reason_name=type_cast(str, row["reason_name"]),
                notes=type_cast(str | None, row["notes"]),
                audit_summary=audit_summary,
            ),
            related_documents=[
                AdminCorrectionRelatedDocumentView(
                    id=str(row["target_document_id"]),
                    document_type=type_cast(str, row["target_document_type"]),
                    folio=_build_target_document_folio(
                        type_cast(str, row["target_document_type"]),
                        type_cast(uuid.UUID, row["target_document_id"]),
                    ),
                    status=type_cast(str, row["target_status"]),
                    occurred_at=type_cast(datetime | None, row["target_committed_at"])
                    or type_cast(datetime, row["target_created_at"]),
                    route_hint=_route_hint_for_document_type(type_cast(str, row["target_document_type"])),
                )
            ],
        )


def _backend_contract() -> AdminCorrectionsBackendContractView:
    return AdminCorrectionsBackendContractView(
        create_endpoint=None,
        detail_endpoint="GET /v1/admin/returns-corrections/corrections/{correction_id}",
        list_endpoint="GET /v1/admin/returns-corrections/corrections",
        print_endpoint=None,
    )


def _build_correction_base_statement(conditions: list[object]) -> Select[tuple[object, ...]]:
    line_stats = (
        select(
            CorrectionDocumentLine.correction_document_id.label("correction_document_id"),
            func.count(CorrectionDocumentLine.id).label("line_count"),
            func.coalesce(func.sum(CorrectionDocumentLine.delta_quantity), ZERO_QUANTITY).label(
                "net_effect_quantity"
            ),
            func.coalesce(func.sum(func.abs(CorrectionDocumentLine.delta_quantity)), ZERO_QUANTITY).label(
                "total_units_affected"
            ),
        )
        .group_by(CorrectionDocumentLine.correction_document_id)
        .subquery()
    )
    statement = (
        select(
            CorrectionDocument.id,
            CorrectionDocument.target_document_id,
            CorrectionDocument.target_document_type,
            CorrectionDocument.correction_type,
            CorrectionDocument.source_branch_id.label("branch_id"),
            Branch.name.label("branch_name"),
            CorrectionDocument.workstation_id,
            Workstation.code.label("workstation_code"),
            Workstation.name.label("workstation_name"),
            CorrectionDocument.created_by_user_id.label("operator_id"),
            User.full_name.label("operator_name"),
            CorrectionDocument.reason_code,
            CorrectionReason.name.label("reason_name"),
            CorrectionDocument.status,
            CorrectionDocument.created_at_utc,
            CorrectionDocument.committed_at_utc,
            func.coalesce(line_stats.c.line_count, 0).label("line_count"),
            func.coalesce(line_stats.c.net_effect_quantity, ZERO_QUANTITY).label(
                "net_effect_quantity"
            ),
            func.coalesce(line_stats.c.total_units_affected, ZERO_QUANTITY).label(
                "total_units_affected"
            ),
        )
        .select_from(CorrectionDocument)
        .join(Branch, Branch.id == CorrectionDocument.source_branch_id)
        .join(Workstation, Workstation.id == CorrectionDocument.workstation_id)
        .join(User, User.id == CorrectionDocument.created_by_user_id)
        .join(CorrectionReason, CorrectionReason.code == CorrectionDocument.reason_code)
        .outerjoin(line_stats, line_stats.c.correction_document_id == CorrectionDocument.id)
    )
    if conditions:
        statement = statement.where(and_(*conditions))
    return statement


def _build_correction_conditions(
    *,
    branch_id: uuid.UUID | None,
    correction_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    net_effect: str | None,
    operator_id: uuid.UUID | None,
    reason_code: str | None,
    search: str | None,
    status_filter: str | None,
    target_document_type: str | None,
) -> list[object]:
    conditions: list[object] = []
    if branch_id is not None:
        conditions.append(CorrectionDocument.source_branch_id == branch_id)
    if operator_id is not None:
        conditions.append(CorrectionDocument.created_by_user_id == operator_id)
    if date_from is not None:
        conditions.append(CorrectionDocument.created_at_utc >= date_from)
    if date_to is not None:
        conditions.append(CorrectionDocument.created_at_utc <= date_to)
    normalized_correction_type = _normalize_optional(correction_type)
    if normalized_correction_type is not None:
        if normalized_correction_type not in {
            CORRECTION_TYPE_DELTA_ADJUSTMENT,
            CORRECTION_TYPE_DESTINATION_ADJUSTMENT,
        }:
            raise CorrectionValidationError("El tipo de correccion solicitado no es valido.")
        conditions.append(CorrectionDocument.correction_type == normalized_correction_type)
    normalized_reason_code = _normalize_optional(reason_code)
    if normalized_reason_code is not None:
        conditions.append(CorrectionDocument.reason_code == normalized_reason_code)
    normalized_status = _normalize_optional(status_filter)
    if normalized_status is not None:
        if normalized_status != CORRECTION_STATUS_COMMITTED:
            raise CorrectionValidationError("El estado solicitado no es valido para correcciones.")
        conditions.append(CorrectionDocument.status == normalized_status)
    normalized_target_type = _normalize_optional(target_document_type)
    if normalized_target_type is not None:
        if normalized_target_type not in VALID_CORRECTION_TARGET_DOCUMENT_TYPES:
            raise CorrectionValidationError("El tipo de documento original no es valido.")
        conditions.append(CorrectionDocument.target_document_type == normalized_target_type)
    normalized_search = _normalize_search(search)
    if normalized_search:
        correction_id_query = normalized_search.removeprefix("cor-")
        target_id_query = normalized_search
        if "-" in normalized_search:
            _prefix, target_id_query = normalized_search.split("-", maxsplit=1)
        conditions.append(
            or_(
                func.lower(cast(CorrectionDocument.id, String)).like(f"{correction_id_query}%"),
                func.lower(cast(CorrectionDocument.id, String)).contains(correction_id_query),
                func.lower(cast(CorrectionDocument.target_document_id, String)).like(
                    f"{target_id_query}%"
                ),
                func.lower(cast(CorrectionDocument.target_document_id, String)).contains(
                    target_id_query
                ),
                func.lower(CorrectionReason.name).contains(normalized_search),
                func.lower(User.full_name).contains(normalized_search),
                func.lower(Branch.name).contains(normalized_search),
            )
        )
    normalized_net_effect = _normalize_optional(net_effect)
    if normalized_net_effect is not None:
        line_effect_subquery = (
            select(func.coalesce(func.sum(CorrectionDocumentLine.delta_quantity), ZERO_QUANTITY))
            .where(CorrectionDocumentLine.correction_document_id == CorrectionDocument.id)
            .scalar_subquery()
        )
        if normalized_net_effect == NET_EFFECT_POSITIVE:
            conditions.append(line_effect_subquery > ZERO_QUANTITY)
        elif normalized_net_effect == NET_EFFECT_NEGATIVE:
            conditions.append(line_effect_subquery < ZERO_QUANTITY)
        elif normalized_net_effect == NET_EFFECT_NEUTRAL:
            conditions.append(line_effect_subquery == ZERO_QUANTITY)
        else:
            raise CorrectionValidationError("El efecto neto solicitado no es valido.")
    return conditions


def _build_filter_options(session: Session) -> AdminCorrectionFilterOptionsView:
    branch_rows = session.execute(select(Branch.id, Branch.name).order_by(Branch.name.asc())).mappings()
    operator_rows = session.execute(
        select(User.id, User.full_name)
        .where(exists(select(CorrectionDocument.id).where(CorrectionDocument.created_by_user_id == User.id)))
        .order_by(User.full_name.asc())
    ).mappings()
    reason_rows = session.execute(
        select(CorrectionReason.code, CorrectionReason.name).order_by(CorrectionReason.name.asc())
    ).mappings()
    return AdminCorrectionFilterOptionsView(
        branches=[
            AdminReturnCorrectionFilterOptionView(id=str(row["id"]), label=type_cast(str, row["name"]))
            for row in branch_rows
        ],
        correction_types=[
            AdminReturnCorrectionFilterOptionView(
                id=CORRECTION_TYPE_DELTA_ADJUSTMENT,
                label="Ajuste de cantidad",
            ),
            AdminReturnCorrectionFilterOptionView(
                id=CORRECTION_TYPE_DESTINATION_ADJUSTMENT,
                label="Ajuste de destino",
            ),
        ],
        operators=[
            AdminReturnCorrectionFilterOptionView(id=str(row["id"]), label=type_cast(str, row["full_name"]))
            for row in operator_rows
        ],
        reasons=[
            AdminReturnCorrectionFilterOptionView(id=type_cast(str, row["code"]), label=type_cast(str, row["name"]))
            for row in reason_rows
        ],
        statuses=[
            AdminReturnCorrectionFilterOptionView(id=CORRECTION_STATUS_COMMITTED, label="Confirmada")
        ],
        target_document_types=[
            AdminReturnCorrectionFilterOptionView(id=value, label=_document_type_label(value))
            for value in sorted(VALID_CORRECTION_TARGET_DOCUMENT_TYPES)
        ],
    )


def _build_metrics(session: Session, conditions: list[object]) -> AdminCorrectionMetricsView:
    correction_ids_statement = _build_correction_base_statement(conditions).with_only_columns(
        CorrectionDocument.id
    ).order_by(None)
    metric_row = session.execute(
        select(
            func.count(func.distinct(CorrectionDocument.id)).label("corrections_count"),
            func.coalesce(func.sum(func.abs(CorrectionDocumentLine.delta_quantity)), ZERO_QUANTITY).label(
                "total_units_affected"
            ),
            func.count(
                case((CorrectionDocumentLine.delta_quantity > 0, 1))
            ).label("positive_effect_count"),
            func.count(
                case((CorrectionDocumentLine.delta_quantity < 0, 1))
            ).label("negative_effect_count"),
        )
        .select_from(CorrectionDocument)
        .outerjoin(
            CorrectionDocumentLine,
            CorrectionDocumentLine.correction_document_id == CorrectionDocument.id,
        )
        .where(CorrectionDocument.id.in_(correction_ids_statement))
    ).mappings().one()
    return AdminCorrectionMetricsView(
        corrections_count=int(metric_row["corrections_count"] or 0),
        total_units_affected=type_cast(Decimal, metric_row["total_units_affected"]),
        positive_effect_count=int(metric_row["positive_effect_count"] or 0),
        negative_effect_count=int(metric_row["negative_effect_count"] or 0),
        pending_review_count=0,
    )


def _map_correction_list_item(row: RowMapping) -> AdminCorrectionListItemView:
    correction_id = type_cast(uuid.UUID, row["id"])
    target_document_id = type_cast(uuid.UUID, row["target_document_id"])
    target_document_type = type_cast(str, row["target_document_type"])
    net_quantity = type_cast(Decimal, row["net_effect_quantity"])
    return AdminCorrectionListItemView(
        id=correction_id,
        folio=_build_correction_folio(correction_id),
        original_document_id=target_document_id,
        original_document_folio=_build_target_document_folio(target_document_type, target_document_id),
        original_document_type=target_document_type,
        correction_type=type_cast(str, row["correction_type"]),
        created_at=type_cast(datetime, row["created_at_utc"]),
        branch_id=type_cast(uuid.UUID, row["branch_id"]),
        branch_name=type_cast(str, row["branch_name"]),
        workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
        workstation_name=type_cast(str, row["workstation_name"]),
        workstation_code=type_cast(str, row["workstation_code"]),
        operator_id=type_cast(uuid.UUID, row["operator_id"]),
        operator_name=type_cast(str, row["operator_name"]),
        reason_code=type_cast(str, row["reason_code"]),
        reason_name=type_cast(str, row["reason_name"]),
        line_count=int(type_cast(int, row["line_count"])),
        net_effect_quantity=net_quantity,
        total_units_affected=type_cast(Decimal, row["total_units_affected"]),
        net_effect=_net_effect_label(net_quantity),
        status=type_cast(str, row["status"]),
        warning_state=None,
    )


def _map_affected_line(row: RowMapping) -> AdminCorrectionAffectedLineView:
    original_quantity = type_cast(Decimal | None, row["original_quantity"])
    delta_quantity = type_cast(Decimal, row["delta_quantity"])
    corrected_quantity = original_quantity + delta_quantity if original_quantity is not None else None
    return AdminCorrectionAffectedLineView(
        id=type_cast(uuid.UUID, row["id"]),
        target_line_id=type_cast(uuid.UUID | None, row["target_line_id"]),
        product_name=type_cast(str, row["product_name_snapshot"]),
        product_code=type_cast(str, row["product_code_snapshot"]),
        product_class_name=type_cast(str, row["product_class_name_snapshot"]),
        product_class_code=type_cast(str, row["product_class_code_snapshot"]),
        original_quantity=original_quantity,
        corrected_quantity=corrected_quantity,
        difference_quantity=delta_quantity,
        unit_of_measure_code=type_cast(str, row["unit_of_measure_code"]),
        notes=type_cast(str | None, row["notes"]),
    )


def _get_correction_record(session: Session, *, correction_id: uuid.UUID) -> CorrectionDocument:
    correction = session.get(CorrectionDocument, correction_id)
    if correction is None:
        raise CorrectionNotFoundError("La correccion solicitada no existe.")
    return correction


def _sum_abs(values: Iterable[object]) -> Decimal:
    return sum((abs(type_cast(Decimal, value)) for value in values), ZERO_QUANTITY)


def _net_effect_label(value: Decimal) -> str:
    if value > ZERO_QUANTITY:
        return NET_EFFECT_POSITIVE
    if value < ZERO_QUANTITY:
        return NET_EFFECT_NEGATIVE
    return NET_EFFECT_NEUTRAL


def _build_correction_folio(correction_id: uuid.UUID) -> str:
    return f"COR-{str(correction_id).split('-', maxsplit=1)[0].upper()}"


def _build_target_document_folio(document_type: str, document_id: uuid.UUID) -> str:
    prefix = {
        OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER: "CTR",
        OPERATION_DOCUMENT_TYPE_WASTE_RECORD: "WST",
        OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT: "ENV",
    }.get(document_type, "DOC")
    return f"{prefix}-{str(document_id).split('-', maxsplit=1)[0].upper()}"


def _document_type_label(document_type: str) -> str:
    return {
        OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER: "Paso a mostrador",
        OPERATION_DOCUMENT_TYPE_WASTE_RECORD: "Merma",
        OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT: "Envio a sucursal",
    }.get(document_type, document_type)


def _route_hint_for_document_type(document_type: str) -> str | None:
    return {
        OPERATION_DOCUMENT_TYPE_COUNTER_TRANSFER: "/admin/transferencias",
        OPERATION_DOCUMENT_TYPE_WASTE_RECORD: "/admin/merma",
        OPERATION_DOCUMENT_TYPE_BRANCH_TRANSFER_SHIPMENT: "/admin/transferencias",
    }.get(document_type)


def _normalize_search(value: str | None) -> str | None:
    normalized = _normalize_optional(value)
    return normalized.casefold() if normalized else None


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized.upper() if normalized else None
