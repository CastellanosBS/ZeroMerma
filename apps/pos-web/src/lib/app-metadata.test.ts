import { describe, expect, it } from "vitest";

import { getAppTitle } from "./app-metadata";

describe("getAppTitle", () => {
  it("returns the POS application title", () => {
    expect(getAppTitle()).toBe("ZeroMerma POS");
  });
});
