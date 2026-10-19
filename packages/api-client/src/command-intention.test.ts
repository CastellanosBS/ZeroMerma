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

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((complete) => {
    resolve = complete;
  });
  return { promise, resolve };
}

function pauseDigest() {
  const entered = deferred<void>();
  const release = deferred<void>();
  vi.stubGlobal("crypto", {
    getRandomValues: webcrypto.getRandomValues.bind(webcrypto),
    subtle: {
      digest: async (algorithm: string, input: ArrayBuffer) => {
        entered.resolve();
        await release.promise;
        return webcrypto.subtle.digest(algorithm, input);
      },
    },
  });
  return { entered: entered.promise, release: () => release.resolve() };
}

it("does not dispatch or persist a new intention after auth changes during its digest", async () => {
  const engine = coordinator();
  const hashing = pauseDigest();
  const result = engine.begin(context, { amount: "20", customer: "private" }, null);
  const rejected = expect(result).rejects.toThrow("sesión cambió");
  await hashing.entered;
  engine.forgetBodies();
  hashing.release();
  await rejected;
  expect(send).not.toHaveBeenCalled();
  expect(engine.read("station")).toBeNull();
  await engine.begin(context, { amount: "21", customer: "new" }, null);
  expect(send).toHaveBeenCalledTimes(1);
});

it("does not dispatch after auth changes while waiting to acquire the browser lock", async () => {
  const engine = coordinator();
  const acquired = deferred<void>();
  vi.stubGlobal("navigator", {
    locks: {
      request: async (_name: string, _options: unknown, callback: (lock: object) => unknown) => {
        await acquired.promise;
        return callback({ name: "lock" });
      },
    },
  });
  const result = engine.begin(context, { amount: "20", customer: "private" }, null);
  const rejected = expect(result).rejects.toThrow("sesión cambió");
  engine.forgetBodies();
  acquired.resolve();
  await rejected;
  expect(send).not.toHaveBeenCalled();
  expect(engine.read("station")).toBeNull();
});

it("keeps recovery metadata and stops retry after auth changes during its digest", async () => {
  const engine = coordinator();
  send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    engine.begin(context, { amount: "20", customer: "private" }, null),
  ).rejects.toThrow();
  const metadata = engine.read("station")!;
  const hashing = pauseDigest();
  const result = engine.retry(context);
  const rejected = expect(result).rejects.toThrow("sesión cambió");
  await hashing.entered;
  engine.forgetBodies();
  hashing.release();
  await rejected;
  expect(send).toHaveBeenCalledTimes(1);
  expect(engine.read("station")).toEqual(metadata);
  expect(engine.hasBody(metadata.key)).toBe(false);
  await engine.recover(context);
  expect(engine.read("station")).toMatchObject({ key: metadata.key, status: "CONFIRMED" });
  expect(store.get("test-intent:station")).not.toMatch(/amount|customer|private/);
});

it("does not expose a late mutation result to a changed session", async () => {
  const engine = coordinator();
  const response = deferred<{ id: string }>();
  send.mockReturnValueOnce(response.promise);
  const result = engine.begin(context, { amount: "20", customer: "private" }, null);
  const rejected = expect(result).rejects.toThrow("sesión cambió");
  await vi.waitFor(() => expect(send).toHaveBeenCalledTimes(1));
  const key = engine.read("station")!.key;
  engine.forgetBodies();
  response.resolve({ id: "old-result" });
  await rejected;
  expect(engine.read("station")).toMatchObject({ key, status: "UNKNOWN" });
  expect(engine.hasBody(key)).toBe(false);
  await engine.recover(context);
  expect(engine.read("station")).toMatchObject({ key, status: "CONFIRMED" });
});

it("retains unknown metadata when auth changes during read-only recovery", async () => {
  const engine = coordinator();
  send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    engine.begin(context, { amount: "20", customer: "private" }, null),
  ).rejects.toThrow();
  const metadata = engine.read("station")!;
  const response = deferred<{ id: string }>();
  recover.mockReturnValueOnce(response.promise);
  const result = engine.recover(context);
  const rejected = expect(result).rejects.toThrow("sesión cambió");
  await vi.waitFor(() => expect(recover).toHaveBeenCalledTimes(1));
  engine.forgetBodies();
  response.resolve({ id: "old-result" });
  await rejected;
  expect(engine.read("station")).toEqual(metadata);
  expect(send).toHaveBeenCalledTimes(1);
  await engine.recover(context);
  expect(engine.read("station")).toMatchObject({ key: metadata.key, status: "CONFIRMED" });
});

it("does not unlock an intention from a late rejection after auth invalidation", async () => {
  const durable = new Error("durable rejection");
  const engine = coordinator((_metadata, error) => error === durable);
  send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    engine.begin(context, { amount: "20", customer: "private" }, null),
  ).rejects.toThrow();
  const key = engine.read("station")!.key;
  const response = deferred<void>();
  recover.mockImplementationOnce(async () => {
    await response.promise;
    throw durable;
  });
  const result = engine.recover(context);
  const rejected = expect(result).rejects.toThrow("sesión cambió");
  await vi.waitFor(() => expect(recover).toHaveBeenCalledTimes(1));
  engine.forgetBodies();
  response.resolve();
  await rejected;
  expect(engine.read("station")).toMatchObject({ key, status: "UNKNOWN" });
  expect(engine.hasBody(key)).toBe(false);
});
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

it("retries a rolled-back concurrency conflict with its original key and frozen body", async () => {
  const engine = coordinator();
  const payload = { amount: "20", customer: "private" };
  send.mockRejectedValueOnce(
    new ApiError(409, "Retry the same intention.", {
      code: "CONCURRENCY_RETRY",
      message: "Retry the same intention.",
      details: { retryable: true },
      field_errors: null,
      request_id: "conflict",
    }),
  );
  await expect(engine.begin(context, payload, null)).rejects.toThrow("Retry the same intention");
  const metadata = engine.read("station")!;
  expect(metadata.status).toBe("UNKNOWN");
  expect(engine.hasBody(metadata.key)).toBe(true);
  expect(store.get("test-intent:station")).not.toMatch(/amount|customer|private/);
  payload.amount = "999";
  await expect(engine.begin(context, payload, metadata.key)).rejects.toThrow();
  await engine.retry(context);
  expect(send).toHaveBeenCalledTimes(2);
  expect(send.mock.calls[1]!.slice(1)).toEqual(send.mock.calls[0]!.slice(1));
  expect(engine.read("station")).toMatchObject({ key: metadata.key, status: "CONFIRMED" });
});

it("still resolves a definitive first-send business conflict as rejected", async () => {
  const engine = coordinator();
  send.mockRejectedValueOnce(
    new ApiError(409, "Insufficient stock.", {
      code: "CONFLICT",
      message: "Insufficient stock.",
      details: null,
      field_errors: null,
      request_id: null,
    }),
  );
  await expect(engine.begin(context, { amount: "20", customer: "x" }, null)).rejects.toThrow();
  const metadata = engine.read("station")!;
  expect(metadata.status).toBe("REJECTED");
  expect(engine.hasBody(metadata.key)).toBe(false);
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
