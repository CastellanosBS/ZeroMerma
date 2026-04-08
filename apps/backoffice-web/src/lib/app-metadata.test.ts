import { describe, expect, it } from "vitest";

import { getAppTitle } from "./app-metadata";

describe("getAppTitle", () => {
  it("returns the backoffice application title", () => {
    expect(getAppTitle()).toBe("ZeroMerma Backoffice");
  });
});
