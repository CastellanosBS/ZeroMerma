// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import type { SessionResponse } from "@zeromerma/api-client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { usePosAuthStore as auth } from "./auth-store";
import { cashIntentions } from "../cash-commands/cash-command-intent";
import { orderIntentions } from "../orders/order-command-intent";
import { returnIntentions } from "../returns/return-command-intent";
import {
  beginSaleConfirmation,
  hasSaleIntentionBody,
  readSaleIntention,
} from "../pos-terminal/sale-confirmation-intent";

const mocks = vi.hoisted(() => ({ send: vi.fn() }));
vi.mock("../cash-session-open/cash-session-api", () => ({ openCashSession: mocks.send }));
vi.mock("../payments/payments-api", () => ({ createPayment: mocks.send }));
vi.mock("../discounts/discounts-api", () => ({ createDiscount: mocks.send }));
vi.mock("../cash-close/cash-close-api", () => ({ commitCashClose: mocks.send }));
vi.mock("../orders/orders-api", () => ({
  createOrder: mocks.send,
  markOrderReady: mocks.send,
  deliverOrder: mocks.send,
  cancelOrder: mocks.send,
  recoverOrderCommand: mocks.send,
}));
vi.mock("../returns/returns-api", () => ({
  commitSaleReturn: mocks.send,
  recoverSaleReturn: mocks.send,
}));
vi.mock("../pos-terminal/pos-terminal-api", () => ({
  confirmPosSale: mocks.send,
  getSaleConfirmation: mocks.send,
}));

function response(): SessionResponse {
  return {
    csrf_token: "test-only-memory-token",
    session: {
      id: "session",
      audience: "POS",
      status: "ACTIVE",
      created_at: "2026-10-18T00:00:00Z",
      last_activity_at: "2026-10-18T00:00:00Z",
      idle_expires_at: "2026-10-18T00:30:00Z",
      absolute_expires_at: "2026-10-18T12:00:00Z",
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
      default_surface: "POS",
      allowed_surfaces: ["POS"],
      authorization_surface: "POS",
      authorization_version: "v1",
      is_superadministrator: false,
      effective_grants: [],
      password_reset_required: false,
    },
  };
}
const context = {
  userId: "actor",
  branchId: "branch",
  workstationId: "station",
  workstationCode: "POS-01",
  cashSessionId: "cash",
};
const cases = [
  {
    name: "cash",
    begin: () =>
      cashIntentions.begin(
        { ...context, commandCode: "open", cashSessionId: null },
        { workstation_code: "POS-01", opening_amount: "0" },
        null,
      ),
    read: () => cashIntentions.read("station"),
    hasBody: cashIntentions.hasBody,
  },
  {
    name: "orders",
    begin: () =>
      orderIntentions.begin(
        { ...context, commandCode: "mark-ready", orderId: "order" },
        { workstation_code: "POS-01", cash_session_id: "cash" },
        null,
      ),
    read: () => orderIntentions.read("station"),
    hasBody: orderIntentions.hasBody,
  },
  {
    name: "returns",
    begin: () =>
      returnIntentions.begin(
        { ...context, originalSaleId: "sale" },
        {
          workstation_code: "POS-01",
          cash_session_id: "cash",
          original_sale_id: "sale",
          reason_code: "OTHER",
          refund_method_code: "CASH",
          high_risk_acknowledged: false,
          lines: [
            {
              original_sale_line_id: "line",
              returned_quantity: "1",
              allocations: [
                {
                  exact_product_id: "product",
                  quantity: "1",
                  disposition_code: "QUARANTINE",
                  restock_safe_acknowledged: false,
                },
              ],
            },
          ],
        },
        null,
      ),
    read: () => returnIntentions.read("station"),
    hasBody: returnIntentions.hasBody,
  },
  {
    name: "sales",
    begin: () =>
      beginSaleConfirmation(
        context,
        {
          cash_session_id: "cash",
          workstation_code: "POS-01",
          lines: [{ capture_mode: "CLASS_CAPTURE", product_class_id: "class", quantity: "1" }],
          payments: [{ payment_method_code: "CASH", tendered_amount: "3" }],
        },
        null,
      ),
    read: () => readSaleIntention("station"),
    hasBody: hasSaleIntentionBody,
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
it("does not send a sale when the session locks while its digest is pending", async () => {
  let release!: () => void;
  const paused = new Promise<void>((resolve) => {
    release = resolve;
  });
  const digest = vi.fn(async (algorithm: string, input: ArrayBuffer) => {
    await paused;
    return webcrypto.subtle.digest(algorithm, input);
  });
  vi.stubGlobal("crypto", {
    getRandomValues: webcrypto.getRandomValues.bind(webcrypto),
    subtle: { digest },
  });
  const result = cases[3]!.begin();
  const rejected = expect(result).rejects.toThrow("sesión cambió");
  await vi.waitFor(() => expect(digest).toHaveBeenCalledTimes(1));
  auth.getState().markLocked();
  release();
  await rejected;
  expect(mocks.send).not.toHaveBeenCalled();
  expect(readSaleIntention("station")).toBeNull();
});
