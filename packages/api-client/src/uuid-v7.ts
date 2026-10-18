import type { components } from "./generated/schema";

/** Generate an intention identity, never a new identity for a retry. */
export function createIdempotencyKey(): components["schemas"]["IdempotencyKey"] {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  let timestamp = Date.now();
  if (!Number.isSafeInteger(timestamp) || timestamp < 0 || timestamp > 0xffffffffffff) {
    throw new Error("The clock cannot produce a UUIDv7 timestamp.");
  }
  for (let index = 5; index >= 0; index -= 1) {
    bytes[index] = timestamp % 256;
    timestamp = Math.floor(timestamp / 256);
  }
  bytes[6] = (bytes[6]! & 0x0f) | 0x70;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
