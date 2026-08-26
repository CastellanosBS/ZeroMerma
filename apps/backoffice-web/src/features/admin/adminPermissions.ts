import type { AdminRoleKey, PermissionAction, PermissionScope } from "./adminTypes";

export const adminPermissionActions: PermissionAction[] = [
  "view",
  "create",
  "update",
  "delete",
  "void",
  "approve",
  "export",
  "configure",
];

export const adminPermissionScopes: PermissionScope[] = [
  "all_branches",
  "assigned_branches",
  "own_branch",
  "own_records",
];

export const adminRoleLabels: Record<AdminRoleKey, string> = {
  super_admin: "Super admin",
  general_admin: "Administrador general",
  branch_manager: "Gerente de sucursal",
  operations_supervisor: "Supervisor operativo",
  cashier: "Cajero",
  production: "Producción",
  auditor: "Auditor / consulta",
};

// Backend RBAC should expose module/action/scope grants. These constants keep the
// backoffice shell aligned with that future contract without adding fake security.
export const sensitiveAdminActions: PermissionAction[] = ["void", "approve", "configure", "delete"];
