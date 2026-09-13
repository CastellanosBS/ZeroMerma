from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

PermissionCode = Literal[
    "pos.operate",
    "sales_tickets.view",
    "sales_tickets.reprint",
    "orders.view",
    "orders.manage",
    "orders.cancel",
    "returns_corrections.view",
    "returns_corrections.manage",
    "catalog.view",
    "catalog.manage",
    "catalog.availability.manage",
    "pricing.view",
    "pricing.manage",
    "recipes.view",
    "recipes.manage",
    "discounts.view",
    "discounts.manage",
    "inventory.view",
    "inventory.adjust",
    "branches.view",
    "branches.manage",
    "workstations.view",
    "workstations.manage",
    "transfers.view",
    "transfers.manage",
    "transfers.execute",
    "transfers.cancel",
    "production.view",
    "production.manage",
    "production.execute",
    "production.cancel",
    "waste.view",
    "waste.manage",
    "suppliers.view",
    "suppliers.manage",
    "purchases.view",
    "purchases.manage",
    "purchases.confirm",
    "purchases.receive",
    "purchases.cancel",
    "cash_finance.view",
    "cash_finance.manage",
    "quality_hygiene.view",
    "quality_hygiene.manage",
    "users.view",
    "users.manage",
    "roles.view",
    "roles.manage",
    "role_assignments.manage",
    "audit.view",
    "audit.export",
    "reports.view",
    "reports.export",
    "config.view",
    "config.manage",
]

SUPERADMIN_ROLE_CODE = "explicit_superadmin"
INITIAL_OWNER_DESIGNATION = "ZEROMERMA_OWNER"

# Shared operations explicitly classified by the canonical functional operation matrix.
POS_PERMISSION_CODES: tuple[PermissionCode, ...] = (
    "pos.operate",
    "orders.view",
    "orders.manage",
    "orders.cancel",
    "sales_tickets.view",
    "sales_tickets.reprint",
    "transfers.view",
    "transfers.execute",
    "returns_corrections.manage",
    "discounts.manage",
)


@dataclass(frozen=True)
class PermissionDefinition:
    code: PermissionCode
    label: str
    description: str
    module: str
    module_label: str
    action: str
    surfaces: tuple[str, ...]
    is_sensitive: bool = False


_MODULE_LABELS = {
    "pos": "POS",
    "sales_tickets": "Ventas / Tickets",
    "orders": "Pedidos",
    "returns_corrections": "Devoluciones / Correcciones",
    "catalog": "Catálogo",
    "pricing": "Precios",
    "recipes": "Recetas",
    "discounts": "Descuentos",
    "inventory": "Inventario",
    "branches": "Sucursales",
    "workstations": "Estaciones",
    "transfers": "Transferencias",
    "production": "Producción",
    "waste": "Merma",
    "suppliers": "Proveedores",
    "purchases": "Compras",
    "cash_finance": "Caja y finanzas",
    "quality_hygiene": "Calidad e higiene",
    "users": "Usuarios",
    "roles": "Roles",
    "role_assignments": "Asignaciones de roles",
    "audit": "Auditoría",
    "reports": "Reportes",
    "config": "Configuración",
}
_ACTION_LABELS = {
    "view": "Consultar",
    "manage": "Gestionar",
    "operate": "Operar",
    "reprint": "Reimprimir",
    "cancel": "Cancelar",
    "adjust": "Ajustar",
    "execute": "Ejecutar",
    "confirm": "Confirmar",
    "receive": "Recibir",
    "export": "Exportar",
    "availability.manage": "Gestionar disponibilidad",
}


def _definition(code: PermissionCode) -> PermissionDefinition:
    module, action = code.split(".", maxsplit=1)
    label = f"{_ACTION_LABELS[action]} {_MODULE_LABELS[module]}"
    return PermissionDefinition(
        code=code,
        label=label,
        description=f"{label} dentro del alcance autorizado.",
        module=module,
        module_label=_MODULE_LABELS[module],
        action=action,
        surfaces=("POS",)
        if code == "pos.operate"
        else (("POS", "BACKOFFICE") if code in POS_PERMISSION_CODES else ("BACKOFFICE",)),
        is_sensitive=action != "view" or module in {"audit", "config", "users", "roles"},
    )


PERMISSION_CODES: tuple[PermissionCode, ...] = get_args(PermissionCode)
PERMISSION_CATALOG = tuple(_definition(code) for code in PERMISSION_CODES)
SENSITIVE_PERMISSION_CODES = tuple(
    permission.code for permission in PERMISSION_CATALOG if permission.is_sensitive
)
