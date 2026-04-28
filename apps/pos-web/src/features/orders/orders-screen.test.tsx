// @vitest-environment jsdom

import { act, type ReactElement, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PosFilterBar, PosRecordList } from "../../components/pos-records";
import { KeyboardShortcutRegistry } from "../pos-shell/keyboard";
import {
  OrderActionConfirmDialog,
  OrderRecordCard,
} from "./orders-screen";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const orders = [
  {
    advance_amount: "20.00",
    created_at_utc: "2026-04-22T18:00:00Z",
    currency_code: "MXN",
    customer_name: "Ana Pan",
    customer_phone: "6621001000",
    folio: "PED-AAA001",
    id: "order-1",
    line_count: 2,
    remaining_balance_amount: "14.00",
    requested_for_at: "2026-04-23T17:30:00Z",
    status: "PENDING",
    total_amount: "34.00",
    total_units: "5.000",
  },
  {
    advance_amount: "10.00",
    created_at_utc: "2026-04-22T19:00:00Z",
    currency_code: "MXN",
    customer_name: "Bruno Cafe",
    customer_phone: "6622002000",
    folio: "PED-BBB002",
    id: "order-2",
    line_count: 1,
    remaining_balance_amount: "0.00",
    requested_for_at: "2026-04-24T18:00:00Z",
    status: "READY",
    total_amount: "24.00",
    total_units: "2.000",
  },
  {
    advance_amount: "0.00",
    created_at_utc: "2026-04-22T20:00:00Z",
    currency_code: "MXN",
    customer_name: "Carla Lista",
    customer_phone: "6623003000",
    folio: "PED-CCC003",
    id: "order-3",
    line_count: 3,
    remaining_balance_amount: "18.00",
    requested_for_at: "2026-04-24T19:30:00Z",
    status: "READY",
    total_amount: "18.00",
    total_units: "3.000",
  },
] as const;

