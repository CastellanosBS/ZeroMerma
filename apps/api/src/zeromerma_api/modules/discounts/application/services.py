from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
from zeromerma_api.modules.discounts.application.schemas import (
    CreateOperationalDiscountRequest,
    DiscountControlsView,
    DiscountsBootstrapResponse,
    DiscountsListResponse,
    OperationalDiscountCategoryView,
    OperationalDiscountDetailResponse,
    OperationalDiscountFilterOptionView,
    OperationalDiscountListItemView,
    OperationalDiscountMethodView,
    OperationalDiscountScopeView,
)
from zeromerma_api.modules.discounts.domain.constants import (
    AUDIT_ACTION_OPERATIONAL_DISCOUNT_COMMITTED,
    AUDIT_ACTION_OPERATIONAL_DISCOUNT_HIGH_VALUE_ALERT_REQUESTED,
    DISCOUNT_LIST_SCOPE_CURRENT_SHIFT,
    DISCOUNT_LIST_SCOPE_RECENT,
    DISCOUNT_LIST_SCOPE_TODAY,
    DISCOUNT_STATUS_COMMITTED,
    OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
    OUTBOX_EVENT_OPERATIONAL_DISCOUNT_COMMITTED_V1,
    OUTBOX_EVENT_OPERATIONAL_DISCOUNT_HIGH_VALUE_ALERT_V1,
    PAYMENT_METHOD_CARD,
    PAYMENT_METHOD_CASH,
    PAYMENT_METHOD_MIXED,
    SUPPORTED_OPERATIONAL_DISCOUNT_METHOD_CODES,
    VALID_OPERATIONAL_DISCOUNT_LIST_SCOPES,
    VALID_OPERATIONAL_DISCOUNT_METHOD_CODES,
)
from zeromerma_api.modules.discounts.domain.exceptions import (
    OperationalDiscountConflictError,
    OperationalDiscountNotFoundError,
    OperationalDiscountValidationError,
)
from zeromerma_api.modules.discounts.infrastructure.models import (
    OperationalDiscount,
    OperationalDiscountCategory,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.domain.constants import BRANCH_BRAND_MAPPING
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.sales.domain.constants import (
    CASH_MOVEMENT_DIRECTION_IN,
    CASH_MOVEMENT_TYPE_OPERATIONAL_DISCOUNT,
)
from zeromerma_api.modules.sales.infrastructure.models import CashMovement

MAX_DISCOUNTS_PER_LIST = 80
MONEY_QUANTIZER = Decimal("0.01")
ZERO_MONEY = Decimal("0.00")


class DiscountsQueryService:
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
    ) -> DiscountsBootstrapResponse:
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
        categories = session.execute(
            select(OperationalDiscountCategory)
            .where(OperationalDiscountCategory.is_active.is_(True))
            .order_by(
                OperationalDiscountCategory.display_order.asc(),
                OperationalDiscountCategory.name.asc(),
            )
        ).scalars()

        return DiscountsBootstrapResponse(
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
            discount_registration_allowed=(
                current_open_cash_session is not None
                and current_open_cash_session.user_id == current_user.id
            ),
            default_scope=DISCOUNT_LIST_SCOPE_CURRENT_SHIFT,
            available_scopes=[
                OperationalDiscountScopeView(
                    code=DISCOUNT_LIST_SCOPE_CURRENT_SHIFT,
                    label="Turno actual",
                ),
                OperationalDiscountScopeView(code=DISCOUNT_LIST_SCOPE_TODAY, label="Hoy"),
                OperationalDiscountScopeView(code=DISCOUNT_LIST_SCOPE_RECENT, label="Recientes"),
            ],
            active_discount_methods=_get_discount_method_views(),
            active_categories=[
                OperationalDiscountCategoryView(
                    code=category.code,
                    name=category.name,
                    display_order=category.display_order,
                )
                for category in categories
            ],
            discount_controls=DiscountControlsView(
                high_value_amount_threshold=self._settings.discount_high_value_amount_threshold,
                high_value_requires_acknowledgement=True,
            ),
        )

    def list_discounts(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        scope: str | None,
        created_by_user_id: uuid.UUID | None,
        query: str | None,
        category_filter: str | None,
        payment_method_filter: str | None,
    ) -> DiscountsListResponse:
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
        normalized_scope = _validate_discount_list_scope(scope)
        normalized_query = _normalize_query(query)
        normalized_category = _validate_category_filter(session, category_filter)
        normalized_payment_method = _validate_payment_method_filter(payment_method_filter)

        base_statement = (
            select(
                OperationalDiscount.id,
                OperationalDiscount.status,
                OperationalDiscount.created_by_user_id,
                OperationalDiscount.subject_name,
                OperationalDiscount.concept,
                OperationalDiscount.category_code,
                OperationalDiscountCategory.name.label("category_name"),
                OperationalDiscount.payment_method_code,
                OperationalDiscount.total_amount,
                OperationalDiscount.cash_amount,
                OperationalDiscount.non_cash_amount,
                OperationalDiscount.currency_code,
                OperationalDiscount.created_at_utc,
                User.full_name.label("operator_full_name"),
            )
            .select_from(OperationalDiscount)
            .join(User, User.id == OperationalDiscount.created_by_user_id)
            .outerjoin(
                OperationalDiscountCategory,
                OperationalDiscountCategory.code == OperationalDiscount.category_code,
            )
            .where(
                OperationalDiscount.branch_id == context.branch_id,
                OperationalDiscount.workstation_id == context.workstation_id,
            )
        )
        base_statement = _apply_discount_list_scope_filters(
            base_statement,
            normalized_scope=normalized_scope,
            context=context,
            current_cash_session_id=current_open_cash_session.id,
        )
        if normalized_category is not None:
            base_statement = base_statement.where(
                OperationalDiscount.category_code == normalized_category
            )
        if normalized_payment_method is not None:
            base_statement = base_statement.where(
                OperationalDiscount.payment_method_code == normalized_payment_method
            )
        if normalized_query is not None:
            discount_id_prefix = normalized_query.removeprefix("des-")
            pattern = f"%{normalized_query}%"
            base_statement = base_statement.where(
                or_(
                    func.lower(cast(OperationalDiscount.id, String)).like(f"{discount_id_prefix}%"),
                    func.lower(cast(OperationalDiscount.id, String)).contains(normalized_query),
                    func.lower(OperationalDiscount.subject_name).like(pattern),
                    func.lower(OperationalDiscount.concept).like(pattern),
                    func.lower(func.coalesce(OperationalDiscount.notes, "")).like(pattern),
                    func.lower(User.full_name).like(pattern),
                    func.lower(func.coalesce(OperationalDiscountCategory.name, "")).like(pattern),
                )
            )

        available_user_rows = (
            session.execute(
                base_statement.with_only_columns(
                    OperationalDiscount.created_by_user_id,
                    User.full_name.label("operator_full_name"),
                )
                .distinct()
                .order_by(User.full_name.asc())
            )
            .mappings()
            .all()
        )

        statement = base_statement
        if created_by_user_id is not None:
            statement = statement.where(
                OperationalDiscount.created_by_user_id == created_by_user_id
            )

        records = (
            session.execute(
                statement.order_by(OperationalDiscount.created_at_utc.desc()).limit(
                    MAX_DISCOUNTS_PER_LIST
                )
            )
            .mappings()
            .all()
        )
        return DiscountsListResponse(
            workstation_code=workstation_code,
            scope=normalized_scope,
            created_by_user_id=str(created_by_user_id) if created_by_user_id is not None else None,
            query=_normalize_optional_string(query),
            category=normalized_category,
            payment_method=normalized_payment_method,
            available_users=[
                OperationalDiscountFilterOptionView(
                    value=str(record["created_by_user_id"]),
                    label=record["operator_full_name"],
                )
                for record in available_user_rows
            ],
            discounts=[
                OperationalDiscountListItemView(
                    id=record["id"],
                    folio=_build_discount_folio(record["id"]),
                    status=record["status"],
                    subject_name=record["subject_name"],
                    concept=record["concept"],
                    category_code=record["category_code"],
                    category_name=record["category_name"],
                    payment_method_code=record["payment_method_code"],
                    total_amount=record["total_amount"],
                    cash_amount=record["cash_amount"],
                    non_cash_amount=record["non_cash_amount"],
                    currency_code=record["currency_code"],
                    created_at_utc=record["created_at_utc"],
                    operator_full_name=record["operator_full_name"],
                    branch_code=context.branch_code,
                    branch_name=context.branch_name,
                    workstation_code=context.workstation_code,
                    workstation_name=context.workstation_name,
                    affects_cash_drawer=Decimal(record["cash_amount"]) > ZERO_MONEY,
                )
                for record in records
            ],
        )

    def get_discount_detail(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        discount_id: uuid.UUID,
    ) -> OperationalDiscountDetailResponse:
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
        discount = _get_discount_for_branch(
            session,
            discount_id=discount_id,
            branch_id=context.branch_id,
        )
        return _build_discount_detail(session, discount)


