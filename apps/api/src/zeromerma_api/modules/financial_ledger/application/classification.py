"""SQL dimensions derived from positive confirmed sale legs."""

from uuid import UUID

from sqlalchemy import Select, func, select

from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)


def mixed_sale_ids() -> Select[tuple[UUID]]:
    return (
        select(FinancialOperation.source_id)
        .join(FinancialEntry, FinancialEntry.financial_operation_id == FinancialOperation.id)
        .where(FinancialOperation.kind == "SALE_COLLECTION", FinancialEntry.state == "CONFIRMED")
        .group_by(FinancialOperation.source_id)
        .having(func.count(func.distinct(FinancialEntry.payment_method_code)) > 1)
        .correlate(None)
    )
