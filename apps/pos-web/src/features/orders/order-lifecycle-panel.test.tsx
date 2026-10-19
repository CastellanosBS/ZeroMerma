// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { components } from "@zeromerma/api-client";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OrderLifecyclePanel } from "./order-lifecycle-panel";
import { quoteOrder } from "./orders-api";

vi.mock("./orders-api", () => ({
  getOrdersCatalog: vi.fn().mockResolvedValue({ classes: [] }),
  getOrdersClassProducts: vi.fn().mockResolvedValue({ products: [] }),
  quoteOrder: vi.fn(),
}));
(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

const order: components["schemas"]["CustomerOrderDetailResponse"] = {
  id: "order-1",
  folio: "PED-1",
  status: "PENDING",
  version: 1,
  branch: {
    id: "branch-1",
    code: "MAIN",
    name: "Main",
    timezone: "America/Hermosillo",
    is_active: true,
  },
  workstation_created: { id: "station-1", code: "POS-1", name: "Caja", is_active: true },
  created_by: {
    id: "actor-1",
    email: "actor@validation.invalid",
    full_name: "Actor",
    is_active: true,
    authorization_version: "1",
    default_surface: "POS",
    is_superadministrator: false,
    password_reset_required: false,
  },
  active_cash_session_id: "cash-1",
  customer_name: "Test client",
  currency_code: "MXN",
  subtotal_amount: "12.00",
  total_amount: "12.00",
  advance_amount: "6.00",
  remaining_balance_amount: "6.00",
  cancellation_refund_eligible: true,
  cancellation_refund_amount: "6.00",
  created_at_utc: "2026-10-19T12:00:00Z",
  updated_at_utc: "2026-10-19T12:00:00Z",
  requested_for_at: "2026-10-22T17:00:00Z",
  production_commit_at: "2026-10-21T17:00:00Z",
  items: [
    {
      id: "line-1",
      product_id: "product-1",
      product_code_snapshot: "BOL",
      product_name_snapshot: "Bolillo",
      product_class_id: "class-1",
      product_class_code_snapshot: "BREAD",
      product_class_name_snapshot: "Pan",
      line_number: 1,
      quantity: "4.000",
      unit_price: "3.00",
      line_total_amount: "12.00",
    },
  ],
  payments: [],
  can_amend: true,
  can_pay: true,
  can_cancel: true,
  can_deliver: false,
  can_mark_ready: false,
  requires_settlement_on_delivery: false,
  recognized_revenue_amount: "0.00",
  retained_amount: "0.00",
  unapplied_amount: "6.00",
};

const cleanup: Array<() => void> = [];
afterEach(() => {
  cleanup.splice(0).forEach((dispose) => dispose());
  vi.clearAllMocks();
});

function renderPanel(pending = false) {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onCommand = vi.fn().mockResolvedValue({ id: order.id });
  const onChanged = vi.fn();
  act(() =>
    root.render(
      <QueryClientProvider client={query}>
        <OrderLifecyclePanel
          order={order}
          workstationCode="POS-1"
          cashSessionId="cash-1"
          pending={pending}
          onCommand={onCommand}
          onChanged={onChanged}
        />
      </QueryClientProvider>,
    ),
  );
  cleanup.push(() => {
    act(() => root.unmount());
    query.clear();
    container.remove();
  });
  return { container, onCommand, onChanged };
}
function input(container: HTMLElement, label: string, value: string) {
  const field = container.querySelector<HTMLInputElement | HTMLTextAreaElement>(
    `[aria-label="${label}"]`,
  )!;
  const prototype =
    field instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;
  act(() => {
    Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(field, value);
    field.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function click(container: HTMLElement, label: string) {
  const button = [...container.querySelectorAll("button")].find(
    (item) => item.textContent?.trim() === label,
  )!;
  await act(async () => {
    button.click();
  });
}

describe("order lifecycle panel", () => {
  it("registers actual cash/card legs through the recoverable command coordinator", async () => {
    const { container, onCommand, onChanged } = renderPanel();
    input(container, "Abono en efectivo", "1.25");
    input(container, "Abono en tarjeta", "2.75");
    await click(container, "Confirmar abono");
    expect(onCommand).toHaveBeenCalledOnce();
    expect(onCommand).toHaveBeenCalledWith("pay", {
      workstation_code: "POS-1",
      cash_session_id: "cash-1",
      payments: [
        { payment_method_code: "CASH", amount: "1.25" },
        { payment_method_code: "CARD", amount: "2.75" },
      ],
    });
    expect(onChanged).toHaveBeenCalledOnce();
    expect(container.textContent).toContain("Abono confirmado.");
  });

  it("quotes exact products and branch-local delivery before confirming an optimistic version", async () => {
    const { container, onCommand } = renderPanel();
    vi.mocked(quoteOrder).mockResolvedValue({
      quote_fingerprint: "f".repeat(64),
      policy_id: "policy-1",
      policy_version: 1,
      lead_time_minutes: 1440,
      branch_id: "branch-1",
      branch_timezone: "America/Hermosillo",
      requested_for_at: "2026-10-23T17:00:00Z",
      production_commit_at: "2026-10-22T17:00:00Z",
      currency_code: "MXN",
      total_amount: "15.00",
      minimum_advance_amount: "7.50",
      items: [
        {
          product_id: "product-1",
          quantity: "5.000",
          unit_price: "3.00",
          line_total_amount: "15.00",
        },
      ],
    });
    await click(container, "Modificar pedido");
    input(container, "Cantidad de Bolillo", "5");
    input(container, "Nueva fecha de entrega", "2026-10-23T10:00");
    input(container, "Motivo de modificación", "Customer requested one more");
    input(container, "Abono en efectivo", "1.50");
    await click(container, "Cotizar modificación");
    expect(quoteOrder).toHaveBeenCalledWith({
      workstation_code: "POS-1",
      requested_for_at: "2026-10-23T17:00:00.000Z",
      items: [{ product_id: "product-1", quantity: "5" }],
    });
    expect(onCommand).not.toHaveBeenCalled();
    await click(container, "Confirmar nueva versión");
    expect(onCommand).toHaveBeenCalledWith(
      "amend",
      expect.objectContaining({
        expected_version: 1,
        quote_fingerprint: "f".repeat(64),
        reason: "Customer requested one more",
        additional_payments: [{ payment_method_code: "CASH", amount: "1.5" }],
      }),
    );
  });

  it("keeps captured amounts on uncertain outcomes and blocks while recovery is pending", async () => {
    const { container, onCommand, onChanged } = renderPanel();
    onCommand.mockRejectedValue(new Error("Resultado incierto"));
    input(container, "Abono en efectivo", "2.00");
    await click(container, "Confirmar abono");
    expect(
      container.querySelector<HTMLInputElement>('[aria-label="Abono en efectivo"]')!.value,
    ).toBe("2.00");
    expect(onChanged).not.toHaveBeenCalled();
    const blocked = renderPanel(true);
    await click(blocked.container, "Confirmar abono");
    expect(blocked.onCommand).not.toHaveBeenCalled();
  });
});
