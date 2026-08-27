import { describe, expect, it } from "vitest";

import {
  getUrlWithoutDisallowedAccessToken,
  isBackofficeUser,
  isPosUser,
} from "./auth-surfaces";

describe("backoffice auth surface helpers", () => {
  it("recognizes backoffice users", () => {
    expect(isBackofficeUser({ default_surface: "BACKOFFICE" })).toBe(true);
    expect(isBackofficeUser({ default_surface: "POS" })).toBe(false);
  });

  it("recognizes POS users", () => {
    expect(isPosUser({ default_surface: "POS" })).toBe(true);
    expect(isPosUser({ default_surface: "BACKOFFICE" })).toBe(false);
  });

  it("removes access tokens from query strings without returning or persisting them", () => {
    expect(
      getUrlWithoutDisallowedAccessToken(
        new URL("http://localhost:5174/admin?access_token=secret&source=pos"),
      ),
    ).toBe("/admin?source=pos");
  });

  it("removes access tokens from fragments without returning or persisting them", () => {
    expect(
      getUrlWithoutDisallowedAccessToken(
        new URL("http://localhost:5174/admin#access_token=secret&section=sales"),
      ),
    ).toBe("/admin#section=sales");
  });

  it("preserves normal backoffice login URLs", () => {
    expect(getUrlWithoutDisallowedAccessToken(new URL("http://localhost:5174/login"))).toBe(
      "/login",
    );
  });
});