class DiscountsCommandService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        query_service: DiscountsQueryService | None = None,
        settings: ApiSettings | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._settings = settings or get_settings()
        self._query_service = query_service or DiscountsQueryService(
            workstation_access=self._workstation_access,
            cash_session_query=self._cash_session_query,
            settings=self._settings,
        )

    def create_discount(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CreateOperationalDiscountRequest,
        request_id: str | None,
    ) -> OperationalDiscountDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=command.workstation_code,
        )
        current_open_cash_session = _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=command.workstation_code,
            context=context,
        )
        subject_name = _require_non_empty(command.subject_name, field_label="persona o entidad")
        concept = _require_non_empty(command.concept, field_label="motivo o referencia")
        category_code = _validate_category_filter(session, command.category_code)
        payment_method_code = _validate_supported_payment_method_code(command.payment_method_code)
        total_amount = _quantize_money(command.total_amount)
        notes = _normalize_optional_string(command.notes)
        is_high_value = total_amount >= self._settings.discount_high_value_amount_threshold
        if is_high_value and not command.high_value_acknowledged:
            raise OperationalDiscountValidationError(
                "Confirma el descuento de alto valor antes de registrar."
            )
        created_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        cash_amount = total_amount if payment_method_code == PAYMENT_METHOD_CASH else ZERO_MONEY
        non_cash_amount = total_amount if payment_method_code == PAYMENT_METHOD_CARD else ZERO_MONEY

        discount = OperationalDiscount(
            branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            created_by_user_id=current_user.id,
            active_cash_session_id=current_open_cash_session.id,
            subject_name=subject_name,
            concept=concept,
            category_code=category_code,
            notes=notes,
            payment_method_code=payment_method_code,
            currency_code="MXN",
            total_amount=total_amount,
            cash_amount=cash_amount,
            non_cash_amount=non_cash_amount,
            status=DISCOUNT_STATUS_COMMITTED,
            created_at_utc=created_at,
            committed_at_utc=created_at,
        )

        try:
            session.add(discount)
            session.flush()

            if cash_amount > ZERO_MONEY:
                session.add(
                    CashMovement(
                        sale_id=None,
                        cash_session_id=current_open_cash_session.id,
                        branch_id=context.branch_id,
                        workstation_id=context.workstation_id,
                        operator_id=current_user.id,
                        movement_type=CASH_MOVEMENT_TYPE_OPERATIONAL_DISCOUNT,
                        direction=CASH_MOVEMENT_DIRECTION_IN,
                        payment_method_code=PAYMENT_METHOD_CASH,
                        amount=cash_amount,
                        currency_code="MXN",
                        occurred_at=created_at,
                    )
                )

            discount_folio = _build_discount_folio(discount.id)
            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action=AUDIT_ACTION_OPERATIONAL_DISCOUNT_COMMITTED,
                resource_type=OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
                resource_id=str(discount.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "folio": discount_folio,
                    "branch_code": context.branch_code,
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(current_open_cash_session.id),
                    "subject_name": subject_name,
                    "concept": concept,
                    "category_code": category_code,
                    "payment_method_code": payment_method_code,
                    "currency_code": "MXN",
                    "total_amount": str(total_amount),
                    "cash_amount": str(cash_amount),
                    "non_cash_amount": str(non_cash_amount),
                    "notes": notes,
                    "high_value": is_high_value,
                    "high_value_acknowledged": command.high_value_acknowledged,
                    "high_value_threshold_amount": str(
                        self._settings.discount_high_value_amount_threshold
                    ),
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type=OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
                aggregate_id=str(discount.id),
                event_name=OUTBOX_EVENT_OPERATIONAL_DISCOUNT_COMMITTED_V1,
                payload={
                    "discount_id": str(discount.id),
                    "folio": discount_folio,
                    "branch_id": str(context.branch_id),
                    "branch_code": context.branch_code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(current_open_cash_session.id),
                    "created_by_user_id": str(current_user.id),
                    "subject_name": subject_name,
                    "concept": concept,
                    "category_code": category_code,
                    "payment_method_code": payment_method_code,
                    "currency_code": "MXN",
                    "total_amount": str(total_amount),
                    "cash_amount": str(cash_amount),
                    "non_cash_amount": str(non_cash_amount),
                    "notes": notes,
                    "high_value": is_high_value,
                    "high_value_acknowledged": command.high_value_acknowledged,
                    "high_value_threshold_amount": str(
                        self._settings.discount_high_value_amount_threshold
                    ),
                    "committed_at_utc": created_at.isoformat(),
                },
                headers={"request_id": resolved_request_id},
            )
            if is_high_value:
                self._audit_recorder.record(
                    session,
                    actor_id=current_user.id,
                    action=AUDIT_ACTION_OPERATIONAL_DISCOUNT_HIGH_VALUE_ALERT_REQUESTED,
                    resource_type=OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
                    resource_id=str(discount.id),
                    branch_id=context.branch_id,
                    request_id=resolved_request_id,
                    metadata={
                        "folio": discount_folio,
                        "notification_target": "backoffice",
                        "threshold_amount": str(
                            self._settings.discount_high_value_amount_threshold
                        ),
                        "total_amount": str(total_amount),
                        "category_code": category_code,
                    },
                )
                self._outbox_writer.append(
                    session,
                    aggregate_type=OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
                    aggregate_id=str(discount.id),
                    event_name=OUTBOX_EVENT_OPERATIONAL_DISCOUNT_HIGH_VALUE_ALERT_V1,
                    payload={
                        "discount_id": str(discount.id),
                        "folio": discount_folio,
                        "notification_target": "backoffice",
                        "branch_id": str(context.branch_id),
                        "branch_code": context.branch_code,
                        "workstation_id": str(context.workstation_id),
                        "workstation_code": context.workstation_code,
                        "created_by_user_id": str(current_user.id),
                        "subject_name": subject_name,
                        "category_code": category_code,
                        "total_amount": str(total_amount),
                        "threshold_amount": str(
                            self._settings.discount_high_value_amount_threshold
                        ),
                        "committed_at_utc": created_at.isoformat(),
                    },
                    headers={"request_id": resolved_request_id},
                )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise OperationalDiscountValidationError(
                "Las reglas de integridad del descuento fallaron durante el guardado."
            ) from error

        return self._query_service.get_discount_detail(
            session,
            current_user=current_user,
            workstation_code=command.workstation_code,
            discount_id=discount.id,
        )


