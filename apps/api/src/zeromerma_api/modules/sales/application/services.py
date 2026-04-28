from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.application.access import WorkstationAccessService
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.domain.constants import CASH_SESSION_STATUS_OPEN
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.pricing.application.services import PricedSaleLine, SalePricingService
from zeromerma_api.modules.sales.application.schemas import (
    CashMovementView,
    ConfirmSaleRequest,
    SaleDetailView,
    SaleLineView,
    SalePaymentView,
)
from zeromerma_api.modules.sales.domain.constants import (
    CASH_MOVEMENT_DIRECTION_IN,
    CASH_MOVEMENT_TYPE_SALE_COLLECTION,
    NON_CASH_SALE_PAYMENT_METHOD_CODES,
    OUTBOX_EVENT_SALE_CONFIRMED_V1,
    SALE_PAYMENT_METHOD_CASH,
    SALE_PAYMENT_METHOD_MIXED,
    SALE_STATUS_CONFIRMED,
    VALID_SALE_PAYMENT_METHOD_CODES,
)
from zeromerma_api.modules.sales.domain.exceptions import (
    InsufficientCashPaymentError,
    OpenCashSessionRequiredError,
    SaleNotFoundError,
    SaleValidationError,
    UnsupportedPaymentMethodError,
)
from zeromerma_api.modules.sales.infrastructure.models import (
    CashMovement,
    Sale,
    SaleLine,
    SalePayment,
)

MONEY_QUANTIZER = Decimal("0.01")


@dataclass(frozen=True)
class PreparedSalePayment:
    payment_method_code: str
    tendered_amount: Decimal
    applied_amount: Decimal
    change_amount: Decimal


