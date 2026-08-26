// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, useSyncExternalStore, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CorrectionDocumentView, OperationDocumentView } from "../../lib/api-contracts";
import { commitCorrection } from "../corrections/corrections-api";
import { CounterTransferScreen } from "./counter-transfer-screen";
import { commitCounterTransfer } from "./operations-api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const refetchMock = vi.fn();
const showErrorMock = vi.fn();
const showSuccessMock = vi.fn();
const showWarningMock = vi.fn();
const historyFilterRequests: Array<{ enabled: boolean; filters: unknown }> = [];
let rightPanelContent: ReactNode = null;
const rightPanelListeners = new Set<() => void>();

const bootstrapResponse = {
  branch: {
    code: "MAIN",
    id: "branch-1",
    is_active: true,
    name: "Main Branch",
    timezone: "America/Hermosillo",
  },
  branch_brand_key: "EL_MEJOR_PAN",
  destination_branches: [],
  local_timestamp: "2026-04-22T18:00:00Z",
  user: {
    email: "cashier@zeromerma.local",
    full_name: "Main Branch Cashier",
    id: "user-1",
    is_active: true,
  },
  waste_controls: {
    attachment_evidence_supported: false,
    high_impact_quantity_threshold: "10",
    high_impact_requires_acknowledgement: true,
    high_impact_requires_note: true,
    stock_validated_source_bucket_codes: ["COUNTER"],
  },
  waste_reasons: [],
  workstation: {
    code: "POS-01",
    id: "workstation-1",
    is_active: true,
    name: "Front Register 01",
  },
} as const;

const counterTransferDocument: OperationDocumentView = {
  audit_summary: null,
  committed_at_utc: "2026-04-22T18:10:00Z",
  created_at_utc: "2026-04-22T18:08:00Z",
  created_by_user_email: "cashier@zeromerma.local",
  created_by_user_full_name: "Main Branch Cashier",
  created_by_user_id: "user-1",
  destination_branch_code: null,
  destination_branch_id: null,
  destination_branch_name: null,
  destination_bucket_code: "COUNTER",
  document_type: "COUNTER_TRANSFER",
  folio: "CTR-000001",
  id: "operation-1",
  lines: [
    {
      expected_quantity: null,
      id: "operation-line-1",
      line_number: 1,
      notes: null,
      product_class_code_snapshot: "PAN-DULCE",
      product_class_id: "class-1",
      product_class_name_snapshot: "Pan dulce",
      product_code_snapshot: "CONCHA-VAN",
      product_id: "product-1",
      product_name_snapshot: "Concha vainilla",
      quantity: "2.000",
      received_quantity: null,
      unit_of_measure_code: "EACH",
      variance_reason: null,
    },
  ],
  notes: null,
  reason_code: null,
  reason_name: null,
  reference_document_id: null,
  source_branch_code: "MAIN",
  source_branch_id: "branch-1",
  source_branch_name: "Main Branch",
  source_bucket_code: "BACKROOM",
  status: "COMMITTED",
  workstation_code: "POS-01",
  workstation_id: "workstation-1",
  workstation_name: "Front Register 01",
};