def _build_discount_detail(
    session: Session,
    discount: OperationalDiscount,
) -> OperationalDiscountDetailResponse:
    branch = session.execute(select(Branch).where(Branch.id == discount.branch_id)).scalar_one()
    workstation = session.execute(
        select(Workstation).where(Workstation.id == discount.workstation_id)
    ).scalar_one()
    created_by = session.execute(
        select(User).where(User.id == discount.created_by_user_id)
    ).scalar_one()
    category_name = (
        session.execute(
            select(OperationalDiscountCategory.name).where(
                OperationalDiscountCategory.code == discount.category_code
            )
        ).scalar_one_or_none()
        if discount.category_code is not None
        else None
    )

    return OperationalDiscountDetailResponse(
        id=discount.id,
        folio=_build_discount_folio(discount.id),
        status=discount.status,
        branch=BranchSummary(
            id=branch.id,
            code=branch.code,
            name=branch.name,
            timezone=branch.timezone,
            is_active=branch.is_active,
        ),
        workstation=WorkstationSummary(
            id=workstation.id,
            code=workstation.code,
            name=workstation.name,
            is_active=workstation.is_active,
        ),
        created_by=AuthenticatedUser(
            id=created_by.id,
            email=created_by.email,
            full_name=created_by.full_name,
            is_active=created_by.is_active,
        ),
        active_cash_session_id=discount.active_cash_session_id,
        subject_name=discount.subject_name,
        concept=discount.concept,
        category_code=discount.category_code,
        category_name=category_name,
        notes=discount.notes,
        payment_method_code=discount.payment_method_code,
        currency_code=discount.currency_code,
        total_amount=discount.total_amount,
        cash_amount=discount.cash_amount,
        non_cash_amount=discount.non_cash_amount,
        created_at_utc=discount.created_at_utc,
        committed_at_utc=discount.committed_at_utc,
        affects_cash_drawer=discount.cash_amount > ZERO_MONEY,
        audit_summary=AuditVisibilityQueryService().build_summary(
            session,
            created_actor=build_audit_actor_snapshot(
                user_id=created_by.id,
                full_name=created_by.full_name,
                email=created_by.email,
            ),
            created_at_utc=discount.created_at_utc,
            confirmed_at_utc=discount.committed_at_utc,
            acknowledgement_label="Validacion de alto valor",
            notes=discount.notes,
            notification_config=BackofficeNotificationConfig(
                aggregate_id=str(discount.id),
                aggregate_type=OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
                event_names=(OUTBOX_EVENT_OPERATIONAL_DISCOUNT_HIGH_VALUE_ALERT_V1,),
                label="Alerta a backoffice",
            ),
        ),
    )


