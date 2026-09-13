export type AdminModuleStatus = "ready" | "partial" | "preparation" | "planned";

export type AdminScopeFilterKind =
  | "branch"
  | "brand"
  | "dateRange"
  | "status"
  | "shift"
  | "user"
  | "search";

export interface AdminScope {
  branchId?: string | null;
  brandId?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
  status?: string | null;
  shiftId?: string | null;
  userId?: string | null;
}

export type PermissionAction =
  | "view"
  | "create"
  | "update"
  | "delete"
  | "void"
  | "approve"
  | "export"
  | "configure";

export interface AdminMetricDefinition {
  description?: string;
  key: string;
  label: string;
  tone?: "default" | "success" | "warning" | "danger" | "info";
  value: string;
}

export interface AdminTableColumn {
  key: string;
  label: string;
}

export type AdminModuleKey =
  | "dashboard"
  | "alerts"
  | "products"
  | "categories"
  | "recipesCosts"
  | "prices"
  | "discounts"
  | "sales"
  | "orders"
  | "returnsCorrections"
  | "branches"
  | "registersStations"
  | "inventory"
  | "transfers"
  | "production"
  | "waste"
  | "suppliers"
  | "purchases"
  | "suppliesConsumables"
  | "cashCuts"
  | "reconciliation"
  | "operationalPayments"
  | "cashFlow"
  | "cleaningLogs"
  | "sanitaryChecks"
  | "incidents"
  | "equipmentMaintenance"
  | "users"
  | "rolesPermissions"
  | "audit"
  | "reports"
  | "settings";

export interface AdminModuleDefinition {
  actionLabel?: string;
  auditEntityType: string;
  description: string;
  detailTitle: string;
  emptyDescription: string;
  filters: AdminScopeFilterKind[];
  key: AdminModuleKey;
  metrics: AdminMetricDefinition[];
  path: `/admin/${string}`;
  permissionActions: PermissionAction[];
  routeSlug: string;
  sectionKey: AdminSectionKey;
  status: AdminModuleStatus;
  tableColumns: AdminTableColumn[];
  title: string;
}

export type AdminSectionKey =
  | "principal"
  | "catalogCosts"
  | "salesOrders"
  | "multibranchOperations"
  | "purchasesSupply"
  | "cashFinance"
  | "qualityHygiene"
  | "control";

export interface AdminSectionDefinition {
  description: string;
  key: AdminSectionKey;
  title: string;
}
