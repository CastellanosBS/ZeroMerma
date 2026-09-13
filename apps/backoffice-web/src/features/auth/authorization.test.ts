import { describe, expect, it } from "vitest";

import { authorizationUser } from "../../test-support/authorization";
import {
  getAuthorizedAdminLanding,
  getAuthorizedAdminNavigation,
} from "../admin/navigation/adminNavigation";
import { hasEffectiveCapability } from "./authorization";

describe("server-resolved authorization presentation", () => {
  it("rejects capabilities resolved for another application surface", () => {
    const user = authorizationUser([
      { capability: "catalog.view", scope_type: "GLOBAL", branch_ids: [] },
    ]);
    expect(hasEffectiveCapability({ ...user, authorization_surface: "POS" }, "catalog.view")).toBe(
      false,
    );
    expect(hasEffectiveCapability({ ...user, authorization_surface: null }, "catalog.view")).toBe(
      false,
    );
  });
  it("denies missing grants, empty branch sets and inactive users without inferring superadministrator authority", () => {
    const user = {
      ...authorizationUser(),
      email: "admin@zeromerma.local",
      is_superadministrator: true,
    };
    expect(hasEffectiveCapability(user, "users.manage")).toBe(false);
    expect(
      hasEffectiveCapability(
        authorizationUser([{ capability: "users.view", scope_type: "BRANCH_SET", branch_ids: [] }]),
        "users.view",
      ),
    ).toBe(false);
    expect(
      hasEffectiveCapability(
        {
          ...authorizationUser([
            { capability: "users.view", scope_type: "GLOBAL", branch_ids: [] },
          ]),
          is_active: false,
        },
        "users.view",
      ),
    ).toBe(false);
  });

  it("keeps capabilities independent and requires both ends of a transfer", () => {
    const user = authorizationUser([
      { capability: "inventory.view", scope_type: "BRANCH_SET", branch_ids: ["north", "south"] },
      { capability: "inventory.adjust", scope_type: "BRANCH_SET", branch_ids: ["north"] },
      { capability: "transfers.execute", scope_type: "BRANCH_SET", branch_ids: ["north"] },
      { capability: "reports.view", scope_type: "GLOBAL", branch_ids: [] },
    ]);
    expect(hasEffectiveCapability(user, "inventory.view", ["south"])).toBe(true);
    expect(hasEffectiveCapability(user, "inventory.adjust", ["south"])).toBe(false);
    expect(hasEffectiveCapability(user, "inventory.adjust", ["north"])).toBe(true);
    expect(hasEffectiveCapability(user, "transfers.execute", ["north", "south"])).toBe(false);
    expect(hasEffectiveCapability(user, "reports.export")).toBe(false);
  });

  it("requires explicit GLOBAL for shared master changes without treating branch reads as global", () => {
    const user = authorizationUser([
      { capability: "catalog.manage", scope_type: "BRANCH_SET", branch_ids: ["north"] },
    ]);
    expect(hasEffectiveCapability(user, "catalog.manage", [], true)).toBe(false);
    expect(
      hasEffectiveCapability(
        authorizationUser([{ capability: "catalog.manage", scope_type: "GLOBAL", branch_ids: [] }]),
        "catalog.manage",
        [],
        true,
      ),
    ).toBe(true);
  });

  it("selects a permitted landing, hides empty sections and preserves release exclusions", () => {
    expect(getAuthorizedAdminLanding(authorizationUser())).toBeNull();
    const user = authorizationUser([
      { capability: "inventory.view", scope_type: "BRANCH_SET", branch_ids: ["north"] },
      { capability: "roles.view", scope_type: "GLOBAL", branch_ids: [] },
    ]);
    expect(getAuthorizedAdminLanding(user)).toBe("/admin/inventario");
    expect(
      getAuthorizedAdminNavigation(user).flatMap((section) =>
        section.items.map((item) => item.key),
      ),
    ).toEqual(["inventory"]);
  });
});