def _get_discount_for_branch(
    session: Session,
    *,
    discount_id: uuid.UUID,
    branch_id: uuid.UUID,
) -> OperationalDiscount:
    discount = session.execute(
        select(OperationalDiscount).where(
            OperationalDiscount.id == discount_id,
            OperationalDiscount.branch_id == branch_id,
        )
    ).scalar_one_or_none()
    if discount is None:
        raise OperationalDiscountNotFoundError(
            "El descuento solicitado no existe en la sucursal actual."
        )
    return discount


def _get_branch_brand_key(branch_code: str) -> str:
    return BRANCH_BRAND_MAPPING.get(branch_code, "EL_MEJOR_PAN")


def _get_discount_method_views() -> list[OperationalDiscountMethodView]:
    return [
        OperationalDiscountMethodView(
            code=PAYMENT_METHOD_CASH,
            label="Efectivo",
            affects_cash_drawer=True,
            is_enabled=True,
            helper_text="Registra un cobro interno y aumenta el efectivo esperado del turno.",
        ),
        OperationalDiscountMethodView(
            code=PAYMENT_METHOD_CARD,
            label="Tarjeta",
            affects_cash_drawer=False,
            is_enabled=True,
            helper_text="Queda auditado, pero no cambia el efectivo esperado de la caja.",
        ),
        OperationalDiscountMethodView(
            code=PAYMENT_METHOD_MIXED,
            label="Mixto",
            affects_cash_drawer=False,
            is_enabled=False,
            helper_text="No esta disponible todavia en esta fase.",
        ),
    ]


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
        raise OperationalDiscountConflictError(
            "Necesitas una caja abierta en esta estacion para registrar descuentos."
        )
    if current_open_cash_session.user_id != current_user.id:
        raise OperationalDiscountConflictError(
            "La caja abierta de esta estacion pertenece a otro cajero."
        )
    if (
        current_open_cash_session.branch_id != context.branch_id
        or current_open_cash_session.workstation_id != context.workstation_id
    ):
        raise OperationalDiscountConflictError(
            "La caja abierta no coincide con el contexto actual de la estacion."
        )
    return current_open_cash_session


