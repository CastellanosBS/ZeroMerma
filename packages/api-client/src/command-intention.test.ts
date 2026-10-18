import { webcrypto } from "node:crypto";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { createCommandIntentionCoordinator } from "./command-intention";
import { ApiError } from "./transport";

type Context = { userId: string; commandCode: string; orderId: string | null };
const context: Context = { userId: "actor", commandCode: "create", orderId: null };
const store = new Map<string, string>();
const send = vi.fn();
const recover = vi.fn();
const coordinator = (isRecoveredRejection?: (metadata: Context, error: unknown) => boolean) =>
  createCommandIntentionCoordinator<Context, { amount: string; customer: string }, { id: string }>({
    storagePrefix: "test-intent:",
    eventName: "intent",
    contextFields: ["userId", "commandCode", "orderId"],
    nullableFields: ["orderId"],
    scope: () => "station",
    send,
    recover,
    isRecoveredRejection,
  });
beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto);
  vi.stubGlobal("window", new EventTarget());
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => store.set(key, value),
  });
  vi.stubGlobal("navigator", {
    locks: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  store.clear();
  send.mockReset().mockResolvedValue({ id: "order" });
  recover.mockReset().mockResolvedValue({ id: "order" });
});
afterEach(() => vi.unstubAllGlobals());
it("keeps economic and customer bodies only in memory and retries the original identity", async () => {
  const engine = coordinator();
  const payload = { amount: "20", customer: "private customer" };
  send.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(engine.begin(context, payload, null)).rejects.toThrow("lost response");
  const metadata = engine.read("station")!;
  expect(Object.keys(metadata).sort()).toEqual(
    ["userId", "commandCode", "orderId", "key", "payloadDigest", "status"].sort(),
  );
  expect(store.get("test-intent:station")).not.toMatch(/amount|customer|private/);
  payload.amount = "999";
  await engine.retry(context);
  expect(send.mock.calls[1]!.slice(1)).toEqual(send.mock.calls[0]!.slice(1));
  expect(engine.read("station")?.status).toBe("CONFIRMED");
});
it("uses a distinct key per new command and refuses reuse across operation or target", async () => {
  const engine = coordinator();
  send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(engine.begin(context, { amount: "20", customer: "x" }, null)).rejects.toThrow();
  await expect(
    engine.retry({ ...context, commandCode: "deliver", orderId: "order" }),
  ).rejects.toThrow("mismo comando");
  await engine.recover(context);
  const first = engine.read("station")!;
  await engine.begin(
    { ...context, commandCode: "deliver", orderId: "order" },
    { amount: "0", customer: "x" },
    first.key,
  );
  expect(send.mock.calls[1]![2]).not.toBe(first.key);
});
it("recovers a reload through GET without reconstructing or sending the economic body", async () => {
  const first = coordinator();
  send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(first.begin(context, { amount: "20", customer: "x" }, null)).rejects.toThrow();
  const reloaded = coordinator();
  await expect(reloaded.retry(context)).rejects.toThrow("contenido original");
  await expect(
    reloaded.begin(context, { amount: "20", customer: "x" }, reloaded.read("station")!.key),
  ).rejects.toThrow("otra pestaña");
  await reloaded.recover(context);
  expect(send).toHaveBeenCalledTimes(1);
  expect(recover).toHaveBeenCalledTimes(1);
});
it("keeps unknown outcomes pending after a later deterministic rejection", async () => {
  const engine = coordinator();
  send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(engine.begin(context, { amount: "20", customer: "x" }, null)).rejects.toThrow();
  send.mockRejectedValueOnce(
    new ApiError(409, "invalid state", {
      code: "ORDER_STATE_CONFLICT",
      message: "invalid state",
      details: null,
      field_errors: null,
      request_id: null,
    }),
  );
  await expect(engine.retry(context)).rejects.toThrow();
  expect(engine.read("station")?.status).toBe("UNKNOWN");
});
it("coordinates synchronous and independently instantiated clients under the same claim", async () => {
  const first = coordinator();
  const second = coordinator();
  const pending = first.begin(context, { amount: "20", customer: "x" }, null);
  await expect(second.begin(context, { amount: "20", customer: "x" }, null)).rejects.toThrow(
    "procesando",
  );
  await pending;
  expect(send).toHaveBeenCalledTimes(1);
});

it("resolves a verified durable rejection only during recovery and preserves the original error", async () => {
  const rejection = new Error("durable rejection");
  const predicate = vi.fn((_metadata: Context, error: unknown) => error === rejection);
  const engine = coordinator(predicate);
  send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(engine.begin(context, { amount: "20", customer: "x" }, null)).rejects.toThrow();
  const key = engine.read("station")!.key;
  send.mockRejectedValueOnce(rejection);
  await expect(engine.retry(context)).rejects.toBe(rejection);
  expect(predicate).not.toHaveBeenCalled();
  expect(engine.read("station")?.status).toBe("UNKNOWN");
  recover.mockRejectedValueOnce(rejection);
  await expect(engine.recover(context)).rejects.toBe(rejection);
  expect(engine.read("station")).toMatchObject({ key, status: "REJECTED" });
  expect(engine.hasBody(key)).toBe(false);
  await engine.begin(context, { amount: "21", customer: "x" }, key);
  expect(engine.read("station")!.key).not.toBe(key);
});
