// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, useSyncExternalStore, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OperationModuleScreen } from "./operation-module-screen";
import { commitCounterTransfer, commitWasteRecord } from "./operations-api";
import type { OperationDocumentView } from "../../lib/api-contracts";
import { KeyboardShortcutRegistry } from "../pos-shell/keyboard";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const refetchMock = vi.fn();
const pushMessageMock = vi.fn();
const showErrorMock = vi.fn();
const showSuccessMock = vi.fn();
const showWarningMock = vi.fn();
let mockCounterAvailabilityData = {
  counter_class_availability: [
    {
      available_quantity: "5.000",
      expected_quantity_before_deferred_attr: "5.000",
      pending_class_capture_quantity: "0.000",
      product_class_code: "PAN-DULCE",
      product_class_id: "class-1",
      product_class_name: "Pan dulce",
    },
  ],
  relevant_products: [
    {
      counted_quantity: null,
      discrepancy_quantity: null,
      expected_quantity_before_deferred_attr: "5.000",
      final_expected_quantity: "5.000",
      notes: null,
      product_class_code: "PAN-DULCE",
      product_class_id: "class-1",
      product_class_name: "Pan dulce",
      product_code: "CONCHA-VAN",
      product_id: "product-1",
      product_name: "Concha vainilla",
    },
  ],
};
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
  destination_branches: [
    {
      brand_key: null,
      code: "MAIN",
      id: "branch-1",
      name: "Main Branch",
      timezone: "America/Hermosillo",
    },
  ],
  local_timestamp: "2026-04-22T18:00:00Z",
  user: {
    email: "cashier@zeromerma.local",
    full_name: "Main Branch Cashier",
    id: "user-1",
    is_active: true,
  },
  waste_reasons: [
    { code: "OLD_COUNTER", display_order: 10, name: "Old counter", requires_note: false },
    { code: "DAMAGED", display_order: 20, name: "Damaged", requires_note: true },
  ],
  waste_controls: {
    attachment_evidence_supported: false,
    high_impact_quantity_threshold: "10",
    high_impact_requires_acknowledgement: true,
    high_impact_requires_note: true,
    stock_validated_source_bucket_codes: ["COUNTER"],
  },
  workstation: {
    code: "POS-01",
    id: "workstation-1",
    is_active: true,
    name: "Front Register 01",
  },
} as const;

const counterTransferHistoryResponse = {
  available_destination_buckets: [{ label: "COUNTER", value: "COUNTER" }],
  available_scopes: [
    { code: "ALL", label: "Todos" },
    { code: "CURRENT_SHIFT", label: "Turno actual" },
    { code: "TODAY", label: "Hoy" },
    { code: "RECENT", label: "Recientes" },
  ],
  available_source_buckets: [{ label: "BACKROOM", value: "BACKROOM" }],
  available_users: [
    { label: "Main Branch Cashier", value: "user-1" },
    { label: "Night Cashier", value: "user-2" },
  ],
  created_by_user_id: null,
  destination_bucket_code: null,
  document_type: "COUNTER_TRANSFER",
  records: [
    {
      committed_at_utc: "2026-04-22T18:10:00Z",
      created_at_utc: "2026-04-22T18:08:00Z",
      created_by_user_full_name: "Main Branch Cashier",
      created_by_user_id: "user-1",
      destination_branch_code: null,
      destination_branch_name: null,
      destination_bucket_code: "COUNTER",
      document_type: "COUNTER_TRANSFER",
      folio: "CTR-000001",
      id: "operation-1",
      line_count: 1,
      source_branch_code: "MAIN",
      source_branch_name: "Main Branch",
      source_bucket_code: "BACKROOM",
      status: "COMMITTED",
      total_quantity: "2.000",
      workstation_code: "POS-01",
      workstation_name: "Front Register 01",
    },
    {
      committed_at_utc: "2026-04-22T21:15:00Z",
      created_at_utc: "2026-04-22T21:10:00Z",
      created_by_user_full_name: "Main Branch Cashier",
      created_by_user_id: "user-1",
      destination_branch_code: null,
      destination_branch_name: null,
      destination_bucket_code: "COUNTER",
      document_type: "COUNTER_TRANSFER",
      folio: "CTR-000002",
      id: "operation-2",
      line_count: 2,
      source_branch_code: "MAIN",
      source_branch_name: "Main Branch",
      source_bucket_code: "BACKROOM",
      status: "COMMITTED",
      total_quantity: "4.000",
      workstation_code: "POS-01",
      workstation_name: "Front Register 01",
    },
    {
      committed_at_utc: "2026-04-23T04:10:00Z",
      created_at_utc: "2026-04-23T04:08:00Z",
      created_by_user_full_name: "Night Cashier",
      created_by_user_id: "user-2",
      destination_branch_code: null,
      destination_branch_name: null,
      destination_bucket_code: "COUNTER",
      document_type: "COUNTER_TRANSFER",
      folio: "CTR-000003",
      id: "operation-3",
      line_count: 1,
      source_branch_code: "MAIN",
      source_branch_name: "Main Branch",
      source_bucket_code: "BACKROOM",
      status: "COMMITTED",
      total_quantity: "1.000",
      workstation_code: "POS-01",
      workstation_name: "Front Register 01",
    },
  ],
  scope: "CURRENT_SHIFT",
  source_bucket_code: null,
  workstation_code: "POS-01",
} as const;

