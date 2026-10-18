// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { ApiError } from "@zeromerma/api-client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ConfirmSaleRequest } from "../../lib/api-contracts";
import {
  beginSaleConfirmation,
  forgetSaleIntentionBodies,
  readSaleIntention,
  recoverSaleConfirmation,
  retrySaleConfirmation,
  SALE_INTENTION_STORAGE_PREFIX,
} from "./sale-confirmation-intent";

const mocks = vi.hoisted(() => ({ confirm: vi.fn(), recover: vi.fn() }));
vi.mock("./pos-terminal-api", () => ({
  confirmPosSale: mocks.confirm,
  getSaleConfirmation: mocks.recover,
}));

const context = {
  userId: "user",
  branchId: "branch",
  workstationId: "station",
  workstationCode: "POS-01",
  cashSessionId: "cash",
};
const payload: ConfirmSaleRequest = {
  cash_session_id: "cash",
  workstation_code: "POS-01",
  lines: [{ capture_mode: "CLASS_CAPTURE", product_class_id: "class", quantity: "1" }],
  payments: [{ payment_method_code: "CASH", tendered_amount: "3" }],
};
const sale = { id: "sale", total_amount: "3.00" };
const apiError = (status: number, code: string) =>
  new ApiError(status, code, {
    code,
    message: code,
    details: null,
    request_id: null,
    field_errors: null,
  });

beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "claim" })) },
  });
  localStorage.clear();
  forgetSaleIntentionBodies();
  mocks.confirm.mockReset().mockResolvedValue(sale);
  mocks.recover.mockReset().mockResolvedValue(sale);
});
afterEach(() => vi.unstubAllGlobals());