const counterTransferHistoryResponse = {
  available_destination_buckets: [{ label: "Mostrador", value: "COUNTER" }],
  available_products: [],
  available_reasons: [],
  available_scopes: [
    { code: "ALL", label: "Todos" },
    { code: "CURRENT_SHIFT", label: "Turno actual" },
    { code: "TODAY", label: "Hoy" },
    { code: "RECENT", label: "Recientes" },
  ],
  available_source_buckets: [{ label: "Fondo", value: "BACKROOM" }],
  available_users: [
    { label: "Main Branch Cashier", value: "user-1" },
    { label: "Night Cashier", value: "user-2" },
  ],
  created_by_user_id: null,
  destination_bucket_code: null,
  document_type: "COUNTER_TRANSFER",
  product_id: null,
  reason_code: null,
  records: [
    {
      committed_at_utc: "2026-04-22T15:10:00Z",
      created_at_utc: "2026-04-22T15:08:00Z",
      created_by_user_full_name: "Main Branch Cashier",
      created_by_user_id: "user-1",
      destination_branch_code: null,
      destination_branch_name: null,
      destination_bucket_code: "COUNTER",
      document_type: "COUNTER_TRANSFER",
      folio: "CTR-MORNING",
      id: "operation-morning",
      line_count: 1,
      reason_code: null,
      reason_name: null,
      source_branch_code: "MAIN",
      source_branch_name: "Main Branch",
      source_bucket_code: "BACKROOM",
      status: "COMMITTED",
      total_quantity: "4.000",
      workstation_code: "POS-01",
      workstation_name: "Front Register 01",
    },
    {
      committed_at_utc: "2026-04-22T20:10:00Z",
      created_at_utc: "2026-04-22T20:08:00Z",
      created_by_user_full_name: "Main Branch Cashier",
      created_by_user_id: "user-1",
      destination_branch_code: null,
      destination_branch_name: null,
      destination_bucket_code: "COUNTER",
      document_type: "COUNTER_TRANSFER",
      folio: "CTR-000001",
      id: "operation-1",
      line_count: 1,
      reason_code: null,
      reason_name: null,
      source_branch_code: "MAIN",
      source_branch_name: "Main Branch",
      source_bucket_code: "BACKROOM",
      status: "COMMITTED",
      total_quantity: "2.000",
      workstation_code: "POS-01",
      workstation_name: "Front Register 01",
    },
    {
      committed_at_utc: "2026-04-23T03:10:00Z",
      created_at_utc: "2026-04-23T03:08:00Z",
      created_by_user_full_name: "Night Cashier",
      created_by_user_id: "user-2",
      destination_branch_code: null,
      destination_branch_name: null,
      destination_bucket_code: "COUNTER",
      document_type: "COUNTER_TRANSFER",
      folio: "CTR-NIGHT",
      id: "operation-night",
      line_count: 1,
      reason_code: null,
      reason_name: null,
      source_branch_code: "MAIN",
      source_branch_name: "Main Branch",
      source_bucket_code: "BACKROOM",
      status: "COMMITTED",
      total_quantity: "6.000",
      workstation_code: "POS-01",
      workstation_name: "Front Register 01",
    },
  ],
  scope: "CURRENT_SHIFT",
  source_bucket_code: null,
  workstation_code: "POS-01",
} as const;

const counterAvailabilityResponse = {
  blockers: [],
  can_commit: true,
  cash_session: { id: "cash-session-1" },
  class_reconciliations: [],
  counter_class_availability: [
    {
      available_quantity: "8.000",
      expected_quantity_before_deferred_attr: "11.000",
      pending_class_capture_quantity: "3.000",
      product_class_code: "PAN-DULCE",
      product_class_id: "class-1",
      product_class_name: "Pan dulce",
    },
  ],
  pending_class_capture: {
    has_pending_class_capture: true,
    pending_class_capture_classes_count: 1,
    pending_class_capture_total_quantity: "3.000",
  },
  reconciliation_status: "PENDING_CLASS_ATTRIBUTION",
  relevant_products: [
    {
      counted_quantity: null,
      discrepancy_quantity: null,
      expected_quantity_before_deferred_attr: "5.000",
      final_expected_quantity: null,
      notes: null,
      product_class_code: "PAN-DULCE",
      product_class_id: "class-1",
      product_class_name: "Pan dulce",
      product_code: "CONCHA-VAN",
      product_id: "product-1",
      product_name: "Concha vainilla",
    },
  ],
  warnings: [],
} as const;

