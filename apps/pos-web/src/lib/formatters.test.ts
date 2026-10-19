import { describe, expect, it } from "vitest";
import { formatCurrency, formatLocalDateTime, formatRecordStatus } from "./formatters";

describe("POS localization", () => {
  it("uses MXN and the explicit branch timezone", () => {
    expect(formatCurrency("1234.50")).toContain("1,234.50");
    expect(formatLocalDateTime("2026-10-19T06:30:00Z", "America/Hermosillo")).toContain("18");
    expect(formatLocalDateTime("2026-10-19T06:30:00Z", "UTC")).toContain("19");
  });
  it.each([
    ["CONFIRMED", "Confirmado"], ["PARTIALLY_RECEIVED", "Recibido parcialmente"],
    ["IN_TRANSIT", "En tránsito"], ["UNKNOWN", "Por verificar"], ["NO_SHOW", "Cliente no acudió"],
  ])("translates operational state %s", (value, expected) => {
    expect(formatRecordStatus(value)).toBe(expected);
  });
});
