import { describe, expect, it } from "vitest";

import { resolvePosEntryRoute } from "./route-state";

describe("resolvePosEntryRoute", () => {
  it("routes unauthenticated operators to login", () => {
    expect(resolvePosEntryRoute({ isAuthenticated: false, hasActiveCashSession: false })).toBe(
      "/login",
    );
  });

  it("routes authenticated operators to the gate when there is no session", () => {
    expect(resolvePosEntryRoute({ isAuthenticated: true, hasActiveCashSession: false })).toBe(
      "/cash-session/open",
    );
  });

  it("routes authenticated operators directly to POS when the session is already open", () => {
    expect(resolvePosEntryRoute({ isAuthenticated: true, hasActiveCashSession: true })).toBe(
      "/pos",
    );
  });
});
