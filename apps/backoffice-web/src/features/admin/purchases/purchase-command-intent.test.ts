// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { ApiError } from "@zeromerma/api-client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { purchaseIntentions, type PurchaseIntentionPayload } from "./purchase-command-intent";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
const mocks = vi.hoisted(() => ({ send: vi.fn(), recover: vi.fn() }));
vi.mock("./api", () => ({
  createAdminPurchase: mocks.send,
  createAdminDirectEntry: mocks.send,
  updateAdminPurchase: mocks.send,
  confirmAdminPurchase: mocks.send,
  receiveAdminPurchase: mocks.send,
  cancelAdminPurchase: mocks.send,
  recoverAdminPurchaseCommand: mocks.recover,
}));
beforeEach(() => {
  localStorage.clear();
  purchaseIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  mocks.send.mockReset().mockResolvedValue({ id: "purchase" });
  mocks.recover.mockReset().mockResolvedValue({ id: "purchase" });
});
afterEach(() => vi.unstubAllGlobals());

it("forgets volatile purchase bodies when the authentication generation changes", async () => {
  mocks.send.mockRejectedValueOnce(new TypeError("lost"));
  const context = {
    userId: "actor",
    branchId: "branch",
    purchaseId: null,
    commandCode: "create" as const,
  };
  await expect(purchaseIntentions.begin(context, payloads[0]!, null)).rejects.toThrow();
  const metadata = purchaseIntentions.read("purchases")!;
  expect(purchaseIntentions.hasBody(metadata.key)).toBe(true);
  useBackofficeAuthStore.setState((state) => ({ generation: state.generation + 1 }));
  expect(purchaseIntentions.hasBody(metadata.key)).toBe(false);
  expect(purchaseIntentions.read("purchases")).toEqual(metadata);
});
const payloads: PurchaseIntentionPayload[] = [
  {
    commandCode: "create",
    body: {
      branchId: "branch",
      supplierId: "supplier",
      notes: "Private note",
      lines: [{ productId: "product", orderedQuantity: "5", unitCost: "2" }],
    },
  },
  {
    commandCode: "direct-entry",
    body: {
      branchId: "branch",
      supplierId: "supplier",
      lines: [{ productId: "product", receivedQuantity: "5", unitCost: "2" }],
    },
  },
  { commandCode: "update", body: { notes: "Private updated note" } },
  { commandCode: "receive", body: { lines: [{ purchaseLineId: "line", receivedQuantity: "5" }] } },
  { commandCode: "confirm" },
  { commandCode: "cancel", body: { reason: "Private cancellation" } },
];
it.each(payloads)("keeps the $commandCode identity across retry and reload", async (payload) => {
  const context = {
    userId: "actor",
    branchId: "branch",
    purchaseId: ["create", "direct-entry"].includes(payload.commandCode) ? null : "purchase",
    commandCode: payload.commandCode,
  };
  mocks.send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(purchaseIntentions.begin(context, payload, null)).rejects.toThrow();
  const metadata = purchaseIntentions.read("purchases")!;
  expect(Object.keys(metadata).sort()).toEqual(
    ["userId", "branchId", "purchaseId", "commandCode", "key", "status", "payloadDigest"].sort(),
  );
  expect(JSON.stringify(localStorage)).not.toContain("Private");
  mocks.send.mockRejectedValueOnce(new TypeError("lost again"));
  await expect(purchaseIntentions.retry(context)).rejects.toThrow();
  expect(mocks.send.mock.calls[0]?.at(-1)).toBe(metadata.key);
  expect(mocks.send.mock.calls[1]?.at(-1)).toBe(metadata.key);
  purchaseIntentions.forgetBodies();
  await expect(purchaseIntentions.retry(context)).rejects.toThrow();
  await purchaseIntentions.recover(context);
  expect(mocks.recover).toHaveBeenCalledWith(payload.commandCode, metadata.key, "branch");
  expect(mocks.send).toHaveBeenCalledTimes(2);
});
it("blocks a second actor, a second intention and stale tabs", async () => {
  const payload = payloads[3]!;
  const context = {
    userId: "actor",
    branchId: "branch",
    purchaseId: "purchase",
    commandCode: payload.commandCode,
  };
  mocks.send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(purchaseIntentions.begin(context, payload, null)).rejects.toThrow();
  await expect(purchaseIntentions.recover({ ...context, userId: "other" })).rejects.toThrow(
    "operador",
  );
  await expect(purchaseIntentions.begin(context, payload, null)).rejects.toThrow("otra pestaña");
  await purchaseIntentions.recover(context);
  await expect(purchaseIntentions.begin(context, payload, null)).rejects.toThrow("otra pestaña");
  expect(mocks.send).toHaveBeenCalledTimes(1);
});
it("accepts a durable rejection recovered after a lost response", async () => {
  const payload = payloads[3]!;
  const context = {
    userId: "actor",
    branchId: "branch",
    purchaseId: "purchase",
    commandCode: payload.commandCode,
  };
  mocks.send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(purchaseIntentions.begin(context, payload, null)).rejects.toThrow();
  const error = new ApiError(
    409,
    "Rejected",
    {
      code: "PURCHASE_COMMAND_REJECTED",
      message: "Rejected",
      details: null,
      field_errors: null,
      request_id: null,
    },
    true,
  );
  mocks.recover.mockRejectedValue(error);
  await expect(purchaseIntentions.recover(context)).rejects.toThrow();
  expect(purchaseIntentions.read("purchases")?.status).toBe("REJECTED");
});
