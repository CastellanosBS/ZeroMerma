from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.application.visibility import (
    AuditVisibilityQueryService,
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
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.domain.constants import BRANCH_BRAND_MAPPING
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.payments.application.schemas import (
    CreateOperationalPaymentRequest,
    OperationalPaymentCategoryView,
    OperationalPaymentDetailResponse,
    OperationalPaymentFilterOptionView,
    OperationalPaymentListItemView,
    OperationalPaymentMethodView,
    OperationalPaymentScopeView,
    PaymentsBootstrapResponse,
    PaymentsListResponse,
)
from zeromerma_api.modules.payments.domain.constants import (
    AUDIT_ACTION_OPERATIONAL_PAYMENT_COMMITTED,
    OPERATIONAL_PAYMENT_RESOURCE_TYPE,
    OUTBOX_EVENT_OPERATIONAL_PAYMENT_COMMITTED_V1,
    PAYMENT_LIST_SCOPE_CURRENT_SHIFT,
    PAYMENT_LIST_SCOPE_RECENT,
    PAYMENT_LIST_SCOPE_TODAY,
    PAYMENT_METHOD_CARD,
    PAYMENT_METHOD_CASH,
    PAYMENT_METHOD_MIXED,
    PAYMENT_STATUS_COMMITTED,
    SUPPORTED_OPERATIONAL_PAYMENT_METHOD_CODES,
    VALID_OPERATIONAL_PAYMENT_LIST_SCOPES,
    VALID_OPERATIONAL_PAYMENT_METHOD_CODES,
)
from zeromerma_api.modules.payments.domain.exceptions import (
    OperationalPaymentConflictError,
    OperationalPaymentNotFoundError,
    OperationalPaymentValidationError,
)
from zeromerma_api.modules.payments.infrastructure.models import (
    OperationalPayment,
    OperationalPaymentCategory,
)
from zeromerma_api.modules.sales.domain.constants import (
    CASH_MOVEMENT_DIRECTION_OUT,
    CASH_MOVEMENT_TYPE_OPERATIONAL_PAYMENT,
)
from zeromerma_api.modules.sales.infrastructure.models import CashMovement

MAX_PAYMENTS_PER_LIST = 80
MONEY_QUANTIZER = Decimal("0.01")
ZERO_MONEY = Decimal("0.00")


class PaymentsQueryService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        audit_visibility: AuditVisibilityQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._audit_visibility = audit_visibility or AuditVisibilityQueryService()

    def get_bootstrap(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> PaymentsBootstrapResponse:
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
            select(OperationalPaymentCategory)
            .where(OperationalPaymentCategory.is_active.is_(True))
            .order_by(
                OperationalPaymentCategory.display_order.asc(),
                OperationalPaymentCategory.name.asc(),
            )
        ).scalars()

        return PaymentsBootstrapResponse(
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
            payment_registration_allowed=(
                current_open_cash_session is not None
                and current_open_cash_session.user_id == current_user.id
            ),
            default_scope=PAYMENT_LIST_SCOPE_CURRENT_SHIFT,
            available_scopes=[
                OperationalPaymentScopeView(
                    code=PAYMENT_LIST_SCOPE_CURRENT_SHIFT,
                    label="Turno actual",
                ),
                OperationalPaymentScopeView(code=PAYMENT_LIST_SCOPE_TODAY, label="Hoy"),
                OperationalPaymentScopeView(code=PAYMENT_LIST_SCOPE_RECENT, label="Recientes"),
            ],
            active_payment_methods=_get_payment_method_views(),
            active_categories=[
                OperationalPaymentCategoryView(
                    code=category.code,
                    name=category.name,
                    display_order=category.display_order,
                )
                for category in categories
            ],
        )

    def list_payments(
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
    ) -> PaymentsListResponse:
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
        normalized_scope = _validate_payment_list_scope(scope)
        normalized_query = _normalize_query(query)
        normalized_category = _validate_category_filter(session, category_filter)
        normalized_payment_method = _validate_payment_method_filter(payment_method_filter)

        base_statement = (
            select(
                OperationalPayment.id,
                OperationalPayment.status,
                OperationalPayment.created_by_user_id,
                OperationalPayment.payee_name,
                OperationalPayment.concept,
                OperationalPayment.category_code,
                OperationalPaymentCategory.name.label("category_name"),
                OperationalPayment.payment_method_code,
                OperationalPayment.total_amount,
                OperationalPayment.cash_amount,
                OperationalPayment.non_cash_amount,
                OperationalPayment.currency_code,
                OperationalPayment.created_at_utc,
                User.full_name.label("operator_full_name"),
            )
            .select_from(OperationalPayment)
            .join(User, User.id == OperationalPayment.created_by_user_id)
            .outerjoin(
                OperationalPaymentCategory,
                OperationalPaymentCategory.code == OperationalPayment.category_code,
            )
            .where(
                OperationalPayment.branch_id == context.branch_id,
                OperationalPayment.workstation_id == context.workstation_id,
            )
        )
        base_statement = _apply_payment_list_scope_filters(
            base_statement,
            normalized_scope=normalized_scope,
            context=context,
            current_cash_session_id=current_open_cash_session.id,
        )
        if normalized_category is not None:
            base_statement = base_statement.where(
                OperationalPayment.category_code == normalized_category
            )
        if normalized_payment_method is not None:
            base_statement = base_statement.where(
                OperationalPayment.payment_method_code == normalized_payment_method
            )
        if normalized_query is not None:
            payment_id_prefix = normalized_query.removeprefix("pag-")
            pattern = f"%{normalized_query}%"
            base_statement = base_statement.where(
                or_(
                    func.lower(cast(OperationalPayment.id, String)).like(f"{payment_id_prefix}%"),
                    func.lower(cast(OperationalPayment.id, String)).contains(normalized_query),
                    func.lower(OperationalPayment.payee_name).like(pattern),
                    func.lower(OperationalPayment.concept).like(pattern),
                    func.lower(func.coalesce(OperationalPayment.notes, "")).like(pattern),
                    func.lower(User.full_name).like(pattern),
                )
            )

        available_user_rows = session.execute(
            base_statement.with_only_columns(
                OperationalPayment.created_by_user_id,
                User.full_name.label("operator_full_name"),
            )
            .distinct()
            .order_by(User.full_name.asc())
        ).mappings().all()

        statement = base_statement
        if created_by_user_id is not None:
            statement = statement.where(
                OperationalPayment.created_by_user_id == created_by_user_id
            )

        records = session.execute(
            statement
            .order_by(OperationalPayment.created_at_utc.desc())
            .limit(MAX_PAYMENTS_PER_LIST)
        ).mappings().all()
        return PaymentsListResponse(
            workstation_code=workstation_code,
            scope=normalized_scope,
            created_by_user_id=str(created_by_user_id) if created_by_user_id is not None else None,
            query=_normalize_optional_string(query),
            category=normalized_category,
            payment_method=normalized_payment_method,
            available_users=[
                OperationalPaymentFilterOptionView(
                    value=str(record["created_by_user_id"]),
                    label=record["operator_full_name"],
                )
                for record in available_user_rows
            ],
            payments=[
                OperationalPaymentListItemView(
                    id=record["id"],
                    folio=_build_payment_folio(record["id"]),
                    status=record["status"],
                    payee_name=record["payee_name"],
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

    def get_payment_detail(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        payment_id: uuid.UUID,
    ) -> OperationalPaymentDetailResponse:
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
        payment = _get_payment_for_branch(
            session,
            payment_id=payment_id,
            branch_id=context.branch_id,
        )
        return _build_payment_detail(session, payment)


class PaymentsCommandService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        query_service: PaymentsQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._query_service = query_service or PaymentsQueryService(
            workstation_access=self._workstation_access,
            cash_session_query=self._cash_session_query,
        )

    def create_payment(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CreateOperationalPaymentRequest,
        request_id: str | None,
    ) -> OperationalPaymentDetailResponse:
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
        payee_name = _require_non_empty(command.payee_name, field_label="beneficiario")
        concept = _require_non_empty(command.concept, field_label="concepto")
        category_code = _validate_category_filter(session, command.category_code)
        payment_method_code = _validate_supported_payment_method_code(command.payment_method_code)
        total_amount = _quantize_money(command.total_amount)
        notes = _normalize_optional_string(command.notes)
        created_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        cash_amount = total_amount if payment_method_code == PAYMENT_METHOD_CASH else ZERO_MONEY
        non_cash_amount = total_amount if payment_method_code == PAYMENT_METHOD_CARD else ZERO_MONEY

        payment = OperationalPayment(
            branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            created_by_user_id=current_user.id,
            active_cash_session_id=current_open_cash_session.id,
            payee_name=payee_name,
            concept=concept,
            category_code=category_code,
            notes=notes,
            payment_method_code=payment_method_code,
            currency_code="MXN",
            total_amount=total_amount,
            cash_amount=cash_amount,
            non_cash_amount=non_cash_amount,
            status=PAYMENT_STATUS_COMMITTED,
            created_at_utc=created_at,
            committed_at_utc=created_at,
        )

        try:
            session.add(payment)
            session.flush()

            if cash_amount > ZERO_MONEY:
                session.add(
                    CashMovement(
                        sale_id=None,
                        cash_session_id=current_open_cash_session.id,
                        branch_id=context.branch_id,
                        workstation_id=context.workstation_id,
                        operator_id=current_user.id,
                        movement_type=CASH_MOVEMENT_TYPE_OPERATIONAL_PAYMENT,
                        direction=CASH_MOVEMENT_DIRECTION_OUT,
                        payment_method_code=PAYMENT_METHOD_CASH,
                        amount=cash_amount,
                        currency_code="MXN",
                        occurred_at=created_at,
                    )
                )

            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action=AUDIT_ACTION_OPERATIONAL_PAYMENT_COMMITTED,
                resource_type=OPERATIONAL_PAYMENT_RESOURCE_TYPE,
                resource_id=str(payment.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "folio": _build_payment_folio(payment.id),
                    "branch_code": context.branch_code,
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(current_open_cash_session.id),
                    "payee_name": payee_name,
                    "concept": concept,
                    "category_code": category_code,
                    "payment_method_code": payment_method_code,
                    "currency_code": "MXN",
                    "total_amount": str(total_amount),
                    "cash_amount": str(cash_amount),
                    "non_cash_amount": str(non_cash_amount),
                    "notes": notes,
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type=OPERATIONAL_PAYMENT_RESOURCE_TYPE,
                aggregate_id=str(payment.id),
                event_name=OUTBOX_EVENT_OPERATIONAL_PAYMENT_COMMITTED_V1,
                payload={
                    "payment_id": str(payment.id),
                    "folio": _build_payment_folio(payment.id),
                    "branch_id": str(context.branch_id),
                    "branch_code": context.branch_code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(current_open_cash_session.id),
                    "created_by_user_id": str(current_user.id),
                    "payee_name": payee_name,
                    "concept": concept,
                    "category_code": category_code,
                    "payment_method_code": payment_method_code,
                    "currency_code": "MXN",
                    "total_amount": str(total_amount),
                    "cash_amount": str(cash_amount),
                    "non_cash_amount": str(non_cash_amount),
                    "notes": notes,
                    "committed_at_utc": created_at.isoformat(),
                },
                headers={"request_id": resolved_request_id},
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise OperationalPaymentValidationError(
                "Las reglas de integridad del pago fallaron durante el guardado."
            ) from error

        return self._query_service.get_payment_detail(
            session,
            current_user=current_user,
            workstation_code=command.workstation_code,
            payment_id=payment.id,
        )


def _build_payment_detail(
    session: Session,
    payment: OperationalPayment,
) -> OperationalPaymentDetailResponse:
    branch = session.execute(select(Branch).where(Branch.id == payment.branch_id)).scalar_one()
    workstation = session.execute(
        select(Workstation).where(Workstation.id == payment.workstation_id)
    ).scalar_one()
    created_by = session.execute(
        select(User).where(User.id == payment.created_by_user_id)
    ).scalar_one()
    category_name = (
        session.execute(
            select(OperationalPaymentCategory.name).where(
                OperationalPaymentCategory.code == payment.category_code
            )
        ).scalar_one_or_none()
        if payment.category_code is not None
        else None
    )

    return OperationalPaymentDetailResponse(
        id=payment.id,
        folio=_build_payment_folio(payment.id),
        status=payment.status,
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
        active_cash_session_id=payment.active_cash_session_id,
        payee_name=payment.payee_name,
        concept=payment.concept,
        category_code=payment.category_code,
        category_name=category_name,
        notes=payment.notes,
        payment_method_code=payment.payment_method_code,
        currency_code=payment.currency_code,
        total_amount=payment.total_amount,
        cash_amount=payment.cash_amount,
        non_cash_amount=payment.non_cash_amount,
        created_at_utc=payment.created_at_utc,
        committed_at_utc=payment.committed_at_utc,
        affects_cash_drawer=payment.cash_amount > ZERO_MONEY,
        audit_summary=AuditVisibilityQueryService().build_summary(
            session,
            created_actor=build_audit_actor_snapshot(
                user_id=created_by.id,
                full_name=created_by.full_name,
                email=created_by.email,
            ),
            created_at_utc=payment.created_at_utc,
            confirmed_at_utc=payment.committed_at_utc,
            notes=payment.notes,
        ),
    )


def _get_payment_for_branch(
    session: Session,
    *,
    payment_id: uuid.UUID,
    branch_id: uuid.UUID,
) -> OperationalPayment:
    payment = session.execute(
        select(OperationalPayment).where(
            OperationalPayment.id == payment_id,
            OperationalPayment.branch_id == branch_id,
        )
    ).scalar_one_or_none()
    if payment is None:
        raise OperationalPaymentNotFoundError(
            "El pago solicitado no existe en la sucursal actual."
        )
    return payment


def _get_branch_brand_key(branch_code: str) -> str:
    return BRANCH_BRAND_MAPPING.get(branch_code, "EL_MEJOR_PAN")


def _get_payment_method_views() -> list[OperationalPaymentMethodView]:
    return [
        OperationalPaymentMethodView(
            code=PAYMENT_METHOD_CASH,
            label="Efectivo",
            affects_cash_drawer=True,
            is_enabled=True,
            helper_text="Registra una salida real de caja y afecta el cierre.",
        ),
        OperationalPaymentMethodView(
            code=PAYMENT_METHOD_CARD,
            label="Tarjeta",
            affects_cash_drawer=False,
            is_enabled=True,
            helper_text="Queda auditado, pero no reduce el efectivo de la caja.",
        ),
        OperationalPaymentMethodView(
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
        raise OperationalPaymentConflictError(
            "Necesitas una caja abierta en esta estacion para registrar pagos."
        )
    if current_open_cash_session.user_id != current_user.id:
        raise OperationalPaymentConflictError(
            "La caja abierta de esta estacion pertenece a otro cajero."
        )
    if (
        current_open_cash_session.branch_id != context.branch_id
        or current_open_cash_session.workstation_id != context.workstation_id
    ):
        raise OperationalPaymentConflictError(
            "La caja abierta no coincide con el contexto actual de la estacion."
        )
    return current_open_cash_session


def _apply_payment_list_scope_filters(
    statement: Select[tuple[object, ...]],
    *,
    normalized_scope: str,
    context: WorkstationContext,
    current_cash_session_id: uuid.UUID,
) -> Select[tuple[object, ...]]:
    if normalized_scope == PAYMENT_LIST_SCOPE_CURRENT_SHIFT:
        return statement.where(OperationalPayment.active_cash_session_id == current_cash_session_id)

    if normalized_scope == PAYMENT_LIST_SCOPE_TODAY:
        branch_timezone = ZoneInfo(context.branch_timezone)
        local_now = datetime.now(tz=UTC).astimezone(branch_timezone)
        local_start = datetime.combine(local_now.date(), time.min, tzinfo=branch_timezone)
        local_end = local_start + timedelta(days=1)
        return statement.where(
            OperationalPayment.created_at_utc >= local_start.astimezone(UTC),
            OperationalPayment.created_at_utc < local_end.astimezone(UTC),
        )

    return statement


def _validate_payment_list_scope(value: str | None) -> str:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return PAYMENT_LIST_SCOPE_CURRENT_SHIFT

    scope_code = normalized.upper()
    if scope_code not in VALID_OPERATIONAL_PAYMENT_LIST_SCOPES:
        raise OperationalPaymentValidationError(
            "El alcance solicitado no es valido para pagos operativos."
        )
    return scope_code


def _validate_supported_payment_method_code(value: str) -> str:
    payment_method_code = _validate_payment_method_code(value)
    if payment_method_code not in SUPPORTED_OPERATIONAL_PAYMENT_METHOD_CODES:
        raise OperationalPaymentValidationError(
            "Por ahora solo puedes registrar pagos en efectivo o tarjeta."
        )
    return payment_method_code


def _validate_payment_method_filter(value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    return _validate_payment_method_code(normalized)


def _validate_payment_method_code(value: str) -> str:
    payment_method_code = value.strip().upper()
    if payment_method_code not in VALID_OPERATIONAL_PAYMENT_METHOD_CODES:
        raise OperationalPaymentValidationError(
            "Selecciona un metodo de pago valido para este registro."
        )
    return payment_method_code


def _validate_category_filter(session: Session, value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    category_code = normalized.upper()
    category = session.execute(
        select(OperationalPaymentCategory.code).where(
            OperationalPaymentCategory.code == category_code,
            OperationalPaymentCategory.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if category is None:
        raise OperationalPaymentValidationError("Selecciona una categoria valida.")
    return category_code


def _require_non_empty(value: str, *, field_label: str) -> str:
    normalized = value.strip()
    if len(normalized) == 0:
        raise OperationalPaymentValidationError(f"Captura un {field_label} valido.")
    return normalized


def _build_payment_folio(payment_id: uuid.UUID) -> str:
    return f"PAG-{str(payment_id).split('-', maxsplit=1)[0].upper()}"


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
