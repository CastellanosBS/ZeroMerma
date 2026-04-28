import { describe, expect, it } from "vitest";

import { buttonClassNames } from "./button";
import { cn } from "./utils";

describe("cn", () => {
  it("merges tailwind class conflicts", () => {
    expect(cn("rounded-sm", "rounded-md")).toBe("rounded-md");
  });
});

describe("buttonClassNames", () => {
  it("builds primary classes from shared tokens", () => {
    expect(buttonClassNames({ variant: "primary" })).toContain("bg-[var(--ui-color-primary)]");
  });

  it("builds outline classes without hard-coded brand colors", () => {
    const classes = buttonClassNames({ size: "lg", variant: "outline" });

    expect(classes).toContain("border-[var(--ui-color-border)]");
    expect(classes).toContain("h-12");
    expect(classes).not.toContain("green-700");
  });
});
