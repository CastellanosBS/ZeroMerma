from fastapi import APIRouter

from zeromerma_api.modules.audit.presentation.router import admin_router as admin_audit_router
from zeromerma_api.modules.branches.presentation.router import admin_router as admin_branches_router
from zeromerma_api.modules.branches.presentation.router import (
    admin_workstations_router,
)
from zeromerma_api.modules.branches.presentation.router import router as branches_router
from zeromerma_api.modules.cash.presentation.router import router as cash_router
from zeromerma_api.modules.cash_close.presentation.router import (
    admin_cash_flow_router,
    admin_reconciliation_router,
)
from zeromerma_api.modules.cash_close.presentation.router import (
    admin_router as admin_cash_cuts_router,
)
from zeromerma_api.modules.cash_close.presentation.router import router as cash_close_router
from zeromerma_api.modules.catalog.presentation.admin_router import (
    inputs_supplies_router as admin_inputs_supplies_router,
)
from zeromerma_api.modules.catalog.presentation.admin_router import (
    prices_router as admin_prices_router,
)
from zeromerma_api.modules.catalog.presentation.admin_router import (
    product_classes_router as admin_product_classes_router,
)
from zeromerma_api.modules.catalog.presentation.admin_router import (
    recipes_costs_router as admin_recipes_costs_router,
)
from zeromerma_api.modules.catalog.presentation.admin_router import (
    router as admin_products_router,
)
from zeromerma_api.modules.catalog.presentation.router import router as catalog_router
from zeromerma_api.modules.configuration.presentation.router import (
    admin_router as admin_settings_router,
)
from zeromerma_api.modules.corrections.presentation.router import (
    admin_router as admin_corrections_router,
)
from zeromerma_api.modules.corrections.presentation.router import router as corrections_router
from zeromerma_api.modules.dev_audit.presentation.router import router as dev_audit_router
from zeromerma_api.modules.discounts.presentation.router import (
    admin_router as admin_discounts_router,
)
from zeromerma_api.modules.discounts.presentation.router import (
    router as discounts_router,
)
from zeromerma_api.modules.identity.presentation.router import admin_router as admin_users_router
from zeromerma_api.modules.identity.presentation.router import (
    roles_admin_router as admin_roles_router,
)
from zeromerma_api.modules.identity.presentation.router import router as identity_router
from zeromerma_api.modules.inventory.presentation.router import (
    admin_router as admin_inventory_router,
)
from zeromerma_api.modules.operations.presentation.router import router as operations_router
from zeromerma_api.modules.orders.presentation.router import (
    admin_router as admin_orders_router,
)
from zeromerma_api.modules.orders.presentation.router import (
    router as orders_router,
)
from zeromerma_api.modules.payments.presentation.router import router as payments_router
from zeromerma_api.modules.production.presentation.router import (
    admin_router as admin_production_router,
)
from zeromerma_api.modules.purchases.presentation.router import (
    admin_router as admin_purchases_router,
)
from zeromerma_api.modules.quality.presentation.router import (
    admin_cleaning_logs_router,
    admin_equipment_maintenance_router,
    admin_incidents_router,
    admin_sanitary_verifications_router,
)
from zeromerma_api.modules.reports.presentation.router import admin_router as admin_reports_router
from zeromerma_api.modules.returns.presentation.router import admin_router as admin_returns_router
from zeromerma_api.modules.returns.presentation.router import router as returns_router
from zeromerma_api.modules.sales.presentation.router import router as sales_router
from zeromerma_api.modules.suppliers.presentation.router import (
    admin_router as admin_suppliers_router,
)
from zeromerma_api.modules.tickets.presentation.router import (
    admin_router as admin_sales_tickets_router,
)
from zeromerma_api.modules.tickets.presentation.router import (
    router as tickets_router,
)
from zeromerma_api.modules.transfers.presentation.router import (
    admin_router as admin_transfers_router,
)
from zeromerma_api.modules.transfers.presentation.router import router as transfers_router
from zeromerma_api.modules.waste.presentation.router import admin_router as admin_waste_router
from zeromerma_api.presentation.access_policy import install_access_policies
from zeromerma_api.presentation.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(dev_audit_router)
api_router.include_router(identity_router)
api_router.include_router(admin_users_router)
api_router.include_router(admin_roles_router)
api_router.include_router(admin_audit_router)
api_router.include_router(admin_reports_router)
api_router.include_router(admin_settings_router)
api_router.include_router(admin_products_router)
api_router.include_router(admin_inputs_supplies_router)
api_router.include_router(admin_product_classes_router)
api_router.include_router(admin_prices_router)
api_router.include_router(admin_recipes_costs_router)
api_router.include_router(admin_discounts_router)
api_router.include_router(admin_sales_tickets_router)
api_router.include_router(admin_orders_router)
api_router.include_router(admin_returns_router)
api_router.include_router(admin_corrections_router)
api_router.include_router(admin_branches_router)
api_router.include_router(admin_workstations_router)
api_router.include_router(admin_inventory_router)
api_router.include_router(admin_transfers_router)
api_router.include_router(admin_production_router)
api_router.include_router(admin_waste_router)
api_router.include_router(admin_suppliers_router)
api_router.include_router(admin_purchases_router)
api_router.include_router(admin_cash_cuts_router)
api_router.include_router(admin_reconciliation_router)
api_router.include_router(admin_cash_flow_router)
api_router.include_router(admin_cleaning_logs_router)
api_router.include_router(admin_sanitary_verifications_router)
api_router.include_router(admin_incidents_router)
api_router.include_router(admin_equipment_maintenance_router)
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

install_access_policies(api_router)
