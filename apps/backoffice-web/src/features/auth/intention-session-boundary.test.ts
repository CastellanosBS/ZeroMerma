// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import type { SessionResponse } from "@zeromerma/api-client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useBackofficeAuthStore as auth } from "./backoffice-auth-store";
import { adminOrderIntentions } from "../admin/orders/order-command-intent";
import { purchaseIntentions } from "../admin/purchases/purchase-command-intent";
import { productionIntentions } from "../admin/production/production-command-intent";
const mocks = vi.hoisted(() => ({ send: vi.fn() }));
vi.mock("../admin/orders/api", () => ({
  sendAdminOrderCommand: mocks.send,
  recoverAdminOrderCommand: mocks.send,
}));
vi.mock("../admin/purchases/api", () => ({
  createAdminPurchase: mocks.send,
  createAdminDirectEntry: mocks.send,
  updateAdminPurchase: mocks.send,
  confirmAdminPurchase: mocks.send,
  receiveAdminPurchase: mocks.send,
  cancelAdminPurchase: mocks.send,
  recoverAdminPurchaseCommand: mocks.send,
}));
vi.mock("../admin/production/api", () => ({
  sendProductionCommand: mocks.send,
  recoverProductionCommand: mocks.send,
}));
function response(): SessionResponse {
  return {
    csrf_token: "test-only-memory-token",
    session: {
      id: "session",
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
      email: "actor@example.test",
      full_name: "Actor",
      is_active: true,
      default_surface: "BACKOFFICE",
      allowed_surfaces: ["BACKOFFICE"],
      authorization_surface: "BACKOFFICE",
      authorization_version: "v1",
      is_superadministrator: false,
      effective_grants: [],
      password_reset_required: false,
    },
  };
}
const cases = [
  {
    name: "orders",
    begin: () =>
      adminOrderIntentions.begin(
        { userId: "actor", branchId: "branch", orderId: "order", commandCode: "mark-ready" },
        {},
        null,
      ),
    read: () => adminOrderIntentions.read("orders"),
    hasBody: adminOrderIntentions.hasBody,
  },
  {
    name: "purchases",
    begin: () =>
      purchaseIntentions.begin(
        { userId: "actor", branchId: "branch", purchaseId: "purchase", commandCode: "confirm" },
        { commandCode: "confirm" },
        null,
      ),
    read: () => purchaseIntentions.read("purchases"),
    hasBody: purchaseIntentions.hasBody,
  },
  {
    name: "production",
    begin: () =>
      productionIntentions.begin(
        { userId: "actor", branchId: "branch", productionId: "batch", commandCode: "release" },
        {},
        null,
      ),
    read: () => productionIntentions.read("production"),
    hasBody: productionIntentions.hasBody,
  },
];
beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  auth.getState().clearSession();
  auth.getState().setSession(response());
  mocks.send.mockReset().mockRejectedValue(new TypeError("lost response"));
});
afterEach(() => {
  auth.getState().clearSession();
  vi.unstubAllGlobals();
});
for (const boundary of ["lock", "logout", "actor", "session", "authority"] as const) {
  it.each(cases)(
    `clears $name volatile content on ${boundary}, preserving its recovery identity`,
    async (entry) => {
      await expect(entry.begin()).rejects.toThrow("lost response");
      const metadata = entry.read()!;
      expect(entry.hasBody(metadata.key)).toBe(true);
      const generation = auth.getState().generation;
      if (boundary === "lock") auth.getState().markLocked();
      else if (boundary === "logout") auth.getState().clearSession();
      else {
        const next = response();
        if (boundary === "actor") next.user.id = "other";
        if (boundary === "session") next.session.id = "other-session";
        if (boundary === "authority") next.user.authorization_version = "v2";
        auth.getState().setSession(next);
        expect(auth.getState().generation).toBe(generation);
      }
      expect(entry.hasBody(metadata.key)).toBe(false);
      expect(entry.read()).toEqual(metadata);
      expect(mocks.send).toHaveBeenCalledTimes(1);
    },
  );
}
it.each(cases)("keeps $name volatile content through routine activity refresh", async (entry) => {
  await expect(entry.begin()).rejects.toThrow("lost response");
  const metadata = entry.read()!;
  auth
    .getState()
    .updateSession({ ...response().session, last_activity_at: "2026-10-18T00:01:00Z" });
  expect(entry.hasBody(metadata.key)).toBe(true);
  expect(entry.read()).toEqual(metadata);
});
