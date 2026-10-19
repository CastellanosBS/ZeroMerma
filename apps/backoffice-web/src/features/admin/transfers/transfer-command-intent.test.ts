import type { SessionResponse } from "@zeromerma/api-client";
import { useBackofficeAuthStore as auth } from "../../auth/backoffice-auth-store";
// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { transferIntentions, type TransferIntentionContext } from "./transfer-command-intent";
const mocks = vi.hoisted(() => ({
  create: vi.fn(),
  update: vi.fn(),
  dispatch: vi.fn(),
  receive: vi.fn(),
  cancel: vi.fn(),
  recover: vi.fn(),
}));
vi.mock("./api", () => ({
  createAdminTransfer: mocks.create,
  updateAdminTransfer: mocks.update,
  dispatchAdminTransfer: mocks.dispatch,
  receiveAdminTransfer: mocks.receive,
  cancelAdminTransfer: mocks.cancel,
  recoverAdminTransferCommand: mocks.recover,
}));
const context: TransferIntentionContext = {
  userId: "actor",
  branchId: "origin",
  transferId: "shipment",
  commandCode: "receive",
};
beforeEach(() => {
  localStorage.clear();
  transferIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  Object.values(mocks).forEach((mock) => mock.mockReset().mockResolvedValue({ id: "shipment" }));
});
afterEach(() => vi.unstubAllGlobals());
it.each(["update", "dispatch", "receive", "cancel"] as const)(
  "preserves %s identity across a lost response and reload",
  async (commandCode) => {
    const payload =
      commandCode === "update"
        ? { commandCode, body: { notes: "private note" } }
        : commandCode === "receive"
          ? {
              commandCode,
              body: {
                lines: [
                  {
                    shipmentLineId: "line",
                    receivedQuantity: "2",
                    varianceReason: "private reason",
                  },
                ],
              },
            }
          : commandCode === "dispatch"
            ? { commandCode, notes: "private note" }
            : { commandCode, reason: "private reason" };
    mocks[commandCode].mockRejectedValueOnce(new TypeError("lost"));
    await expect(
      transferIntentions.begin({ ...context, commandCode }, payload, null),
    ).rejects.toThrow();
    const key = transferIntentions.read("transfers")!.key;
    expect(localStorage.getItem("zeromerma-admin-transfer-intention:transfers")).not.toContain(
      "private",
    );
    transferIntentions.forgetBodies();
    await transferIntentions.recover({ ...context, commandCode });
    expect(mocks.recover).toHaveBeenCalledWith(commandCode, key, "origin");
    expect(mocks[commandCode]).toHaveBeenCalledTimes(1);
  },
);
it("a lost create never automatically dispatches after recovery", async () => {
  const create = { ...context, transferId: null, commandCode: "create" as const };
  mocks.create.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    transferIntentions.begin(
      create,
      {
        commandCode: "create",
        body: {
          originBranchId: "origin",
          destinationBranchId: "destination",
          lines: [{ productId: "product", quantity: "2" }],
        },
      },
      null,
    ),
  ).rejects.toThrow();
  await transferIntentions.recover(create);
  expect(mocks.dispatch).not.toHaveBeenCalled();
  expect(mocks.create).toHaveBeenCalledTimes(1);
});
it("rejects recovery for another shipment", async () => {
  mocks.dispatch.mockRejectedValueOnce(new TypeError("lost"));
  const dispatch = { ...context, commandCode: "dispatch" as const };
  await expect(
    transferIntentions.begin(dispatch, { commandCode: "dispatch", notes: null }, null),
  ).rejects.toThrow();
  mocks.recover.mockResolvedValueOnce({ id: "other" });
  await expect(transferIntentions.recover(dispatch)).rejects.toThrow(/otro envío/);
});

function authResponse(version = "v1", sessionId = "session"): SessionResponse {
  return {
    csrf_token: "memory-only-token",
    session: {
      id: sessionId,
      audience: "BACKOFFICE",
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
      default_surface: "BACKOFFICE",
      allowed_surfaces: ["BACKOFFICE"],
      authorization_surface: "BACKOFFICE",
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
    await expect(
      transferIntentions.begin(
        context,
        {
          commandCode: "receive",
          body: { lines: [{ shipmentLineId: "line", receivedQuantity: "2" }] },
        },
        null,
      ),
    ).rejects.toThrow();
    const original = transferIntentions.read("transfers")!;
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
    expect(transferIntentions.read("transfers")).toEqual(original);
    await expect(transferIntentions.retry(context)).rejects.toThrow();
    expect(mocks.receive).toHaveBeenCalledTimes(1);
    await transferIntentions.recover(context);
    expect(transferIntentions.read("transfers")?.status).toBe("CONFIRMED");
    auth.getState().clearSession();
  },
);
