import { usePosAuthStore } from "../auth/auth-store";
// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { ApiError } from "@zeromerma/api-client";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import {
  operationIntentions,
  type OperationCommandCode,
  type OperationCommandPayload,
  type OperationIntentionContext,
} from "./operation-command-intent";
const mocks = vi.hoisted(() => ({
  counter: vi.fn(),
  waste: vi.fn(),
  correction: vi.fn(),
  recover: vi.fn(),
}));
vi.mock("../operations/operations-api", () => ({
  commitCounterTransfer: mocks.counter,
  commitWasteRecord: mocks.waste,
}));
vi.mock("../corrections/corrections-api", () => ({ commitCorrection: mocks.correction }));
vi.mock("../../lib/http", () => ({ requestJson: mocks.recover }));
const context = (commandCode: OperationCommandCode): OperationIntentionContext => ({
  userId: "actor",
  branchId: "branch",
  workstationId: "station",
  workstationCode: "POS-01",
  cashSessionId: "historical",
  commandCode,
  targetDocumentId: commandCode === "correction" ? "target" : null,
});
function payload(commandCode: OperationCommandCode): OperationCommandPayload {
  const body = {
    workstation_code: "POS-01",
    cash_session_id: "historical",
    notes: "Private notes",
  };
  if (commandCode === "correction")
    return {
      commandCode,
      body: {
        ...body,
        target_document_id: "target",
        reason_code: "WRONG_QUANTITY",
        high_impact_acknowledged: false,
        lines: [{ product_id: "product", delta_quantity: "-1" }],
      },
    };
  if (commandCode === "waste")
    return {
      commandCode,
      body: {
        ...body,
        reason_code: "DAMAGED",
        high_impact_acknowledged: false,
        source_bucket_code: "BACKROOM",
        lines: [{ product_id: "product", quantity: "1" }],
      },
    };
  return { commandCode, body: { ...body, lines: [{ product_id: "product", quantity: "1" }] } };
}
const result = {
  id: "result",
  branch_id: "branch",
  workstation_id: "station",
  cash_session_id: "historical",
  target_document_id: "target",
};
const error = (status: number, code: string) =>
  new ApiError(status, code, {
    code,
    message: code,
    details: null,
    field_errors: null,
    request_id: null,
  });
const mock = (code: OperationCommandCode) =>
  code === "counter-transfer" ? mocks.counter : mocks[code];