const correctionBootstrapResponse = {
  branch: bootstrapResponse.branch,
  branch_brand_key: "EL_MEJOR_PAN",
  correction_controls: {
    high_impact_quantity_threshold: "10.000",
    high_impact_requires_acknowledgement: true,
  },
  correction_operations_allowed: true,
  correction_reasons: [
    { code: "WRONG_QUANTITY", display_order: 10, name: "Cantidad incorrecta" },
    { code: "WRONG_PRODUCT", display_order: 20, name: "Producto incorrecto" },
  ],
  current_open_cash_session: { user_id: "user-1" },
  destination_branches: [],
  local_timestamp: "2026-04-22T18:00:00Z",
  user: bootstrapResponse.user,
  workstation: bootstrapResponse.workstation,
} as const;

const correctionDocument: CorrectionDocumentView = {
  audit_summary: null,
  committed_at_utc: "2026-04-22T18:20:00Z",
  corrected_destination_branch_code: null,
  corrected_destination_branch_id: null,
  corrected_destination_branch_name: null,
  correction_type: "DELTA_ADJUSTMENT",
  created_at_utc: "2026-04-22T18:19:00Z",
  created_by_user_email: "cashier@zeromerma.local",
  created_by_user_full_name: "Main Branch Cashier",
  created_by_user_id: "user-1",
  folio: "COR-000001",
  id: "correction-1",
  lines: [
    {
      delta_quantity: "-1.000",
      id: "correction-line-1",
      line_number: 1,
      notes: null,
      product_class_code_snapshot: "PAN-DULCE",
      product_class_id: "class-1",
      product_class_name_snapshot: "Pan dulce",
      product_code_snapshot: "CONCHA-VAN",
      product_id: "product-1",
      product_name_snapshot: "Concha vainilla",
      target_line_id: "operation-line-1",
      unit_of_measure_code: "EACH",
    },
  ],
  notes: "Captura duplicada",
  reason_code: "WRONG_QUANTITY",
  reason_name: "Cantidad incorrecta",
  source_branch_code: "MAIN",
  source_branch_id: "branch-1",
  source_branch_name: "Main Branch",
  status: "COMMITTED",
  target_document_id: "operation-1",
  target_document_type: "COUNTER_TRANSFER",
  workstation_code: "POS-01",
  workstation_id: "workstation-1",
  workstation_name: "Front Register 01",
};

vi.mock("@tanstack/react-router", () => ({
  Navigate: ({ to }: { to: string }) => <div data-testid="navigate">{to}</div>,
}));

vi.mock("../../components/app-shell-right-panel", async () => {
  const React = await import("react");

  function emitRightPanel() {
    for (const listener of rightPanelListeners) {
      listener();
    }
  }

  return {
    useAppShellRightPanel(content: ReactNode) {
      React.useEffect(() => {
        rightPanelContent = content;
        emitRightPanel();
        return () => {
          rightPanelContent = null;
          emitRightPanel();
        };
      }, [content]);
    },
  };
});

vi.mock("../auth/auth-store", () => ({
  usePosAuthStore: (selector: (state: { accessToken: string }) => unknown) =>
    selector({ accessToken: "token" }),
}));