def _apply_discount_list_scope_filters(
    statement: Select[tuple[object, ...]],
    *,
    normalized_scope: str,
    context: WorkstationContext,
    current_cash_session_id: uuid.UUID,
) -> Select[tuple[object, ...]]:
    if normalized_scope == DISCOUNT_LIST_SCOPE_CURRENT_SHIFT:
        return statement.where(
            OperationalDiscount.active_cash_session_id == current_cash_session_id
        )

    if normalized_scope == DISCOUNT_LIST_SCOPE_TODAY:
        branch_timezone = ZoneInfo(context.branch_timezone)
        local_now = datetime.now(tz=UTC).astimezone(branch_timezone)
        local_start = datetime.combine(local_now.date(), time.min, tzinfo=branch_timezone)
        local_end = local_start + timedelta(days=1)
        return statement.where(
            OperationalDiscount.created_at_utc >= local_start.astimezone(UTC),
            OperationalDiscount.created_at_utc < local_end.astimezone(UTC),
        )

    return statement


def _validate_discount_list_scope(value: str | None) -> str:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return DISCOUNT_LIST_SCOPE_CURRENT_SHIFT

    scope_code = normalized.upper()
    if scope_code not in VALID_OPERATIONAL_DISCOUNT_LIST_SCOPES:
        raise OperationalDiscountValidationError(
            "El alcance solicitado no es valido para descuentos operativos."
        )
    return scope_code


