from fastapi import APIRouter

from zeromerma_api.modules.branches.presentation.router import router as branches_router
from zeromerma_api.modules.cash.presentation.router import router as cash_router
from zeromerma_api.modules.cash_close.presentation.router import router as cash_close_router
from zeromerma_api.modules.catalog.presentation.router import router as catalog_router
from zeromerma_api.modules.corrections.presentation.router import router as corrections_router
from zeromerma_api.modules.dev_audit.presentation.router import router as dev_audit_router
from zeromerma_api.modules.discounts.presentation.router import router as discounts_router
from zeromerma_api.modules.identity.presentation.router import router as identity_router
from zeromerma_api.modules.operations.presentation.router import router as operations_router
from zeromerma_api.modules.orders.presentation.router import router as orders_router
from zeromerma_api.modules.payments.presentation.router import router as payments_router
from zeromerma_api.modules.returns.presentation.router import router as returns_router
from zeromerma_api.modules.sales.presentation.router import router as sales_router
from zeromerma_api.modules.tickets.presentation.router import router as tickets_router
from zeromerma_api.modules.transfers.presentation.router import router as transfers_router
from zeromerma_api.presentation.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(dev_audit_router)
api_router.include_router(identity_router)
api_router.include_router(branches_router)
api_router.include_router(catalog_router)
api_router.include_router(cash_router)
api_router.include_router(cash_close_router)
api_router.include_router(corrections_router)
api_router.include_router(discounts_router)
api_router.include_router(operations_router)
api_router.include_router(orders_router)
api_router.include_router(payments_router)
api_router.include_router(returns_router)
api_router.include_router(tickets_router)
api_router.include_router(transfers_router)
api_router.include_router(sales_router)
