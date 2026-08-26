// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";
import { act, type ReactElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CashCloseScreen } from "./cash-close-screen";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

const navigateMock = vi.fn();
const showErrorMock = vi.fn();
const showSuccessMock = vi.fn();
const resetPosTerminalMock = vi.fn();
const clearSessionMock = vi.fn();
const previewCashCloseMock = vi.fn();
const commitCashCloseMock = vi.fn();
let publishRightPanel: ((node: React.ReactNode) => void) | null = null;

const branch = {
  code: "MAIN",
  id: "branch-1",
  is_active: true,
  name: "Main Branch",
  timezone: "America/Hermosillo",
} as const;

const workstation = {
  code: "POS-01",
  id: "workstation-1",
  is_active: true,
  name: "Front Register 01",
} as const;

const user = {
  email: "cashier@zeromerma.local",
  full_name: "Main Branch Cashier",
  id: "user-1",
  is_active: true,
} as const;

const openCashSession = {
  branch_code: "MAIN",
  branch_id: "branch-1",
  branch_name: "Main Branch",
  id: "cash-session-1",
  opening_amount: "300.00",
  opened_at: "2026-04-22T18:00:00Z",
  status: "OPEN",
  user_email: user.email,
  user_full_name: user.full_name,
  user_id: user.id,
  workstation_code: "POS-01",
  workstation_id: "workstation-1",
  workstation_name: "Front Register 01",
} as const;

const baselineSnapshot = {
  captured_at_utc: "2026-04-22T17:50:00Z",
  is_available: true,
  is_first_controlled_close: false,
  latest_snapshot_id: "snapshot-1",
  snapshot_type: "COUNTER_BASELINE",
  source_cash_session_close_id: null,
} as const;

const pendingClassCapture = {
  has_pending_class_capture: true,
  pending_class_capture_classes_count: 1,
  pending_class_capture_total_quantity: "5.000",
} as const;

const relevantProduct = {
  counted_quantity: "5.000",
  discrepancy_quantity: "0.000",
  expected_quantity_before_deferred_attr: "5.000",
  final_expected_quantity: "5.000",
  notes: null,
  product_class_code: "PAN-DULCE",
  product_class_id: "class-1",
  product_class_name: "Pan dulce",
  product_code: "CONCHA-VAN",
  product_id: "product-1",
  product_name: "Concha vainilla",
} as const;

const paymentMethodCatalog = [
  {
    currency_code: "MXN",
    display_order: 10,
    is_active: true,
    is_expected_supported: true,
    payment_method_code: "CASH",
  },
  {
    currency_code: "MXN",
    display_order: 20,
    is_active: true,
    is_expected_supported: false,
    payment_method_code: "CARD",
  },
] as const;

const summaryResponse = {
  baseline_snapshot: baselineSnapshot,
  blockers: [],
  can_start_close: true,
  cash_session: openCashSession,
  currency_code: "MXN",
  expected_cash_amount: "180.00",
  movement_breakdown: [],
  opening_amount: "300.00",
  pending_class_capture: pendingClassCapture,
  reconciliation_status: "REVIEW_REQUIRED",
  total_cash_in: "205.00",
  total_cash_out: "10.00",
  warnings: [],
} as const;

const committedCloseDetail = {
  baseline_snapshot: baselineSnapshot,
  branch,
  branch_brand_key: "EL_MEJOR_PAN",
  cash_session: openCashSession,
  close_mode: "WITH_COUNT",
  counter_empty_confirmed: false,
  cash_variance_amount: "0.00",
  class_reconciliations: [],
  closed_at: "2026-04-22T20:10:00Z",
  closed_by: user,
  counted_cash_amount: "180.00",
  counted_product_lines: [relevantProduct],
  currency_code: "MXN",
  discrepancy_resolutions: [],
  expected_cash_amount: "180.00",
  generated_discrepancy_documents: [],
  id: "close-1",
  movement_breakdown: [],
  notes: "Caja sin centavos",
  opened_at: "2026-04-22T18:00:00Z",
  opened_by: user,
  opening_amount: "300.00",
  payment_method_rows: [
    {
      counted_amount: "180.00",
      currency_code: "MXN",
      display_order: 10,
      expected_amount: "180.00",
      is_expected_supported: true,
      payment_method_code: "CASH",
      variance_amount: "0.00",
    },
    {
      counted_amount: "0.00",
      currency_code: "MXN",
      display_order: 20,
      expected_amount: null,
      is_expected_supported: false,
      payment_method_code: "CARD",
      variance_amount: null,
    },
  ],
  pending_class_capture: pendingClassCapture,
  reconciliation_status: "READY",
  total_cash_in: "205.00",
  total_cash_out: "10.00",
  warnings: [],
  workstation,
} as const;

