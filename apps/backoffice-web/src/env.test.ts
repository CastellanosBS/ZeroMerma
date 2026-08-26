import { describe, expect, it } from "vitest";

import { resolveBackofficeEnv } from "./env";

describe("resolveBackofficeEnv", () => {
  it("defaults local API and POS base URLs", () => {
    expect(resolveBackofficeEnv({})).toEqual({
      VITE_API_BASE_URL: "http://localhost:8000",
      VITE_POS_BASE_URL: "http://localhost:5173",
    });
  });

  it("accepts explicit URL overrides", () => {
    expect(
      resolveBackofficeEnv({
        VITE_API_BASE_URL: "http://localhost:8010",
        VITE_POS_BASE_URL: "http://localhost:5178",
      }),
    ).toEqual({
      VITE_API_BASE_URL: "http://localhost:8010",
      VITE_POS_BASE_URL: "http://localhost:5178",
    });
  });
});
