import { describe, expect, it } from "vitest";

import { isBackofficeUser, isPosUser, readAccessTokenFromUrl } from "./auth-surfaces";

describe("backoffice auth surface helpers", () => {
  it("recognizes backoffice users", () => {
    expect(isBackofficeUser({ default_surface: "BACKOFFICE" })).toBe(true);
    expect(isBackofficeUser({ default_surface: "POS" })).toBe(false);
  });

  it("recognizes POS users", () => {
    expect(isPosUser({ default_surface: "POS" })).toBe(true);
    expect(isPosUser({ default_surface: "BACKOFFICE" })).toBe(false);
  });

  it("reads an access token from a URL fragment", () => {
    expect(readAccessTokenFromUrl(new URL("http://localhost:5174/admin#access_token=abc"))).toBe("abc");
  });
});
