// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { ApiError } from "@zeromerma/api-client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { returnIntentions, type ReturnIntentionContext } from "./return-command-intent";
const mocks = vi.hoisted(() => ({ commit: vi.fn(), recover: vi.fn() }));
vi.mock("./returns-api", () => ({
  commitSaleReturn: mocks.commit,
  recoverSaleReturn: mocks.recover,
}));
const context: ReturnIntentionContext = {
  userId: "actor",
  branchId: "branch",
  workstationId: "station",
  workstationCode: "POS-01",
  cashSessionId: "historic-cash",
  originalSaleId: "sale",
};
const body = () => ({
  workstation_code: "POS-01",
  cash_session_id: "historic-cash",
  original_sale_id: "sale",
  reason_code: "OTHER",
  refund_method_code: "CASH",
  notes: "private note",
  high_risk_acknowledged: false,
  lines: [
    {
      original_sale_line_id: "line",
      returned_quantity: "0.333",
      disposition_code: "RESTOCK_COUNTER",
    },
  ],
});
const failure = (status: number, code: string) =>
  new ApiError(status, code, {
    code,
    message: code,
    details: null,
    field_errors: null,
    request_id: null,
  });
beforeEach(() => {
  localStorage.clear();
  returnIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  Object.values(mocks).forEach((mock) =>
    mock
      .mockReset()
      .mockResolvedValue({
        id: "return",
        original_sale_id: "sale",
        refund_cash_movement_id: "refund",
      }),
  );
});
afterEach(() => vi.unstubAllGlobals());

it("retries the frozen return with the same identity and persists metadata only", async () => {
  const payload = body();
  mocks.commit.mockRejectedValueOnce(new TypeError("lost"));
  await expect(returnIntentions.begin(context, payload, null)).rejects.toThrow();
  payload.lines[0]!.returned_quantity = "9";
  await returnIntentions.retry(context);
  const [first, second] = mocks.commit.mock.calls.map((call) => call[0]);
  expect(second.payload.lines[0].returned_quantity).toBe("0.333");
  expect(second.idempotencyKey).toBe(first.idempotencyKey);
  expect(second.requestId).not.toBe(first.requestId);
  const saved = JSON.parse(localStorage.getItem("zeromerma-return-intention:station")!);
  expect(Object.keys(saved).sort()).toEqual(
    [
      "branchId",
      "cashSessionId",
      "key",
      "originalSaleId",
      "payloadDigest",
      "status",
      "userId",
      "workstationCode",
      "workstationId",
    ].sort(),
  );
  expect(JSON.stringify(saved)).not.toMatch(/private|notes|lines|quantity|refund_method/);
});
it("recovers the historic cash session after reload without sending another refund", async () => {
  mocks.commit.mockRejectedValueOnce(new TypeError("lost"));
  await expect(returnIntentions.begin(context, body(), null)).rejects.toThrow();
  const key = returnIntentions.read("station")!.key;
  returnIntentions.forgetBodies();
  const result = await returnIntentions.recover(context);
  expect(mocks.recover).toHaveBeenCalledWith(key, "POS-01", "historic-cash");
  expect(result.refund_cash_movement_id).toBe("refund");
  expect(mocks.commit).toHaveBeenCalledTimes(1);
});
it("blocks duplicate clicks and another tab's stale draft after confirmation", async () => {
  let finish!: (value: unknown) => void;
  mocks.commit.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const first = returnIntentions.begin(context, body(), null);
  await expect(returnIntentions.begin(context, body(), null)).rejects.toThrow();
  await vi.waitFor(() => expect(mocks.commit).toHaveBeenCalledTimes(1));
  finish({ id: "return", original_sale_id: "sale" });
  await first;
  await expect(returnIntentions.begin(context, body(), null)).rejects.toThrow();
  expect(mocks.commit).toHaveBeenCalledTimes(1);
});
it("retains UNKNOWN when recovery is unknown and a later retry rejects", async () => {
  mocks.commit.mockRejectedValueOnce(new TypeError("lost"));
  await expect(returnIntentions.begin(context, body(), null)).rejects.toThrow();
  mocks.recover.mockRejectedValueOnce(failure(409, "IDEMPOTENCY_RESULT_UNKNOWN"));
  await expect(returnIntentions.recover(context)).rejects.toThrow();
  mocks.commit.mockRejectedValueOnce(failure(409, "CONFLICT"));
  await expect(returnIntentions.retry(context)).rejects.toThrow();
  expect(returnIntentions.read("station")?.status).toBe("UNKNOWN");
  await expect(
    returnIntentions.begin(context, body(), returnIntentions.read("station")!.key),
  ).rejects.toThrow();
});
it("rejects a recovery snapshot belonging to a different original sale", async () => {
  mocks.commit.mockRejectedValueOnce(new TypeError("lost"));
  await expect(returnIntentions.begin(context, body(), null)).rejects.toThrow();
  mocks.recover.mockResolvedValueOnce({ id: "other", original_sale_id: "other-sale" });
  await expect(returnIntentions.recover(context)).rejects.toThrow(/otra venta/);
  expect(returnIntentions.read("station")?.status).toBe("CONFLICT");
});
it("allocates a new identity only after a known first-send rejection is corrected", async () => {
  mocks.commit.mockRejectedValueOnce(failure(400, "VALIDATION_ERROR"));
  await expect(returnIntentions.begin(context, body(), null)).rejects.toThrow();
  const previous = returnIntentions.read("station")!;
  expect(previous.status).toBe("REJECTED");
  await returnIntentions.begin(context, body(), previous.key);
  expect(mocks.commit.mock.calls[1]![0].idempotencyKey).not.toBe(previous.key);
});