beforeEach(() => {
  localStorage.clear();
  operationIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  Object.values(mocks).forEach((m) => m.mockReset().mockResolvedValue(result));
});
afterEach(() => vi.unstubAllGlobals());
it("forgets a volatile body when grants change without changing the actor or generation", async () => {
  usePosAuthStore.setState({
    user: {
      id: "actor",
      email: "actor@example.invalid",
      full_name: "Actor",
      is_active: true,
      allowed_surfaces: ["POS"],
      default_surface: "POS",
      authorization_surface: "POS",
      effective_grants: [],
      authorization_version: "before",
      is_superadministrator: false,
      password_reset_required: false,
    },
  });
  mocks.waste.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    operationIntentions.begin(context("waste"), payload("waste"), null),
  ).rejects.toThrow();
  const saved = operationIntentions.read("station")!;
  const generation = usePosAuthStore.getState().generation;
  usePosAuthStore.setState((state) => ({
    user: { ...state.user!, authorization_version: "after" },
  }));
  expect(usePosAuthStore.getState().generation).toBe(generation);
  expect(operationIntentions.hasBody(saved.key)).toBe(false);
  expect(operationIntentions.read("station")).toEqual(saved);
});
it.each(["correction", "counter-transfer", "waste"] as const)(
  "freezes %s body and key across retry, then reload recovery stores metadata only",
  async (code) => {
    const body = payload(code);
    mock(code).mockRejectedValueOnce(new TypeError("lost"));
    await expect(operationIntentions.begin(context(code), body, null)).rejects.toThrow();
    const saved = operationIntentions.read("station")!;
    expect(Object.keys(saved).sort()).toEqual(
      [
        "userId",
        "branchId",
        "workstationId",
        "workstationCode",
        "cashSessionId",
        "commandCode",
        "targetDocumentId",
        "key",
        "status",
        "payloadDigest",
      ].sort(),
    );
    expect(JSON.stringify(saved)).not.toMatch(/Private|notes|quantity|reason_code/);
    body.body.notes = "Mutated draft";
    await operationIntentions.retry(context(code));
    const [first, second] = mock(code).mock.calls;
    const getBody = (args: unknown[]) =>
      code === "correction" ? (args[0] as { payload: unknown }).payload : args[0];
    const getKey = (args: unknown[]) =>
      code === "correction" ? (args[0] as { idempotencyKey: string }).idempotencyKey : args[1];
    expect(getBody(second!)).toEqual(getBody(first!));
    expect(getKey(second!)).toBe(saved.key);
    // Simulate loss of the successful retry response in another document before recovery.
    localStorage.setItem(
      "zeromerma-operation-intention:station",
      JSON.stringify({ ...saved, status: "UNKNOWN" }),
    );
    operationIntentions.forgetBodies();
    await operationIntentions.recover(context(code));
    expect(mock(code)).toHaveBeenCalledTimes(2);
    expect(mocks.recover.mock.calls[0]![0].path).toContain("cash_session_id=historical");
    expect(operationIntentions.read("station")?.status).toBe("CONFIRMED");
  },
);
it("blocks duplicate submission and stale foreign draft after confirmation", async () => {
  let finish!: (value: typeof result) => void;
  mocks.counter.mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  const first = operationIntentions.begin(
    context("counter-transfer"),
    payload("counter-transfer"),
    null,
  );
  await expect(
    operationIntentions.begin(context("waste"), payload("waste"), null),
  ).rejects.toThrow();
  await vi.waitFor(() => expect(mocks.counter).toHaveBeenCalledOnce());
  finish(result);
  await first;
  await expect(
    operationIntentions.begin(context("waste"), payload("waste"), null),
  ).rejects.toThrow();
  expect(mocks.waste).not.toHaveBeenCalled();
});
it("retains unknown after missing result, authorization and later deterministic failures", async () => {
  mocks.correction.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    operationIntentions.begin(context("correction"), payload("correction"), null),
  ).rejects.toThrow();
  const key = operationIntentions.read("station")!.key;
  for (const [status, code] of [
    [409, "IDEMPOTENCY_RESULT_UNKNOWN"],
    [401, "SESSION_REVOKED"],
    [400, "CORRECTION_VALIDATION_ERROR"],
  ] as const) {
    mocks.recover.mockRejectedValueOnce(error(status, code));
    await expect(operationIntentions.recover(context("correction"))).rejects.toThrow();
    expect(operationIntentions.read("station")).toMatchObject({ key, status: "UNKNOWN" });
  }
  await expect(
    operationIntentions.begin(context("waste"), payload("waste"), key),
  ).rejects.toThrow();
});
it("rejects a recovered correction bound to another source document", async () => {
  mocks.correction.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    operationIntentions.begin(context("correction"), payload("correction"), null),
  ).rejects.toThrow();
  mocks.recover.mockResolvedValue({ ...result, target_document_id: "other" });
  await expect(operationIntentions.recover(context("correction"))).rejects.toThrow();
  expect(operationIntentions.read("station")?.status).toBe("CONFLICT");
});

it("discards only the frozen body on an authentication generation change", async () => {
  mocks.waste.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    operationIntentions.begin(context("waste"), payload("waste"), null),
  ).rejects.toThrow();
  const saved = operationIntentions.read("station")!;
  expect(operationIntentions.hasBody(saved.key)).toBe(true);
  usePosAuthStore.getState().clearSession();
  expect(operationIntentions.hasBody(saved.key)).toBe(false);
  expect(operationIntentions.read("station")).toMatchObject({ key: saved.key, status: "UNKNOWN" });
});
