import type { AdminModuleKey } from "./adminTypes";

export const RELEASE_HIDDEN_ADMIN_MODULE_KEYS = [
  "dashboard",
  "alerts",
  "recipesCosts",
  "discounts",
  "operationalPayments",
  "cleaningLogs",
  "sanitaryChecks",
  "rolesPermissions",
  "settings",
] as const satisfies readonly AdminModuleKey[];

const releaseHiddenAdminModuleKeys = new Set<AdminModuleKey>(
  RELEASE_HIDDEN_ADMIN_MODULE_KEYS,
);

export const DEFAULT_ADMIN_RELEASE_PATH = "/admin/productos" as const;

export function isAdminModuleVisibleInCurrentRelease(moduleKey: AdminModuleKey): boolean {
  return !releaseHiddenAdminModuleKeys.has(moduleKey);
}

export function getAdminModuleReleaseRedirect(moduleKey: AdminModuleKey) {
  return isAdminModuleVisibleInCurrentRelease(moduleKey) ? null : DEFAULT_ADMIN_RELEASE_PATH;
}
