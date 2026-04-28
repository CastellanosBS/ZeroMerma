// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, useSyncExternalStore, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  OperationHistoryFilterOptionView,
  OperationHistoryScopeView,
  PendingInboundTransfersResponse,
  TransferDetailResponse,
  TransferReceiptHistoryResponse,
} from "../../lib/api-contracts";
import { KeyboardShortcutRegistry } from "../pos-shell/keyboard";
import { TransferReceiptScreen } from "./receipt-screen";
import { receiveTransfer } from "./transfers-api";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const refetchMock = vi.fn();
const showErrorMock = vi.fn();
const showSuccessMock = vi.fn();
let rightPanelContent: ReactNode = null;
const rightPanelListeners = new Set<() => void>();

const bootstrapResponse = {
  branch: {
    code: "NORTH",
    id: "branch-2",
    is_active: true,
    name: "North Branch",
    timezone: "America/Hermosillo",
  },
  branch_brand_key: "EL_MEJOR_PAN",
  destination_branches: [],
  local_timestamp: "2026-04-22T18:00:00Z",
  user: {
    email: "cashier@zeromerma.local",
    full_name: "North Branch Cashier",
    id: "user-1",
    is_active: true,
  },
  waste_reasons: [],
  workstation: {
    code: "POS-01",
    id: "workstation-1",
    is_active: true,
    name: "Front Register 01",
  },
} as const;

const historyScopes: OperationHistoryScopeView[] = [
  { code: "CURRENT_SHIFT", label: "Turno actual" },
  { code: "TODAY", label: "Hoy" },
  { code: "RECENT", label: "Recientes" },
];

const historyUsers: OperationHistoryFilterOptionView[] = [
  { label: "North Branch Cashier", value: "user-1" },
];

const historySourceBranches: OperationHistoryFilterOptionView[] = [
  { label: "Main Branch", value: "branch-1" },
];

const historyStatuses: OperationHistoryFilterOptionView[] = [
  { label: "Recibido", value: "RECEIVED" },
  { label: "Recibido con diferencia", value: "RECEIVED_WITH_VARIANCE" },
];

const pendingInboundTransfersResponse: PendingInboundTransfersResponse = {
  workstation_code: "POS-01",
  transfers: [
    {
      committed_at_utc: "2026-04-22T18:12:00Z",
      created_at_utc: "2026-04-22T18:10:00Z",
      destination_branch_code: "NORTH",
      destination_branch_id: "branch-2",
      destination_branch_name: "North Branch",
      expected_total_quantity: "3.000",
      folio: "ENV-000001",
      id: "transfer-1",
      line_count: 1,
      source_branch_code: "MAIN",
      source_branch_id: "branch-1",
      source_branch_name: "Main Branch",
      status: "IN_TRANSIT",
      workstation_code: "POS-01",
      workstation_id: "workstation-1",
      workstation_name: "Front Register 01",
    },
  ],
};

