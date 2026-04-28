// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";
import { act, type ReactElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CashCloseScreen } from "./cash-close-screen";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const navigateMock = vi.fn();
const showErrorMock = vi.fn();
const showSuccessMock = vi.fn();
const clearSessionMock = vi.fn();
const resetPosTerminalMock = vi.fn();
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
    is_expected_supported: true,
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
  movement_breakdown: [
    {
      currency_code: "MXN",
      direction: "IN",
      movement_count: 2,
      movement_type: "SALE_PAYMENTS",
      total_amount: "205.00",
    },
    {
      currency_code: "MXN",
      direction: "OUT",
      movement_count: 1,
      movement_type: "OPERATIONAL_PAYMENTS",
      total_amount: "10.00",
    },
  ],
  opening_amount: "300.00",
  pending_class_capture: pendingClassCapture,
  reconciliation_status: "REVIEW_REQUIRED",
  total_cash_in: "205.00",
  total_cash_out: "10.00",
  warnings: [],
} as const;

const reconciliationResponse = {
  baseline_snapshot: baselineSnapshot,
  blockers: [],
  can_commit: false,
  cash_session: openCashSession,
  class_reconciliations: [
    {
      attribution_lines: [],
      auto_attributed_quantity: "5.000",
      discrepancy_quantity: "0.000",
      final_attributed_quantity: "5.000",
      notes: null,
      pending_quantity: "5.000",
      product_class_code: "PAN-DULCE",
      product_class_id: "class-1",
      product_class_name: "Pan dulce",
      resolution_status: "AUTO_RESOLVED",
    },
  ],
  pending_class_capture: pendingClassCapture,
  reconciliation_status: "REVIEW_REQUIRED",
  relevant_products: [relevantProduct],
  warnings: [],
} as const;

