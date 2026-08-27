// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  PosBootstrapResponse,
  PosCatalogClassView,
  SaleDetailView,
} from "../../lib/api-contracts";
import { usePosAuthStore } from "../auth/auth-store";
import { CLASS_CAPTURE_MODE } from "./model";
import { PosCheckoutPanel } from "./pos-checkout-panel";
import { usePosTerminalStore } from "./store";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const confirmPosSaleMock = vi.fn();
const getTicketDetailMock = vi.fn();
const showSuccessMock = vi.fn();
const showWarningMock = vi.fn();
const writeTicketToPrintWindowMock = vi.fn();

vi.mock("./pos-terminal-api", () => ({
  confirmPosSale: (...args: unknown[]) => confirmPosSaleMock(...args),
}));

vi.mock("../tickets/tickets-api", () => ({
  getTicketDetail: (...args: unknown[]) => getTicketDetailMock(...args),
}));

vi.mock("../tickets/print", () => ({
  writeTicketToPrintWindow: (...args: unknown[]) => writeTicketToPrintWindowMock(...args),
}));

vi.mock("../status-messages/store", () => ({
  useStatusMessageStore: (
    selector: (state: {
      showSuccess: typeof showSuccessMock;
      showWarning: typeof showWarningMock;
    }) => unknown,
  ) =>
    selector({
      showSuccess: showSuccessMock,
      showWarning: showWarningMock,
    }),
}));

