import { describe, expect, it } from "vitest";

import { buildBackofficeAdminUrl, shouldRouteToBackoffice } from "./auth-surfaces";

describe("auth surface routing", () => {
  it("keeps POS users in the POS flow", () => {
    expect(shouldRouteToBackoffice({ default_surface: "POS" })).toBe(false);
  });

  it("routes backoffice users to the admin app", () => {
    expect(shouldRouteToBackoffice({ default_surface: "BACKOFFICE" })).toBe(true);
  });

  it("builds a backoffice admin URL carrying the existing access token in the fragment", () => {
    expect(buildBackofficeAdminUrl("http://localhost:5174", "token-123")).toBe(
      "http://localhost:5174/admin#access_token=token-123",
    );
  });
});
