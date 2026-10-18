import { describe, expect, it } from "vitest";

import { buildBackofficeLoginUrl } from "./auth-surfaces";

describe("auth surface routing", () => {
  it("routes to independent backoffice login without exposing credentials in the URL", () => {
    const url = buildBackofficeLoginUrl("http://localhost:5174");

    expect(url).toBe("http://localhost:5174/login");
    expect(url).not.toContain("access_token");
    expect(url).not.toContain("token-123");
  });
});
