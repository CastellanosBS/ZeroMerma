import { adminModules, adminSections, getAdminModulesBySection } from "../adminModules";
import { isAdminModuleVisibleInCurrentRelease } from "../releaseVisibility";
import type { AdminModuleKey, AdminSectionKey } from "../adminTypes";
import type { AdminNavigationIconName } from "./AdminNavigationIcon";
import type { AuthenticatedUser } from "../../../lib/api";
import { canReadAdminModule } from "./adminCapabilities";

export type AdminRoutePath = (typeof adminModules)[number]["path"] | "/admin";

export interface AdminNavigationItem {
  key: AdminModuleKey;
  label: string;
  path: AdminRoutePath;
  description: string;
  status: (typeof adminModules)[number]["status"];
}

export interface AdminNavigationSection {
  description: string;
  icon: AdminNavigationIconName;
  key: AdminSectionKey;
  title: string;
  items: AdminNavigationItem[];
}

const sectionIconByKey: Record<AdminSectionKey, AdminNavigationIconName> = {
  cashFinance: "wallet",
  catalogCosts: "package",
  control: "settings",
  multibranchOperations: "building",
  principal: "home",
  purchasesSupply: "truck",
  qualityHygiene: "shieldCheck",
  salesOrders: "receipt",
};

export const adminNavigationSections: AdminNavigationSection[] = adminSections
  .map((section) => ({
    key: section.key,
    title: section.title,
    description: section.description,
    icon: sectionIconByKey[section.key],
    items: getAdminModulesBySection(section.key)
      .filter((module) => isAdminModuleVisibleInCurrentRelease(module.key))
      .map((module) => ({
        key: module.key,
        label: module.title,
        path: module.path,
        description: module.description,
        status: module.status,
      })),
  }))
  .filter((section) => section.items.length > 0);

export const adminNavigationItems = adminNavigationSections.flatMap((section) => section.items);

export function getAuthorizedAdminNavigation(user: AuthenticatedUser | null) {
  return adminNavigationSections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => canReadAdminModule(user, item.key)),
    }))
    .filter((section) => section.items.length > 0);
}

export function getAuthorizedAdminLanding(user: AuthenticatedUser | null) {
  return getAuthorizedAdminNavigation(user)[0]?.items[0]?.path ?? null;
}

export function getAdminNavigationItem(pathname: string): AdminNavigationItem {
  return (
    adminNavigationItems.find((item) => pathname === item.path) ??
    adminNavigationItems.find((item) => pathname.startsWith(`${item.path}/`)) ??
    adminNavigationItems[0]
  );
}
