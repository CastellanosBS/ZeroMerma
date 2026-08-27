import { describe, expect, it } from "vitest";

import { buildBackofficeLoginUrl, shouldRouteToBackoffice } from "./auth-surfaces";

describe("auth surface routing", () => {
  it("keeps POS users in the POS flow", () => {
    expect(shouldRouteToBackoffice({ default_surface: "POS" })).toBe(false);
  });

  it("routes backoffice users to the admin app", () => {
    expect(shouldRouteToBackoffice({ default_surface: "BACKOFFICE" })).toBe(true);
  });

  it("routes to independent backoffice login without exposing credentials in the URL", () => {
    const url = buildBackofficeLoginUrl("http://localhost:5174");

    expect(url).toBe("http://localhost:5174/login");
    expect(url).not.toContain("access_token");
    expect(url).not.toContain("token-123");
  });
});
