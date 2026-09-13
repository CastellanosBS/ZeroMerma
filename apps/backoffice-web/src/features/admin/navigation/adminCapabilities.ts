import type { AuthenticatedUser } from "../../../lib/api";
import { hasEffectiveCapability, type PermissionCode } from "../../auth/authorization";
import type { AdminModuleKey } from "../adminTypes";

// UI routes reference backend capability codes; hidden release modules stay hidden.
// null means no released authority has been defined for this placeholder.
export const adminReadCapabilities = {
  dashboard: null,
  alerts: null,
  products: "catalog.view",
  categories: "catalog.view",
  recipesCosts: "recipes.view",
  prices: "pricing.view",
  discounts: "discounts.view",
  sales: "sales_tickets.view",
  orders: "orders.view",
  returnsCorrections: "returns_corrections.view",
  branches: "branches.view",
  registersStations: "workstations.view",
  inventory: "inventory.view",
  transfers: "transfers.view",
  production: "production.view",
  waste: "waste.view",
  suppliers: "suppliers.view",
  purchases: "purchases.view",
  suppliesConsumables: "catalog.view",
  cashCuts: "cash_finance.view",
  reconciliation: "cash_finance.view",
  operationalPayments: "cash_finance.view",
  cashFlow: "cash_finance.view",
  cleaningLogs: "quality_hygiene.view",
  sanitaryChecks: "quality_hygiene.view",
  incidents: "quality_hygiene.view",
  equipmentMaintenance: "quality_hygiene.view",
  users: "users.view",
  rolesPermissions: "roles.view",
  audit: "audit.view",
  reports: "reports.view",
  settings: "config.view",
} as const satisfies Record<AdminModuleKey, PermissionCode | null>;

export function canReadAdminModule(user: AuthenticatedUser | null, moduleKey: AdminModuleKey) {
  const capability = adminReadCapabilities[moduleKey];
  return capability !== null && hasEffectiveCapability(user, capability);
}