const committedCloseDetail = {
  baseline_snapshot: baselineSnapshot,
  branch,
  branch_brand_key: "EL_MEJOR_PAN",
  cash_session: openCashSession,
  cash_variance_amount: "0.00",
  class_reconciliations: reconciliationResponse.class_reconciliations,
  closed_at: "2026-04-22T20:10:00Z",
  closed_by: user,
  counted_cash_amount: "180.00",
  counted_product_lines: [relevantProduct],
  currency_code: "MXN",
  discrepancy_resolutions: [],
  expected_cash_amount: "180.00",
  generated_discrepancy_documents: [],
  id: "close-1",
  movement_breakdown: summaryResponse.movement_breakdown,
  notes: null,
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
      counted_amount: "25.00",
      currency_code: "MXN",
      display_order: 20,
      expected_amount: "25.00",
      is_expected_supported: true,
      payment_method_code: "CARD",
      variance_amount: "0.00",
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
let previewMode: "difference" | "exact" = "exact";

function buildBootstrapResponse(hasOpenSession: boolean) {
  return {
    baseline_snapshot: baselineSnapshot,
    blockers: hasOpenSession
      ? []
      : [{ code: "NO_ACTIVE_OPEN_CASH_SESSION", message: "No hay una sesion abierta para cerrar." }],
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
  counted_payment_methods: Array<{ counted_amount: string; payment_method_code: string }>;
  counted_product_lines: Array<{ counted_quantity: string; product_id: string }>;
  workstation_code: string;
}) {
  void payload.workstation_code;

  const cashCount =
    payload.counted_payment_methods.find((row) => row.payment_method_code === "CASH")
      ?.counted_amount ?? "0.00";
  const cardCount =
    payload.counted_payment_methods.find((row) => row.payment_method_code === "CARD")
      ?.counted_amount ?? "0.00";
  const hasCash = Number(cashCount) > 0;
  const hasCard = Number(cardCount) > 0;
  const hasPhysical = payload.counted_product_lines.some(
    (row) => Number(row.counted_quantity) > 0,
  );
  const isReady = hasCash && hasCard && hasPhysical;
  const hasDifference = isReady && previewMode === "difference";

  return {
    baseline_snapshot: baselineSnapshot,
    blockers: [
      ...(hasCash && hasCard ? [] : [{ code: "MISSING_COUNTED_PAYMENT_TOTALS", message: "Faltan montos contados del cierre." }]),
      ...(hasPhysical ? [] : [{ code: "MISSING_COUNTED_CLOSING_STOCK", message: "Falta conteo fisico del mostrador." }]),
    ],
    can_start_close: true,
    cash_session: openCashSession,
    cash_variance_amount: hasDifference ? "50.00" : "0.00",
    class_reconciliations: [
      {
        attribution_lines: [],
        auto_attributed_quantity: "5.000",
        discrepancy_quantity: hasDifference ? "1.000" : "0.000",
        final_attributed_quantity: "5.000",
        notes: null,
        pending_quantity: "5.000",
        product_class_code: "PAN-DULCE",
        product_class_id: "class-1",
        product_class_name: "Pan dulce",
        resolution_status: hasPhysical ? "AUTO_RESOLVED" : "PENDING",
      },
    ],
    counted_cash_amount: cashCount,
    counted_product_lines: hasPhysical
      ? [
          {
            ...relevantProduct,
            counted_quantity: payload.counted_product_lines[0]?.counted_quantity ?? "0.000",
            discrepancy_quantity: hasDifference ? "1.000" : "0.000",
          },
        ]
      : [],
    currency_code: "MXN",
    discrepancy_resolutions: hasDifference
      ? [
          {
            counted_quantity: payload.counted_product_lines[0]?.counted_quantity ?? "5.000",
            discrepancy_quantity: "1.000",
            expected_quantity: "5.000",
            generated_document_id: "adjustment-1",
            notes: null,
            product_class_code: "PAN-DULCE",
            product_class_id: "class-1",
            product_class_name: "Pan dulce",
            product_code: "CONCHA-VAN",
            product_id: "product-1",
            product_name: "Concha vainilla",
            reason_code: "AUTO_ADJUSTMENT",
            resolution_type: "COUNTER_ADJUSTMENT",
          },
        ]
      : [],
    expected_cash_amount: "180.00",
    generated_discrepancy_documents: hasDifference
      ? [{ document_type: "COUNTER_ADJUSTMENT", id: "adjustment-1", status: "PENDING" }]
      : [],
    movement_breakdown: summaryResponse.movement_breakdown,
    notes: null,
    opening_amount: "300.00",
    payment_method_rows: [
      {
        counted_amount: cashCount,
        currency_code: "MXN",
        display_order: 10,
        expected_amount: "180.00",
        is_expected_supported: true,
        payment_method_code: "CASH",
        variance_amount: hasDifference ? "50.00" : "0.00",
      },
      {
        counted_amount: cardCount,
        currency_code: "MXN",
        display_order: 20,
        expected_amount: "25.00",
        is_expected_supported: true,
        payment_method_code: "CARD",
        variance_amount: "0.00",
      },
    ],
    pending_class_capture: pendingClassCapture,
    reconciliation_status: isReady ? "READY" : "REVIEW_REQUIRED",
    total_cash_in: "205.00",
    total_cash_out: "10.00",
    warnings: hasDifference
      ? [{ code: "LARGE_CASH_VARIANCE", message: "La diferencia de efectivo es alta." }]
      : [],
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
  usePosTerminalStore: (
    selector: (state: { reset: typeof resetPosTerminalMock }) => unknown,
  ) =>
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
          unit_price: "0.00",
        },
      ],
    },
    error: null,
    isPending: false,
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
  useCashCloseReconciliationQuery: () => ({
    data: reconciliationResponse,
    error: null,
    isPending: false,
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

function setInputValue(input: HTMLInputElement, value: string) {
  const descriptor = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value",
  )?.set;

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

async function moveToPhysicalStep(container: HTMLElement) {
  click(getButtonByText(container, "Ver resumen del turno"));
  await flushAsync();

  click(getButtonByText(container, "Capturar efectivo"));
  await flushAsync();

  const cashInput = getInputByLabel(container, "Total contado en Efectivo");
  if (!cashInput) {
    throw new Error("Expected cash input to exist.");
  }
  setInputValue(cashInput, "180.00");
  dispatchElementKey(cashInput, "Enter");
  await flushAsync();

  const cardInput = getInputByLabel(container, "Total contado en Tarjeta");
  if (!cardInput) {
    throw new Error("Expected card input to exist.");
  }
  setInputValue(cardInput, "25.00");
  dispatchElementKey(cardInput, "Enter");
  await flushAsync();
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
  await advancePreview();
}

let mountedRoots: Array<() => void> = [];

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-04-22T19:30:00Z"));
  mockBootstrapResponse = buildBootstrapResponse(true);
  previewMode = "exact";
  navigateMock.mockReset();
  showErrorMock.mockReset();
  showSuccessMock.mockReset();
  clearSessionMock.mockReset();
  resetPosTerminalMock.mockReset();
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

describe("cash close wizard screen", () => {
  it("shows a blocker when there is no open cash session", async () => {
    mockBootstrapResponse = buildBootstrapResponse(false);

    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);
    await flushAsync();

    expect(view.container.textContent).toContain("No hay turno abierto");
    expect(view.container.textContent).toContain("No hay una sesion abierta para cerrar.");
    expect(getButtonByText(view.container, "Ir a apertura")).not.toBeNull();
  });

  it("advances from cash count to payment reconciliation with Enter", async () => {
    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);

    click(getButtonByText(view.container, "Ver resumen del turno"));
    await flushAsync();
    click(getButtonByText(view.container, "Capturar efectivo"));
    await flushAsync();

    const cashInput = getInputByLabel(view.container, "Total contado en Efectivo");
    if (!cashInput) {
      throw new Error("Expected cash input to exist.");
    }

    setInputValue(cashInput, "180.00");
    dispatchElementKey(cashInput, "Enter");
    await flushAsync();

    expect(view.container.textContent).toContain("Tarjeta y otros medios");
  });

  it("shows class capture reconciliation data in the differences step", async () => {
    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);

    await moveToPhysicalStep(view.container);
    await addPhysicalCountWithKeyboard(view.container);

    click(getButtonByText(view.container, "Revisar diferencias"));
    await flushAsync();

    expect(view.container.textContent).toContain("Paso 6");
    expect(view.container.textContent).toContain("Pan dulce");
    expect(view.container.textContent).toContain("AUTO_RESOLVED");
  });

  it("requires cashier acknowledgement for a high-impact difference and marks the cash reason step as deferred", async () => {
    previewMode = "difference";

    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);

    await moveToPhysicalStep(view.container);
    await addPhysicalCountWithKeyboard(view.container);

    click(getButtonByText(view.container, "Revisar diferencias"));
    await flushAsync();

    expect(view.container.textContent).toContain(
      "El motivo manual para la diferencia de efectivo sigue pendiente de contrato backend.",
    );

    click(getButtonByText(view.container, "Validar cierre"));
    await flushAsync();

    expect(view.container.textContent).toContain("Paso 7");
    expect(view.container.textContent).toContain("Reconocimiento requerido");
    expect(view.container.textContent).toContain("Confirma la revision del cajero para continuar.");

    const acknowledgement = view.container.querySelector<HTMLInputElement>('input[type="checkbox"]');
    if (!acknowledgement) {
      throw new Error("Expected acknowledgement checkbox to exist.");
    }

    click(acknowledgement);
    await flushAsync();

    expect(view.container.textContent).not.toContain("Confirma la revision del cajero para continuar.");
  });

  it("confirms and commits a close without differences", async () => {
    const view = renderUi(<CashCloseScreen />);
    mountedRoots.push(view.unmount);

    await moveToPhysicalStep(view.container);
    await addPhysicalCountWithKeyboard(view.container);

    click(getButtonByText(view.container, "Revisar diferencias"));
    await flushAsync();
    click(getButtonByText(view.container, "Validar cierre"));
    await flushAsync();
    click(getButtonByText(view.container, "Ir al cierre final"));
    await flushAsync();

    const finalizeButton = getButtonByText(view.container, "Confirmar cierre");
    if (!finalizeButton) {
      throw new Error("Expected final confirm button to exist.");
    }
    click(finalizeButton);
    await flushAsync();
    expect(getButtonByText(view.container, "Cancelar")).not.toBeNull();

    const dialogSurface = view.container.querySelector(".fixed.inset-0");
    if (!dialogSurface) {
      throw new Error("Expected confirmation dialog to be visible.");
    }

    const dialogConfirmButton = [...dialogSurface.querySelectorAll("button")].find(
      (button) => button.textContent?.trim() === "Confirmar cierre",
    );
    click(dialogConfirmButton ?? null);
    await flushAsync();

    expect(commitCashCloseMock).toHaveBeenCalledTimes(1);
    expect(showSuccessMock).toHaveBeenCalledTimes(1);
    expect(showSuccessMock.mock.calls[0]?.[0]).toContain("Turno cerrado");
    expect(view.container.textContent).toContain("Resultado del cierre");
    expect(view.container.textContent).toContain("Copiar referencia");
    expect(view.container.textContent).toContain("Exportar PDF");
    expect(view.container.textContent).toContain("Abrir nuevo turno");
  });
});
