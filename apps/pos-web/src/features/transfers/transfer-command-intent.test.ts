import type { SessionResponse } from "@zeromerma/api-client";
import { usePosAuthStore as auth } from "../auth/auth-store";
// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { ApiError } from "@zeromerma/api-client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { transferIntentions, type TransferIntentionContext } from "./transfer-command-intent";
const mocks = vi.hoisted(() => ({ dispatch: vi.fn(), receive: vi.fn(), recover: vi.fn() }));
vi.mock("./transfers-api", () => ({
  commitTransferDispatch: mocks.dispatch,
  receiveTransfer: mocks.receive,
  recoverTransferCommand: mocks.recover,
}));
const context: TransferIntentionContext = {
  userId: "actor",
  branchId: "branch",
  workstationId: "station",
  workstationCode: "POS-01",
  cashSessionId: "historic-cash",
  commandCode: "receive",
  transferId: "shipment",
};
const body = () => ({
  workstation_code: "POS-01",
  cash_session_id: "historic-cash",
  notes: "private note",
  lines: [
    {
      shipment_line_id: "line",
      expected_quantity: "3",
      received_quantity: "2",
      variance_reason: "private reason",
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
  transferIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  Object.values(mocks).forEach((mock) =>
    mock.mockReset().mockResolvedValue({ id: "shipment", receipt_id: "receipt" }),
  );
});
afterEach(() => vi.unstubAllGlobals());
it("freezes the receipt body and keeps the same key on retry without persisting sensitive input", async () => {
  const payload = body();
  mocks.receive.mockRejectedValueOnce(new TypeError("lost"));
  await expect(transferIntentions.begin(context, payload, null)).rejects.toThrow();
  payload.lines[0]!.received_quantity = "9";
  await transferIntentions.retry(context);
  expect(mocks.receive.mock.calls[1]![1].lines[0].received_quantity).toBe("2");
  expect(mocks.receive.mock.calls[1]![2]).toBe(mocks.receive.mock.calls[0]![2]);
  const saved = localStorage.getItem("zeromerma-transfer-intention:station")!;
  expect(saved).not.toContain("private");
  expect(saved).not.toContain("received_quantity");
});
it("recovers after reload using the original cash context without sending again", async () => {
  mocks.receive.mockRejectedValueOnce(new TypeError("lost"));
  await expect(transferIntentions.begin(context, body(), null)).rejects.toThrow();
  const key = transferIntentions.read("station")!.key;
  transferIntentions.forgetBodies();
  await transferIntentions.recover(context);
  expect(mocks.recover).toHaveBeenCalledWith("receive", key, "POS-01", "historic-cash");
  expect(mocks.receive).toHaveBeenCalledTimes(1);
});
it("blocks duplicate clicks and a stale draft after another tab confirms", async () => {
  let finish!: (value: unknown) => void;
  mocks.receive.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const first = transferIntentions.begin(context, body(), null);
  await expect(transferIntentions.begin(context, body(), null)).rejects.toThrow();
  await vi.waitFor(() => expect(mocks.receive).toHaveBeenCalledTimes(1));
  finish({ id: "shipment" });
  await first;
  await expect(transferIntentions.begin(context, body(), null)).rejects.toThrow();
  expect(mocks.receive).toHaveBeenCalledTimes(1);
});
it("does not replace an unknown receipt after later rejection", async () => {
  mocks.receive.mockRejectedValueOnce(new TypeError("lost"));
  await expect(transferIntentions.begin(context, body(), null)).rejects.toThrow();
  mocks.recover.mockRejectedValueOnce(failure(409, "IDEMPOTENCY_RESULT_UNKNOWN"));
  await expect(transferIntentions.recover(context)).rejects.toThrow();
  mocks.receive.mockRejectedValueOnce(failure(400, "VALIDATION_ERROR"));
  await expect(transferIntentions.retry(context)).rejects.toThrow();
  expect(transferIntentions.read("station")?.status).toBe("UNKNOWN");
});
it("rejects a recovered result bound to another shipment", async () => {
  mocks.receive.mockRejectedValueOnce(new TypeError("lost"));
  await expect(transferIntentions.begin(context, body(), null)).rejects.toThrow();
  mocks.recover.mockResolvedValueOnce({ id: "other" });
  await expect(transferIntentions.recover(context)).rejects.toThrow(/otro envío/);
  expect(transferIntentions.read("station")?.status).toBe("CONFLICT");
});
it("allows correction only after a known first-send rejection", async () => {
  mocks.receive.mockRejectedValueOnce(failure(400, "VALIDATION_ERROR"));
  await expect(transferIntentions.begin(context, body(), null)).rejects.toThrow();
  const previous = transferIntentions.read("station")!;
  expect(previous.status).toBe("REJECTED");
  await transferIntentions.begin(context, body(), previous.key);
  expect(mocks.receive.mock.calls[1]![2]).not.toBe(previous.key);
});
it("dispatches through its own command while preserving the single station intention", async () => {
  await transferIntentions.begin(
    { ...context, commandCode: "dispatch", transferId: null },
    {
      workstation_code: "POS-01",
      cash_session_id: "historic-cash",
      destination_branch_id: "destination",
      lines: [{ product_id: "product", quantity: "1" }],
    },
    null,
  );
  expect(mocks.dispatch).toHaveBeenCalledTimes(1);
  expect(mocks.receive).not.toHaveBeenCalled();
});

function authResponse(version = "v1", sessionId = "session"): SessionResponse {
  return {
    csrf_token: "memory-only-token",
    session: {
      id: sessionId,
      audience: "POS",
      status: "ACTIVE",
      created_at: "2026-10-18T00:00:00Z",
      last_activity_at: "2026-10-18T00:00:00Z",
      idle_expires_at: "2026-10-18T00:30:00Z",
      absolute_expires_at: "2026-10-18T08:00:00Z",
      workstation_id: null,
      cash_session_id: null,
      revoked_at: null,
      revocation_reason: null,
    },
    user: {
      id: "actor",
      email: "operator@example.invalid",
      full_name: "Operator",
      is_active: true,
      default_surface: "POS",
      allowed_surfaces: ["POS"],
      authorization_surface: "POS",
      authorization_version: version,
      is_superadministrator: false,
      effective_grants: [],
      password_reset_required: false,
    },
  };
}

it.each(["lock", "version", "session"] as const)(
  "forgets retry bodies on %s changes while preserving recovery metadata",
  async (change) => {
    auth.getState().setSession(authResponse());
    mocks.receive.mockRejectedValueOnce(new TypeError("lost"));
    await expect(transferIntentions.begin(context, body(), null)).rejects.toThrow();
    const original = transferIntentions.read("station")!;
    expect(transferIntentions.hasBody(original.key)).toBe(true);
    const generation = auth.getState().generation;
    if (change === "lock") auth.getState().markLocked();
    else
      auth
        .getState()
        .setSession(
          authResponse(
            change === "version" ? "v2" : "v1",
            change === "session" ? "new-session" : "session",
          ),
        );
    if (change !== "lock") expect(auth.getState().generation).toBe(generation);
    expect(transferIntentions.hasBody(original.key)).toBe(false);
    expect(transferIntentions.read("station")).toEqual(original);
    await expect(transferIntentions.retry(context)).rejects.toThrow();
    expect(mocks.receive).toHaveBeenCalledTimes(1);
    await transferIntentions.recover(context);
    expect(transferIntentions.read("station")?.status).toBe("CONFIRMED");
    auth.getState().clearSession();
  },
);