class SaleQueryService:
    def get_sale_by_id(
        self,
        session: Session,
        *,
        sale_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SaleDetailView:
        sale_record = session.execute(
            select(
                Sale.id,
                Sale.status,
                Sale.branch_id,
                Branch.code.label("branch_code"),
                Branch.name.label("branch_name"),
                Sale.workstation_id,
                Workstation.code.label("workstation_code"),
                Workstation.name.label("workstation_name"),
                Sale.cash_session_id,
                Sale.operator_id,
                User.email.label("operator_email"),
                User.full_name.label("operator_full_name"),
                Sale.currency_code,
                Sale.subtotal_amount,
                Sale.total_amount,
                Sale.paid_amount,
                Sale.change_amount,
                Sale.confirmed_at,
            )
            .select_from(Sale)
            .join(Branch, Branch.id == Sale.branch_id)
            .join(Workstation, Workstation.id == Sale.workstation_id)
            .join(User, User.id == Sale.operator_id)
            .where(Sale.id == sale_id)
        ).mappings().one_or_none()
        if sale_record is None:
            raise SaleNotFoundError("Sale was not found.")

        branch_assignment = session.execute(
            select(UserBranchAssignment.id).where(
                UserBranchAssignment.user_id == user_id,
                UserBranchAssignment.branch_id == sale_record["branch_id"],
                UserBranchAssignment.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if branch_assignment is None:
            raise SaleNotFoundError("Sale was not found.")

        direct_product_class = aliased(ProductClass)
        line_records = session.execute(
            select(
                SaleLine.id,
                SaleLine.sequence,
                SaleLine.capture_mode,
                SaleLine.product_class_id,
                ProductClass.code.label("class_capture_code"),
                ProductClass.name.label("class_capture_name"),
                SaleLine.product_id,
                Product.code.label("product_code"),
                Product.name.label("product_name"),
                direct_product_class.id.label("direct_product_class_id"),
                direct_product_class.code.label("direct_product_class_code"),
                direct_product_class.name.label("direct_product_class_name"),
                SaleLine.catalog_code_snapshot,
                SaleLine.catalog_name_snapshot,
                SaleLine.quantity,
                SaleLine.unit_price,
                SaleLine.line_total_amount,
                SaleLine.physical_attribution_status,
            )
            .select_from(SaleLine)
            .outerjoin(ProductClass, ProductClass.id == SaleLine.product_class_id)
            .outerjoin(Product, Product.id == SaleLine.product_id)
            .outerjoin(direct_product_class, direct_product_class.id == Product.product_class_id)
            .where(SaleLine.sale_id == sale_id)
            .order_by(SaleLine.sequence.asc())
        ).mappings().all()

        payment_records = session.execute(
            select(
                SalePayment.id,
                SalePayment.sequence,
                SalePayment.payment_method_code,
                SalePayment.tendered_amount,
                SalePayment.applied_amount,
                SalePayment.change_amount,
                SalePayment.currency_code,
                SalePayment.received_at,
            )
            .where(SalePayment.sale_id == sale_id)
            .order_by(SalePayment.sequence.asc())
        ).mappings().all()

        cash_movement_records = session.execute(
            select(
                CashMovement.id,
                CashMovement.movement_type,
                CashMovement.direction,
                CashMovement.payment_method_code,
                CashMovement.amount,
                CashMovement.currency_code,
                CashMovement.occurred_at,
            )
            .where(CashMovement.sale_id == sale_id)
            .order_by(CashMovement.occurred_at.asc())
        ).mappings().all()

        return SaleDetailView(
            id=sale_record["id"],
            status=sale_record["status"],
            branch_id=sale_record["branch_id"],
            branch_code=sale_record["branch_code"],
            branch_name=sale_record["branch_name"],
            workstation_id=sale_record["workstation_id"],
            workstation_code=sale_record["workstation_code"],
            workstation_name=sale_record["workstation_name"],
            cash_session_id=sale_record["cash_session_id"],
            operator_id=sale_record["operator_id"],
            operator_email=sale_record["operator_email"],
            operator_full_name=sale_record["operator_full_name"],
            currency_code=sale_record["currency_code"],
            subtotal_amount=sale_record["subtotal_amount"],
            total_amount=sale_record["total_amount"],
            paid_amount=sale_record["paid_amount"],
            change_amount=sale_record["change_amount"],
            confirmed_at=sale_record["confirmed_at"],
            lines=[
                SaleLineView(
                    id=record["id"],
                    sequence=record["sequence"],
                    capture_mode=record["capture_mode"],
                    product_class_id=(
                        record["product_class_id"] or record["direct_product_class_id"]
                    ),
                    product_class_code=(
                        record["class_capture_code"] or record["direct_product_class_code"]
                    ),
                    product_class_name=(
                        record["class_capture_name"] or record["direct_product_class_name"]
                    ),
                    product_id=record["product_id"],
                    product_code=record["product_code"],
                    product_name=record["product_name"],
                    catalog_code_snapshot=record["catalog_code_snapshot"],
                    catalog_name_snapshot=record["catalog_name_snapshot"],
                    quantity=record["quantity"],
                    unit_price=record["unit_price"],
                    line_total_amount=record["line_total_amount"],
                    physical_attribution_status=record["physical_attribution_status"],
                )
                for record in line_records
            ],
            payments=[
                SalePaymentView(
                    id=record["id"],
                    sequence=record["sequence"],
                    payment_method_code=record["payment_method_code"],
                    tendered_amount=record["tendered_amount"],
                    applied_amount=record["applied_amount"],
                    change_amount=record["change_amount"],
                    currency_code=record["currency_code"],
                    received_at=record["received_at"],
                )
                for record in payment_records
            ],
            cash_movements=[
                CashMovementView(
                    id=record["id"],
                    movement_type=record["movement_type"],
                    direction=record["direction"],
                    payment_method_code=record["payment_method_code"],
                    amount=record["amount"],
                    currency_code=record["currency_code"],
                    occurred_at=record["occurred_at"],
                )
                for record in cash_movement_records
            ],
        )


class SaleCommandService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        pricing_service: SalePricingService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        query_service: SaleQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._pricing_service = pricing_service or SalePricingService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._query_service = query_service or SaleQueryService()

    def confirm_sale(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: ConfirmSaleRequest,
        request_id: str | None,
    ) -> SaleDetailView:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=command.workstation_code,
        )
        cash_session = session.execute(
            select(CashSession).where(
                CashSession.workstation_id == context.workstation_id,
                CashSession.user_id == current_user.id,
                CashSession.status == CASH_SESSION_STATUS_OPEN,
            )
        ).scalar_one_or_none()
        if cash_session is None:
            raise OpenCashSessionRequiredError(
                f"Workstation {command.workstation_code} requires "
                "an OPEN cash session for this operator."
            )

        priced_lines = self._price_lines(session, command=command)
        sale_currency = _resolve_sale_currency(priced_lines)
        subtotal_amount = _quantize_money(
            sum((line.line_total_amount for line in priced_lines), Decimal("0.00"))
        )
        total_amount = subtotal_amount
        prepared_payments = _prepare_sale_payments(
            command=command,
            total_amount=total_amount,
        )
        change_amount = _quantize_money(
            sum((payment.change_amount for payment in prepared_payments), Decimal("0.00"))
        )
        confirmed_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())

        sale = Sale(
            branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            cash_session_id=cash_session.id,
            operator_id=current_user.id,
            status=SALE_STATUS_CONFIRMED,
            currency_code=sale_currency,
            subtotal_amount=subtotal_amount,
            total_amount=total_amount,
            paid_amount=total_amount,
            change_amount=change_amount,
            confirmed_at=confirmed_at,
        )

        try:
            session.add(sale)
            session.flush()

            for sequence, priced_line in enumerate(priced_lines, start=1):
                session.add(
                    SaleLine(
                        sale_id=sale.id,
                        sequence=sequence,
                        capture_mode=priced_line.capture_mode,
                        product_class_id=priced_line.product_class_id,
                        product_id=priced_line.product_id,
                        catalog_code_snapshot=priced_line.catalog_code_snapshot,
                        catalog_name_snapshot=priced_line.catalog_name_snapshot,
                        quantity=priced_line.quantity,
                        unit_price=priced_line.unit_price,
                        line_total_amount=priced_line.line_total_amount,
                        physical_attribution_status=priced_line.physical_attribution_status,
                    )
                )

            for sequence, payment in enumerate(prepared_payments, start=1):
                session.add(
                    SalePayment(
                        sale_id=sale.id,
                        sequence=sequence,
                        payment_method_code=payment.payment_method_code,
                        tendered_amount=payment.tendered_amount,
                        applied_amount=payment.applied_amount,
                        change_amount=payment.change_amount,
                        currency_code=sale_currency,
                        received_at=confirmed_at,
                    )
                )

                if payment.payment_method_code == SALE_PAYMENT_METHOD_CASH:
                    session.add(
                        CashMovement(
                            sale_id=sale.id,
                            cash_session_id=cash_session.id,
                            branch_id=context.branch_id,
                            workstation_id=context.workstation_id,
                            operator_id=current_user.id,
                            movement_type=CASH_MOVEMENT_TYPE_SALE_COLLECTION,
                            direction=CASH_MOVEMENT_DIRECTION_IN,
                            payment_method_code=SALE_PAYMENT_METHOD_CASH,
                            amount=payment.applied_amount,
                            currency_code=sale_currency,
                            occurred_at=confirmed_at,
                        )
                    )

            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action="sale.confirmed",
                resource_type="sale",
                resource_id=str(sale.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "branch_code": context.branch_code,
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(cash_session.id),
                    "currency_code": sale_currency,
                    "total_amount": str(total_amount),
                    "paid_amount": str(total_amount),
                    "change_amount": str(change_amount),
                    "line_count": len(priced_lines),
                    "payment_method_codes": [
                        payment.payment_method_code for payment in prepared_payments
                    ],
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type="sale",
                aggregate_id=str(sale.id),
                event_name=OUTBOX_EVENT_SALE_CONFIRMED_V1,
                payload={
                    "sale_id": str(sale.id),
                    "branch_id": str(context.branch_id),
                    "branch_code": context.branch_code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(cash_session.id),
                    "operator_id": str(current_user.id),
                    "operator_email": current_user.email,
                    "currency_code": sale_currency,
                    "subtotal_amount": str(subtotal_amount),
                    "total_amount": str(total_amount),
                    "paid_amount": str(total_amount),
                    "change_amount": str(change_amount),
                    "confirmed_at": confirmed_at.isoformat(),
                    "lines": [
                        {
                            "capture_mode": line.capture_mode,
                            "product_class_id": (
                                str(line.product_class_id)
                                if line.product_class_id is not None
                                else None
                            ),
                            "product_id": (
                                str(line.product_id) if line.product_id is not None else None
                            ),
                            "catalog_code_snapshot": line.catalog_code_snapshot,
                            "catalog_name_snapshot": line.catalog_name_snapshot,
                            "quantity": str(line.quantity),
                            "unit_price": str(line.unit_price),
                            "line_total_amount": str(line.line_total_amount),
                            "physical_attribution_status": line.physical_attribution_status,
                        }
                        for line in priced_lines
                    ],
                    "payments": [
                        {
                            "payment_method_code": payment.payment_method_code,
                            "tendered_amount": str(payment.tendered_amount),
                            "applied_amount": str(payment.applied_amount),
                            "change_amount": str(payment.change_amount),
                        }
                        for payment in prepared_payments
                    ],
                },
                headers={"request_id": resolved_request_id},
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise SaleValidationError(
                "Sale confirmation invariants were violated by a concurrent request."
            ) from error

        return self._query_service.get_sale_by_id(
            session,
            sale_id=sale.id,
            user_id=current_user.id,
        )

    def _price_lines(
        self,
        session: Session,
        *,
        command: ConfirmSaleRequest,
    ) -> Sequence[PricedSaleLine]:
        priced_lines: list[PricedSaleLine] = []
        for line in command.lines:
            if line.capture_mode == "CLASS_CAPTURE":
                if line.product_class_id is None:
                    raise SaleValidationError("CLASS_CAPTURE line is missing product_class_id.")
                priced_lines.append(
                    self._pricing_service.price_class_capture_line(
                        session,
                        product_class_id=line.product_class_id,
                        quantity=line.quantity,
                    )
                )
                continue

            if line.product_id is None:
                raise SaleValidationError("PRODUCT_DIRECT line is missing product_id.")
            priced_lines.append(
                self._pricing_service.price_product_direct_line(
                    session,
                    product_id=line.product_id,
                    quantity=line.quantity,
                )
            )

        return priced_lines


def _prepare_sale_payments(
    *,
    command: ConfirmSaleRequest,
    total_amount: Decimal,
) -> list[PreparedSalePayment]:
    if len(command.payments) == 0:
        raise SaleValidationError("Agrega al menos un metodo de pago para confirmar la venta.")

    normalized_payments: list[tuple[str, Decimal]] = []
    seen_payment_methods: set[str] = set()
    for payment in command.payments:
        payment_method_code = payment.payment_method_code.strip().upper()
        if payment_method_code not in VALID_SALE_PAYMENT_METHOD_CODES:
            raise UnsupportedPaymentMethodError(
                f"El metodo de pago {payment_method_code} no esta disponible."
            )
        if payment_method_code == SALE_PAYMENT_METHOD_MIXED:
            raise UnsupportedPaymentMethodError(
                "Mixto debe enviarse como efectivo combinado con tarjeta u otro."
            )
        if payment_method_code in seen_payment_methods:
            raise SaleValidationError(
                f"El metodo de pago {payment_method_code} no puede repetirse en la misma venta."
            )

        tendered_amount = _quantize_money(payment.tendered_amount)
        if tendered_amount <= Decimal("0.00"):
            raise SaleValidationError(
                f"El monto de {payment_method_code} debe ser mayor que cero."
            )

        normalized_payments.append((payment_method_code, tendered_amount))
        seen_payment_methods.add(payment_method_code)

    remaining_amount = total_amount
    prepared_payments_by_code: dict[str, PreparedSalePayment] = {}

    for payment_method_code, tendered_amount in normalized_payments:
        if payment_method_code not in NON_CASH_SALE_PAYMENT_METHOD_CODES:
            continue

        if tendered_amount > remaining_amount:
            raise SaleValidationError(
                "Los pagos sin efectivo no pueden exceder el total pendiente."
            )

        prepared_payments_by_code[payment_method_code] = PreparedSalePayment(
            payment_method_code=payment_method_code,
            tendered_amount=tendered_amount,
            applied_amount=tendered_amount,
            change_amount=Decimal("0.00"),
        )
        remaining_amount = _quantize_money(remaining_amount - tendered_amount)

    cash_payment = next(
        (
            payment
            for payment in normalized_payments
            if payment[0] == SALE_PAYMENT_METHOD_CASH
        ),
        None,
    )
    if cash_payment is not None:
        cash_tendered_amount = cash_payment[1]
        if cash_tendered_amount < remaining_amount:
            raise InsufficientCashPaymentError(
                "El efectivo registrado no cubre el total pendiente."
            )

        prepared_payments_by_code[SALE_PAYMENT_METHOD_CASH] = PreparedSalePayment(
            payment_method_code=SALE_PAYMENT_METHOD_CASH,
            tendered_amount=cash_tendered_amount,
            applied_amount=remaining_amount,
            change_amount=_quantize_money(cash_tendered_amount - remaining_amount),
        )
        remaining_amount = Decimal("0.00")

    if remaining_amount > Decimal("0.00"):
        raise SaleValidationError("El monto registrado no cubre el total de la compra.")

    return [
        prepared_payments_by_code[payment_method_code]
        for payment_method_code, _ in normalized_payments
    ]


def _resolve_sale_currency(priced_lines: Sequence[PricedSaleLine]) -> str:
    if len(priced_lines) == 0:
        raise SaleValidationError("Sale must contain at least one line.")

    sale_currency = priced_lines[0].currency_code
    for line in priced_lines[1:]:
        if line.currency_code != sale_currency:
            raise SaleValidationError("All sale lines must use the same currency.")
    return sale_currency


def _quantize_money(amount: Decimal) -> Decimal:
    return amount.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
