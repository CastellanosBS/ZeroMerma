import { describe, expect, it } from "vitest";

import { cn } from "./button";

describe("cn", () => {
  it("merges tailwind class conflicts", () => {
    expect(cn("rounded-sm", "rounded-md")).toBe("rounded-md");
  });
});
