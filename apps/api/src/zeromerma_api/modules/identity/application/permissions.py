from __future__ import annotations

from dataclasses import dataclass

from zeromerma_api.modules.identity.domain.constants import (
    IDENTITY_SURFACE_BACKOFFICE,
    IDENTITY_SURFACE_POS,
)


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    label: str
    description: str
    module: str
    module_label: str
    action: str
    surfaces: tuple[str, ...]
    is_sensitive: bool = False


PERMISSION_CATALOG: tuple[PermissionDefinition, ...] = (
    PermissionDefinition(
        code="pos.operate",
        label="Operar POS",
        description="Permite operar el punto de venta en sucursales asignadas.",
        module="pos",
        module_label="POS",
        action="operate",
        surfaces=(IDENTITY_SURFACE_POS,),
    ),
    PermissionDefinition(
        code="sales_tickets.view",
        label="Consultar ventas / tickets",
        description="Permite revisar ventas, tickets y su trazabilidad.",
        module="sales_tickets",
        module_label="Ventas / Tickets",
        action="view",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
    ),
    PermissionDefinition(
        code="orders.manage",
        label="Gestionar pedidos",
        description="Permite consultar y actualizar pedidos operativos.",
        module="orders",
        module_label="Pedidos",
        action="manage",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
    ),
    PermissionDefinition(
        code="returns_corrections.manage",
        label="Gestionar devoluciones / correcciones",
        description="Permite operar reversas y correcciones auditadas.",
        module="returns_corrections",
        module_label="Devoluciones / Correcciones",
        action="manage",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="catalog_products.manage",
        label="Gestionar catalogo y precios",
        description="Permite administrar productos, clases, recetas, costos y precios.",
        module="catalog_costs",
        module_label="Catalogo y costos",
        action="manage",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="discounts.manage",
        label="Gestionar descuentos",
        description="Permite crear y modificar reglas de descuento.",
        module="discounts",
        module_label="Descuentos",
        action="manage",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="inventory.adjust",
        label="Ajustar inventario",
        description="Permite ejecutar ajustes de inventario auditados.",
        module="inventory",
        module_label="Inventario",
        action="adjust",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="multibranch_operations.manage",
        label="Gestionar operaciones multisucursal",
        description="Permite administrar sucursales, estaciones, transferencias y produccion.",
        module="multibranch_operations",
        module_label="Operacion multisucursal",
        action="manage",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="purchases_supply.manage",
        label="Gestionar compras y abastecimiento",
        description="Permite administrar proveedores, compras e insumos.",
        module="purchases_supply",
        module_label="Compras y abastecimiento",
        action="manage",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="cash_finance.view",
        label="Consultar caja y finanzas",
        description="Permite revisar cortes, conciliacion y flujo de efectivo.",
        module="cash_finance",
        module_label="Caja y finanzas",
        action="view",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="cash_finance.manage",
        label="Gestionar conciliaciones financieras",
        description="Permite crear y resolver documentos financieros auditados.",
        module="cash_finance",
        module_label="Caja y finanzas",
        action="manage",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="quality_hygiene.manage",
        label="Gestionar calidad e higiene",
        description="Permite administrar limpieza, verificaciones, incidencias y mantenimiento.",
        module="quality_hygiene",
        module_label="Calidad e higiene",
        action="manage",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
    ),
    PermissionDefinition(
        code="users.manage",
        label="Gestionar usuarios",
        description="Permite crear usuarios, cambiar estado y administrar accesos.",
        module="control",
        module_label="Control",
        action="manage_users",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="roles.manage",
        label="Gestionar roles y permisos",
        description="Permite modificar roles, permisos y asignaciones.",
        module="control",
        module_label="Control",
        action="manage_roles",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="audit.view",
        label="Consultar auditoria",
        description="Permite revisar eventos auditables del sistema.",
        module="audit",
        module_label="Auditoria",
        action="view",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
    PermissionDefinition(
        code="reports.export",
        label="Exportar reportes",
        description="Permite descargar reportes operativos disponibles.",
        module="reports",
        module_label="Reportes",
        action="export",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
    ),
    PermissionDefinition(
        code="config.manage",
        label="Gestionar configuracion",
        description="Permite modificar configuracion operativa del sistema.",
        module="configuration",
        module_label="Configuracion",
        action="manage",
        surfaces=(IDENTITY_SURFACE_BACKOFFICE,),
        is_sensitive=True,
    ),
)

PERMISSION_CODES = tuple(permission.code for permission in PERMISSION_CATALOG)
SENSITIVE_PERMISSION_CODES = tuple(
    permission.code for permission in PERMISSION_CATALOG if permission.is_sensitive
)

