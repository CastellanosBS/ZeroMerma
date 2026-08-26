import { describe, expect, it } from "vitest";

import { adminModules, adminSections } from "./adminModules";

describe("admin module configuration", () => {
  it("defines unique route slugs and paths", () => {
    const paths = adminModules.map((module) => module.path);
    const slugs = adminModules.map((module) => module.routeSlug);

    expect(new Set(paths).size).toBe(paths.length);
    expect(new Set(slugs).size).toBe(slugs.length);
  });

  it("assigns every module to a declared section", () => {
    const sectionKeys = new Set(adminSections.map((section) => section.key));

    for (const module of adminModules) {
      expect(sectionKeys.has(module.sectionKey)).toBe(true);
    }
  });

  it("prepares a multisucursal scope for operational and financial modules", () => {
    const scopedModules = adminModules.filter((module) =>
      [
        "salesOrders",
        "multibranchOperations",
        "cashFinance",
        "qualityHygiene",
      ].includes(module.sectionKey),
    );

    expect(scopedModules.every((module) => module.filters.includes("branch"))).toBe(true);
  });
});