const pendingTransferDetail: TransferDetailResponse = {
  receipt: null,
  receipt_summary: null,
  shipment: {
    committed_at_utc: "2026-04-22T18:12:00Z",
    created_at_utc: "2026-04-22T18:10:00Z",
    created_by_user_email: "cashier@zeromerma.local",
    created_by_user_full_name: "North Branch Cashier",
    created_by_user_id: "user-1",
    destination_branch_code: "NORTH",
    destination_branch_id: "branch-2",
    destination_branch_name: "North Branch",
    destination_bucket_code: "BACKROOM",
    document_type: "BRANCH_TRANSFER_SHIPMENT",
    folio: "ENV-000001",
    id: "transfer-1",
    lines: [
      {
        expected_quantity: "3.000",
        id: "transfer-line-1",
        line_number: 1,
        notes: null,
        product_class_code_snapshot: "PAN-DULCE",
        product_class_id: "class-1",
        product_class_name_snapshot: "Pan dulce",
        product_code_snapshot: "CONCHA-VAN",
        product_id: "product-1",
        product_name_snapshot: "Concha vainilla",
        quantity: "3.000",
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
    source_bucket_code: "IN_TRANSIT",
    status: "IN_TRANSIT",
    workstation_code: "POS-01",
    workstation_id: "workstation-1",
    workstation_name: "Front Register 01",
  },
  shipment_summary: {
    committed_at_utc: "2026-04-22T18:12:00Z",
    document_id: "transfer-1",
    folio: "ENV-000001",
    linked_shipment_id: null,
    quantity_summary: {
      expected_total_quantity: "3.000",
      has_variance: false,
      line_count: 1,
      received_total_quantity: null,
      variance_line_count: 0,
    },
    status: "IN_TRANSIT",
  },
};

const receivedTransferDetail: TransferDetailResponse = {
  receipt: {
    committed_at_utc: "2026-04-22T18:20:00Z",
    created_at_utc: "2026-04-22T18:20:00Z",
    created_by_user_email: "cashier@zeromerma.local",
    created_by_user_full_name: "North Branch Cashier",
    created_by_user_id: "user-1",
    destination_branch_code: "NORTH",
    destination_branch_id: "branch-2",
    destination_branch_name: "North Branch",
    destination_bucket_code: "BACKROOM",
    document_type: "BRANCH_TRANSFER_RECEIPT",
    folio: "REC-000001",
    id: "receipt-1",
    lines: [
      {
        expected_quantity: "3.000",
        id: "receipt-line-1",
        line_number: 1,
        notes: null,
        product_class_code_snapshot: "PAN-DULCE",
        product_class_id: "class-1",
        product_class_name_snapshot: "Pan dulce",
        product_code_snapshot: "CONCHA-VAN",
        product_id: "product-1",
        product_name_snapshot: "Concha vainilla",
        quantity: "3.000",
        received_quantity: "3.000",
        unit_of_measure_code: "EACH",
        variance_reason: null,
      },
    ],
    notes: null,
    reason_code: null,
    reason_name: null,
    reference_document_id: "transfer-1",
    source_branch_code: "MAIN",
    source_branch_id: "branch-1",
    source_branch_name: "Main Branch",
    source_bucket_code: "IN_TRANSIT",
    status: "RECEIVED",
    workstation_code: "POS-01",
    workstation_id: "workstation-1",
    workstation_name: "Front Register 01",
  },
  receipt_summary: {
    committed_at_utc: "2026-04-22T18:20:00Z",
    document_id: "receipt-1",
    folio: "REC-000001",
    linked_shipment_id: "transfer-1",
    quantity_summary: {
      expected_total_quantity: "3.000",
      has_variance: false,
      line_count: 1,
      received_total_quantity: "3.000",
      variance_line_count: 0,
    },
    status: "RECEIVED",
  },
  shipment: {
    ...pendingTransferDetail.shipment,
    status: "RECEIVED",
  },
  shipment_summary: {
    ...pendingTransferDetail.shipment_summary,
    status: "RECEIVED",
  },
};

const receiptHistoryResponse: TransferReceiptHistoryResponse = {
  available_scopes: historyScopes,
  available_source_branches: historySourceBranches,
  available_statuses: historyStatuses,
  available_users: historyUsers,
  created_by_user_id: null,
  records: [
    {
      committed_at_utc: "2026-04-22T18:20:00Z",
      created_at_utc: "2026-04-22T18:20:00Z",
      created_by_user_full_name: "North Branch Cashier",
      created_by_user_id: "user-1",
      destination_branch_code: "NORTH",
      destination_branch_name: "North Branch",
      destination_bucket_code: "BACKROOM",
      document_type: "BRANCH_TRANSFER_RECEIPT",
      folio: "REC-000001",
      id: "transfer-1",
      line_count: 1,
      source_branch_code: "MAIN",
      source_branch_name: "Main Branch",
      source_bucket_code: "IN_TRANSIT",
      status: "RECEIVED",
      total_quantity: "3.000",
      workstation_code: "POS-01",
      workstation_name: "Front Register 01",
    },
  ],
  scope: "CURRENT_SHIFT",
  source_branch_id: null,
  status: null,
  workstation_code: "POS-01",
};

let pendingInboundResponseState: PendingInboundTransfersResponse = pendingInboundTransfersResponse;
let activeTransferDetailState: TransferDetailResponse | null = pendingTransferDetail;
let receiptHistoryResponseState: TransferReceiptHistoryResponse = receiptHistoryResponse;

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
  useOperationsBootstrapQuery: () => ({
    data: bootstrapResponse,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock("./queries", () => ({
  usePendingInboundTransfersQuery: () => ({
    data: pendingInboundResponseState,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useTransferDetailQuery: (transferId: string | null) => ({
    data: transferId === null ? undefined : activeTransferDetailState,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useTransferReceiptHistoryQuery: (_filters: unknown, enabled = true) => ({
    data: enabled ? receiptHistoryResponseState : undefined,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  pendingInboundTransfersQueryKey: (workstationCode: string) => [
    "pending-inbound-transfers",
    workstationCode,
  ],
  transferDetailQueryKey: (workstationCode: string, transferId: string) => [
    "transfer-detail",
    workstationCode,
    transferId,
  ],
  transferReceiptHistoryQueryKey: (workstationCode: string, filters: unknown) => [
    "transfer-receipt-history",
    workstationCode,
    filters,
  ],
}));

vi.mock("./transfers-api", () => ({
  receiveTransfer: vi.fn(),
}));

function click(element: Element | undefined | null) {
  if (!element) {
    throw new Error("Expected element to exist.");
  }

  act(() => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function keydown(element: Element | Window | undefined | null, key: string) {
  if (!element) {
    throw new Error(`Expected target for key ${key}.`);
  }

  act(() => {
    element.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key }));
  });
}

function focus(element: HTMLElement | null) {
  if (!element) {
    throw new Error("Expected focus target to exist.");
  }

  act(() => {
    element.focus();
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

async function flush() {
  await act(async () => {
    await Promise.resolve();
  });
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
        <KeyboardShortcutRegistry>
          <>
            <TransferReceiptScreen />
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

function findButtonByText(container: ParentNode, text: string): HTMLButtonElement | undefined {
  return Array.from(container.querySelectorAll("button")).find((button) =>
    button.textContent?.includes(text),
  ) as HTMLButtonElement | undefined;
}

function findButtonByExactText(
  container: ParentNode,
  text: string,
): HTMLButtonElement | undefined {
  return Array.from(container.querySelectorAll("button")).find(
    (button) => button.textContent?.trim() === text,
  ) as HTMLButtonElement | undefined;
}

function findInputByLabel(container: ParentNode, label: string): HTMLInputElement | null {
  return container.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`);
}

async function selectPendingShipmentWithKeyboard(container: HTMLElement) {
  const shipmentButton = findButtonByText(container, "ENV-000001");
  focus(shipmentButton ?? null);
  keydown(shipmentButton, "Enter");
  await flush();
}

let mountedRoots: Array<() => void> = [];

beforeEach(() => {
  rightPanelContent = null;
  showErrorMock.mockReset();
  showSuccessMock.mockReset();
  refetchMock.mockReset();
  pendingInboundResponseState = pendingInboundTransfersResponse;
  activeTransferDetailState = pendingTransferDetail;
  receiptHistoryResponseState = receiptHistoryResponse;
  vi.mocked(receiveTransfer).mockReset();
  vi.mocked(receiveTransfer).mockImplementation(async () => {
    pendingInboundResponseState = {
      workstation_code: "POS-01",
      transfers: [],
    };
    activeTransferDetailState = receivedTransferDetail;
    return receivedTransferDetail;
  });
});

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("TransferReceiptScreen", () => {
  it("shows an empty pending state when there are no inbound shipments", async () => {
    pendingInboundResponseState = {
      workstation_code: "POS-01",
      transfers: [],
    };
    activeTransferDetailState = null;

    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    expect(view.container.textContent).toContain("No hay envios pendientes para esta sucursal.");
    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    expect(rightPanel?.textContent).toContain("No hay envios pendientes para esta sucursal.");
  });

  it("supports keyboard selection and quantity entry for a pending shipment", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    await selectPendingShipmentWithKeyboard(view.container);

    const receivedInput = findInputByLabel(
      view.container,
      "Cantidad recibida de Concha vainilla",
    );
    expect(document.activeElement).toBe(receivedInput);

    changeInput(receivedInput, "2");
    await flush();

    expect(receivedInput?.value).toBe("2");
    expect(view.container.textContent).toContain("Faltan 1");
  });

  it("opens an exact pending shipment from scanner input", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const scannerInput = findInputByLabel(view.container, "Escanear folio de envio");
    changeInput(scannerInput, "env-000001");
    keydown(scannerInput, "Enter");
    await flush();

    const receivedInput = findInputByLabel(
      view.container,
      "Cantidad recibida de Concha vainilla",
    );

    expect(receivedInput).not.toBeNull();
    expect(document.activeElement).toBe(receivedInput);
  });

  it("blocks confirmation when a variance reason is missing", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    await selectPendingShipmentWithKeyboard(view.container);

    const receivedInput = findInputByLabel(
      view.container,
      "Cantidad recibida de Concha vainilla",
    );
    changeInput(receivedInput, "2");
    await flush();

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const confirmButton = findButtonByText(rightPanel ?? document, "Confirmar recepcion");

    expect(rightPanel?.textContent).toContain("Revisa las lineas con diferencia.");
    expect(confirmButton?.disabled).toBe(true);
    expect(receiveTransfer).not.toHaveBeenCalled();
  });

  it("cancels receipt confirmation without persisting", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    await selectPendingShipmentWithKeyboard(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const confirmButton = findButtonByText(rightPanel ?? document, "Confirmar recepcion");
    click(confirmButton ?? null);
    await flush();

    expect(view.container.textContent).toContain(
      "La recepcion quedara confirmada y el envio se cerrara sin diferencias.",
    );

    const cancelButton = findButtonByText(view.container, "Cancelar");
    click(cancelButton ?? null);
    await flush();

    expect(view.container.textContent).not.toContain(
      "La recepcion quedara confirmada y el envio se cerrara sin diferencias.",
    );
    expect(receiveTransfer).not.toHaveBeenCalled();
  });

  it("registers an exact receipt, shows the result, and opens history", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    await selectPendingShipmentWithKeyboard(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const confirmButton = findButtonByText(rightPanel ?? document, "Confirmar recepcion");
    click(confirmButton ?? null);
    await flush();

    const dialogConfirmButton = findButtonByExactText(view.container, "Confirmar");
    click(dialogConfirmButton ?? null);
    await flush();

    expect(receiveTransfer).toHaveBeenCalledWith("token", "transfer-1", {
      lines: [
        {
          expected_quantity: "3",
          notes: null,
          received_quantity: "3",
          shipment_line_id: "transfer-line-1",
          variance_reason: null,
        },
      ],
      notes: null,
      workstation_code: "POS-01",
    });
    expect(showSuccessMock).toHaveBeenCalledWith("Recepcion registrada. Folio REC-000001.");
    expect(rightPanel?.textContent).toContain("REC-000001");
    expect(rightPanel?.textContent).toContain("Ver historial");

    const historyButton = findButtonByText(rightPanel ?? document, "Ver historial");
    click(historyButton ?? null);
    await flush();

    expect(view.container.textContent).toContain("Historial de recepciones");
    expect(view.container.textContent).toContain("REC-000001");
    expect(rightPanel?.textContent).toContain("Recepcion seleccionada");
  });
});
