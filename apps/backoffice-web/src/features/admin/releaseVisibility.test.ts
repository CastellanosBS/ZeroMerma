import { describe, expect, it } from "vitest";

import { adminModules } from "./adminModules";
import {
  DEFAULT_ADMIN_RELEASE_PATH,
  getAdminModuleReleaseRedirect,
  isAdminModuleVisibleInCurrentRelease,
  RELEASE_HIDDEN_ADMIN_MODULE_KEYS,
} from "./releaseVisibility";

const expectedHiddenModuleKeys = [
  "dashboard",
  "alerts",
  "recipesCosts",
  "discounts",
  "operationalPayments",
  "cleaningLogs",
  "sanitaryChecks",
  "rolesPermissions",
  "settings",
];

describe("backoffice release visibility", () => {
  it("centralizes exactly the nine DEC-02 hidden module keys", () => {
    expect(RELEASE_HIDDEN_ADMIN_MODULE_KEYS).toEqual(expectedHiddenModuleKeys);
  });

  it("redirects every hidden module to the deterministic visible products route", () => {
    for (const key of RELEASE_HIDDEN_ADMIN_MODULE_KEYS) {
      expect(isAdminModuleVisibleInCurrentRelease(key)).toBe(false);
      expect(getAdminModuleReleaseRedirect(key)).toBe(DEFAULT_ADMIN_RELEASE_PATH);
    }
  });

  it("keeps every other declared module visible without release redirect", () => {
    const visibleModules = adminModules.filter(
      (module) => !expectedHiddenModuleKeys.includes(module.key),
    );

    expect(visibleModules).toHaveLength(adminModules.length - 9);
    for (const module of visibleModules) {
      expect(isAdminModuleVisibleInCurrentRelease(module.key)).toBe(true);
      expect(getAdminModuleReleaseRedirect(module.key)).toBeNull();
    }
  });
});
