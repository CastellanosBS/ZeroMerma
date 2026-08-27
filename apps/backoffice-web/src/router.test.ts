import { describe, expect, it } from "vitest";

import { adminModules } from "./features/admin/adminModules";
import {
  DEFAULT_ADMIN_RELEASE_PATH,
  getAdminModuleReleaseRedirect,
  RELEASE_HIDDEN_ADMIN_MODULE_KEYS,
} from "./features/admin/releaseVisibility";
import { getBackofficeDevelopmentRouteRedirect } from "./router";

describe("backoffice release routes", () => {
  it("gates all nine hidden admin module routes with the shared release policy", () => {
    expect(
      adminModules
        .filter((module) => RELEASE_HIDDEN_ADMIN_MODULE_KEYS.includes(module.key as never))
        .map((module) => ({
          key: module.key,
          path: module.path,
          redirect: getAdminModuleReleaseRedirect(module.key),
        })),
    ).toEqual([
      { key: "dashboard", path: "/admin/dashboard", redirect: DEFAULT_ADMIN_RELEASE_PATH },
      { key: "alerts", path: "/admin/alertas", redirect: DEFAULT_ADMIN_RELEASE_PATH },
      {
        key: "recipesCosts",
        path: "/admin/recetas-costos",
        redirect: DEFAULT_ADMIN_RELEASE_PATH,
      },
      { key: "discounts", path: "/admin/descuentos", redirect: DEFAULT_ADMIN_RELEASE_PATH },
      {
        key: "operationalPayments",
        path: "/admin/pagos-operativos",
        redirect: DEFAULT_ADMIN_RELEASE_PATH,
      },
      {
        key: "cleaningLogs",
        path: "/admin/bitacoras-limpieza",
        redirect: DEFAULT_ADMIN_RELEASE_PATH,
      },
      {
        key: "sanitaryChecks",
        path: "/admin/verificaciones-sanitarias",
        redirect: DEFAULT_ADMIN_RELEASE_PATH,
      },
      {
        key: "rolesPermissions",
        path: "/admin/roles-permisos",
        redirect: DEFAULT_ADMIN_RELEASE_PATH,
      },
      { key: "settings", path: "/admin/configuracion", redirect: DEFAULT_ADMIN_RELEASE_PATH },
    ]);
  });

  it("keeps representative approved routes available", () => {
    expect(getAdminModuleReleaseRedirect("products")).toBeNull();
    expect(getAdminModuleReleaseRedirect("sales")).toBeNull();
    expect(getAdminModuleReleaseRedirect("reports")).toBeNull();
  });

  it("keeps public demo routes only in development", () => {
    expect(getBackofficeDevelopmentRouteRedirect("/", true)).toBeNull();
    expect(getBackofficeDevelopmentRouteRedirect("/health", true)).toBeNull();
    expect(getBackofficeDevelopmentRouteRedirect("/", false)).toBe("/login");
    expect(getBackofficeDevelopmentRouteRedirect("/health", false)).toBe("/login");
  });
});