let mockBootstrapResponse = buildBootstrapResponse(true);

function buildBootstrapResponse(hasOpenSession: boolean) {
  return {
    baseline_snapshot: baselineSnapshot,
    blockers: hasOpenSession
      ? []
      : [
          {
            code: "NO_ACTIVE_OPEN_CASH_SESSION",
            message: "No hay una sesion abierta para cerrar.",
          },
        ],
    branch,
    branch_brand_key: "EL_MEJOR_PAN",
    can_start_close: hasOpenSession,
    current_open_cash_session: hasOpenSession ? openCashSession : null,
    local_timestamp: "2026-04-22T19:30:00Z",
    payment_method_catalog: paymentMethodCatalog,
    pending_class_capture: pendingClassCapture,
    user,
    warnings: [],
    workstation,
  } as const;
}

function buildPreviewResponse(payload: {
  close_mode?: string;
  counter_empty_confirmed?: boolean;
  counted_payment_methods?: Array<{ counted_amount: string; payment_method_code: string }>;
  counted_product_lines?: Array<{ counted_quantity: string; product_id: string }>;
  notes?: string | null;
  workstation_code: string;
}) {
  void payload.workstation_code;

  const counterEmptyConfirmed = payload.counter_empty_confirmed === true;
  const cashCount =
    payload.counted_payment_methods?.find((row) => row.payment_method_code === "CASH")
      ?.counted_amount ?? "0.00";
  const cardCount =
    payload.counted_payment_methods?.find((row) => row.payment_method_code === "CARD")
      ?.counted_amount ?? "0.00";
  const hasCash =
    Number(cashCount) >= 0 &&
    payload.counted_payment_methods?.some((row) => row.payment_method_code === "CASH");
  const hasPhysical =
    payload.counted_product_lines?.some((row) => Number(row.counted_quantity) > 0) ?? false;
  const isReady = Boolean(hasCash && (hasPhysical || counterEmptyConfirmed));

  return {
    baseline_snapshot: baselineSnapshot,
    blockers: [
      ...(hasCash
        ? []
        : [
            {
              code: "MISSING_COUNTED_PAYMENT_TOTALS",
              message: "Falta capturar el total contado de efectivo.",
            },
          ]),
      ...(counterEmptyConfirmed || hasPhysical
        ? []
        : [
            {
              code: "MISSING_COUNTED_CLOSING_STOCK",
              message: "Falta capturar el conteo final del mostrador.",
            },
          ]),
    ],
    can_start_close: true,
    cash_session: openCashSession,
    close_mode: payload.close_mode ?? "WITH_COUNT",
    counter_empty_confirmed: counterEmptyConfirmed,
    cash_variance_amount: hasCash ? (Number(cashCount) - 180).toFixed(2) : "0.00",
    class_reconciliations: [],
    counted_cash_amount: cashCount,
    counted_product_lines:
      hasPhysical || counterEmptyConfirmed
        ? [
            {
              ...relevantProduct,
              counted_quantity: counterEmptyConfirmed
                ? "0.000"
                : (payload.counted_product_lines?.[0]?.counted_quantity ?? "0.000"),
            },
          ]
        : [],
    currency_code: "MXN",
    discrepancy_resolutions: [],
    expected_cash_amount: "180.00",
    generated_discrepancy_documents: [],
    movement_breakdown: [],
    notes: payload.notes ?? null,
    opening_amount: "300.00",
    payment_method_rows: [
      {
        counted_amount: cashCount,
        currency_code: "MXN",
        display_order: 10,
        expected_amount: "180.00",
        is_expected_supported: true,
        payment_method_code: "CASH",
        variance_amount: hasCash ? (Number(cashCount) - 180).toFixed(2) : "0.00",
      },
      {
        counted_amount: cardCount,
        currency_code: "MXN",
        display_order: 20,
        expected_amount: null,
        is_expected_supported: false,
        payment_method_code: "CARD",
        variance_amount: null,
      },
    ],
    pending_class_capture: pendingClassCapture,
    reconciliation_status: isReady ? "READY" : "REVIEW_REQUIRED",
    total_cash_in: "205.00",
    total_cash_out: "10.00",
    warnings: [],
  };
}

