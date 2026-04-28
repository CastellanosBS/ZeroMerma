// @vitest-environment jsdom

import { act, type ReactElement, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TicketDetailResponse, TicketListItemView } from "../../lib/api-contracts";
import { PosScannerInput } from "../../components/pos-scanner-input";
import { matchesScannerValue, normalizeScannerText, parseTicketScannerValue } from "../../lib/scanner";
import { KeyboardShortcutRegistry } from "../pos-shell/keyboard";
import { PosFilterBar, PosRecordList } from "../../components/pos-records";
import { TicketRecordCard, TicketSummaryPanel } from "./tickets-screen";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const tickets: TicketListItemView[] = [
  {
    change_amount: "0.00",
    confirmed_at: "2026-04-22T18:15:00Z",
    currency_code: "MXN",
    folio: "TCK-AAA001",
    has_returnable_quantity: true,
    id: "ticket-1",
    item_count: 2,
    operator_full_name: "Main Branch Cashier",
    payment_summary: [{ amount: "42.00", currency_code: "MXN", payment_method_code: "CASH" }],
    return_count: 0,
    return_status: "NOT_RETURNED",
    returned_amount: "0.00",
    total_amount: "42.00",
    total_quantity: "2.000",
  },
  {
    change_amount: "5.00",
    confirmed_at: "2026-04-22T19:00:00Z",
    currency_code: "MXN",
    folio: "TCK-BBB002",
    has_returnable_quantity: true,
    id: "ticket-2",
    item_count: 1,
    operator_full_name: "Main Branch Cashier",
    payment_summary: [{ amount: "120.00", currency_code: "MXN", payment_method_code: "CARD" }],
    return_count: 1,
    return_status: "PARTIALLY_RETURNED",
    returned_amount: "40.00",
    total_amount: "120.00",
    total_quantity: "3.000",
  },
];

const ticketDetail: TicketDetailResponse = {
  branch: {
    code: "MAIN",
    id: "branch-1",
    is_active: true,
    name: "Main Branch",
    timezone: "America/Hermosillo",
  },
  can_reprint: true,
  cash_session_id: "cash-session-1",
  change_amount: "5.00",
  confirmed_at: "2026-04-22T19:00:00Z",
  currency_code: "MXN",
  folio: "TCK-BBB002",
  id: "ticket-2",
  item_count: 1,
  lines: [
    {
      id: "line-1",
      line_total_amount: "120.00",
      name: "Caja de bolillo",
      quantity: "3.000",
      sequence: 1,
      unit_price: "40.00",
    },
  ],
  operator: {
    email: "cashier@zeromerma.local",
    full_name: "Main Branch Cashier",
    id: "user-1",
  },
  paid_amount: "125.00",
  return_count: 1,
  returned_amount: "40.00",
  return_status: "PARTIALLY_RETURNED",
  has_returnable_quantity: true,
  payments: [
    {
      applied_amount: "120.00",
      change_amount: "5.00",
      currency_code: "MXN",
      id: "payment-1",
      payment_method_code: "CARD",
      received_at: "2026-04-22T19:00:05Z",
      sequence: 1,
      tendered_amount: "125.00",
    },
  ],
  status: "CONFIRMED",
  subtotal_amount: "120.00",
  total_amount: "120.00",
  total_quantity: "3.000",
  workstation: {
    code: "POS-01",
    id: "workstation-1",
    is_active: true,
    name: "Front Register 01",
  },
};

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