vi.mock("../cash-session-open/queries", () => ({
  useCurrentCashSessionQuery: () => ({
    data: { user_id: "user-1" },
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock("../cash-close/queries", () => ({
  cashCloseReconciliationQueryKey: vi.fn(() => ["cash-close-reconciliation", "POS-01"]),
  useCashCloseReconciliationQuery: (enabled = true) => ({
    data: enabled ? counterAvailabilityResponse : undefined,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock("../corrections/corrections-api", () => ({
  commitCorrection: vi.fn(),
}));

vi.mock("../corrections/queries", () => ({
  correctionTargetDetailQueryKey: vi.fn((workstationCode: string, targetDocumentId: string) => [
    "corrections",
    "detail",
    workstationCode,
    targetDocumentId,
  ]),
  correctionsBootstrapQueryKey: vi.fn((workstationCode: string) => [
    "corrections",
    "bootstrap",
    workstationCode,
  ]),
  useCorrectionsBootstrapQuery: () => ({
    data: correctionBootstrapResponse,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock("../status-messages/store", () => ({
  useStatusMessageStore: (
    selector: (state: {
      showError: typeof showErrorMock;
      showSuccess: typeof showSuccessMock;
      showWarning: typeof showWarningMock;
    }) => unknown,
  ) =>
    selector({
      showError: showErrorMock,
      showSuccess: showSuccessMock,
      showWarning: showWarningMock,
    }),
}));

vi.mock("./queries", () => ({
  operationDocumentQueryKey: vi.fn(() => ["operation-document", "POS-01", "operation-1"]),
  operationHistoryQueryKey: vi.fn(() => ["operation-history", "POS-01", "COUNTER_TRANSFER"]),
  useOperationDocumentQuery: (documentId: string | null) => ({
    data: documentId === "operation-1" ? counterTransferDocument : null,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useOperationHistoryQuery: (_documentType: string, filters: unknown, enabled = true) => {
    historyFilterRequests.push({ enabled, filters });
    return {
      data: enabled ? counterTransferHistoryResponse : undefined,
      error: null,
      isPending: false,
      refetch: refetchMock,
    };
  },
  useOperationsBootstrapQuery: () => ({
    data: bootstrapResponse,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
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
    refetch: refetchMock,
  }),
  useOperationsClassProductsQuery: (_module: string, classId: string | null) => ({
    data:
      classId === "class-1"
        ? {
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
          }
        : undefined,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock("./operations-api", () => ({
  commitCounterTransfer: vi.fn(),
}));

function AppShellRightPanelProbe() {
  const content = useSyncExternalStore(
    (listener) => {
      rightPanelListeners.add(listener);
      return () => rightPanelListeners.delete(listener);
    },
    () => rightPanelContent,
    () => rightPanelContent,
  );

  return <div data-testid="right-panel-probe">{content}</div>;
}

function click(element: Element | undefined | null) {
  if (!element) {
    throw new Error("Expected element to exist.");
  }

  act(() => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function keydown(
  element: Element | Window | undefined | null,
  key: string,
  init?: KeyboardEventInit,
) {
  if (!element) {
    throw new Error(`Expected target for key ${key}.`);
  }

  act(() => {
    element.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key, ...init }));
  });
}

function changeInput(element: HTMLInputElement | HTMLTextAreaElement | null, value: string) {
  if (!element) {
    throw new Error("Expected input element to exist.");
  }

  act(() => {
    const prototype =
      element instanceof HTMLTextAreaElement
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype;
    const valueSetter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
    valueSetter?.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function changeSelect(element: HTMLSelectElement | null, value: string) {
  if (!element) {
    throw new Error("Expected select element to exist.");
  }

  act(() => {
    const valueSetter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set;
    valueSetter?.call(element, value);
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function findButtonByText(scope: ParentNode, text: string) {
  return Array.from(scope.querySelectorAll("button")).find((button) =>
    button.textContent?.includes(text),
  ) as HTMLButtonElement | undefined;
}

function getRightPanel(container: HTMLElement) {
  return container.querySelector<HTMLElement>('[data-testid="right-panel-probe"]');
}

function renderUi() {
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
    root.render(
      <QueryClientProvider client={queryClient}>
        <CounterTransferScreen />
        <AppShellRightPanelProbe />
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

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

async function selectProductWithShortcuts(container: HTMLElement) {
  await flush();
  keydown(window, "1");
  await flush();
  expect(container.textContent).toContain("Concha vainilla");
  keydown(window, "1");
  await flush();
}

async function addLineWithShortcuts(container: HTMLElement, quantity: string) {
  await selectProductWithShortcuts(container);
  const quantityInput = container.querySelector<HTMLInputElement>('input[aria-label="Cantidad"]');
  changeInput(quantityInput, quantity);
  await flush();
  keydown(quantityInput, "Enter");
  await flush();
}

let mountedRoots: Array<() => void> = [];

beforeEach(() => {
  rightPanelContent = null;
  historyFilterRequests.length = 0;
  vi.mocked(commitCounterTransfer).mockResolvedValue(counterTransferDocument);
  vi.mocked(commitCorrection).mockResolvedValue(correctionDocument);
});

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  rightPanelContent = null;
  document.body.innerHTML = "";
  vi.clearAllMocks();
});

describe("CounterTransferScreen", () => {
  it("cannot confirm an empty transfer", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = getRightPanel(view.container);
    const transferButton = findButtonByText(rightPanel ?? view.container, "Pasar a Mostrador");

    expect(transferButton?.disabled).toBe(true);
    expect(commitCounterTransfer).not.toHaveBeenCalled();
  });

  it("adds a product with numpad-first flow and does not show prices", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);

    await addLineWithShortcuts(view.container, "2");

    const rightPanel = getRightPanel(view.container);
    const summaryQuantityButton = rightPanel?.querySelector<HTMLButtonElement>(
      'button[aria-label="Editar cantidad de Concha vainilla"]',
    );

    expect(view.container.textContent).not.toContain("12.50");
    expect(rightPanel?.textContent).not.toContain("12.50");
    expect(rightPanel?.textContent).toContain("Concha vainilla");
    expect(rightPanel?.textContent).not.toContain("Pan dulce");
    expect(rightPanel?.textContent).not.toContain("Resumen");
    expect(summaryQuantityButton?.textContent).toBe("2");
    expect(view.container.querySelector('input[placeholder="Filtrar clase"]')).not.toBeNull();
  });

  it("toggles the current counter state from the capture right panel", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = getRightPanel(view.container);
    expect(rightPanel?.textContent).toContain("Mostrador actual");
    expect(rightPanel?.querySelector('table[aria-label="Estado actual del mostrador"]')).toBeNull();

    const showCounterButton = findButtonByText(
      rightPanel ?? view.container,
      "Mostrar mostrador actual",
    );
    expect(showCounterButton?.getAttribute("aria-expanded")).toBe("false");

    click(showCounterButton);
    await flush();

    expect(rightPanel?.querySelector('table[aria-label="Estado actual del mostrador"]')).not.toBeNull();
    expect(rightPanel?.textContent).toContain("Pan dulce");
    expect(rightPanel?.textContent).toContain("Diferido");
    expect(rightPanel?.textContent).not.toContain("Concha vainilla");

    click(
      rightPanel?.querySelector<HTMLTableRowElement>('tr[aria-label="Expandir Pan dulce"]') ?? null,
    );
    await flush();
    expect(rightPanel?.textContent).toContain("Concha vainilla");

    const hideCounterButton = findButtonByText(
      rightPanel ?? view.container,
      "Ocultar mostrador actual",
    );
    expect(hideCounterButton?.getAttribute("aria-expanded")).toBe("true");

    click(hideCounterButton);
    await flush();

    expect(rightPanel?.querySelector('table[aria-label="Estado actual del mostrador"]')).toBeNull();
    expect(rightPanel?.textContent).toContain("Mostrar mostrador actual");
  });

  it("updates duplicate products instead of creating duplicate rows", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);

    await addLineWithShortcuts(view.container, "2");
    await addLineWithShortcuts(view.container, "3");

    const rightPanel = getRightPanel(view.container);
    const quantityButtons = rightPanel?.querySelectorAll<HTMLButtonElement>(
      'button[aria-label="Editar cantidad de Concha vainilla"]',
    );

    expect(quantityButtons).toHaveLength(1);
    expect(quantityButtons?.[0]?.textContent).toBe("5");
  });

  it("does not add invalid quantities", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);

    await selectProductWithShortcuts(view.container);
    const quantityInput = view.container.querySelector<HTMLInputElement>('input[aria-label="Cantidad"]');
    changeInput(quantityInput, "0");
    await flush();
    keydown(quantityInput, "Enter");
    await flush();

    const rightPanel = getRightPanel(view.container);
    const transferButton = findButtonByText(rightPanel ?? view.container, "Pasar a Mostrador");

    expect(rightPanel?.textContent).toContain("Sin productos seleccionados.");
    expect(transferButton?.disabled).toBe(true);
    expect(commitCounterTransfer).not.toHaveBeenCalled();
  });

  it("edits and removes selected products from the right panel", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);

    await addLineWithShortcuts(view.container, "2");

    const rightPanel = getRightPanel(view.container);
    const summaryQuantityButton = rightPanel?.querySelector<HTMLButtonElement>(
      'button[aria-label="Editar cantidad de Concha vainilla"]',
    );
    click(summaryQuantityButton ?? null);
    await flush();

    const summaryInput = rightPanel?.querySelector<HTMLInputElement>(
      'input[aria-label="Cantidad de Concha vainilla"]',
    );
    changeInput(summaryInput ?? null, "5");
    await flush();
    keydown(summaryInput, "Enter");
    await flush();

    const committedQuantityButton = rightPanel?.querySelector<HTMLButtonElement>(
      'button[aria-label="Editar cantidad de Concha vainilla"]',
    );
    expect(committedQuantityButton?.textContent).toBe("5");

    const removeButton = rightPanel?.querySelector<HTMLButtonElement>(
      'button[aria-label="Eliminar Concha vainilla"]',
    );
    click(removeButton);
    await flush();

    const transferButton = findButtonByText(rightPanel ?? view.container, "Pasar a Mostrador");
    expect(rightPanel?.textContent).toContain("Sin productos seleccionados.");
    expect(transferButton?.disabled).toBe(true);
  });

  it("commits the transfer with notes and clears the summary", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);

    await addLineWithShortcuts(view.container, "2");

    const rightPanel = getRightPanel(view.container);
    click(findButtonByText(rightPanel ?? view.container, "Agregar observación"));
    await flush();

    const notesInput = rightPanel?.querySelector<HTMLTextAreaElement>(
      'textarea[aria-label="Observación del movimiento"]',
    );
    changeInput(notesInput ?? null, "Salida de charola 3");
    await flush();

    click(findButtonByText(rightPanel ?? view.container, "Ocultar observación"));
    await flush();
    expect(rightPanel?.querySelector('textarea[aria-label="Observación del movimiento"]')).toBeNull();
    expect(rightPanel?.textContent).toContain("Con texto");

    click(findButtonByText(rightPanel ?? view.container, "Agregar observación"));
    await flush();
    expect(
      rightPanel?.querySelector<HTMLTextAreaElement>(
        'textarea[aria-label="Observación del movimiento"]',
      )?.value,
    ).toBe("Salida de charola 3");

    const transferButton = findButtonByText(rightPanel ?? view.container, "Pasar a Mostrador");
    click(transferButton);
    await flush();

    expect(commitCounterTransfer).toHaveBeenCalledWith("token", {
      lines: [{ product_id: "product-1", quantity: "2" }],
      notes: "Salida de charola 3",
      workstation_code: "POS-01",
    });
    expect(showSuccessMock).toHaveBeenCalledWith(
      "Movimiento a mostrador registrado. Folio CTR-000001.",
    );
    expect(rightPanel?.textContent).toContain("Sin productos seleccionados.");
    expect(rightPanel?.textContent).toContain("Ultimo movimiento: CTR-000001");
  });

  it("opens history as an internal table view with current counter state", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = getRightPanel(view.container);
    const historyButton = findButtonByText(rightPanel ?? view.container, "Historial");
    click(historyButton);
    await flush();

    expect(view.container.querySelector('[role="dialog"]')).toBeNull();
    expect(view.container.textContent).toContain("Historial a mostrador");
    expect(view.container.textContent).toContain("Captura");
    expect(view.container.textContent).toContain("Mañana");
    expect(view.container.textContent).toContain("Tarde");
    expect(view.container.textContent).toContain("Noche");
    expect(view.container.textContent).toContain("CTR-000001");
    expect(
      view.container.querySelector('table[aria-label="Historial de movimientos a mostrador"]'),
    ).not.toBeNull();
    expect(view.container.textContent).toContain("Fecha/hora");
    expect(view.container.textContent).toContain("Cajero");
    expect(view.container.textContent).not.toContain("Lineas");
    expect(view.container.textContent).toContain("Unidades");
    expect(view.container.textContent).toContain("Estado");
    expect(view.container.textContent).not.toContain("Accion");
    expect(findButtonByText(view.container, "Ver")).toBeUndefined();
    expect(view.container.textContent).toContain("Main Branch Cashier");
    expect(rightPanel?.textContent).not.toContain("Detalle de historial");
    expect(rightPanel?.textContent).toContain("Mostrador actual");
    expect(rightPanel?.querySelector('table[aria-label="Estado actual del mostrador"]')).not.toBeNull();
    expect(rightPanel?.textContent).toContain("Pan dulce");
    expect(rightPanel?.textContent).toContain("Diferido");
    expect(rightPanel?.textContent).toContain("aprox.");
    expect(rightPanel?.textContent).not.toContain("8 confirmado / 3 diferido");
    expect(rightPanel?.textContent).not.toContain("Concha vainilla");

    const classRow = rightPanel?.querySelector<HTMLTableRowElement>(
      'tr[aria-label="Expandir Pan dulce"]',
    );
    expect(classRow?.getAttribute("aria-expanded")).toBe("false");

    click(classRow);
    await flush();

    expect(
      rightPanel?.querySelector<HTMLTableRowElement>('tr[aria-label="Contraer Pan dulce"]'),
    ).not.toBeNull();
    expect(rightPanel?.textContent).toContain("Concha vainilla");
    expect(rightPanel?.textContent).toContain("estimado");
  });

  it("filters history by time of day without changing backend filters", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = getRightPanel(view.container);
    click(findButtonByText(rightPanel ?? view.container, "Historial"));
    await flush();

    click(findButtonByText(view.container, "Mañana"));
    await flush();
    expect(view.container.textContent).toContain("CTR-MORNING");
    expect(view.container.textContent).not.toContain("CTR-000001");
    expect(view.container.textContent).not.toContain("CTR-NIGHT");

    click(findButtonByText(view.container, "Tarde"));
    await flush();
    expect(view.container.textContent).toContain("CTR-000001");
    expect(view.container.textContent).not.toContain("CTR-MORNING");
    expect(view.container.textContent).not.toContain("CTR-NIGHT");

    click(findButtonByText(view.container, "Noche"));
    await flush();
    expect(view.container.textContent).toContain("CTR-NIGHT");
    expect(view.container.textContent).not.toContain("CTR-MORNING");
    expect(view.container.textContent).not.toContain("CTR-000001");
  });

  it("selects a history row, shows movement detail, and can return to current counter state", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = getRightPanel(view.container);
    click(findButtonByText(rightPanel ?? view.container, "Historial"));
    await flush();

    const movementRow = view.container.querySelector<HTMLTableRowElement>(
      'tr[aria-label="Seleccionar movimiento CTR-000001"]',
    );
    keydown(movementRow, "Enter");
    await flush();

    expect(movementRow?.getAttribute("aria-selected")).toBe("true");
    expect(rightPanel?.textContent).toContain("Detalle de movimiento");
    expect(rightPanel?.textContent).toContain("CTR-000001");
    expect(rightPanel?.textContent).toContain("Main Branch Cashier");
    expect(rightPanel?.textContent).toContain("Front Register 01");
    expect(rightPanel?.textContent).toContain("Concha vainilla");
    expect(rightPanel?.textContent).not.toContain("Pan dulce");
    expect(rightPanel?.textContent).toContain("2");

    click(findButtonByText(rightPanel ?? view.container, "Mostrar mostrador actual"));
    await flush();

    expect(rightPanel?.textContent).toContain("Mostrador actual");
    expect(rightPanel?.textContent).not.toContain("Detalle de movimiento");

    click(movementRow);
    await flush();
    expect(rightPanel?.textContent).toContain("Detalle de movimiento");

    keydown(window, "Escape");
    await flush();
    expect(rightPanel?.textContent).toContain("Mostrador actual");
  });

  it("registers a formal adjustment from the selected movement detail", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = getRightPanel(view.container);
    click(findButtonByText(rightPanel ?? view.container, "Historial"));
    await flush();

    click(
      view.container.querySelector<HTMLTableRowElement>(
        'tr[aria-label="Seleccionar movimiento CTR-000001"]',
      ),
    );
    await flush();

    click(findButtonByText(rightPanel ?? view.container, "Aplicar ajuste"));
    await flush();

    expect(rightPanel?.textContent).toContain("Detalle de movimiento");
    expect(rightPanel?.textContent).toContain("No hay cambios para guardar.");
    expect(rightPanel?.textContent).toContain("Concha vainilla");
    expect(rightPanel?.textContent).not.toContain("Cantidad incorrecta");
    expect(rightPanel?.textContent).not.toContain("Motivo");
    expect(rightPanel?.querySelector('textarea[aria-label="Observacion del ajuste"]')).toBeNull();

    const saveButton = findButtonByText(rightPanel ?? view.container, "Guardar ajuste");
    expect(saveButton?.disabled).toBe(true);

    const adjustmentInput = rightPanel?.querySelector<HTMLInputElement>(
      'input[aria-label="Cantidad corregida de Concha vainilla"]',
    );
    expect(adjustmentInput?.value).toBe("2");
    changeInput(adjustmentInput ?? null, "5");
    await flush();

    expect(rightPanel?.textContent).toContain("+3");
    expect(saveButton?.disabled).toBe(false);
    click(findButtonByText(rightPanel ?? view.container, "Guardar ajuste"));
    await flush();

    expect(commitCorrection).toHaveBeenCalledWith({
      accessToken: "token",
      payload: {
        high_impact_acknowledged: false,
        lines: [
          {
            delta_quantity: "3",
            product_id: "product-1",
            target_line_id: "operation-line-1",
          },
        ],
        reason_code: "WRONG_QUANTITY",
        target_document_id: "operation-1",
        workstation_code: "POS-01",
      },
      requestId: expect.stringMatching(/^counter-transfer-adjustment-/),
    });
    expect(showSuccessMock).toHaveBeenCalledWith("Ajuste COR-000001 registrado correctamente.");
    expect(rightPanel?.textContent).toContain("Detalle de movimiento");
    expect(rightPanel?.textContent).toContain("Ajuste registrado: COR-000001");
  });

  it("filters history by cashier and reloads by scope", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = getRightPanel(view.container);
    click(findButtonByText(rightPanel ?? view.container, "Historial"));
    await flush();

    changeSelect(
      view.container.querySelector<HTMLSelectElement>('select[aria-label="Filtrar por cajero"]'),
      "user-1",
    );
    await flush();

    click(findButtonByText(view.container, "Hoy"));
    await flush();

    click(findButtonByText(view.container, "Todos"));
    await flush();

    expect(
      historyFilterRequests.some(
        (request) =>
          request.enabled &&
          typeof request.filters === "object" &&
          request.filters !== null &&
          "createdByUserId" in request.filters &&
          request.filters.createdByUserId === "user-1",
      ),
    ).toBe(true);
    expect(
      historyFilterRequests.some(
        (request) =>
          request.enabled &&
          typeof request.filters === "object" &&
          request.filters !== null &&
          "scope" in request.filters &&
          request.filters.scope === "TODAY",
      ),
    ).toBe(true);
    expect(
      historyFilterRequests.some(
        (request) =>
          request.enabled &&
          typeof request.filters === "object" &&
          request.filters !== null &&
          "scope" in request.filters &&
          request.filters.scope === "ALL",
      ),
    ).toBe(true);
  });
});
