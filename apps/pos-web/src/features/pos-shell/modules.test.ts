import { describe, expect, it } from "vitest";

import { posModules } from "./modules";

describe("POS release-visible modules", () => {
  it("keeps the exact approved module list used by sidebar, command palette, and shortcuts", () => {
    expect(posModules.map((module) => module.key)).toEqual([
      "pos",
      "passToCounter",
      "sendToBranch",
      "receiveTransfer",
      "orders",
      "tickets",
      "returns",
      "corrections",
      "waste",
      "payments",
      "shiftClose",
    ]);
    expect(posModules.some((module) => module.key === "discounts")).toBe(false);
    expect(posModules.some((module) => module.path === "/descuentos")).toBe(false);
    expect(posModules.some((module) => module.navigationShortcut === "Ctrl+Alt+F")).toBe(false);
  });
});