function setInputValue(input: HTMLInputElement, value: string) {
  const valueSetter = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value",
  )?.set;

  act(() => {
    valueSetter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function TicketListHarness() {
  const [selectedScope, setSelectedScope] = useState("CURRENT_SHIFT");
  const [searchText, setSearchText] = useState("");
  const [scannerText, setScannerText] = useState("");
  const [pendingScannerFolio, setPendingScannerFolio] = useState<string | null>(null);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(tickets[0]!.id);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const scannerInputRef = useRef<HTMLInputElement | null>(null);

  const visibleTickets = useMemo(() => {
    const scopeTickets = selectedScope === "TODAY" ? tickets.slice(1) : tickets;
    const normalizedQuery = searchText.trim().toLowerCase();
    return scopeTickets.filter((ticket) => ticket.folio.toLowerCase().includes(normalizedQuery));
  }, [searchText, selectedScope]);

  useEffect(() => {
    if (pendingScannerFolio === null) {
      return;
    }

    const exactMatch = visibleTickets.find((ticket) =>
      matchesScannerValue(ticket.folio, pendingScannerFolio),
    );

    if (exactMatch) {
      setSelectedTicketId(exactMatch.id);
      setPendingScannerFolio(null);
      return;
    }

    if (visibleTickets.length === 1) {
      setSelectedTicketId(visibleTickets[0]!.id);
      setPendingScannerFolio(null);
    }
  }, [pendingScannerFolio, visibleTickets]);

  function handleScannerSubmit() {
    const scannedValue =
      parseTicketScannerValue(scannerText) ?? normalizeScannerText(scannerText);

    if (scannedValue.length === 0) {
      return;
    }

    setScannerText("");
    setPendingScannerFolio(scannedValue);
    setSearchText(scannedValue);
  }

  return (
    <KeyboardShortcutRegistry>
      <div className="grid gap-3">
        <PosScannerInput
          ariaLabel="Escanear folio de ticket"
          inputRef={scannerInputRef}
          modeLabel="Escaneo de ticket"
          onChange={setScannerText}
          onSubmit={handleScannerSubmit}
          placeholder="Escanear folio de ticket"
          submitLabel="Buscar folio"
          value={scannerText}
        />
        <PosFilterBar
          chipFilters={[
            {
              isActive: selectedScope === "CURRENT_SHIFT",
              key: "current-shift",
              label: "Turno actual",
              onSelect: () => setSelectedScope("CURRENT_SHIFT"),
            },
            {
              isActive: selectedScope === "TODAY",
              key: "today",
              label: "Hoy",
              onSelect: () => setSelectedScope("TODAY"),
            },
          ]}
          searchInput={{
            ariaLabel: "Buscar ticket por folio",
            inputRef: searchInputRef,
            onChange: (value) => {
              setPendingScannerFolio(null);
              setSearchText(value);
            },
            placeholder: "Buscar por folio",
            value: searchText,
          }}
          title="Tickets emitidos"
        />
      </div>
      <PosRecordList
        getKey={(ticket) => ticket.id}
        onSelect={(ticket) => setSelectedTicketId(ticket.id)}
        records={visibleTickets}
        renderContent={(ticket, state) => (
          <TicketRecordCard
            isSelected={state.isSelected}
            ticket={ticket}
            timeZone="America/Hermosillo"
          />
        )}
        selectedKey={selectedTicketId}
      />
      <output data-testid="selected-ticket">{selectedTicketId ?? ""}</output>
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

describe("Tickets shared hub pieces", () => {
  it("renders return status and returned amount in ticket cards", () => {
    const view = renderUi(
      <TicketRecordCard
        isSelected={false}
        ticket={tickets[1]!}
        timeZone="America/Hermosillo"
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("Devolucion parcial");
    expect(view.container.textContent).toContain("Devuelto $40.00");
  });

  it("filters tickets by scope and folio", () => {
    const view = renderUi(<TicketListHarness />);
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("TCK-AAA001");
    expect(view.container.textContent).toContain("TCK-BBB002");

    const todayFilter = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Hoy"),
    ) as HTMLButtonElement | undefined;
    expect(todayFilter).toBeDefined();

    act(() => {
      todayFilter?.click();
    });

    expect(view.container.textContent).not.toContain("TCK-AAA001");
    expect(view.container.textContent).toContain("TCK-BBB002");

    const searchInput = view.container.querySelector(
      'input[aria-label="Buscar ticket por folio"]',
    ) as HTMLInputElement;
    setInputValue(searchInput, "AAA");

    expect(view.container.textContent).toContain("Sin resultados");
  });

  it("navigates the ticket list with arrows and Enter", () => {
    const view = renderUi(<TicketListHarness />);
    mountedRoots.push(view.unmount);

    const recordButtons = Array.from(
      view.container.querySelectorAll(".pos-record-card__button"),
    ) as HTMLButtonElement[];
    expect(recordButtons).toHaveLength(2);

    act(() => {
      recordButtons[0]?.focus();
    });

    dispatchKey(recordButtons[0]!, "ArrowDown");
    expect(document.activeElement).toBe(recordButtons[1]);

    dispatchKey(recordButtons[1]!, "Enter");
    expect(view.container.querySelector('[data-testid="selected-ticket"]')?.textContent).toBe(
      "ticket-2",
    );
  });

  it("selects an exact ticket from scanner input", () => {
    const view = renderUi(<TicketListHarness />);
    mountedRoots.push(view.unmount);

    const scannerInput = view.container.querySelector(
      'input[aria-label="Escanear folio de ticket"]',
    ) as HTMLInputElement;

    setInputValue(scannerInput, "tck-bbb002");
    dispatchKey(scannerInput, "Enter");

    expect(view.container.querySelector('[data-testid="selected-ticket"]')?.textContent).toBe(
      "ticket-2",
    );
  });

  it("exposes reprint and return actions in the summary panel", () => {
    const onReprint = vi.fn();
    const onStartReturn = vi.fn();
    const view = renderUi(
      <TicketSummaryPanel
        consoleState="TICKET_SELECTED"
        detailError={null}
        isDetailPending={false}
        isReprintPending={false}
        onReprint={onReprint}
        onStartReturn={onStartReturn}
        selectedTicket={ticketDetail}
      />,
    );
    mountedRoots.push(view.unmount);

    const copyButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Copiar folio"),
    ) as HTMLButtonElement | undefined;
    const startReturnButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Iniciar devolucion"),
    ) as HTMLButtonElement | undefined;
    const reprintButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Reimprimir"),
    ) as HTMLButtonElement | undefined;

    expect(copyButton).toBeDefined();
    expect(startReturnButton).toBeDefined();
    expect(reprintButton).toBeDefined();

    act(() => {
      startReturnButton?.click();
      reprintButton?.click();
    });

    expect(onStartReturn).toHaveBeenCalledWith("ticket-2");
    expect(onReprint).toHaveBeenCalledWith("ticket-2");
  });

  it("keeps customer delivery actions disabled while notification infrastructure is missing", () => {
    const view = renderUi(
      <TicketSummaryPanel
        consoleState="TICKET_SELECTED"
        detailError={null}
        isDetailPending={false}
        isReprintPending={false}
        onReprint={() => undefined}
        onStartReturn={() => undefined}
        selectedTicket={ticketDetail}
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain(
      "Envio de tickets pendiente: falta proveedor de entrega y el contrato no conserva contacto del cliente.",
    );

    const sendEmailButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Enviar ticket por correo"),
    ) as HTMLButtonElement | undefined;
    const sendSmsButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Enviar ticket por SMS"),
    ) as HTMLButtonElement | undefined;

    expect(sendEmailButton).toBeDefined();
    expect(sendSmsButton).toBeDefined();
    expect(sendEmailButton?.disabled).toBe(true);
    expect(sendSmsButton?.disabled).toBe(true);
  });
});