describe("sale intention lifecycle", () => {
  it("stores only recovery metadata and reuses an immutable body and key after a lost response", async () => {
    mocks.confirm.mockRejectedValueOnce(new TypeError("connection lost"));
    const draft = structuredClone(payload);
    await expect(beginSaleConfirmation(context, draft, null)).rejects.toThrow("connection lost");
    const metadata = readSaleIntention("station")!;
    expect(metadata.status).toBe("UNKNOWN");
    expect(Object.keys(metadata).sort()).toEqual(
      [
        "userId",
        "branchId",
        "workstationId",
        "workstationCode",
        "cashSessionId",
        "key",
        "payloadDigest",
        "status",
      ].sort(),
    );
    expect(localStorage.getItem(`${SALE_INTENTION_STORAGE_PREFIX}station`)).not.toMatch(
      /payments|quantity|tendered_amount|cookie|csrf|password/,
    );
    draft.payments[0]!.tendered_amount = "999";
    expect(await retrySaleConfirmation(context)).toEqual(sale);
    expect(mocks.confirm.mock.calls[1]).toEqual(mocks.confirm.mock.calls[0]);
    expect(mocks.confirm.mock.calls[1]![0].payments[0].tendered_amount).toBe("3");
    expect(readSaleIntention("station")?.status).toBe("CONFIRMED");
  });

  it("allocates a new UUIDv7 for an intentionally new sale with an identical cart", async () => {
    await beginSaleConfirmation(context, payload, null);
    const previous = readSaleIntention("station")!;
    await beginSaleConfirmation(context, payload, previous.key);
    expect(mocks.confirm.mock.calls[1]![1]).not.toBe(previous.key);
  });

  it("blocks a synchronous double submit before the first asynchronous step", async () => {
    const first = beginSaleConfirmation(context, payload, null);
    await expect(beginSaleConfirmation(context, payload, null)).rejects.toThrow("procesando");
    await first;
    expect(mocks.confirm).toHaveBeenCalledTimes(1);
  });

  it("refuses a foreign tab claim and never silently queues a new sale", async () => {
    vi.mocked(navigator.locks.request).mockImplementationOnce(async (_name, _options, callback) =>
      callback!(null),
    );
    await expect(beginSaleConfirmation(context, payload, null)).rejects.toThrow("Otra pestaña");
    expect(mocks.confirm).not.toHaveBeenCalled();
  });

  it("rejects a stale draft after another tab completed a new intention", async () => {
    await beginSaleConfirmation(context, payload, null);
    await expect(beginSaleConfirmation(context, payload, null)).rejects.toThrow("otra pestaña");
    expect(mocks.confirm).toHaveBeenCalledTimes(1);
  });

  it("recovers the committed response after losing the in-memory body without another POST", async () => {
    mocks.confirm.mockRejectedValueOnce(new TypeError("lost"));
    await expect(beginSaleConfirmation(context, payload, null)).rejects.toThrow();
    const metadata = readSaleIntention("station")!;
    forgetSaleIntentionBodies();
    expect(await recoverSaleConfirmation(context)).toEqual(sale);
    expect(mocks.recover).toHaveBeenCalledWith(metadata.key, "POS-01", "cash");
    expect(mocks.confirm).toHaveBeenCalledTimes(1);
  });

  it("preserves UNKNOWN after reload with no result and cannot construct a new intention", async () => {
    mocks.confirm.mockRejectedValueOnce(new TypeError("lost"));
    await expect(beginSaleConfirmation(context, payload, null)).rejects.toThrow();
    const key = readSaleIntention("station")!.key;
    forgetSaleIntentionBodies();
    mocks.recover.mockRejectedValueOnce(apiError(409, "IDEMPOTENCY_RESULT_UNKNOWN"));
    await expect(recoverSaleConfirmation(context)).rejects.toThrow();
    await expect(retrySaleConfirmation(context)).rejects.toThrow("contenido original");
    await expect(beginSaleConfirmation(context, payload, key)).rejects.toThrow("otra pestaña");
    expect(readSaleIntention("station")!.key).toBe(key);
    expect(mocks.confirm).toHaveBeenCalledTimes(1);
  });

  it.each([401, 403, 409, 422, 423, 429])(
    "retains an uncertain intention after a subsequent %i response",
    async (status) => {
      mocks.confirm
        .mockRejectedValueOnce(new TypeError("lost"))
        .mockRejectedValueOnce(apiError(status, "LATER_FAILURE"));
      await expect(beginSaleConfirmation(context, payload, null)).rejects.toThrow();
      await expect(retrySaleConfirmation(context)).rejects.toThrow();
      expect(readSaleIntention("station")?.status).toBe("UNKNOWN");
    },
  );

  it("releases a known first-send validation rejection for a corrected new intention", async () => {
    mocks.confirm.mockRejectedValueOnce(apiError(422, "VALIDATION_ERROR"));
    await expect(beginSaleConfirmation(context, payload, null)).rejects.toThrow();
    const previous = readSaleIntention("station")!;
    expect(previous.status).toBe("REJECTED");
    await beginSaleConfirmation(context, payload, previous.key);
    expect(mocks.confirm.mock.calls[1]![1]).not.toBe(previous.key);
  });

  it("blocks conflicting keys and another operator without resubmitting", async () => {
    mocks.confirm.mockRejectedValueOnce(apiError(409, "IDEMPOTENCY_KEY_REUSED"));
    await expect(beginSaleConfirmation(context, payload, null)).rejects.toThrow();
    await expect(retrySaleConfirmation(context)).rejects.toThrow("conflicto");
    await expect(recoverSaleConfirmation({ ...context, userId: "other" })).rejects.toThrow(
      "operador",
    );
    expect(readSaleIntention("station")?.status).toBe("CONFLICT");
    expect(mocks.confirm).toHaveBeenCalledTimes(1);
  });

  it("fails closed when coordination or persistent metadata are unavailable", async () => {
    Object.defineProperty(navigator, "locks", { configurable: true, value: undefined });
    await expect(beginSaleConfirmation(context, payload, null)).rejects.toThrow("navegador");
    expect(mocks.confirm).not.toHaveBeenCalled();
  });
});
