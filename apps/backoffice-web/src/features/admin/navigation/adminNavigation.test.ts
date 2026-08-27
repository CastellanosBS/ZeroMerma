import { describe, expect, it } from "vitest";

import { RELEASE_HIDDEN_ADMIN_MODULE_KEYS } from "../releaseVisibility";
import { adminNavigationItems, adminNavigationSections } from "./adminNavigation";

describe("admin release navigation", () => {
  it("omits all nine hidden release modules", () => {
    const navigationKeys = adminNavigationItems.map((item) => item.key);

    for (const key of RELEASE_HIDDEN_ADMIN_MODULE_KEYS) {
      expect(navigationKeys).not.toContain(key);
    }
  });

  it("keeps every other declared admin module in navigation", () => {
    expect(adminNavigationItems.map((item) => item.key)).toEqual([
      "products",
      "categories",
      "prices",
      "sales",
      "orders",
      "returnsCorrections",
      "branches",
      "registersStations",
      "inventory",
      "transfers",
      "production",
      "waste",
      "suppliers",
      "purchases",
      "suppliesConsumables",
      "cashCuts",
      "reconciliation",
      "cashFlow",
      "incidents",
      "equipmentMaintenance",
      "users",
      "audit",
      "reports",
    ]);
  });

  it("does not retain empty navigation sections", () => {
    expect(adminNavigationSections.every((section) => section.items.length > 0)).toBe(true);
  });
});