vi.mock("@tanstack/react-router", () => ({
  Navigate: ({ to }: { to: string }) => <div data-testid="navigate">{to}</div>,
  useNavigate: () => navigateMock,
}));

vi.mock("../../components/app-shell-right-panel", () => ({
  useAppShellRightPanel: (content: React.ReactNode) => {
    React.useEffect(() => {
      publishRightPanel?.(content);
      return () => publishRightPanel?.(null);
    }, [content]);
  },
}));

vi.mock("../auth/auth-store", () => ({
  usePosAuthStore: (
    selector: (state: { accessToken: string; clearSession: typeof clearSessionMock }) => unknown,
  ) =>
    selector({
      accessToken: "token",
      clearSession: clearSessionMock,
    }),
}));

vi.mock("../pos-terminal/store", () => ({
  usePosTerminalStore: (selector: (state: { reset: typeof resetPosTerminalMock }) => unknown) =>
    selector({
      reset: resetPosTerminalMock,
    }),
}));

vi.mock("../status-messages/store", () => ({
  useStatusMessageStore: (
    selector: (state: {
      showError: typeof showErrorMock;
      showSuccess: typeof showSuccessMock;
    }) => unknown,
  ) =>
    selector({
      showError: showErrorMock,
      showSuccess: showSuccessMock,
    }),
}));