function renderUi(element: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  const container = document.createElement("div");
  document.body.appendChild(container);

  const root = createRoot(container);
  act(() => {
    root.render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
  });

  return {
    container,
    unmount: () => {
      act(() => {
        root.unmount();
      });
      queryClient.clear();
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

const bolilloClass: PosCatalogClassView = {
  capture_mode_default: CLASS_CAPTURE_MODE,
  class_capture_unit_price: "3.00",
  code: "BOLILLO",
  currency_code: "MXN",
  display_order: 10,
  id: "class-bolillo",
  name: "Bolillo",
  product_count: 0,
  quick_name: "Bolillo",
};

const bootstrap = {
  workstation: {
    code: "POS-01",
  },
} as PosBootstrapResponse;

function createSaleDetail(overrides?: Partial<SaleDetailView>): SaleDetailView {
  return {
    payments: [{ payment_method_code: "CASH" }],
    change_amount: "0.00",
    id: "sale-1",
    total_amount: "3.00",
    ...overrides,
  } as SaleDetailView;
}

function createTicketDetail() {
  return {
    branch: { timezone: "America/Hermosillo" },
    can_reprint: true,
    cash_session_id: "cash-session-1",
    change_amount: "0.00",
    confirmed_at: "2026-04-22T10:00:00Z",
    currency_code: "MXN",
    folio: "TCK-SALE",
    id: "sale-1",
    item_count: 1,
    lines: [],
    operator: { full_name: "Main Branch Cashier" },
    paid_amount: "3.00",
    payments: [],
    status: "CONFIRMED",
    subtotal_amount: "3.00",
    total_amount: "3.00",
    total_quantity: "1.000",
    workstation: { code: "POS-01", name: "Front Register 01" },
  } as const;
}

function seedTicket() {
  const store = usePosTerminalStore.getState();
  store.selectClass(bolilloClass);
  store.setQuantityText("1");
  store.addPendingLine();
}

let mountedRoots: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
  localStorage.clear();
  confirmPosSaleMock.mockReset();
  getTicketDetailMock.mockReset();
  showSuccessMock.mockReset();
  showWarningMock.mockReset();
  writeTicketToPrintWindowMock.mockReset();
  vi.restoreAllMocks();
  act(() => {
    usePosAuthStore.getState().clearSession();
    usePosTerminalStore.getState().reset();
  });
});

describe("PosCheckoutPanel", () => {
  it("keeps Recibe enabled and lets the cashier confirm without clicking Cobrar first", async () => {
    act(() => {
      usePosAuthStore.getState().setAccessToken("token");
      seedTicket();
    });

    const view = renderUi(<PosCheckoutPanel bootstrap={bootstrap} />);
    mountedRoots.push(view.unmount);

    const input = view.container.querySelector(
      'input[aria-label="Dinero recibido"]',
    ) as HTMLInputElement;
    expect(input).toBeDefined();

    act(() => {
      input.focus();
    });

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    expect(document.activeElement).toBe(input);

    setInputValue(input, "3.00");
    dispatchKey(input, "Enter");

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    expect(view.container.textContent).toContain("Ticket");
    const cobrarButton = Array.from(view.container.querySelectorAll("button")).find(
      (button) => button.textContent?.trim() === "Cobrar",
    ) as HTMLButtonElement;
    expect(document.activeElement).toBe(cobrarButton);
  });

  it("focuses Recibe after explicit payment entry", async () => {
    act(() => {
      usePosAuthStore.getState().setAccessToken("token");
      seedTicket();
    });

    const view = renderUi(<PosCheckoutPanel bootstrap={bootstrap} />);
    mountedRoots.push(view.unmount);

    const paymentButton = Array.from(view.container.querySelectorAll("button")).find(
      (button) => button.textContent?.trim() === "Cobrar",
    ) as HTMLButtonElement;

    act(() => {
      paymentButton.click();
    });

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    const input = view.container.querySelector(
      'input[aria-label="Dinero recibido"]',
    ) as HTMLInputElement;
    expect(document.activeElement).toBe(input);
  });

  it("switches payment method with keyboard shortcuts inside payment capture", async () => {
    act(() => {
      usePosAuthStore.getState().setAccessToken("token");
      seedTicket();
    });

    const view = renderUi(<PosCheckoutPanel bootstrap={bootstrap} />);
    mountedRoots.push(view.unmount);

    act(() => {
      Array.from(view.container.querySelectorAll("button"))
        .find((button) => button.textContent?.trim() === "Cobrar")
        ?.click();
    });

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    expect(view.container.textContent).toContain("Tarjeta (registro)");
    expect(view.container.textContent).toContain("Mixto (registro)");

    dispatchKey(window, "*");
    expect(view.container.textContent).toContain("Registro de pago con tarjeta");
    expect(view.container.textContent).toContain("Solo registra el medio de pago");
    expect(view.container.textContent).toContain("no autoriza ni captura");
    expect(view.container.textContent).toContain("DEC-14");
    expect(view.container.textContent).not.toContain("Pago autorizado");
    expect(view.container.querySelector('input[aria-label="Dinero recibido"]')).toBeNull();

    dispatchKey(window, "/");
    expect(view.container.textContent).toContain("Cobro en efectivo");
    expect(view.container.textContent).not.toContain("integracion externa pendiente");
    expect(view.container.querySelector('input[aria-label="Dinero recibido"]')).not.toBeNull();
  });

  it("allows editing and deleting the selected ticket line from the keyboard", async () => {
    act(() => {
      usePosAuthStore.getState().setAccessToken("token");
      seedTicket();
    });

    const view = renderUi(<PosCheckoutPanel bootstrap={bootstrap} />);
    mountedRoots.push(view.unmount);

    const row = view.container.querySelector('[role="row"]') as HTMLDivElement;
    expect(row).toBeDefined();

    act(() => {
      row.focus();
    });
    dispatchKey(window, "=");
    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    const quantityInput = view.container.querySelector(
      'input[aria-label="Cantidad de Bolillo"]',
    ) as HTMLInputElement;
    expect(quantityInput).toBeDefined();

    setInputValue(quantityInput, "2");
    dispatchKey(quantityInput, "Enter");
    expect(usePosTerminalStore.getState().cartLines[0]?.quantityText).toBe("2");

    const refreshedRow = view.container.querySelector('[role="row"]') as HTMLDivElement;
    act(() => {
      refreshedRow.focus();
    });
    dispatchKey(window, "Delete");
    expect(usePosTerminalStore.getState().cartLines).toHaveLength(0);
  });

  it("keeps the sale in amount capture when the amount is insufficient", async () => {
    act(() => {
      usePosAuthStore.getState().setAccessToken("token");
      seedTicket();
    });

    const view = renderUi(<PosCheckoutPanel bootstrap={bootstrap} />);
    mountedRoots.push(view.unmount);

    act(() => {
      Array.from(view.container.querySelectorAll("button"))
        .find((button) => button.textContent?.trim() === "Cobrar")
        ?.click();
    });

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    const input = view.container.querySelector(
      'input[aria-label="Dinero recibido"]',
    ) as HTMLInputElement;
    setInputValue(input, "1.00");
    dispatchKey(input, "Enter");

    expect(confirmPosSaleMock).not.toHaveBeenCalled();
    expect(view.container.textContent).toContain("Faltan $2.00. Captura un monto suficiente.");
    expect(document.activeElement).toBe(input);
    const ticketToggle = view.container.querySelector(
      'button[aria-label="Solicitar ticket"]',
    ) as HTMLButtonElement;
    expect(ticketToggle).not.toBeNull();
    expect(ticketToggle.disabled).toBe(true);
    expect(ticketToggle.getAttribute("role")).toBe("switch");
    expect(ticketToggle.getAttribute("aria-checked")).toBe("false");

    act(() => {
      ticketToggle.click();
    });
    expect(ticketToggle.getAttribute("aria-checked")).toBe("false");
  });

  it("uses the ticket toggle before Cobrar and resets the panel after a successful sale", async () => {
    vi.spyOn(window, "open").mockReturnValue({
      close: vi.fn(),
    } as unknown as Window);
    confirmPosSaleMock.mockResolvedValue(createSaleDetail());
    getTicketDetailMock.mockResolvedValue(createTicketDetail());

    act(() => {
      usePosAuthStore.getState().setAccessToken("token");
      seedTicket();
    });

    const view = renderUi(<PosCheckoutPanel bootstrap={bootstrap} />);
    mountedRoots.push(view.unmount);

    act(() => {
      Array.from(view.container.querySelectorAll("button"))
        .find((button) => button.textContent?.trim() === "Cobrar")
        ?.click();
    });

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    const input = view.container.querySelector(
      'input[aria-label="Dinero recibido"]',
    ) as HTMLInputElement;
    setInputValue(input, "3.00");
    dispatchKey(input, "Enter");

    expect(confirmPosSaleMock).not.toHaveBeenCalled();
    expect(view.container.textContent).toContain("Cobrar");
    const ticketToggle = view.container.querySelector(
      'button[aria-label="Solicitar ticket"]',
    ) as HTMLButtonElement;
    expect(ticketToggle.disabled).toBe(false);
    expect(ticketToggle.getAttribute("role")).toBe("switch");
    expect(ticketToggle.getAttribute("aria-checked")).toBe("false");

    act(() => {
      ticketToggle.focus();
    });
    dispatchKey(ticketToggle, " ");
    expect(ticketToggle.getAttribute("aria-checked")).toBe("true");

    dispatchKey(ticketToggle, "Enter");
    expect(ticketToggle.getAttribute("aria-checked")).toBe("false");

    dispatchKey(window, ".");
    expect(ticketToggle.getAttribute("aria-checked")).toBe("true");

    act(() => {
      ticketToggle.click();
    });
    expect(ticketToggle.getAttribute("aria-checked")).toBe("false");

    act(() => {
      ticketToggle.click();
    });
    expect(ticketToggle.getAttribute("aria-checked")).toBe("true");

    dispatchKey(window, "Enter");

    await act(async () => { await Promise.resolve(); await new Promise((resolve) => window.setTimeout(resolve, 0)); });

    expect(confirmPosSaleMock).toHaveBeenCalledTimes(1);
    expect(getTicketDetailMock).toHaveBeenCalledTimes(1);
    expect(writeTicketToPrintWindowMock).toHaveBeenCalledTimes(1);
    expect(showSuccessMock).toHaveBeenCalledWith("Venta registrada.");
    expect(usePosTerminalStore.getState().cartLines).toHaveLength(0);
    expect(view.container.textContent).toContain("El ticket esta vacio. Agrega productos desde el catalogo para empezar la venta.");
  });

  it("supports mixed payment legs until the remaining amount reaches zero", async () => {
    confirmPosSaleMock.mockResolvedValue(
      createSaleDetail({
        payments: [
          { payment_method_code: "CARD" },
          { payment_method_code: "CASH" },
        ] as unknown as SaleDetailView["payments"],
      }),
    );
    getTicketDetailMock.mockResolvedValue(createTicketDetail());

    act(() => {
      usePosAuthStore.getState().setAccessToken("token");
      seedTicket();
    });

    const view = renderUi(<PosCheckoutPanel bootstrap={bootstrap} />);
    mountedRoots.push(view.unmount);

    act(() => {
      Array.from(view.container.querySelectorAll("button"))
        .find((button) => button.textContent?.includes("Mixto (registro)"))
        ?.click();
    });

    expect(view.container.textContent).toContain("Registro de pago mixto");
    expect(view.container.textContent).toContain("Solo registra el medio de pago");

    const legInput = view.container.querySelector(
      'input[aria-label="Monto del tramo"]',
    ) as HTMLInputElement;
    expect(legInput).toBeDefined();

    setInputValue(legInput, "1.00");
    dispatchKey(legInput, "Enter");
    expect(view.container.textContent).toContain("Restante confirmado");
    expect(view.container.textContent).toContain("$2.00");

    act(() => {
      Array.from(view.container.querySelectorAll("button"))
        .find((button) => button.textContent?.includes("* Tarjeta"))
        ?.click();
    });
    setInputValue(legInput, "2.00");
    dispatchKey(legInput, "Enter");

    expect(view.container.textContent).toContain("Cobrar");
    dispatchKey(window, "Enter");

    await act(async () => {
      await Promise.resolve();
    });

    expect(confirmPosSaleMock).toHaveBeenCalledTimes(1);
    expect(confirmPosSaleMock.mock.calls[0]?.[1]).toMatchObject({
      payments: [
        { payment_method_code: "CASH", tendered_amount: "1" },
        { payment_method_code: "CARD", tendered_amount: "2" },
      ],
    });
  });

  it("blocks double submit while the sale is processing", async () => {
    let resolveSale: ((value: SaleDetailView) => void) | null = null;
    confirmPosSaleMock.mockImplementation(
      () =>
        new Promise<SaleDetailView>((resolve) => {
          resolveSale = resolve;
        }),
    );
    getTicketDetailMock.mockResolvedValue(createTicketDetail());

    act(() => {
      usePosAuthStore.getState().setAccessToken("token");
      seedTicket();
    });

    const view = renderUi(<PosCheckoutPanel bootstrap={bootstrap} />);
    mountedRoots.push(view.unmount);

    act(() => {
      Array.from(view.container.querySelectorAll("button"))
        .find((button) => button.textContent?.trim() === "Cobrar")
        ?.click();
    });

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    const input = view.container.querySelector(
      'input[aria-label="Dinero recibido"]',
    ) as HTMLInputElement;
    setInputValue(input, "3.00");
    dispatchKey(input, "Enter");
    dispatchKey(window, "Enter");
    dispatchKey(window, "Enter");

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    expect(confirmPosSaleMock).toHaveBeenCalledTimes(1);
    expect(view.container.textContent).toContain("Procesando...");

    await act(async () => {
      resolveSale?.(createSaleDetail());
      await Promise.resolve();
    });
  });

  it("keeps the ticket alive on recoverable backend errors", async () => {
    confirmPosSaleMock.mockRejectedValue(new Error("network down"));

    act(() => {
      usePosAuthStore.getState().setAccessToken("token");
      seedTicket();
    });

    const view = renderUi(<PosCheckoutPanel bootstrap={bootstrap} />);
    mountedRoots.push(view.unmount);

    act(() => {
      Array.from(view.container.querySelectorAll("button"))
        .find((button) => button.textContent?.trim() === "Cobrar")
        ?.click();
    });

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    const input = view.container.querySelector(
      'input[aria-label="Dinero recibido"]',
    ) as HTMLInputElement;
    setInputValue(input, "3.00");
    dispatchKey(input, "Enter");
    dispatchKey(window, "Enter");

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(view.container.textContent).toContain("No se pudo registrar la venta.");
    expect(usePosTerminalStore.getState().cartLines).toHaveLength(1);
    expect(view.container.textContent).toContain("Reintentar");
  });

  it("shows print failure as a toast after a successful sale", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    confirmPosSaleMock.mockResolvedValue(createSaleDetail());
    getTicketDetailMock.mockResolvedValue(createTicketDetail());

    act(() => {
      usePosAuthStore.getState().setAccessToken("token");
      seedTicket();
    });

    const view = renderUi(<PosCheckoutPanel bootstrap={bootstrap} />);
    mountedRoots.push(view.unmount);

    act(() => {
      Array.from(view.container.querySelectorAll("button"))
        .find((button) => button.textContent?.trim() === "Cobrar")
        ?.click();
    });

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });

    const input = view.container.querySelector(
      'input[aria-label="Dinero recibido"]',
    ) as HTMLInputElement;
    setInputValue(input, "3.00");
    dispatchKey(input, "Enter");
    dispatchKey(window, ".");
    dispatchKey(window, "Enter");

    await act(async () => {
      await Promise.resolve();
    });

    expect(showWarningMock).toHaveBeenCalledWith("Venta registrada, pero no se pudo imprimir.");
    expect(showSuccessMock).not.toHaveBeenCalled();
    expect(usePosTerminalStore.getState().cartLines).toHaveLength(0);
  });
});
