import { describe, expect, it } from "vitest";

import { resolvePosEntryRoute } from "./route-state";

describe("resolvePosEntryRoute", () => {
  it("routes unauthenticated operators to login", () => {
    expect(resolvePosEntryRoute({ hasAccessToken: false, hasActiveCashSession: false })).toBe(
      "/login",
    );
  });

  it("routes authenticated operators without a session to the open screen", () => {
    expect(resolvePosEntryRoute({ hasAccessToken: true, hasActiveCashSession: false })).toBe(
      "/cash-session/open",
    );
  });

  it("routes authenticated operators with an active session to the register home", () => {
    expect(resolvePosEntryRoute({ hasAccessToken: true, hasActiveCashSession: true })).toBe("/");
  });
});
