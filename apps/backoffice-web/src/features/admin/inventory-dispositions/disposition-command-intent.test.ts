// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
import {
  dispositionIntentions,
  type DispositionContext,
  type InventoryDispositionRequest,
} from "./disposition-command-intent";

const request = vi.hoisted(() => vi.fn());
vi.mock("../../../lib/api", () => ({ requestJson: request }));
const context: DispositionContext = {
  userId: "actor",
  branchId: "branch",
  productId: "product",
  kind: "QUARANTINE_RELEASE",
  returnAllocationId: null,
  lotId: "lot",
};
const body = (): InventoryDispositionRequest => ({
  branch_id: "branch",
  product_id: "product",
  kind: "QUARANTINE_RELEASE",
  lot_id: "lot",
  quantity: "1",
  destination: "BACKROOM",
  inspection_passed: true,
  reason: "Private inspection reason",
});
const result = {
  operation_id: "operation",
  branch_id: "branch",
  product_id: "product",
  kind: "QUARANTINE_RELEASE",
  return_allocation_id: null,
  lot_id: "lot",
  source: "QUARANTINE",
  destination: "BACKROOM",
  quantity: "1",
  movement_ids: ["out", "in"],
};
beforeEach(() => {
  localStorage.clear();
  dispositionIntentions.forgetBodies();
  request.mockReset().mockResolvedValue(result);
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
});
afterEach(() => vi.unstubAllGlobals());

it("freezes the physical disposition and retries the same key while persisting only identity", async () => {
  request.mockRejectedValueOnce(new TypeError("lost response"));
  const payload = body();
  await expect(dispositionIntentions.begin(context, payload, null)).rejects.toThrow();
  payload.quantity = "9";
  await dispositionIntentions.retry(context);
  expect(request.mock.calls[1]![0].body.quantity).toBe("1");
  expect(request.mock.calls[1]![0].headers["Idempotency-Key"]).toBe(
    request.mock.calls[0]![0].headers["Idempotency-Key"],
  );
  const saved = localStorage.getItem(
    "zeromerma-inventory-disposition-intention:inventory-dispositions",
  )!;
  expect(saved).not.toMatch(/Private|reason|quantity|inspection_passed|destination/);
});
it("recovers after reload with GET without issuing another physical mutation", async () => {
  request.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(dispositionIntentions.begin(context, body(), null)).rejects.toThrow();
  const metadata = dispositionIntentions.read("inventory-dispositions")!;
  dispositionIntentions.forgetBodies();
  expect(dispositionIntentions.hasBody(metadata.key)).toBe(false);
  expect(await dispositionIntentions.recover(metadata)).toEqual(result);
  expect(request.mock.calls[1]![0]).toEqual({
    path: `/v1/admin/inventory-dispositions/confirmations/${metadata.key}?branch_id=branch&kind=QUARANTINE_RELEASE`,
  });
  expect(request.mock.calls.filter(([argument]) => argument.method === "POST")).toHaveLength(1);
});
it("rejects an acknowledgement for another product and keeps its conflict reference", async () => {
  request.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(dispositionIntentions.begin(context, body(), null)).rejects.toThrow();
  request.mockResolvedValueOnce({ ...result, product_id: "other" });
  await expect(dispositionIntentions.recover(context)).rejects.toThrow(/otra disposicion/);
  expect(dispositionIntentions.read("inventory-dispositions")?.status).toBe("CONFLICT");
});
it("rejects a changed physical cause before issuing a request", async () => {
  await expect(
    dispositionIntentions.begin(context, { ...body(), lot_id: "other" }, null),
  ).rejects.toThrow(/contexto/);
  expect(request).not.toHaveBeenCalled();
});
it("forgets the volatile body at a session boundary while retaining recovery identity", async () => {
  request.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(dispositionIntentions.begin(context, body(), null)).rejects.toThrow();
  const metadata = dispositionIntentions.read("inventory-dispositions")!;
  expect(dispositionIntentions.hasBody(metadata.key)).toBe(true);
  useBackofficeAuthStore.getState().clearSession();
  expect(dispositionIntentions.hasBody(metadata.key)).toBe(false);
  expect(dispositionIntentions.read("inventory-dispositions")).toEqual(metadata);
  expect(request).toHaveBeenCalledTimes(1);
});
