import { describe, expect, it } from "vitest";

import { resolvePosEnv } from "./env";

describe("resolvePosEnv", () => {
  it("defaults the local API base URL and workstation code", () => {
    expect(resolvePosEnv({})).toEqual({
      VITE_API_BASE_URL: "http://localhost:8000",
      VITE_BACKOFFICE_BASE_URL: "http://localhost:5174",
      VITE_POS_WORKSTATION_CODE: "POS-01",
    });
  });

  it("accepts explicit workstation and backoffice overrides", () => {
    expect(
      resolvePosEnv({
        VITE_API_BASE_URL: "http://localhost:8010",
        VITE_BACKOFFICE_BASE_URL: "http://localhost:5179",
        VITE_POS_WORKSTATION_CODE: "POS-77",
      }),
    ).toEqual({
      VITE_API_BASE_URL: "http://localhost:8010",
      VITE_BACKOFFICE_BASE_URL: "http://localhost:5179",
      VITE_POS_WORKSTATION_CODE: "POS-77",
    });
  });
});
