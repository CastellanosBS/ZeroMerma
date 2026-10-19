// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { ApiError } from "@zeromerma/api-client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  beginProductionCommand,
  productionIntentions,
  type ProductionIntentionContext,
} from "./production-command-intent";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";

const mocks = vi.hoisted(() => ({ send: vi.fn(), recover: vi.fn() }));
vi.mock("./api", () => ({
  sendProductionCommand: mocks.send,
  recoverProductionCommand: mocks.recover,
}));
const created = { id: "batch", branch_id: "branch", status: "DRAFT" };
beforeEach(() => {
  localStorage.clear();
  productionIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: {
      request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })),
    },
  });
  mocks.send.mockReset().mockResolvedValue(created);
  mocks.recover.mockReset().mockResolvedValue(created);
});
afterEach(() => vi.unstubAllGlobals());

it.each(["create", "update", "start", "complete", "cancel"] as const)(
  "recovers %s after reload using only metadata",
  async (commandCode) => {
    const context = {
      userId: "actor",
      branchId: "branch",
      productionId: commandCode === "create" ? null : "batch",
      commandCode,
    };
    mocks.send.mockRejectedValueOnce(new TypeError("lost"));
    await expect(
      productionIntentions.begin(context, { notes: "private memo" }, null),
    ).rejects.toThrow();
    const metadata = productionIntentions.read("production")!;
    expect(Object.keys(metadata).sort()).toEqual(
      [
        "userId",
        "branchId",
        "productionId",
        "commandCode",
        "key",
        "payloadDigest",
        "status",
      ].sort(),
    );
    expect(localStorage.getItem("zeromerma-production-intention:production")).not.toContain(
      "private memo",
    );
    productionIntentions.forgetBodies();
    await expect(productionIntentions.retry(context)).rejects.toThrow("original");
    await productionIntentions.recover(context);
    expect(mocks.recover).toHaveBeenCalledWith(commandCode, metadata.key, "branch");
    expect(mocks.send).toHaveBeenCalledTimes(1);
  },
);

const createContext: ProductionIntentionContext = {
  userId: "actor",
  branchId: "branch",
  productionId: null,
  commandCode: "create",
};
const createPayload = { branch_id: "branch", product_id: "product", planned_output_qty: "20" };
it("keeps a frozen body and key on retry and blocks a second tab intention", async () => {
  mocks.send.mockRejectedValueOnce(new TypeError("lost"));
  const body = { ...createPayload };
  await expect(productionIntentions.begin(createContext, body, null)).rejects.toThrow();
  body.planned_output_qty = "99";
  await expect(productionIntentions.begin(createContext, body, null)).rejects.toThrow("intención");
  await productionIntentions.retry(createContext);
  expect(mocks.send.mock.calls[1]![2]).toEqual(createPayload);
  expect(mocks.send.mock.calls[1]![3]).toBe(mocks.send.mock.calls[0]![3]);
});
it("creates and starts with different keys and retries only start after response loss", async () => {
  mocks.send.mockResolvedValueOnce(created).mockRejectedValueOnce(new TypeError("lost start"));
  const onCreated = vi.fn();
  await expect(
    beginProductionCommand(createContext, createPayload, null, {
      startNow: true,
      canContinue: () => true,
      onCreated,
    }),
  ).rejects.toThrow();
  expect(onCreated).toHaveBeenCalledWith(created);
  const metadata = productionIntentions.read("production")!;
  expect(metadata.commandCode).toBe("start");
  expect(mocks.send.mock.calls[0]![3]).not.toBe(mocks.send.mock.calls[1]![3]);
  await productionIntentions.retry(metadata);
  expect(mocks.send.mock.calls.map((call) => call[0])).toEqual(["create", "start", "start"]);
});
it("never starts or recreates when creation response is lost", async () => {
  mocks.send.mockRejectedValueOnce(new TypeError("lost create"));
  await expect(
    beginProductionCommand(createContext, createPayload, null, {
      startNow: true,
      canContinue: () => true,
      onCreated: vi.fn(),
    }),
  ).rejects.toThrow();
  productionIntentions.forgetBodies();
  await productionIntentions.recover(createContext);
  expect(mocks.send).toHaveBeenCalledTimes(1);
});
it("does not start after the original operator lost the session", async () => {
  await beginProductionCommand(createContext, createPayload, null, {
    startNow: true,
    canContinue: () => false,
    onCreated: vi.fn(),
  });
  expect(mocks.send).toHaveBeenCalledTimes(1);
});
it("preserves UNKNOWN and rejects another actor or a mismatched recovered lot", async () => {
  const context = { ...createContext, commandCode: "complete" as const, productionId: "batch" };
  mocks.send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    productionIntentions.begin(context, { actual_output_qty: "20" }, null),
  ).rejects.toThrow();
  await expect(productionIntentions.recover({ ...context, userId: "other" })).rejects.toThrow(
    "operador",
  );
  mocks.recover.mockRejectedValueOnce(
    new ApiError(409, "Unknown", {
      code: "IDEMPOTENCY_RESULT_UNKNOWN",
      message: "Unknown",
      details: null,
      field_errors: null,
      request_id: null,
    }),
  );
  await expect(productionIntentions.recover(context)).rejects.toThrow();
  expect(productionIntentions.read("production")?.status).toBe("UNKNOWN");
  mocks.recover.mockResolvedValue({ ...created, id: "another" });
  await expect(productionIntentions.recover(context)).rejects.toThrow("otro lote");
  expect(productionIntentions.read("production")?.status).toBe("CONFLICT");
});

it("drops the volatile command body when the session is locked", async () => {
  mocks.send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(productionIntentions.begin(createContext, createPayload, null)).rejects.toThrow();
  const metadata = productionIntentions.read("production")!;
  expect(productionIntentions.hasBody(metadata.key)).toBe(true);
  useBackofficeAuthStore.getState().markLocked();
  expect(productionIntentions.hasBody(metadata.key)).toBe(false);
  expect(productionIntentions.read("production")?.key).toBe(metadata.key);
});

it("a recovered durable rejection allows a corrected new intention without retaining its body", async () => {
  mocks.send.mockRejectedValueOnce(new TypeError("lost"));
  await expect(productionIntentions.begin(createContext, createPayload, null)).rejects.toThrow();
  const metadata = productionIntentions.read("production")!;
  mocks.recover.mockRejectedValueOnce(
    new ApiError(
      409,
      "Rejected",
      {
        code: "PRODUCTION_CONFLICT",
        message: "Rejected",
        details: null,
        field_errors: null,
        request_id: null,
      },
      true,
    ),
  );
  await expect(productionIntentions.recover(createContext)).rejects.toThrow();
  expect(productionIntentions.read("production")?.status).toBe("REJECTED");
  expect(productionIntentions.hasBody(metadata.key)).toBe(false);
  await productionIntentions.begin(
    createContext,
    { ...createPayload, planned_output_qty: "21" },
    metadata.key,
  );
  expect(mocks.send.mock.calls[1]![3]).not.toBe(metadata.key);
});
