import { describe, expect, it, vi } from "vitest";
import { orderDateTimeInput, orderDateTimeLabel, orderDateTimeToUtc } from "./order-date-time";

describe("order branch date/time", () => {
  it("uses Hermosillo time regardless of the browser zone", () => {
    expect(orderDateTimeToUtc("2026-10-20T12:30", "America/Hermosillo")).toBe(
      "2026-10-20T19:30:00.000Z",
    );
    expect(orderDateTimeInput("2026-10-20T19:30:00Z", "America/Hermosillo")).toBe(
      "2026-10-20T12:30",
    );
  });
  it("rejects nonexistent, ambiguous and invalid wall times", () => {
    expect(() => orderDateTimeToUtc("2026-03-08T02:30", "America/New_York")).toThrow();
    expect(() => orderDateTimeToUtc("2026-11-01T01:30", "America/New_York")).toThrow();
    expect(() => orderDateTimeToUtc("2026-02-30T12:30", "America/Hermosillo")).toThrow();
  });
  it("shows the same Hermosillo wall time in the review label on a UTC computer", () => {
    vi.stubEnv("TZ", "UTC");
    try {
      expect(new Intl.DateTimeFormat().resolvedOptions().timeZone).toBe("UTC");
      const label = orderDateTimeLabel("2026-10-20T12:00", "America/Hermosillo");
      expect(label).toContain("12:00");
      expect(label).not.toContain("05:00");
      expect(orderDateTimeLabel("2026-02-30T12:00", "America/Hermosillo")).toContain("Revisa");
    } finally {
      vi.unstubAllEnvs();
    }
  });
});