def _validate_supported_payment_method_code(value: str) -> str:
    payment_method_code = _validate_payment_method_code(value)
    if payment_method_code not in SUPPORTED_OPERATIONAL_DISCOUNT_METHOD_CODES:
        raise OperationalDiscountValidationError(
            "Por ahora solo puedes registrar descuentos en efectivo o tarjeta."
        )
    return payment_method_code


def _validate_payment_method_filter(value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    return _validate_payment_method_code(normalized)


def _validate_payment_method_code(value: str) -> str:
    payment_method_code = value.strip().upper()
    if payment_method_code not in VALID_OPERATIONAL_DISCOUNT_METHOD_CODES:
        raise OperationalDiscountValidationError("Selecciona un metodo valido para este registro.")
    return payment_method_code


def _validate_category_filter(session: Session, value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    category_code = normalized.upper()
    category = session.execute(
        select(OperationalDiscountCategory.code).where(
            OperationalDiscountCategory.code == category_code,
            OperationalDiscountCategory.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if category is None:
        raise OperationalDiscountValidationError("Selecciona una categoria valida.")
    return category_code


def _require_non_empty(value: str, *, field_label: str) -> str:
    normalized = value.strip()
    if len(normalized) == 0:
        raise OperationalDiscountValidationError(f"Captura un valor valido para {field_label}.")
    return normalized


def _build_discount_folio(discount_id: uuid.UUID) -> str:
    return f"DES-{str(discount_id).split('-', maxsplit=1)[0].upper()}"


def _normalize_query(value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    return normalized.casefold() if normalized else None


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _quantize_money(value: Decimal | int | None) -> Decimal:
    raw_value = ZERO_MONEY if value is None else Decimal(value)
    return raw_value.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
