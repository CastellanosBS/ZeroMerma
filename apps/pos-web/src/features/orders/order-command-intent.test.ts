// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { orderIntentions, type OrderIntentionContext } from "./order-command-intent";
const mocks = vi.hoisted(() => ({
  create: vi.fn(),
  ready: vi.fn(),
  deliver: vi.fn(),
  cancel: vi.fn(),
  pay: vi.fn(),
  amend: vi.fn(),
  recover: vi.fn(),
}));
vi.mock("./orders-api", () => ({
  createOrder: mocks.create,
  markOrderReady: mocks.ready,
  deliverOrder: mocks.deliver,
  cancelOrder: mocks.cancel,
  payOrder: mocks.pay,
  amendOrder: mocks.amend,
  recoverOrderCommand: mocks.recover,
}));
const context: OrderIntentionContext = {
  userId: "actor",
  branchId: "branch",
  workstationId: "station",
  workstationCode: "POS-01",
  cashSessionId: "historic-cash",
  commandCode: "mark-ready",
  orderId: "order",
};
beforeEach(() => {
  localStorage.clear();
  orderIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  Object.values(mocks).forEach((mock) => mock.mockReset().mockResolvedValue({ id: "order" }));
});
afterEach(() => vi.unstubAllGlobals());
it.each(["create", "mark-ready", "deliver", "cancel", "pay", "amend"] as const)(
  "retains the original %s identity and body on a failed response",
  async (commandCode) => {
    const mock =
      commandCode === "create"
        ? mocks.create
        : commandCode === "mark-ready"
          ? mocks.ready
          : commandCode === "deliver"
            ? mocks.deliver
            : commandCode === "pay"
              ? mocks.pay
              : commandCode === "amend"
                ? mocks.amend
                : mocks.cancel;
    const commandContext = {
      ...context,
      commandCode,
      orderId: commandCode === "create" ? null : "order",
    };
    const payload = {
      workstation_code: "POS-01",
      cash_session_id: "historic-cash",
      customer_name: "private",
      items: [{ product_id: "product", quantity: "1" }],
      cancellation_reason: "private reason",
      settlement_amount: "10.00",
    };
    mock.mockRejectedValueOnce(new TypeError("connection lost"));
    await expect(orderIntentions.begin(commandContext, payload, null)).rejects.toThrow();
    await orderIntentions.retry(commandContext);
    const first = mock.mock.calls[0]![0];
    const second = mock.mock.calls[1]![0];
    expect(second.payload).toEqual(first.payload);
    expect(second.idempotencyKey).toBe(first.idempotencyKey);
    expect(second).not.toHaveProperty("requestId");
    expect(localStorage.getItem("zeromerma-order-intention:station")).not.toMatch(
      /private|settlement_amount|customer_name|items/,
    );
  },
);
it("recovers the original cash session after reload without a new POST", async () => {
  mocks.ready.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    orderIntentions.begin(
      context,
      { workstation_code: "POS-01", cash_session_id: "historic-cash" },
      null,
    ),
  ).rejects.toThrow();
  const key = orderIntentions.read("station")!.key;
  orderIntentions.forgetBodies();
  await orderIntentions.recover(context);
  expect(mocks.recover).toHaveBeenCalledWith("mark-ready", key, "POS-01", "historic-cash");
  expect(mocks.ready).toHaveBeenCalledTimes(1);
});
it("rejects a recovered result bound to another order and keeps the original intention blocked", async () => {
  mocks.ready.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    orderIntentions.begin(
      context,
      { workstation_code: "POS-01", cash_session_id: "historic-cash" },
      null,
    ),
  ).rejects.toThrow();
  mocks.recover.mockResolvedValueOnce({ id: "foreign-order" });
  await expect(orderIntentions.recover(context)).rejects.toThrow("otro pedido");
  expect(orderIntentions.read("station")?.status).toBe("CONFLICT");
});
