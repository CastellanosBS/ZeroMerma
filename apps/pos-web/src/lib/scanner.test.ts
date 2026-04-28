import { describe, expect, it } from "vitest";

import {
  extractScannerTokens,
  matchesScannerValue,
  normalizeScannerText,
  parseProductScannerValue,
  parseShipmentScannerValue,
  parseTicketScannerValue,
} from "./scanner";

describe("scanner helpers", () => {
  it("normalizes whitespace and line endings", () => {
    expect(normalizeScannerText("  tck-abc123\r\n")).toBe("TCK-ABC123");
  });

  it("extracts alphanumeric and dashed tokens from qr-like payloads", () => {
    expect(extractScannerTokens("https://zeromerma.local/tickets/TCK-AAA001?station=POS-01")).toEqual([
      "HTTPS",
      "ZEROMERMA",
      "LOCAL",
      "TICKETS",
      "TCK-AAA001",
      "STATION",
      "POS-01",
    ]);
  });

  it("parses ticket folios from plain values and urls", () => {
    expect(parseTicketScannerValue("tck-aaa001")).toBe("TCK-AAA001");
    expect(parseTicketScannerValue("https://zeromerma.local/tickets/TCK-BBB002")).toBe(
      "TCK-BBB002",
    );
  });

  it("parses shipment folios for outbound and inbound documents", () => {
    expect(parseShipmentScannerValue("env-000001")).toBe("ENV-000001");
    expect(parseShipmentScannerValue("https://zeromerma.local/transfers/rec-000005")).toBe(
      "REC-000005",
    );
  });

  it("parses product codes without keeping url markers", () => {
    expect(parseProductScannerValue("COCA-355")).toBe("COCA-355");
    expect(
      parseProductScannerValue("https://zeromerma.local/product/COCA-355?mode=scan"),
    ).toBe("COCA-355");
  });

  it("matches scanner values case-insensitively", () => {
    expect(matchesScannerValue("tck-aaa001", "TCK-AAA001")).toBe(true);
    expect(matchesScannerValue("ENV-000001", "REC-000001")).toBe(false);
  });
});