function renderUi(element: ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);

  const root = createRoot(container);
  act(() => {
    root.render(element);
  });

  return {
    container,
    unmount: () => {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

function dispatchKey(target: EventTarget, key: string, options?: KeyboardEventInit) {
  act(() => {
    target.dispatchEvent(
      new KeyboardEvent("keydown", {
        bubbles: true,
        cancelable: true,
        key,
        ...options,
      }),
    );
  });
}

function setInputValue(
  input: HTMLInputElement | HTMLTextAreaElement,
  value: string,
) {
  const prototype =
    input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const valueSetter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;

  act(() => {
    valueSetter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function OrdersListHarness() {
  const [selectedStatus, setSelectedStatus] = useState("PENDING");
  const [searchText, setSearchText] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(orders[0]!.id);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  const visibleOrders = useMemo(() => {
    const normalizedQuery = searchText.trim().toLowerCase();

    return orders.filter((order) => {
      if (order.status !== selectedStatus) {
        return false;
      }

      const orderDate = order.requested_for_at.slice(0, 10);
      if (dateFrom && orderDate < dateFrom) {
        return false;
      }
      if (dateTo && orderDate > dateTo) {
        return false;
      }
      if (normalizedQuery.length === 0) {
        return true;
      }

      return (
        order.folio.toLowerCase().includes(normalizedQuery) ||
        order.customer_name.toLowerCase().includes(normalizedQuery) ||
        (order.customer_phone ?? "").includes(normalizedQuery)
      );
    });
  }, [dateFrom, dateTo, searchText, selectedStatus]);

  return (
    <KeyboardShortcutRegistry>
      <PosFilterBar
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <input
              aria-label="Fecha inicial de entrega"
              onChange={(event) => setDateFrom(event.target.value)}
              type="date"
              value={dateFrom}
            />
            <input
              aria-label="Fecha final de entrega"
              onChange={(event) => setDateTo(event.target.value)}
              type="date"
              value={dateTo}
            />
          </div>
        }
        chipFilters={[
          {
            isActive: selectedStatus === "PENDING",
            key: "pending",
            label: "Pendientes",
            onSelect: () => {
              setSelectedStatus("PENDING");
              setSelectedOrderId(null);
            },
          },
          {
            isActive: selectedStatus === "READY",
            key: "ready",
            label: "Listos para entrega",
            onSelect: () => {
              setSelectedStatus("READY");
              setSelectedOrderId(null);
            },
          },
        ]}
        countLabel={<span>{visibleOrders.length} pedidos</span>}
        searchInput={{
          ariaLabel: "Buscar pedido por folio, cliente o telefono",
          inputRef: searchInputRef,
          onChange: setSearchText,
          placeholder: "Buscar por folio, cliente o telefono",
          value: searchText,
        }}
        title="Pedidos registrados"
      />
      <PosRecordList
        emptyAction={<button type="button">Nuevo pedido</button>}
        emptyDescription="No hay pedidos que coincidan con ese folio, cliente o telefono dentro del filtro actual."
        emptyTitle="Sin pedidos para esta vista"
        getKey={(order) => order.id}
        onSelect={(order) => setSelectedOrderId(order.id)}
        records={visibleOrders}
        renderContent={(order, state) => (
          <OrderRecordCard
            isSelected={state.isSelected}
            order={order}
            timezone="America/Hermosillo"
          />
        )}
        selectedKey={selectedOrderId}
      />
      <output data-testid="selected-order">{selectedOrderId ?? ""}</output>
    </KeyboardShortcutRegistry>
  );
}

let mountedRoots: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

describe("Orders shared operational surfaces", () => {
  it("shows an empty state with CTA when no orders match the current query", () => {
    const view = renderUi(<OrdersListHarness />);
    mountedRoots.push(view.unmount);

    const searchInput = view.container.querySelector(
      'input[aria-label="Buscar pedido por folio, cliente o telefono"]',
    ) as HTMLInputElement;
    setInputValue(searchInput, "ZZZ");

    expect(view.container.textContent).toContain("Sin pedidos para esta vista");
    expect(view.container.textContent).toContain("Nuevo pedido");
  });

  it("supports keyboard navigation through the operational order list", () => {
    const view = renderUi(<OrdersListHarness />);
    mountedRoots.push(view.unmount);

    const pendingFilter = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Pendientes"),
    ) as HTMLButtonElement;
    act(() => pendingFilter.click());

    const readyFilter = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Listos para entrega"),
    ) as HTMLButtonElement;
    act(() => readyFilter.click());

    const firstCard = view.container.querySelector(
      ".pos-record-card__button",
    ) as HTMLButtonElement;
    firstCard.focus();

    dispatchKey(firstCard, "ArrowDown");
    dispatchKey(document.activeElement as EventTarget, "Enter");
    const selectedOrderOutput = view.container.querySelector(
      '[data-testid="selected-order"]',
    ) as HTMLOutputElement;
    expect(selectedOrderOutput.textContent).toBe("order-3");
  });

  it("requires a cancellation reason before allowing confirmation", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const onChange = vi.fn();

    const view = renderUi(
      <OrderActionConfirmDialog
        cancelReason=""
        cancelReasonError="Captura un motivo claro antes de cancelar el pedido."
        isPending={false}
        onCancel={onCancel}
        onCancelReasonChange={onChange}
        onConfirm={onConfirm}
        state={{
          kind: "cancel",
          order: {
            advance_amount: "20.00",
            cancellation_refund_amount: "20.00",
            cancellation_refund_eligible: true,
            customer_name: "Ana Pan",
            folio: "PED-AAA001",
            id: "order-1",
            status: "PENDING",
          },
        }}
      />,
    );
    mountedRoots.push(view.unmount);

    const confirmButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Confirmar cancelacion"),
    ) as HTMLButtonElement;
    expect(confirmButton.disabled).toBe(true);
    expect(view.container.textContent).toContain(
      "Captura un motivo claro antes de cancelar el pedido.",
    );

    const reasonInput = view.container.querySelector("textarea") as HTMLTextAreaElement;
    setInputValue(reasonInput, "Cliente ya no puede recogerlo.");

    expect(onChange).toHaveBeenCalledWith("Cliente ya no puede recogerlo.");
  });
});