vi.mock("../operations/queries", () => ({
  useOperationsCatalogQuery: () => ({
    data: {
      classes: [
        {
          code: "PAN-DULCE",
          display_order: 10,
          id: "class-1",
          name: "Pan dulce",
          product_count: 1,
          quick_name: "PD",
        },
      ],
    },
    error: null,
    isPending: false,
    refetch: vi.fn(),
  }),
  useOperationsClassProductsQuery: () => ({
    data: {
      products: [
        {
          code: "CONCHA-VAN",
          currency_code: "MXN",
          display_order: 10,
          id: "product-1",
          name: "Concha vainilla",
          quick_name: "Concha",
          unit_price: "12.50",
        },
      ],
    },
    error: null,
    isPending: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("./queries", () => ({
  useCashCloseBootstrapQuery: () => ({
    data: mockBootstrapResponse,
    error: null,
    isError: false,
    isPending: false,
    refetch: vi.fn(),
  }),
  useCashCloseSummaryQuery: () => ({
    data: summaryResponse,
    error: null,
    isError: false,
    isPending: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("./cash-close-api", () => ({
  commitCashClose: (...args: unknown[]) => commitCashCloseMock(...args),
  previewCashClose: (...args: unknown[]) => previewCashCloseMock(...args),
}));

function renderUi(element: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  const container = document.createElement("div");
  document.body.appendChild(container);

  const root = createRoot(container);

  function TestShell({ children }: { children: React.ReactNode }) {
    const [rightPanelNode, setRightPanelNode] = React.useState<React.ReactNode>(null);

    React.useEffect(() => {
      publishRightPanel = setRightPanelNode;
      return () => {
        publishRightPanel = null;
      };
    }, []);

    return (
      <>
        {children}
        <div data-testid="right-panel-host">{rightPanelNode}</div>
      </>
    );
  }

  act(() => {
    root.render(
      <QueryClientProvider client={queryClient}>
        <TestShell>{element}</TestShell>
      </QueryClientProvider>,
    );
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

function click(element: Element | null | undefined) {
  if (!element) {
    throw new Error("Expected element to exist.");
  }

  act(() => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function dispatchElementKey(
  element: Element | null | undefined,
  key: string,
  options?: KeyboardEventInit,
) {
  if (!element) {
    throw new Error("Expected element to exist.");
  }

  act(() => {
    element.dispatchEvent(
      new KeyboardEvent("keydown", {
        bubbles: true,
        cancelable: true,
        key,
        ...options,
      }),
    );
  });
}

function dispatchWindowKey(key: string, options?: KeyboardEventInit) {
  act(() => {
    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        bubbles: true,
        cancelable: true,
        key,
        ...options,
      }),
    );
  });
}

function setInputValue(input: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const descriptor = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value")?.set;

  act(() => {
    descriptor?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

async function flushAsync() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

async function advancePreview() {
  await act(async () => {
    vi.advanceTimersByTime(400);
    await Promise.resolve();
    await Promise.resolve();
  });
}

function getButtonByText(container: HTMLElement, text: string, index = 0) {
  const buttons = [...container.querySelectorAll("button")].filter(
    (button) => button.textContent?.trim() === text,
  );
  return buttons[index] ?? null;
}

function getInputByLabel(container: HTMLElement, label: string) {
  return container.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`);
}

async function addPhysicalCountWithKeyboard(container: HTMLElement) {
  dispatchWindowKey("1");
  await flushAsync();

  dispatchWindowKey("1");
  await flushAsync();

  const quantityInput = getInputByLabel(container, "Cantidad contada de Concha vainilla");
  if (!quantityInput) {
    throw new Error("Expected quantity input to exist.");
  }

  setInputValue(quantityInput, "5");
  dispatchElementKey(quantityInput, "Enter");
  await flushAsync();
}

let mountedRoots: Array<() => void> = [];

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-04-22T19:30:00Z"));
  mockBootstrapResponse = buildBootstrapResponse(true);
  navigateMock.mockReset();
  showErrorMock.mockReset();
  showSuccessMock.mockReset();
  resetPosTerminalMock.mockReset();
  clearSessionMock.mockReset();
  previewCashCloseMock.mockReset();
  commitCashCloseMock.mockReset();
  previewCashCloseMock.mockImplementation(async (_token, payload) => buildPreviewResponse(payload));
  commitCashCloseMock.mockResolvedValue(committedCloseDetail);
});

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  vi.useRealTimers();
});

describe("cash close screen", () => {
  it("shows a blocker when there is no open cash session", async () => {
    mockBootstrapResponse = buildBootstrapResponse(false);

    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);
    await flushAsync();

    expect(view.container.textContent).toContain("No hay turno abierto");
    expect(view.container.textContent).toContain("No hay una caja abierta para cerrar.");
    expect(getButtonByText(view.container, "Ir a apertura")).not.toBeNull();
  });

  it("counts products with the POS selection flow and hides product prices", async () => {
    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);

    await addPhysicalCountWithKeyboard(view.container);

    expect(view.container.textContent).toContain("Conteo guardado");
    expect(view.container.textContent).toContain("Concha vainilla");
    expect(view.container.textContent).toContain("5");
    expect(view.container.querySelector('input[placeholder="Filtrar clase"]')).not.toBeNull();
    expect(getInputByLabel(view.container, "Efectivo")).toBeNull();
    expect(view.container.textContent).not.toContain("12.50");

    click(getButtonByText(view.container, "Cerrar con conteo"));
    await flushAsync();

    expect(view.container.textContent).toContain("Productos contados");
    expect(view.container.textContent).toContain("Producto");
    expect(view.container.textContent).toContain("Clase");
    expect(view.container.textContent).toContain("Cantidad");
    expect(getInputByLabel(view.container, "Efectivo")).not.toBeNull();
    expect(view.container.textContent).not.toContain("Lineas");
    expect(view.container.textContent).not.toContain("Líneas");
  });

  it("closes the shift with counted cash, product counts, and an optional observation", async () => {
    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);

    await addPhysicalCountWithKeyboard(view.container);
    click(getButtonByText(view.container, "Cerrar con conteo"));
    await flushAsync();

    expect(view.container.textContent).not.toContain("Contado");
    const cashInput = getInputByLabel(view.container, "Efectivo");
    if (!cashInput) {
      throw new Error("Expected counted cash input to exist.");
    }
    setInputValue(cashInput, "180.00");
    expect(getInputByLabel(view.container, "Tarjeta")).not.toBeNull();
    expect(view.container.textContent).toContain("Diferencia");
    expect(view.container.textContent).toContain("$0.00");

    click(getButtonByText(view.container, "Agregar observación"));
    const observationInput = view.container.querySelector<HTMLTextAreaElement>(
      'textarea[aria-label="Observación del cierre"]',
    );
    if (!observationInput) {
      throw new Error("Expected observation textarea to exist.");
    }
    setInputValue(observationInput, "Caja sin centavos");

    await advancePreview();

    click(getButtonByText(view.container, "Cerrar turno"));
    await flushAsync();

    expect(commitCashCloseMock).toHaveBeenCalledTimes(1);
    expect(commitCashCloseMock.mock.calls[0]?.[1]).toEqual({
      close_mode: "WITH_COUNT",
      counter_empty_confirmed: false,
      counted_payment_methods: [
        {
          counted_amount: "180.00",
          payment_method_code: "CASH",
        },
        {
          counted_amount: "0.00",
          payment_method_code: "CARD",
        },
      ],
      counted_product_lines: [
        {
          counted_quantity: "5",
          product_id: "product-1",
        },
      ],
      notes: "Caja sin centavos",
      workstation_code: "POS-01",
    });
    expect(showSuccessMock).toHaveBeenCalledWith("Turno cerrado correctamente");
    expect(resetPosTerminalMock).toHaveBeenCalledTimes(1);
    expect(clearSessionMock).toHaveBeenCalledTimes(1);
    expect(navigateMock).toHaveBeenCalledWith({ to: "/login" });
    expect(view.container.textContent).not.toContain("Abrir nuevo turno");
  });

  it("keeps the cashier in close shift when the backend rejects the close", async () => {
    commitCashCloseMock.mockRejectedValueOnce(new Error("Fallo del backend"));

    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);

    await addPhysicalCountWithKeyboard(view.container);
    click(getButtonByText(view.container, "Cerrar con conteo"));
    await flushAsync();

    const cashInput = getInputByLabel(view.container, "Efectivo");
    if (!cashInput) {
      throw new Error("Expected counted cash input to exist.");
    }
    setInputValue(cashInput, "180.00");

    await advancePreview();

    click(getButtonByText(view.container, "Cerrar turno"));
    await flushAsync();

    expect(commitCashCloseMock).toHaveBeenCalledTimes(1);
    expect(showErrorMock).toHaveBeenCalledWith("Fallo del backend");
    expect(showSuccessMock).not.toHaveBeenCalled();
    expect(resetPosTerminalMock).not.toHaveBeenCalled();
    expect(clearSessionMock).not.toHaveBeenCalled();
    expect(navigateMock).not.toHaveBeenCalled();
    expect(getButtonByText(view.container, "Cerrar turno")).not.toBeNull();
  });

  it("closes with an explicit empty counter after money count confirmation", async () => {
    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);
    await flushAsync();

    click(getButtonByText(view.container, "No sobró pan"));
    await flushAsync();

    expect(view.container.textContent).toContain("Mostrador vacío: 0 piezas de pan contadas.");
    expect(commitCashCloseMock).not.toHaveBeenCalled();

    const cashInput = getInputByLabel(view.container, "Efectivo");
    if (!cashInput) {
      throw new Error("Expected counted cash input to exist.");
    }
    setInputValue(cashInput, "180.00");
    await advancePreview();

    click(getButtonByText(view.container, "Cerrar turno"));
    await flushAsync();

    expect(view.container.textContent).toContain("Cerrar turno con mostrador vacío");
    expect(view.container.textContent).toContain("conteo físico de pan registrado en cero piezas");

    click(getButtonByText(view.container, "Cerrar con mostrador vacío"));
    await flushAsync();
    await flushAsync();

    expect(commitCashCloseMock).toHaveBeenCalledTimes(1);
    expect(commitCashCloseMock.mock.calls[0]?.[1]).toEqual({
      close_mode: "WITH_COUNT",
      counter_empty_confirmed: true,
      counted_payment_methods: [
        {
          counted_amount: "180.00",
          payment_method_code: "CASH",
        },
        {
          counted_amount: "0.00",
          payment_method_code: "CARD",
        },
      ],
      counted_product_lines: [],
      workstation_code: "POS-01",
    });
    expect(showSuccessMock).toHaveBeenCalledWith("Turno cerrado correctamente");
    expect(clearSessionMock).toHaveBeenCalledTimes(1);
    expect(navigateMock).toHaveBeenCalledWith({ to: "/login" });
  });

  it("calculates the difference and payload from efectivo plus tarjeta", async () => {
    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);

    await addPhysicalCountWithKeyboard(view.container);
    click(getButtonByText(view.container, "Cerrar con conteo"));
    await flushAsync();

    const cashInput = getInputByLabel(view.container, "Efectivo");
    const cardInput = getInputByLabel(view.container, "Tarjeta");
    if (!cashInput || !cardInput) {
      throw new Error("Expected efectivo and tarjeta inputs to exist.");
    }

    setInputValue(cardInput, "180.00");
    expect(view.container.textContent).toContain("$0.00");

    setInputValue(cashInput, "20.00");
    expect(view.container.textContent).toContain("$20.00");

    await advancePreview();

    click(getButtonByText(view.container, "Cerrar turno"));
    await flushAsync();

    expect(commitCashCloseMock.mock.calls[0]?.[1].counted_payment_methods).toEqual([
      {
        counted_amount: "20.00",
        payment_method_code: "CASH",
      },
      {
        counted_amount: "180.00",
        payment_method_code: "CARD",
      },
    ]);
  });
});
