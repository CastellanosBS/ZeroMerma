// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { webcrypto } from "node:crypto";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { RefundSettlementPanel } from "./refund-settlement-panel";
import { RefundRecoveryPanel } from "./refund-recovery-panel";
import type { FinancialRefund } from "./refund-command-intent";
import { buildReturnReceiptDocument } from "../returns/print";
import type { SaleReturnDetailResponse } from "../../lib/api-contracts";
import { usePosAuthStore } from "../auth/auth-store";
import { refundIntentions } from "./refund-command-intent";
const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  cash: null as { id: string; branch_id: string; workstation_id: string } | null,
}));
vi.mock("../../lib/http", () => ({
  requestJson: mocks.request,
  toOperationalErrorMessage: (error: Error) => error.message,
}));
vi.mock("../cash-session-open/queries", () => ({
  useCurrentCashSessionQuery: () => ({ data: mocks.cash }),
}));
const refund: FinancialRefund = {
  financial_operation_id: "refund",
  source_type: "SALE_RETURN",
  source_id: "return",
  amount_due: "100.00",
  amount_settled: "40.00",
  amount_pending: "60.00",
  cash_settled_amount: "40.00",
  card_settled_amount: "0.00",
  state: "PARTIALLY_SETTLED",
  original_collection_operation_ids: ["collection"],
  entries: [
    {
      id: "cash-leg",
      payment_method_code: "CASH",
      execution_mode: "LOCAL",
      state: "CONFIRMED",
      amount: "40.00",
      cash_session_id: "old-shift",
      occurred_at: "2026-10-19T18:00:00Z",
    },
  ],
};
beforeEach(() => {
  localStorage.clear();
  refundIntentions.forgetBodies();
  mocks.cash = null;
});
afterEach(() => vi.unstubAllGlobals());
it("shows actual delivered and outstanding amounts without inventing a card delivery", () => {
  const html = renderToString(
    <QueryClientProvider client={new QueryClient()}>
      <RefundSettlementPanel refund={refund} />
    </QueryClientProvider>,
  );
  expect(html).toContain("Entrega confirmada:");
  expect(html).toContain("$40.00");
  expect(html).toContain("Pendiente de entregar:");
  expect(html).toContain("$60.00");
  expect(html).toContain("old-shift");
  expect(html).not.toContain("Tarjeta");
  expect(html).toContain("disabled");
});
it("prints the obligation separately from money already delivered", () => {
  const detail = {
    folio: "DEV-1",
    lines: [],
    branch: { name: "Branch", timezone: "America/Hermosillo" },
    workstation: { name: "Caja" },
    created_by: { full_name: "Operator" },
    created_at_utc: "2026-10-19T18:00:00Z",
    original_sale_folio: "V-1",
    refund_method_code: "CASH",
    reason_name: "Requested",
    total_refund_amount: "100.00",
    financial_refund: refund,
    receipt: {
      source_kind: "RETURN", source_id: "return-1", folio: "DEV-1",
      occurred_at: "2026-10-19T18:00:00Z",
      context: { branch_name: "Branch", timezone: "America/Hermosillo", workstation_name: "Caja",
        actor_name: "Operator", cash_session_id: "shift-1" },
      seller: { configuration_status: "UNCONFIGURED" },
      subtotal_amount: "100.00", discount_amount: "0.00", total_amount: "100.00",
      change_amount: "0.00", settled_amount: "40.00", pending_amount: "60.00",
      lines: [], payments: [{ method: "CASH", execution_mode: "LOCAL", amount: "40.00",
        tendered_amount: "40.00", change_amount: "0.00" }],
    },
  } as unknown as SaleReturnDetailResponse;
  const html = buildReturnReceiptDocument(detail);
  expect(html).not.toContain("Total reembolsado");
  expect(html).toContain("Reembolsado:");
  expect(html).toContain("$40.00");
  expect(html).toContain("Pendiente:");
  expect(html).toContain("$60.00");
  expect(buildReturnReceiptDocument({ ...detail, financial_refund: null })).toBe(html);
  expect(() => buildReturnReceiptDocument({ ...detail, receipt: null })).toThrow("inmutable");
});

