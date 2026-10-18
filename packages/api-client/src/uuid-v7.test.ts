import { afterEach, describe, expect, it, vi } from "vitest";
import { createIdempotencyKey } from "./uuid-v7";

afterEach(() => vi.restoreAllMocks());

describe("UUIDv7 intention keys", () => {
  it("encodes milliseconds and keeps distinct secure randomness within the same millisecond", () => {
    const now = 1_729_000_123_456;
    vi.spyOn(Date, "now").mockReturnValue(now);
    const keys = Array.from({ length: 128 }, createIdempotencyKey);
    expect(new Set(keys).size).toBe(keys.length);
    for (const key of keys) {
      expect(key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
      expect(Number.parseInt(key.replaceAll("-", "").slice(0, 12), 16)).toBe(now);
    }
  });

  it("does not fall back to weak randomness when the secure source fails", () => {
    vi.spyOn(crypto, "getRandomValues").mockImplementation(() => {
      throw new Error("unavailable");
    });
    expect(() => createIdempotencyKey()).toThrow("unavailable");
  });
});
