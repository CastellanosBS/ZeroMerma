// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { ApiError } from "@zeromerma/api-client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cashIntentions,
  type CashCommandCode,
  type CashIntentionContext,
  type CashCommandPayload,
} from "./cash-command-intent";
const mocks = vi.hoisted(() => ({
  open: vi.fn(),
  payment: vi.fn(),
  discount: vi.fn(),
  close: vi.fn(),
  recover: vi.fn(),
}));
vi.mock("../cash-session-open/cash-session-api", () => ({ openCashSession: mocks.open }));
vi.mock("../payments/payments-api", () => ({ createPayment: mocks.payment }));
vi.mock("../discounts/discounts-api", () => ({ createDiscount: mocks.discount }));
vi.mock("../cash-close/cash-close-api", () => ({ commitCashClose: mocks.close }));
vi.mock("../../lib/http", () => ({ requestJson: mocks.recover }));
const context = (commandCode: CashCommandCode): CashIntentionContext => ({
  userId: "actor",
  branchId: "branch",
  workstationId: "station",
  workstationCode: "POS-01",
  cashSessionId: commandCode === "open" ? null : "historic-cash",
  commandCode,
});
const body = (command: CashCommandCode): CashCommandPayload => {
  if (command === "open") return { workstation_code: "POS-01", opening_amount: "0.00" };
  if (command === "close")
    return {
      workstation_code: "POS-01",
      cash_session_id: "historic-cash",
      counted_payment_methods: [{ payment_method_code: "CASH", counted_amount: "10.00" }],
      counted_product_lines: [],
      close_mode: "WITH_COUNT",
      counter_empty_confirmed: true,
    };
  return {
    workstation_code: "POS-01",
    cash_session_id: "historic-cash",
    total_amount: "10.00",
    payment_method_code: "CASH",
    concept: "private concept",
    notes: "private note",
    ...(command === "payment"
      ? { payee_name: "private payee" }
      : { subject_name: "private subject", high_value_acknowledged: false }),
  };
};
const result = {
  id: "result",
  branch_id: "branch",
  workstation_id: "station",
  cash_session_id: "historic-cash",
  cash_movement_id: "movement",
};
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
  cashIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  Object.values(mocks).forEach((mock) => mock.mockReset().mockResolvedValue(result));
});
afterEach(() => vi.unstubAllGlobals());
const commands = ["open", "payment", "discount", "close"] as const;
it.each(commands)(
  "retries %s with the exact frozen body and key, storing metadata only",
  async (command) => {
    const payload = body(command);
    mocks[command].mockRejectedValueOnce(new TypeError("lost"));
    await expect(cashIntentions.begin(context(command), payload, null)).rejects.toThrow();
    payload.workstation_code = "OTHER";
    await cashIntentions.retry(context(command));
    const [first, second] = mocks[command].mock.calls;
    const firstPayload = command === "close" ? first![0] : first![0].payload;
    const secondPayload = command === "close" ? second![0] : second![0].payload;
    expect(secondPayload).toEqual(firstPayload);
    expect(secondPayload.workstation_code).toBe("POS-01");
    expect(command === "close" ? second![1] : second![0].idempotencyKey).toBe(
      command === "close" ? first![1] : first![0].idempotencyKey,
    );
    const saved = JSON.parse(localStorage.getItem("zeromerma-cash-intention:station")!);
    expect(Object.keys(saved).sort()).toEqual(
      [
        "branchId",
        "cashSessionId",
        "commandCode",
        "key",
        "payloadDigest",
        "status",
        "userId",
        "workstationCode",
        "workstationId",
      ].sort(),
    );
    expect(JSON.stringify(saved)).not.toMatch(/private|amount|payee|notes|counted/);
  },
);
it.each(commands)(
  "recovers %s after reload using the original cash context and no new POST",
  async (command) => {
    mocks[command].mockRejectedValueOnce(new TypeError("lost"));
    await expect(cashIntentions.begin(context(command), body(command), null)).rejects.toThrow();
    cashIntentions.forgetBodies();
    await cashIntentions.recover(context(command));
    expect(mocks[command]).toHaveBeenCalledTimes(1);
    const path = mocks.recover.mock.calls[0]![0].path as string;
    expect(path).toContain("workstation_code=POS-01");
    if (command === "open") expect(path).not.toContain("cash_session_id");
    else expect(path).toContain("cash_session_id=historic-cash");
    expect(cashIntentions.read("station")?.status).toBe("CONFIRMED");
  },
);
it("blocks other cash commands, synchronous double submit and a foreign tab while one request is pending", async () => {
  let finish!: (value: typeof result) => void;
  mocks.payment.mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  const first = cashIntentions.begin(context("payment"), body("payment"), null);
  await expect(cashIntentions.begin(context("close"), body("close"), null)).rejects.toThrow();
  await vi.waitFor(() => expect(mocks.payment).toHaveBeenCalledOnce());
  finish(result);
  await first;
  await expect(cashIntentions.begin(context("discount"), body("discount"), null)).rejects.toThrow();
  expect(mocks.discount).not.toHaveBeenCalled();
});
it("never releases an uncertain close on later authentication, closed-state or missing-result failures", async () => {
  mocks.close.mockRejectedValueOnce(new TypeError("lost"));
  await expect(cashIntentions.begin(context("close"), body("close"), null)).rejects.toThrow();
  const key = cashIntentions.read("station")!.key;
  for (const [status, code] of [
    [401, "SESSION_REVOKED"],
    [409, "CASH_CLOSE_ALREADY_EXISTS"],
    [409, "IDEMPOTENCY_RESULT_UNKNOWN"],
  ] as const) {
    mocks.recover.mockRejectedValueOnce(failure(status, code));
    await expect(cashIntentions.recover(context("close"))).rejects.toThrow();
    expect(cashIntentions.read("station")).toMatchObject({ key, status: "UNKNOWN" });
  }
  await expect(cashIntentions.begin(context("open"), body("open"), key)).rejects.toThrow();
});
it("rejects a result bound to a different historic cash session", async () => {
  mocks.payment.mockRejectedValueOnce(new TypeError("lost"));
  await expect(cashIntentions.begin(context("payment"), body("payment"), null)).rejects.toThrow();
  mocks.recover.mockResolvedValueOnce({ ...result, cash_session_id: "new-shift" });
  await expect(cashIntentions.recover(context("payment"))).rejects.toThrow();
  expect(cashIntentions.read("station")?.status).toBe("CONFLICT");
});
it("allows a corrected draft with a new identity only after a deterministic first rejection", async () => {
  mocks.payment.mockRejectedValueOnce(failure(422, "VALIDATION_ERROR"));
  await expect(cashIntentions.begin(context("payment"), body("payment"), null)).rejects.toThrow();
  const rejected = cashIntentions.read("station")!;
  expect(rejected.status).toBe("REJECTED");
  await cashIntentions.begin(context("payment"), body("payment"), rejected.key);
  expect(cashIntentions.read("station")!.key).not.toBe(rejected.key);
});

it.each(["open", "payment", "discount", "close"] as const)(
  "releases only the verified durable close rejection while recovering %s",
  async (command) => {
    mocks[command].mockRejectedValueOnce(new TypeError("lost"));
    await expect(cashIntentions.begin(context(command), body(command), null)).rejects.toThrow();
    const key = cashIntentions.read("station")!.key;
    mocks.recover.mockRejectedValueOnce(
      new ApiError(
        409,
        "Already closed",
        {
          code: "CASH_CLOSE_ALREADY_EXISTS",
          message: "Already closed",
          details: null,
          field_errors: null,
          request_id: null,
        },
        true,
      ),
    );
    await expect(cashIntentions.recover(context(command))).rejects.toThrow("Already closed");
    expect(cashIntentions.read("station")).toMatchObject({
      key,
      status: command === "close" ? "REJECTED" : "UNKNOWN",
    });
  },
);