it("mounts recovery after a lost response and reload without issuing another POST", async () => {
  (
    globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
  ).IS_REACT_ACT_ENVIRONMENT = true;
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  mocks.cash = { id: "current-shift", branch_id: "branch", workstation_id: "station" };
  usePosAuthStore.setState({
    user: { id: "actor" } as NonNullable<ReturnType<typeof usePosAuthStore.getState>["user"]>,
  });
  mocks.request
    .mockReset()
    .mockRejectedValueOnce(new TypeError("Lost acknowledgement"))
    .mockResolvedValue(refund);
  const host = document.createElement("div");
  document.body.append(host);
  let root = createRoot(host);
  const mount = async () => {
    await act(async () =>
      root.render(
        <QueryClientProvider client={new QueryClient()}>
          <RefundSettlementPanel refund={refund} />
        </QueryClientProvider>,
      ),
    );
  };
  try {
    await mount();
    await act(async () => {
      (
        Array.from(host.querySelectorAll("button")).find(
          (button) => button.textContent === "Continuar reembolso en efectivo",
        ) as HTMLButtonElement
      ).click();
    });
    await act(async () => {
      await vi.waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(1));
    });
    expect(mocks.request.mock.calls[0]![0].body.cash_session_id).toBe("current-shift");
    const key = refundIntentions.read("station")!.key;
    await act(async () => root.unmount());
    refundIntentions.forgetBodies();
    root = createRoot(host);
    await mount();
    expect(host.textContent).toContain("Consultar entrega pendiente");
    expect(host.textContent).not.toContain("Reintentar la misma entrega");
    await act(async () => {
      (
        Array.from(host.querySelectorAll("button")).find(
          (button) => button.textContent === "Consultar entrega pendiente",
        ) as HTMLButtonElement
      ).click();
    });
    await act(async () => {
      await vi.waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2));
    });
    expect(mocks.request.mock.calls[1]![0].path).toContain(`/refund-settlements/${key}?`);
    expect(mocks.request.mock.calls[1]![0].method).toBeUndefined();
  } finally {
    await act(async () => root.unmount());
    host.remove();
  }
});

it("offers global GET recovery without requiring an open cash session", async () => {
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  usePosAuthStore.setState({
    user: { id: "actor" } as NonNullable<ReturnType<typeof usePosAuthStore.getState>["user"]>,
  });
  const context = {
    userId: "actor",
    branchId: "branch",
    workstationId: "station",
    workstationCode: "POS-01",
    cashSessionId: "closed-original-shift",
    sourceType: "SALE_RETURN",
    sourceId: "return",
  };
  mocks.request
    .mockReset()
    .mockRejectedValueOnce(new TypeError("Lost acknowledgement"))
    .mockResolvedValue(refund);
  await expect(
    refundIntentions.begin(
      context,
      { workstation_code: "POS-01", cash_session_id: "closed-original-shift" },
      null,
    ),
  ).rejects.toThrow();
  refundIntentions.forgetBodies();
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  try {
    await act(async () =>
      root.render(
        <QueryClientProvider client={new QueryClient()}>
          <RefundRecoveryPanel workstationId="station" />
        </QueryClientProvider>,
      ),
    );
    expect(host.textContent).toContain("Entrega de reembolso por verificar");
    await act(async () => {
      (host.querySelector("button") as HTMLButtonElement).click();
    });
    await act(async () => {
      await vi.waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2));
    });
    expect(mocks.request.mock.calls[1]![0].path).toContain("cash_session_id=closed-original-shift");
    expect(mocks.request.mock.calls[1]![0].method).toBeUndefined();
  } finally {
    await act(async () => root.unmount());
    host.remove();
  }
});
