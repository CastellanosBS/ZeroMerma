// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { refundIntentions, type RefundIntentionContext } from "./refund-command-intent";
const request = vi.hoisted(() => vi.fn());
vi.mock("../../lib/http", () => ({ requestJson: request }));
const context: RefundIntentionContext = {
  userId: "actor",
  branchId: "branch",
  workstationId: "station",
  workstationCode: "POS-01",
  cashSessionId: "historic-shift",
  sourceType: "SALE_RETURN",
  sourceId: "return-1",
};
const body = { workstation_code: "POS-01", cash_session_id: "historic-shift" };
beforeEach(() => {
  localStorage.clear();
  refundIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  request.mockReset().mockResolvedValue({ source_type: "SALE_RETURN", source_id: "return-1" });
});
afterEach(() => vi.unstubAllGlobals());

it("retries a lost settlement with the identical command key and original drawer", async () => {
  request.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(refundIntentions.begin(context, body, null)).rejects.toThrow();
  await refundIntentions.retry(context);
  expect(request.mock.calls[1]![0]).toEqual(request.mock.calls[0]![0]);
  expect(request.mock.calls[0]![0].path).toBe("/v1/returns/return-1/refund-settlements");
  expect(
    JSON.stringify(JSON.parse(localStorage.getItem("zeromerma-refund-settlement:station")!)),
  ).not.toMatch(/amount|notes|entries/);
});

it("recovers after reload with the original session and cannot blindly submit a new key", async () => {
  request.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(refundIntentions.begin(context, body, null)).rejects.toThrow();
  const saved = refundIntentions.read("station")!;
  refundIntentions.forgetBodies();
  await expect(
    refundIntentions.begin({ ...context, cashSessionId: "next-shift" }, body, saved.key),
  ).rejects.toThrow();
  await refundIntentions.recover(context);
  expect(request.mock.calls[1]![0].path).toContain(`/v1/returns/refund-settlements/${saved.key}?`);
  expect(request.mock.calls[1]![0].path).toContain("cash_session_id=historic-shift");
  expect(request.mock.calls[1]![0].method).toBeUndefined();
});

it("routes an order obligation independently and rejects another obligation's recovered result", async () => {
  const order = { ...context, sourceType: "ORDER_CANCELLATION", sourceId: "order-1" };
  request.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(refundIntentions.begin(order, body, null)).rejects.toThrow();
  expect(request.mock.calls[0]![0].path).toBe("/v1/orders/order-1/refund-settlements");
  await expect(refundIntentions.recover(order)).rejects.toThrow(/otro reembolso/);
  expect(refundIntentions.read("station")!.status).toBe("CONFLICT");
});

it("blocks another refund while the original settlement is unresolved", async () => {
  request.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(refundIntentions.begin(context, body, null)).rejects.toThrow();
  await expect(
    refundIntentions.begin(
      { ...context, sourceId: "return-2" },
      body,
      refundIntentions.read("station")!.key,
    ),
  ).rejects.toThrow();
  expect(request).toHaveBeenCalledTimes(1);
});