const counterTransferDocument: OperationDocumentView = {
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

const wasteHistoryResponse = {
  available_destination_buckets: [{ label: "WASTE", value: "WASTE" }],
  available_products: [{ label: "BOL-STD · Standard Bolillo", value: "product-1" }],
  available_reasons: [{ label: "Old counter", value: "OLD_COUNTER" }],
  available_scopes: [
    { code: "ALL", label: "Todos" },
    { code: "CURRENT_SHIFT", label: "Turno actual" },
    { code: "TODAY", label: "Hoy" },
    { code: "RECENT", label: "Recientes" },
  ],
  available_source_buckets: [{ label: "COUNTER", value: "COUNTER" }],
  available_users: [{ label: "Main Branch Cashier", value: "user-1" }],
  created_by_user_id: null,
  destination_bucket_code: null,
  document_type: "WASTE_RECORD",
  product_id: null,
  reason_code: null,
  records: [
    {
      committed_at_utc: "2026-04-22T19:10:00Z",
      created_at_utc: "2026-04-22T19:08:00Z",
      created_by_user_full_name: "Main Branch Cashier",
      created_by_user_id: "user-1",
      destination_branch_code: null,
      destination_branch_name: null,
      destination_bucket_code: "WASTE",
      document_type: "WASTE_RECORD",
      folio: "WST-000001",
      id: "waste-1",
      line_count: 1,
      reason_code: "OLD_COUNTER",
      reason_name: "Old counter",
      source_branch_code: "MAIN",
      source_branch_name: "Main Branch",
      source_bucket_code: "COUNTER",
      status: "COMMITTED",
      total_quantity: "2.000",
      workstation_code: "POS-01",
      workstation_name: "Front Register 01",
    },
  ],
  scope: "CURRENT_SHIFT",
  source_bucket_code: null,
  workstation_code: "POS-01",
} as const;

const wasteDocument: OperationDocumentView = {
  committed_at_utc: "2026-04-22T19:10:00Z",
  created_at_utc: "2026-04-22T19:08:00Z",
  created_by_user_email: "cashier@zeromerma.local",
  created_by_user_full_name: "Main Branch Cashier",
  created_by_user_id: "user-1",
  destination_branch_code: null,
  destination_branch_id: null,
  destination_branch_name: null,
  destination_bucket_code: "WASTE",
  document_type: "WASTE_RECORD",
  folio: "WST-000001",
  id: "waste-1",
  lines: [
    {
      expected_quantity: null,
      id: "waste-line-1",
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
  notes: "Morning waste review",
  reason_code: "OLD_COUNTER",
  reason_name: "Old counter",
  reference_document_id: null,
  source_branch_code: "MAIN",
  source_branch_id: "branch-1",
  source_branch_name: "Main Branch",
  source_bucket_code: "COUNTER",
  status: "COMMITTED",
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
  useCashCloseReconciliationQuery: () => ({
    data: mockCounterAvailabilityData,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock("../status-messages/store", () => ({
  useStatusMessageStore: (
    selector: (state: {
      pushMessage: typeof pushMessageMock;
      showError: typeof showErrorMock;
      showSuccess: typeof showSuccessMock;
      showWarning: typeof showWarningMock;
    }) => unknown,
  ) =>
    selector({
      pushMessage: pushMessageMock,
      showError: showErrorMock,
      showSuccess: showSuccessMock,
      showWarning: showWarningMock,
    }),
}));

vi.mock("./queries", () => ({
  operationDocumentQueryKey: vi.fn(),
  operationHistoryQueryKey: vi.fn(),
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
                unit_price: "12.00",
              },
            ],
          }
        : undefined,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useOperationDocumentQuery: (documentId: string | null) => ({
    data:
      documentId === "operation-1"
        ? counterTransferDocument
        : documentId === "waste-1"
          ? wasteDocument
          : null,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useOperationHistoryQuery: (documentType: string, _filters: unknown, enabled = true) => ({
    data:
      enabled && documentType === "WASTE_RECORD"
        ? wasteHistoryResponse
        : enabled
          ? counterTransferHistoryResponse
          : undefined,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock("./operations-api", () => ({
  commitCounterTransfer: vi.fn(),
  commitWasteRecord: vi.fn(),
}));

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

function changeInput(element: HTMLInputElement | null, value: string) {
  if (!element) {
    throw new Error("Expected input element to exist.");
  }

  act(() => {
    const valueSetter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    )?.set;
    valueSetter?.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function renderUi(variant: "counterTransfer" | "waste" = "counterTransfer") {
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
        <KeyboardShortcutRegistry>
          <>
            <OperationModuleScreen variant={variant} />
            <AppShellRightPanelProbe />
          </>
        </KeyboardShortcutRegistry>
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
  });
}

async function addCounterTransferLine(container: HTMLElement) {
  const classButton = Array.from(container.querySelectorAll("button")).find((button) =>
    button.textContent?.includes("Pan dulce"),
  );
  keydown(classButton, "Enter");

  const productButton = Array.from(container.querySelectorAll("button")).find((button) =>
    button.textContent?.includes("Concha vainilla"),
  );
  keydown(productButton, "Enter");

  const quantityInput = container.querySelector<HTMLInputElement>('input[aria-label="Cantidad"]');
  changeInput(quantityInput, "2");
  await flush();
  keydown(quantityInput, "Enter");
  await flush();
}

function findCounterTransferPrimaryButton(scope: ParentNode) {
  return Array.from(scope.querySelectorAll("button")).find((button) =>
    button.textContent?.includes("Transferir") || button.textContent?.includes("Confirmar traspaso"),
  ) as HTMLButtonElement | undefined;
}

async function addWasteLine(
  container: HTMLElement,
  options?: {
    notes?: string;
    quantity?: string;
    reasonLabel?: string;
    sourceLabel?: string;
  },
) {
  const sourceLabel = options?.sourceLabel ?? "Mostrador";
  const reasonLabel = options?.reasonLabel ?? "Producto rezagado";
  const quantity = options?.quantity ?? "2";
  const originButton = Array.from(container.querySelectorAll("button")).find((button) =>
    button.textContent?.includes(sourceLabel),
  ) as HTMLButtonElement | undefined;
  originButton?.focus();
  keydown(originButton, "Enter");
  await flush();

  const firstReasonButton = Array.from(container.querySelectorAll("button")).find((button) =>
    button.textContent?.includes(reasonLabel),
  ) as HTMLButtonElement | undefined;
  firstReasonButton?.focus();
  keydown(firstReasonButton, "Enter");
  await flush();

  const classButton = Array.from(container.querySelectorAll("button")).find((button) =>
    button.textContent?.includes("Pan dulce"),
  );
  keydown(classButton, "Enter");
  await flush();

  const productButton = Array.from(container.querySelectorAll("button")).find((button) =>
    button.textContent?.includes("Concha vainilla"),
  );
  keydown(productButton, "Enter");
  await flush();

  const quantityInput = container.querySelector<HTMLInputElement>('input[aria-label="Cantidad"]');
  changeInput(quantityInput, quantity);
  await flush();
  keydown(quantityInput, "Enter");
  await flush();

  if (options?.notes) {
    const notesInput = container.querySelector<HTMLTextAreaElement>(
      'textarea[placeholder="Observacion opcional"]',
    );
    if (!notesInput) {
      throw new Error("Expected notes textarea to exist.");
    }

    act(() => {
      const valueSetter = Object.getOwnPropertyDescriptor(
        HTMLTextAreaElement.prototype,
        "value",
      )?.set;
      valueSetter?.call(notesInput, options.notes);
      notesInput.dispatchEvent(new Event("input", { bubbles: true }));
      notesInput.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await flush();
  }
}

let mountedRoots: Array<() => void> = [];

beforeEach(() => {
  rightPanelContent = null;
  mockCounterAvailabilityData = {
    counter_class_availability: [
      {
        available_quantity: "5.000",
        expected_quantity_before_deferred_attr: "5.000",
        pending_class_capture_quantity: "0.000",
        product_class_code: "PAN-DULCE",
        product_class_id: "class-1",
        product_class_name: "Pan dulce",
      },
    ],
    relevant_products: [
      {
        counted_quantity: null,
        discrepancy_quantity: null,
        expected_quantity_before_deferred_attr: "5.000",
        final_expected_quantity: "5.000",
        notes: null,
        product_class_code: "PAN-DULCE",
        product_class_id: "class-1",
        product_class_name: "Pan dulce",
        product_code: "CONCHA-VAN",
        product_id: "product-1",
        product_name: "Concha vainilla",
      },
    ],
  };
  showErrorMock.mockReset();
  pushMessageMock.mockReset();
  showSuccessMock.mockReset();
  showWarningMock.mockReset();
  vi.mocked(commitCounterTransfer).mockReset();
  vi.mocked(commitWasteRecord).mockReset();
  vi.mocked(commitCounterTransfer).mockResolvedValue(counterTransferDocument);
  vi.mocked(commitWasteRecord).mockResolvedValue(wasteDocument);
});

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("OperationModuleScreen counter transfer", () => {
  it("shows a warning toast when trying to transfer without lines", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const registerButton = findCounterTransferPrimaryButton(rightPanel ?? view.container);
    expect(registerButton?.disabled).toBe(false);

    click(registerButton ?? null);
    await flush();

    expect(showWarningMock).toHaveBeenCalledWith(
      "Agrega al menos una linea para registrar el traspaso.",
    );
    expect(commitCounterTransfer).not.toHaveBeenCalled();
  });

  it("opens and cancels confirmation without persisting", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await addCounterTransferLine(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const transferButton = findCounterTransferPrimaryButton(rightPanel ?? view.container);
    click(transferButton ?? null);
    await flush();

    expect(view.container.textContent).toContain("Confirmar traspaso a mostrador");

    const cancelButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Cancelar"),
    );
    click(cancelButton ?? null);
    await flush();

    expect(view.container.textContent).not.toContain("Confirmar traspaso a mostrador");
    expect(commitCounterTransfer).not.toHaveBeenCalled();
  });

  it("registers a transfer and returns to a fresh draft with success toast", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await addCounterTransferLine(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const transferButton = findCounterTransferPrimaryButton(rightPanel ?? view.container);
    click(transferButton ?? null);
    await flush();

    const confirmButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Confirmar traspaso"),
    );
    click(confirmButton ?? null);
    await flush();

    expect(commitCounterTransfer).toHaveBeenCalledWith("token", {
      lines: [{ product_id: "product-1", quantity: "2" }],
      notes: null,
      workstation_code: "POS-01",
    });
    expect(showSuccessMock).toHaveBeenCalledWith("Traspaso registrado. Folio CTR-000001.");
    expect(rightPanel?.textContent).toContain("Nuevo traspaso");
    expect(rightPanel?.textContent).toContain("Aun no hay lineas");
    expect(rightPanel?.textContent).toContain("Ver historial");
  });

  it("navigates to the history view", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const historyButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Ver historial"),
    );
    click(historyButton ?? null);
    await flush();

    expect(view.container.textContent).toContain("Historial de traspasos");
    expect(view.container.textContent).toContain("Historial del mostrador");
    expect(view.container.textContent).toContain("CTR-000001");
    expect(
      view.container.querySelector('[aria-label="Historial de traspasos a mostrador"]'),
    ).not.toBeNull();
    expect(view.container.textContent).toContain("Main Branch Cashier");
    expect(view.container.textContent).toContain("Todo el dia");
    expect(view.container.textContent).toContain("Manana");
    expect(view.container.textContent).toContain("Tarde");
    expect(view.container.textContent).toContain("Noche");
  });

  it("supports inline quantity editing from the draft panel", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await addCounterTransferLine(view.container);

    const editButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.getAttribute("aria-label")?.includes("Editar cantidad de Concha vainilla"),
    ) as HTMLButtonElement | undefined;
    click(editButton ?? null);
    await flush();

    const quantityInput = view.container.querySelector<HTMLInputElement>(
      'input[aria-label="Cantidad de Concha vainilla"]',
    );
    changeInput(quantityInput, "5");
    await flush();
    keydown(quantityInput, "Enter");
    await flush();

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    expect(rightPanel?.textContent).toContain("5");

    const transferButton = findCounterTransferPrimaryButton(rightPanel ?? view.container);
    click(transferButton ?? null);
    await flush();

    const confirmButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Confirmar traspaso"),
    );
    click(confirmButton ?? null);
    await flush();

    expect(commitCounterTransfer).toHaveBeenCalledWith("token", {
      lines: [{ product_id: "product-1", quantity: "5" }],
      notes: null,
      workstation_code: "POS-01",
    });
  });

  it("supports the keyboard path to select class, product, and add quantity", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await addCounterTransferLine(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    expect(rightPanel?.textContent).toContain("Concha vainilla");
    expect(rightPanel?.textContent).not.toContain("Pan dulce");
    expect(view.container.querySelector('input[aria-label="Cantidad"]')).toBeNull();
  });

  it("cancels quantity capture and returns to the product flow", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const classButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Pan dulce"),
    );
    keydown(classButton, "Enter");
    await flush();

    const productButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Concha vainilla"),
    );
    keydown(productButton, "Enter");
    await flush();

    const quantityInput = view.container.querySelector<HTMLInputElement>('input[aria-label="Cantidad"]');
    expect(quantityInput).not.toBeNull();
    keydown(quantityInput, "Escape");
    await flush();

    expect(view.container.querySelector('input[aria-label="Cantidad"]')).toBeNull();
    expect(view.container.textContent).toContain("Concha vainilla");
  });

  it("supports Ctrl+Enter to confirm the final transfer", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await addCounterTransferLine(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const transferButton = findCounterTransferPrimaryButton(rightPanel ?? view.container);
    click(transferButton ?? null);
    await flush();

    keydown(window, "Enter", { ctrlKey: true });
    await flush();

    expect(commitCounterTransfer).toHaveBeenCalledTimes(1);
    expect(showSuccessMock).toHaveBeenCalledWith("Traspaso registrado. Folio CTR-000001.");
  });

  it("shows the real counter table after a successful transfer", async () => {
    mockCounterAvailabilityData = {
      counter_class_availability: [
        {
          available_quantity: "5.000",
          expected_quantity_before_deferred_attr: "5.000",
          pending_class_capture_quantity: "0.000",
          product_class_code: "BOLILLO",
          product_class_id: "class-2",
          product_class_name: "Bolillo",
        },
      ],
      relevant_products: [
        {
          counted_quantity: null,
          discrepancy_quantity: null,
          expected_quantity_before_deferred_attr: "5.000",
          final_expected_quantity: "5.000",
          notes: null,
          product_class_code: "BOLILLO",
          product_class_id: "class-2",
          product_class_name: "Bolillo",
          product_code: "BOL-MOS",
          product_id: "product-counter-1",
          product_name: "Bolillo de mostrador",
        },
      ],
    };

    const view = renderUi();
    mountedRoots.push(view.unmount);
    await addCounterTransferLine(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const transferButton = findCounterTransferPrimaryButton(rightPanel ?? view.container);
    click(transferButton ?? null);
    await flush();

    const confirmButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Confirmar traspaso"),
    );
    click(confirmButton ?? null);
    await flush();

    const availabilityTable = view.container.querySelector(
      '[aria-label="Clases y productos actualmente en mostrador"]',
    );
    expect(availabilityTable).not.toBeNull();
    expect(availabilityTable?.textContent).toContain("Bolillo");
    expect(availabilityTable?.textContent).toContain("Bolillo de mostrador");
  });
});

describe("OperationModuleScreen waste", () => {
  it("cannot register without origin, reason, and lines", async () => {
    const view = renderUi("waste");
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    expect(view.container.textContent).toContain("Contexto de la merma");
    expect(view.container.textContent).toContain("Origen pendiente");
    expect(view.container.textContent).toContain("Motivo pendiente");
    expect(view.container.textContent).toContain("Buscar producto o clase");
    expect(view.container.textContent).toContain("Selecciona origen y motivo para capturar productos.");
    expect(rightPanel?.textContent).toContain("Selecciona origen y motivo para continuar.");
    expect(rightPanel?.textContent).toContain("Agrega productos para construir el documento.");

    const classCards = Array.from(
      view.container.querySelectorAll<HTMLButtonElement>('button[data-pos-catalog-card="true"]'),
    );
    expect(classCards.length).toBeGreaterThan(0);
    expect(classCards.every((button) => button.disabled)).toBe(true);

    const registerButton = Array.from(rightPanel?.querySelectorAll("button") ?? []).find((button) =>
      button.textContent?.includes("Registrar merma"),
    ) as HTMLButtonElement | undefined;

    expect(registerButton?.disabled).toBe(true);
  });

  it("supports keyboard origin and reason selection", async () => {
    const view = renderUi("waste");
    mountedRoots.push(view.unmount);
    await flush();

    const originButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Mostrador"),
    ) as HTMLButtonElement | undefined;
    originButton?.focus();
    keydown(originButton, "ArrowRight");
    await flush();
    keydown(document.activeElement, "Enter");

    const reasonButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Producto rezagado"),
    ) as HTMLButtonElement | undefined;
    reasonButton?.focus();
    keydown(reasonButton, "ArrowRight");
    await flush();
    keydown(document.activeElement, "Enter");
    await flush();

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    expect(rightPanel?.textContent).toContain("Fondo");
    expect(rightPanel?.textContent).toContain("Danado");

    const classButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Pan dulce"),
    ) as HTMLButtonElement | undefined;
    expect(classButton?.disabled).toBe(false);
  });

  it("registers waste directly without opening a confirmation dialog", async () => {
    const view = renderUi("waste");
    mountedRoots.push(view.unmount);
    await addWasteLine(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const registerButton = Array.from(rightPanel?.querySelectorAll("button") ?? []).find((button) =>
      button.textContent?.includes("Registrar merma"),
    );
    click(registerButton ?? null);
    await flush();

    expect(view.container.textContent).not.toContain("Confirmar merma");
    expect(commitWasteRecord).toHaveBeenCalledWith("token", {
      high_impact_acknowledged: false,
      lines: [{ product_id: "product-1", quantity: "2" }],
      notes: null,
      reason_code: "OLD_COUNTER",
      source_bucket_code: "COUNTER",
      workstation_code: "POS-01",
    });
  });

  it("registers waste and shows success folio with history access", async () => {
    const view = renderUi("waste");
    mountedRoots.push(view.unmount);
    await addWasteLine(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const registerButton = Array.from(rightPanel?.querySelectorAll("button") ?? []).find((button) =>
      button.textContent?.includes("Registrar merma"),
    );
    click(registerButton ?? null);
    await flush();

    expect(commitWasteRecord).toHaveBeenCalledWith("token", {
      high_impact_acknowledged: false,
      lines: [{ product_id: "product-1", quantity: "2" }],
      notes: null,
      reason_code: "OLD_COUNTER",
      source_bucket_code: "COUNTER",
      workstation_code: "POS-01",
    });
    expect(showSuccessMock).toHaveBeenCalledWith("Merma registrada. Folio WST-000001.");
    expect(rightPanel?.textContent).toContain("Ver historial");

    const historyButton = Array.from(rightPanel?.querySelectorAll("button") ?? []).find((button) =>
      button.textContent?.includes("Ver historial"),
    );
    click(historyButton ?? null);
    await flush();

    expect(view.container.textContent).toContain("Historial de merma");
    expect(view.container.textContent).toContain("WST-000001");
  });

  it("blocks waste when quantity exceeds expected counter stock", async () => {
    mockCounterAvailabilityData = {
      counter_class_availability: [
        {
          available_quantity: "1.000",
          expected_quantity_before_deferred_attr: "1.000",
          pending_class_capture_quantity: "0.000",
          product_class_code: "PAN-DULCE",
          product_class_id: "class-1",
          product_class_name: "Pan dulce",
        },
      ],
      relevant_products: [
        {
          counted_quantity: null,
          discrepancy_quantity: null,
          expected_quantity_before_deferred_attr: "1.000",
          final_expected_quantity: "1.000",
          notes: null,
          product_class_code: "PAN-DULCE",
          product_class_id: "class-1",
          product_class_name: "Pan dulce",
          product_code: "CONCHA-VAN",
          product_id: "product-1",
          product_name: "Concha vainilla",
        },
      ],
    };

    const view = renderUi("waste");
    mountedRoots.push(view.unmount);
    await addWasteLine(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    expect(rightPanel?.textContent).toContain("excede el saldo esperado en mostrador");

    const registerButton = Array.from(rightPanel?.querySelectorAll("button") ?? []).find((button) =>
      button.textContent?.includes("Registrar merma"),
    ) as HTMLButtonElement | undefined;
    expect(registerButton?.disabled).toBe(true);
  });

  it("requires notes for reasons that need evidence", async () => {
    const view = renderUi("waste");
    mountedRoots.push(view.unmount);
    const originButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Mostrador"),
    );
    click(originButton ?? null);
    await flush();

    const reasonButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Danado"),
    );
    click(reasonButton ?? null);
    await flush();

    const classButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Pan dulce"),
    );
    keydown(classButton, "Enter");
    await flush();

    const productButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Concha vainilla"),
    );
    keydown(productButton, "Enter");
    await flush();

    const quantityInput = view.container.querySelector<HTMLInputElement>('input[aria-label="Cantidad"]');
    changeInput(quantityInput, "2");
    await flush();
    keydown(quantityInput, "Enter");
    await flush();

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    expect(rightPanel?.textContent).toContain(
      "Agrega notas operativas para documentar la evidencia.",
    );

    const registerButton = Array.from(rightPanel?.querySelectorAll("button") ?? []).find((button) =>
      button.textContent?.includes("Registrar merma"),
    ) as HTMLButtonElement | undefined;
    expect(registerButton?.disabled).toBe(true);
  });

  it("requires high-impact acknowledgement and passes it to the backend", async () => {
    mockCounterAvailabilityData = {
      counter_class_availability: [
        {
          available_quantity: "20.000",
          expected_quantity_before_deferred_attr: "20.000",
          pending_class_capture_quantity: "0.000",
          product_class_code: "PAN-DULCE",
          product_class_id: "class-1",
          product_class_name: "Pan dulce",
        },
      ],
      relevant_products: [
        {
          counted_quantity: null,
          discrepancy_quantity: null,
          expected_quantity_before_deferred_attr: "20.000",
          final_expected_quantity: "20.000",
          notes: null,
          product_class_code: "PAN-DULCE",
          product_class_id: "class-1",
          product_class_name: "Pan dulce",
          product_code: "CONCHA-VAN",
          product_id: "product-1",
          product_name: "Concha vainilla",
        },
      ],
    };

    const view = renderUi("waste");
    mountedRoots.push(view.unmount);
    await addWasteLine(view.container, {
      notes: "Large high-impact waste batch.",
      quantity: "12",
    });

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    expect(rightPanel?.textContent).toContain("Confirma la merma de alto impacto antes de registrar.");

    const acknowledgement = view.container.querySelector<HTMLInputElement>('input[type="checkbox"]');
    if (!acknowledgement) {
      throw new Error("Expected high-impact acknowledgement checkbox.");
    }

    act(() => {
      acknowledgement.click();
    });
    await flush();

    const registerButton = Array.from(rightPanel?.querySelectorAll("button") ?? []).find((button) =>
      button.textContent?.includes("Registrar merma"),
    );
    click(registerButton ?? null);
    await flush();

    expect(commitWasteRecord).toHaveBeenCalledWith("token", {
      high_impact_acknowledged: true,
      lines: [{ product_id: "product-1", quantity: "12" }],
      notes: "Large high-impact waste batch.",
      reason_code: "OLD_COUNTER",
      source_bucket_code: "COUNTER",
      workstation_code: "POS-01",
    });
    expect(showSuccessMock).toHaveBeenCalledWith(
      "Merma registrada. Folio WST-000001. Se preparo alerta para backoffice.",
    );
  });
});
