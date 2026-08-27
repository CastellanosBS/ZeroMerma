import { describe, expect, it } from "vitest";

import { getPosReleaseRouteRedirect } from "./router";

describe("POS release route enforcement", () => {
  it("redirects the hidden operational discounts route in every environment", () => {
    expect(getPosReleaseRouteRedirect("/descuentos", true)).toBe("/pos");
    expect(getPosReleaseRouteRedirect("/descuentos", false)).toBe("/pos");
  });

  it("keeps the health demo in development and redirects it in production", () => {
    expect(getPosReleaseRouteRedirect("/health", true)).toBeNull();
    expect(getPosReleaseRouteRedirect("/health", false)).toBe("/");
  });

  it("does not redirect a representative approved route", () => {
    expect(getPosReleaseRouteRedirect("/pos", false)).toBeNull();
  });
});
