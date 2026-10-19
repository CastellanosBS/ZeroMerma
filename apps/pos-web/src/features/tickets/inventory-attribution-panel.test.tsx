// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import type { components } from "@zeromerma/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { attributionIntentions } from "./attribution-command-intent";
import { InventoryAttributionPanel } from "./inventory-attribution-panel";
const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  auth: {
    user: {
      id: "actor",
      effective_grants: [{ capability: "pos.operate", scope_type: "GLOBAL", branch_ids: [] }],
    },
  },
}));
vi.mock("../../lib/http", () => ({ requestJson: mocks.request }));
vi.mock("../auth/auth-store", () => ({
  usePosAuthStore: Object.assign(
    (selector: (state: typeof mocks.auth) => unknown) => selector(mocks.auth),
    { subscribe: () => () => {} },
  ),
}));
vi.mock("./queries", () => ({
  useTicketsBootstrapQuery: () => ({
    data: { branch: { id: "branch" }, workstation: { id: "station", code: "POS-01" } },
  }),
}));
vi.mock("../cash-session-open/queries", () => ({
  useCurrentCashSessionQuery: () => ({ data: { id: "cash", status: "OPEN" } }),
}));
(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;
type Ticket = Pick<components["schemas"]["TicketDetailResponse"], "id" | "branch" | "lines">;
const ticket: Ticket = {
  id: "sale",
  branch: {
    id: "branch",
    code: "MAIN",
    name: "Main",
    timezone: "America/Hermosillo",
    is_active: true,
  },
  lines: [
    {
      id: "line",
      sequence: 1,
      name: "Pan dulce",
      quantity: "3.000",
      unit_price: "10.00",
      line_total_amount: "30.00",
      capture_mode: "CLASS_CAPTURE",
      remaining_attribution_quantity: "2.000",
      physical_attributions: [],
      attribution_options: [
        {
          product_id: "product",
          product_code: "BREAD",
          product_name: "Bread",
          lot_id: "lot",
          lot_code: "LOT-1",
          expires_at: "2026-10-20T00:00:00Z",
          available_quantity: "1.000",
          is_inventory_tracked: true,
          lot_tracking_enabled: true,
        },
      ],
    },
  ],
};
let host: HTMLDivElement;
let root: Root;
let queries: QueryClient;
beforeEach(() => {
  localStorage.clear();
  attributionIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  mocks.request
    .mockReset()
    .mockResolvedValue({ sale_id: "sale", operation_id: "operation", lines: [] });
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  queries = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  act(() =>
    root.render(
      <QueryClientProvider client={queries}>
        <InventoryAttributionPanel ticket={ticket} />
      </QueryClientProvider>,
    ),
  );
});
afterEach(() => {
  act(() => root.unmount());
  queries.clear();
  host.remove();
  vi.unstubAllGlobals();
});
function change(selector: string, value: string) {
  const input = host.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!;
  act(() => {
    Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value")!.set!.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}
async function submit() {
  act(() => host.querySelector<HTMLButtonElement>("button")!.click());
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 20));
  });
}
it("shows the unresolved quantity and records only the selected partial physical leg", async () => {
  expect(host.textContent).toContain("Pendiente de atribuir: 2.000");
  expect(host.textContent).toContain("lote LOT-1");
  change("select", "product:lot");
  change("input", "0.4");
  await submit();
  expect(mocks.request).toHaveBeenCalledWith(
    expect.objectContaining({
      method: "POST",
      path: "/v1/sales/sale/attribute-inventory",
      body: {
        workstation_code: "POS-01",
        cash_session_id: "cash",
        lines: [{ sale_line_id: "line", product_id: "product", lot_id: "lot", quantity: "0.4" }],
      },
    }),
  );
  expect(mocks.request).toHaveBeenCalledTimes(1);
});
it("requires an exact product and lot and rejects quantities above current capacity", async () => {
  change("input", "0.4");
  await submit();
  expect(mocks.request).not.toHaveBeenCalled();
  change("select", "product:lot");
  change("input", "1.5");
  await submit();
  expect(host.textContent).toContain("supera la existencia disponible");
  expect(mocks.request).not.toHaveBeenCalled();
  change("input", "3");
  await submit();
  expect(host.textContent).toContain("dentro del pendiente");
  expect(mocks.request).not.toHaveBeenCalled();
});
