from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import authorization_scope, bind_authorization_scope
from zeromerma_api.db.session import get_session
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.identity.application.authorization import require_branches
from zeromerma_api.modules.identity.application.schemas import (
    AuthenticatedUser,
    CapabilityCode,
    IdentitySurface,
)
from zeromerma_api.modules.identity.presentation.dependencies import get_current_user


@dataclass(frozen=True)
class EndpointPolicy:
    capabilities: tuple[CapabilityCode, ...]
    surface: IdentitySurface | None
    mutation: bool = False
    global_only: bool = False
    exception_reason: str | None = None


# Each method/path is deliberate. Unlisted operations are denied, never inferred.
# Shared masters have no branch owner: mutations require explicit GLOBAL (DEC-04).
ENDPOINT_POLICIES: dict[tuple[str, str], EndpointPolicy] = {
    ("POST", "/v1/admin/roles/privileged-changes"): EndpointPolicy(
        (),
        "BACKOFFICE",
        exception_reason=(
            "PrivilegedAccessService validates active Superadmin and dynamic GLOBAL authority."
        ),
    ),
    ("GET", "/v1/admin/roles/privileged-changes/{change_id}"): EndpointPolicy(
        (),
        "BACKOFFICE",
        exception_reason=(
            "PrivilegedAccessService validates active Superadmin and dynamic GLOBAL authority."
        ),
    ),
    ("POST", "/v1/admin/roles/privileged-changes/{change_id}/approve"): EndpointPolicy(
        (),
        "BACKOFFICE",
        exception_reason=(
            "PrivilegedAccessService validates active Superadmin and dynamic GLOBAL authority."
        ),
    ),
    ("POST", "/v1/admin/roles/privileged-changes/{change_id}/execute"): EndpointPolicy(
        (),
        "BACKOFFICE",
        exception_reason=(
            "PrivilegedAccessService validates active Superadmin and dynamic GLOBAL authority."
        ),
    ),
    ("GET", "/dev/audit/snapshot"): EndpointPolicy(
        (),
        None,
        exception_reason=(
            "Internal development diagnostic; disabled by default and token protected."
        ),
    ),
    ("GET", "/health"): EndpointPolicy(
        (), None, exception_reason="Public liveness metadata contains no operational records."
    ),
    ("GET", "/v1/admin/audit"): EndpointPolicy(("audit.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/audit/export"): EndpointPolicy(
        ("audit.export",), "BACKOFFICE", mutation=True
    ),
    ("GET", "/v1/admin/audit/{event_id}"): EndpointPolicy(("audit.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/branches"): EndpointPolicy(("branches.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/branches/{branch_id}"): EndpointPolicy(("branches.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/cash-cuts"): EndpointPolicy(("cash_finance.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/cash-cuts/{cash_session_id}"): EndpointPolicy(
        ("cash_finance.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/cash-flow"): EndpointPolicy(("cash_finance.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/cash-flow/{movement_id:path}"): EndpointPolicy(
        ("cash_finance.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/cleaning-logs"): EndpointPolicy(("quality_hygiene.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/cleaning-logs/templates"): EndpointPolicy(
        ("quality_hygiene.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/cleaning-logs/{cleaning_log_id}"): EndpointPolicy(
        ("quality_hygiene.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/discounts"): EndpointPolicy(("discounts.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/discounts/{discount_id}"): EndpointPolicy(("discounts.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/equipment-maintenance/equipment"): EndpointPolicy(
        ("quality_hygiene.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/equipment-maintenance/equipment/{equipment_id}"): EndpointPolicy(
        ("quality_hygiene.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/incidents"): EndpointPolicy(("quality_hygiene.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/incidents/{incident_id}"): EndpointPolicy(
        ("quality_hygiene.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/inputs-supplies"): EndpointPolicy(("catalog.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/inputs-supplies/{product_id}"): EndpointPolicy(
        ("catalog.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/inventory"): EndpointPolicy(("inventory.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/inventory/{balance_id}"): EndpointPolicy(("inventory.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/inventory/{balance_id}/movements"): EndpointPolicy(
        ("inventory.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/orders"): EndpointPolicy(("orders.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/orders/{order_id}"): EndpointPolicy(("orders.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/prices"): EndpointPolicy(("pricing.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/prices/{entity_type}/{entity_id}"): EndpointPolicy(
        ("pricing.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/product-classes"): EndpointPolicy(("catalog.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/product-classes/{class_id}"): EndpointPolicy(
        ("catalog.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/production"): EndpointPolicy(("production.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/production/{production_id}"): EndpointPolicy(
        ("production.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/products"): EndpointPolicy(("catalog.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/products/{product_id}"): EndpointPolicy(("catalog.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/purchases"): EndpointPolicy(("purchases.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/purchases/{purchase_id}"): EndpointPolicy(("purchases.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/recipes-costs/products"): EndpointPolicy(("recipes.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/recipes-costs/products/{product_id}"): EndpointPolicy(
        ("recipes.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/reconciliation"): EndpointPolicy(("cash_finance.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/reconciliation/pending"): EndpointPolicy(
        ("cash_finance.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/reconciliation/{reconciliation_id}"): EndpointPolicy(
        ("cash_finance.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/reports"): EndpointPolicy(("reports.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/returns-corrections/corrections"): EndpointPolicy(
        ("returns_corrections.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/returns-corrections/corrections/{correction_id}"): EndpointPolicy(
        ("returns_corrections.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/returns-corrections/returns"): EndpointPolicy(
        ("returns_corrections.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/returns-corrections/returns/{return_id}"): EndpointPolicy(
        ("returns_corrections.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/roles"): EndpointPolicy(("roles.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/roles/permissions"): EndpointPolicy(("roles.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/roles/{role_id}"): EndpointPolicy(("roles.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/sales/tickets"): EndpointPolicy(("sales_tickets.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/sales/tickets/{ticket_id}"): EndpointPolicy(
        ("sales_tickets.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/sanitary-verifications"): EndpointPolicy(
        ("quality_hygiene.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/sanitary-verifications/templates"): EndpointPolicy(
        ("quality_hygiene.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/sanitary-verifications/{verification_id}"): EndpointPolicy(
        ("quality_hygiene.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/settings"): EndpointPolicy(("config.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/settings/{setting_key:path}"): EndpointPolicy(
        ("config.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/admin/suppliers"): EndpointPolicy(("suppliers.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/suppliers/{supplier_id}"): EndpointPolicy(("suppliers.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/transfers"): EndpointPolicy(("transfers.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/transfers/{transfer_id}"): EndpointPolicy(("transfers.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/users"): EndpointPolicy(("users.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/users/{user_id}"): EndpointPolicy(("users.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/waste"): EndpointPolicy(("waste.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/waste/reasons"): EndpointPolicy(("waste.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/waste/{waste_id}"): EndpointPolicy(("waste.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/workstations"): EndpointPolicy(("workstations.view",), "BACKOFFICE"),
    ("GET", "/v1/admin/workstations/{workstation_id}"): EndpointPolicy(
        ("workstations.view",), "BACKOFFICE"
    ),
    ("GET", "/v1/auth/me"): EndpointPolicy(
        (),
        None,
        exception_reason="Authenticated introspection requires no implicit capability grant.",
    ),
    ("GET", "/v1/cash-close/bootstrap"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/cash-close/reconciliation"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/cash-close/summary"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/cash-close/{close_id}"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/cash-sessions/current"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/corrections/bootstrap"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/corrections/history"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/corrections/history/{correction_id}"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/corrections/products"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/corrections/search"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/corrections/{target_document_id}"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/discounts"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/discounts/bootstrap"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/discounts/{discount_id}"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/operations/bootstrap"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/operations/catalog"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/operations/classes/{class_id}/products"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/operations/history"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/operations/{document_id}"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/orders"): EndpointPolicy(("orders.view",), "POS"),
    ("GET", "/v1/orders/bootstrap"): EndpointPolicy(("orders.view",), "POS"),
    ("GET", "/v1/orders/catalog"): EndpointPolicy(("orders.view",), "POS"),
    ("GET", "/v1/orders/classes/{class_id}/products"): EndpointPolicy(("orders.view",), "POS"),
    ("GET", "/v1/orders/{order_id}"): EndpointPolicy(("orders.view",), "POS"),
    ("GET", "/v1/payments"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/payments/bootstrap"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/payments/{payment_id}"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/pos/bootstrap"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/pos/catalog"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/pos/classes/{class_id}/products"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/returns/bootstrap"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/returns/classes/{class_id}/products"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/returns/history"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/returns/sales/{sale_id}"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/returns/search-sales"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/returns/{return_id}"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/sales/{sale_id}"): EndpointPolicy(("pos.operate",), "POS"),
    ("GET", "/v1/tickets"): EndpointPolicy(("sales_tickets.view",), "POS"),
    ("GET", "/v1/tickets/bootstrap"): EndpointPolicy(("sales_tickets.view",), "POS"),
    ("GET", "/v1/tickets/{ticket_id}"): EndpointPolicy(("sales_tickets.view",), "POS"),
    ("GET", "/v1/transfers/inbound/history"): EndpointPolicy(("transfers.view",), "POS"),
    ("GET", "/v1/transfers/inbound/pending"): EndpointPolicy(("transfers.view",), "POS"),
    ("GET", "/v1/transfers/outbound/history"): EndpointPolicy(("transfers.view",), "POS"),
    ("GET", "/v1/transfers/{transfer_id}"): EndpointPolicy(("transfers.view",), "POS"),
    ("PATCH", "/v1/admin/branches/{branch_id}"): EndpointPolicy(
        ("branches.manage",), "BACKOFFICE", mutation=True
    ),
    ("PATCH", "/v1/admin/discounts/{discount_id}"): EndpointPolicy(
        ("discounts.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("PATCH", "/v1/admin/equipment-maintenance/equipment/{equipment_id}"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("PATCH", "/v1/admin/incidents/{incident_id}"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("PATCH", "/v1/admin/inputs-supplies/{product_id}"): EndpointPolicy(
        ("catalog.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("PATCH", "/v1/admin/inputs-supplies/{product_id}/suppliers/{relation_id}"): EndpointPolicy(
        ("catalog.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("PATCH", "/v1/admin/prices/{entity_type}/{entity_id}"): EndpointPolicy(
        ("pricing.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("PATCH", "/v1/admin/product-classes/{class_id}"): EndpointPolicy(
        ("catalog.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("PATCH", "/v1/admin/production/{production_id}"): EndpointPolicy(
        ("production.manage",), "BACKOFFICE", mutation=True
    ),
    ("PATCH", "/v1/admin/products/{product_id}"): EndpointPolicy(
        ("catalog.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("PATCH", "/v1/admin/purchases/{purchase_id}"): EndpointPolicy(
        ("purchases.manage",), "BACKOFFICE", mutation=True
    ),
    ("PATCH", "/v1/admin/roles/{role_id}"): EndpointPolicy(
        ("roles.manage",), "BACKOFFICE", mutation=True
    ),
    ("PATCH", "/v1/admin/settings/{setting_key:path}"): EndpointPolicy(
        ("config.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("PATCH", "/v1/admin/suppliers/{supplier_id}"): EndpointPolicy(
        ("suppliers.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("PATCH", "/v1/admin/suppliers/{supplier_id}/contacts/{contact_id}"): EndpointPolicy(
        ("suppliers.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("PATCH", "/v1/admin/suppliers/{supplier_id}/products/{relation_id}"): EndpointPolicy(
        ("suppliers.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("PATCH", "/v1/admin/transfers/{transfer_id}"): EndpointPolicy(
        ("transfers.manage",), "BACKOFFICE", mutation=True
    ),
    ("PATCH", "/v1/admin/users/{user_id}"): EndpointPolicy(
        ("users.manage",), "BACKOFFICE", mutation=True
    ),
    ("PATCH", "/v1/admin/workstations/{workstation_id}"): EndpointPolicy(
        ("workstations.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/branches"): EndpointPolicy(
        ("branches.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/cleaning-logs"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/cleaning-logs/{cleaning_log_id}/cancel"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/cleaning-logs/{cleaning_log_id}/complete"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/discounts"): EndpointPolicy(
        ("discounts.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/discounts/{discount_id}/duplicate"): EndpointPolicy(
        ("discounts.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/equipment-maintenance/equipment"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/equipment-maintenance/equipment/{equipment_id}/status"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/equipment-maintenance/maintenance"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/equipment-maintenance/maintenance/{maintenance_id}/cancel"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    (
        "POST",
        "/v1/admin/equipment-maintenance/maintenance/{maintenance_id}/complete",
    ): EndpointPolicy(("quality_hygiene.manage",), "BACKOFFICE", mutation=True),
    ("POST", "/v1/admin/equipment-maintenance/maintenance/{maintenance_id}/start"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/incidents"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/incidents/{incident_id}/follow-ups"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/incidents/{incident_id}/reopen"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/incidents/{incident_id}/resolve"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/incidents/{incident_id}/status"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/inputs-supplies"): EndpointPolicy(
        ("catalog.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/inputs-supplies/{product_id}/status"): EndpointPolicy(
        ("catalog.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/inputs-supplies/{product_id}/suppliers"): EndpointPolicy(
        ("catalog.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/inventory/adjustments"): EndpointPolicy(
        ("inventory.adjust",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/orders/{order_id}/cancel"): EndpointPolicy(
        ("orders.cancel",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/orders/{order_id}/deliver"): EndpointPolicy(
        ("orders.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/orders/{order_id}/mark-ready"): EndpointPolicy(
        ("orders.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/product-classes"): EndpointPolicy(
        ("catalog.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/production"): EndpointPolicy(
        ("production.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/production/{production_id}/cancel"): EndpointPolicy(
        ("production.cancel",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/production/{production_id}/complete"): EndpointPolicy(
        ("production.execute",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/production/{production_id}/start"): EndpointPolicy(
        ("production.execute",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/products"): EndpointPolicy(
        ("catalog.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/products/{product_id}/availability"): EndpointPolicy(
        ("catalog.availability.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/purchases"): EndpointPolicy(
        ("purchases.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/purchases/direct-entry"): EndpointPolicy(
        ("purchases.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/purchases/{purchase_id}/cancel"): EndpointPolicy(
        ("purchases.cancel",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/purchases/{purchase_id}/confirm"): EndpointPolicy(
        ("purchases.confirm",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/purchases/{purchase_id}/receive"): EndpointPolicy(
        ("purchases.receive",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/recipes-costs/recipes"): EndpointPolicy(
        ("recipes.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/recipes-costs/recipes/{recipe_id}/activate"): EndpointPolicy(
        ("recipes.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/recipes-costs/recipes/{recipe_id}/apply-standard-cost"): EndpointPolicy(
        ("recipes.manage", "pricing.manage"), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/recipes-costs/recipes/{recipe_id}/duplicate"): EndpointPolicy(
        ("recipes.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/reconciliation"): EndpointPolicy(
        ("cash_finance.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/reconciliation/{reconciliation_id}/resolve"): EndpointPolicy(
        ("cash_finance.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/reports/{report_code}/export"): EndpointPolicy(
        ("reports.export",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/reports/{report_code}/preview"): EndpointPolicy(
        ("reports.view",), "BACKOFFICE"
    ),
    ("POST", "/v1/admin/roles"): EndpointPolicy(("roles.manage",), "BACKOFFICE", mutation=True),
    ("POST", "/v1/admin/roles/{role_id}/status"): EndpointPolicy(
        ("roles.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/roles/{role_id}/users/{user_id}"): EndpointPolicy(
        ("role_assignments.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/roles/{role_id}/users/{user_id}/remove"): EndpointPolicy(
        ("role_assignments.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/sales/tickets/{ticket_id}/reprint"): EndpointPolicy(
        ("sales_tickets.reprint",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/sanitary-verifications"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/sanitary-verifications/{verification_id}/cancel"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/sanitary-verifications/{verification_id}/complete"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/sanitary-verifications/{verification_id}/start"): EndpointPolicy(
        ("quality_hygiene.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/settings/{setting_key:path}/reset"): EndpointPolicy(
        ("config.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/suppliers"): EndpointPolicy(
        ("suppliers.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/suppliers/{supplier_id}/branches"): EndpointPolicy(
        ("suppliers.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/suppliers/{supplier_id}/contacts"): EndpointPolicy(
        ("suppliers.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/suppliers/{supplier_id}/products"): EndpointPolicy(
        ("suppliers.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/suppliers/{supplier_id}/status"): EndpointPolicy(
        ("suppliers.manage",), "BACKOFFICE", mutation=True, global_only=True
    ),
    ("POST", "/v1/admin/transfers"): EndpointPolicy(
        ("transfers.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/transfers/{transfer_id}/cancel"): EndpointPolicy(
        ("transfers.cancel",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/transfers/{transfer_id}/dispatch"): EndpointPolicy(
        ("transfers.execute",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/transfers/{transfer_id}/receive"): EndpointPolicy(
        ("transfers.execute",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/users"): EndpointPolicy(("users.manage",), "BACKOFFICE", mutation=True),
    ("POST", "/v1/admin/users/{user_id}/branch-assignments"): EndpointPolicy(
        ("role_assignments.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/users/{user_id}/branch-assignments/{branch_id}/deactivate"): EndpointPolicy(
        ("role_assignments.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/users/{user_id}/branch-assignments/{branch_id}/default"): EndpointPolicy(
        ("role_assignments.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/users/{user_id}/lock"): EndpointPolicy(
        ("users.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/users/{user_id}/roles"): EndpointPolicy(
        ("role_assignments.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/users/{user_id}/roles/{role_id}/remove"): EndpointPolicy(
        ("role_assignments.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/users/{user_id}/status"): EndpointPolicy(
        ("users.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/users/{user_id}/unlock"): EndpointPolicy(
        ("users.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/admin/waste"): EndpointPolicy(("waste.manage",), "BACKOFFICE", mutation=True),
    ("POST", "/v1/admin/workstations"): EndpointPolicy(
        ("workstations.manage",), "BACKOFFICE", mutation=True
    ),
    ("POST", "/v1/auth/login"): EndpointPolicy(
        (),
        None,
        exception_reason="Public authentication validates credentials without implicit authority.",
    ),
    ("POST", "/v1/cash-close/commit"): EndpointPolicy(("pos.operate",), "POS", mutation=True),
    ("POST", "/v1/cash-close/preview"): EndpointPolicy(("pos.operate",), "POS"),
    ("POST", "/v1/cash-sessions/open"): EndpointPolicy(("pos.operate",), "POS", mutation=True),
    ("POST", "/v1/corrections/commit"): EndpointPolicy(
        ("returns_corrections.manage",), "POS", mutation=True
    ),
    ("POST", "/v1/discounts"): EndpointPolicy(("discounts.manage",), "POS", mutation=True),
    ("POST", "/v1/operations/counter-transfer/commit"): EndpointPolicy(
        ("pos.operate",), "POS", mutation=True
    ),
    ("POST", "/v1/operations/waste/commit"): EndpointPolicy(("pos.operate",), "POS", mutation=True),
    ("POST", "/v1/orders"): EndpointPolicy(("orders.manage",), "POS", mutation=True),
    ("POST", "/v1/orders/{order_id}/cancel"): EndpointPolicy(
        ("orders.cancel",), "POS", mutation=True
    ),
    ("POST", "/v1/orders/{order_id}/deliver"): EndpointPolicy(
        ("orders.manage",), "POS", mutation=True
    ),
    ("POST", "/v1/orders/{order_id}/mark-ready"): EndpointPolicy(
        ("orders.manage",), "POS", mutation=True
    ),
    ("POST", "/v1/payments"): EndpointPolicy(("pos.operate",), "POS", mutation=True),
    ("POST", "/v1/returns/commit"): EndpointPolicy(
        ("returns_corrections.manage",), "POS", mutation=True
    ),
    ("POST", "/v1/sales/confirm"): EndpointPolicy(("pos.operate",), "POS", mutation=True),
    ("POST", "/v1/tickets/{ticket_id}/reprint"): EndpointPolicy(
        ("sales_tickets.reprint",), "POS", mutation=True
    ),
    ("POST", "/v1/transfers/dispatch/commit"): EndpointPolicy(
        ("transfers.execute",), "POS", mutation=True
    ),
    ("POST", "/v1/transfers/{transfer_id}/receive"): EndpointPolicy(
        ("transfers.execute",), "POS", mutation=True
    ),
}


def get_endpoint_policy(method: str, path: str) -> EndpointPolicy:
    policy = ENDPOINT_POLICIES.get((method, path))
    if policy is None:
        raise HTTPException(status_code=403, detail="This operation has no authorization policy.")
    return policy


def enforce_operation_policy(
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Generator[None, None, None]:
    route = request.scope.get("route")
    if not isinstance(route, APIRoute):
        raise HTTPException(status_code=403, detail="This operation has no authorization policy.")
    policy = ENDPOINT_POLICIES.get((request.method, route.path))
    try:
        policy = get_endpoint_policy(request.method, route.path)
        if policy.surface is not None and policy.surface not in current_user.allowed_surfaces:
            raise HTTPException(
                status_code=403, detail="This application surface is not authorized."
            )
        if policy.exception_reason and policy.surface is not None:
            # The privileged service selects its capability from the typed lifecycle change.
            # Keep its exclusive transaction and wrap only denial auditing at the HTTP boundary.
            yield
            return
        if not policy.capabilities:
            raise HTTPException(status_code=403, detail="This operation has no capability policy.")
        for capability in policy.capabilities:
            require_branches(current_user, capability, (), global_only=policy.global_only)
        context = bind_authorization_scope(
            session,
            user=current_user,
            capabilities=policy.capabilities,
            mutation=policy.mutation,
            global_only=policy.global_only,
            request_id=request.headers.get("X-Request-ID"),
            surface=policy.surface,
        )
        for parameter in route.dependant.query_params:
            if parameter.name not in {
                "branch_id",
                "source_branch_id",
                "origin_branch_id",
                "destination_branch_id",
                "receiving_branch_id",
            }:
                continue
            value = request.query_params.get(parameter.alias)
            if value is None:
                continue
            try:
                branch_id = UUID(value)
            except ValueError:
                continue  # FastAPI owns malformed parameter validation.
            for capability in policy.capabilities:
                require_branches(context.user, capability, [branch_id])
        yield
    except HTTPException as error:
        denied_context = authorization_scope(session)
        scoped_missing = (
            error.status_code == 404
            and policy is not None
            and policy.mutation
            and denied_context is not None
            and denied_context.branch_ids is not None
        )
        if error.status_code == 403 or scoped_missing:
            session.rollback()
            _record_denied_operation(session, request, route, current_user, policy)
        raise


def _record_denied_operation(
    session: Session,
    request: Request,
    route: APIRoute,
    user: AuthenticatedUser,
    policy: EndpointPolicy | None,
) -> None:
    """Persist denial only after rolling back every attempted business write."""
    context = authorization_scope(session)
    branches = sorted(context.branch_ids or (), key=str) if context is not None else []
    capabilities = list(policy.capabilities) if policy is not None else []
    provenance = {
        "actor_id": str(user.id),
        "capabilities": capabilities,
        "authorization_version": user.authorization_version,
        "scope_type": ("BRANCH_SET" if branches else "GLOBAL")
        if context is not None
        else "UNRESOLVED",
        "branch_ids": [str(branch) for branch in branches],
        "decision": "DENIED",
        "surface": policy.surface if policy is not None else None,
    }
    # This independent audit transaction never carries the rejected request's identity map.
    with Session(bind=session.get_bind()) as audit_session:
        audit_session.add(
            AuditLog(
                actor_id=user.id,
                action="authorization.denied",
                resource_type="api_operation",
                resource_id=f"{request.method} {route.path}"[:120],
                request_id=(request.headers.get("X-Request-ID") or "").strip()[:120] or None,
                metadata_={
                    "authorization": provenance,
                    "method": request.method,
                    "path_template": route.path,
                    "required_capabilities": capabilities,
                    "reason": "CAPABILITY_SCOPE_OR_RESOURCE_UNAVAILABLE",
                    "result": "denied",
                },
            )
        )
        audit_session.commit()


def install_access_policies(router: APIRouter) -> None:
    """Install before the router is included in the application and cloned by FastAPI."""
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        policies = [ENDPOINT_POLICIES.get((method, route.path)) for method in route.methods]
        if all(
            policy is not None and policy.exception_reason and policy.surface is None
            for policy in policies
        ):
            continue
        route.dependencies.append(Depends(enforce_operation_policy))
        declared = {
            capability for policy in policies if policy for capability in policy.capabilities
        }
        route.openapi_extra = {
            **(route.openapi_extra or {}),
            "x-required-capabilities": sorted(declared),
            "x-authorization-policy": "explicit-deny-by-default",
        }
