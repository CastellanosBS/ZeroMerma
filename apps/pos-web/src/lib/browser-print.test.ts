import { describe, expect, it, vi } from "vitest";

import { writePrintableDocument } from "./browser-print";

describe("browser print fallback", () => {
  it("propagates device or permission errors to the operation feedback boundary", () => {
    const printWindow = {
      document: { open: vi.fn(), write: vi.fn(), close: vi.fn() },
      focus: vi.fn(), print: vi.fn(() => { throw new Error("Printer unavailable"); }),
    } as unknown as Window;
    expect(() => writePrintableDocument(printWindow, "<p>Receipt</p>")).toThrow("Printer unavailable");
  });
});
