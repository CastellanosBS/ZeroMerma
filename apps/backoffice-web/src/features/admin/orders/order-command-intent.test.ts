// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { adminOrderIntentions } from "./order-command-intent";
const mocks = vi.hoisted(() => ({ send: vi.fn(), recover: vi.fn() }));
vi.mock("./api", () => ({
  sendAdminOrderCommand: mocks.send,
  recoverAdminOrderCommand: mocks.recover,
}));
beforeEach(() => {
  localStorage.clear();
  adminOrderIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  mocks.send.mockReset().mockResolvedValue({ id: "order" });
  mocks.recover.mockReset().mockResolvedValue({ id: "order" });
});
afterEach(() => vi.unstubAllGlobals());
it.each(["mark-ready", "deliver", "cancel"] as const)(
  "keeps the %s key across retry and reload recovery",
  async (commandCode) => {
    const context = { userId: "actor", branchId: "branch", orderId: "order", commandCode };
    mocks.send.mockRejectedValueOnce(new TypeError("lost"));
    await expect(adminOrderIntentions.begin(context, {}, null)).rejects.toThrow();
    const metadata = adminOrderIntentions.read("orders")!;
    expect(Object.keys(metadata).sort()).toEqual(
      ["userId", "branchId", "orderId", "commandCode", "key", "status", "payloadDigest"].sort(),
    );
    adminOrderIntentions.forgetBodies();
    await adminOrderIntentions.recover(context);
    expect(mocks.recover).toHaveBeenCalledWith(commandCode, metadata.key, "branch");
    expect(mocks.send).toHaveBeenCalledTimes(1);
  },
);
it("blocks another actor and incompatible recovered target", async () => {
  const context = {
    userId: "actor",
    branchId: "branch",
    orderId: "order",
    commandCode: "deliver" as const,
  };
  mocks.send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(adminOrderIntentions.begin(context, {}, null)).rejects.toThrow();
  await expect(adminOrderIntentions.recover({ ...context, userId: "other" })).rejects.toThrow(
    "operador",
  );
  expect(mocks.recover).not.toHaveBeenCalled();
  mocks.recover.mockResolvedValue({ id: "foreign" });
  await expect(adminOrderIntentions.recover(context)).rejects.toThrow("otro pedido");
  expect(adminOrderIntentions.read("orders")?.status).toBe("CONFLICT");
});
