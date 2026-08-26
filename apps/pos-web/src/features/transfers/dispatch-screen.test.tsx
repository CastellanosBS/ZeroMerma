// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, useSyncExternalStore, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TransferDispatchScreen } from "./dispatch-screen";
import { commitTransferDispatch } from "./transfers-api";
import type {
  OperationHistoryFilterOptionView,
  OperationHistoryScopeView,
  TransferDetailResponse,
  TransferDispatchHistoryResponse,
} from "../../lib/api-contracts";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const refetchMock = vi.fn();
const showErrorMock = vi.fn();
const showSuccessMock = vi.fn();
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
      code: "NORTH",
      id: "branch-2",
      name: "North Branch",
      timezone: "America/Hermosillo",
    },
    {
      brand_key: null,
      code: "SOUTH",
      id: "branch-3",
      name: "South Branch",
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
  { label: "Main Branch Cashier", value: "user-1" },
];

const historyDestinations: OperationHistoryFilterOptionView[] = [
  { label: "North Branch", value: "branch-2" },
];

const committedTransfer: TransferDetailResponse = {
  receipt: null,
  receipt_summary: null,
  shipment: {
    committed_at_utc: "2026-04-22T18:12:00Z",
    created_at_utc: "2026-04-22T18:10:00Z",
    created_by_user_email: "cashier@zeromerma.local",
    created_by_user_full_name: "Main Branch Cashier",
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
    source_bucket_code: "BACKROOM",
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
      received_total_quantity: "0.000",
      variance_line_count: 0,
    },
    status: "IN_TRANSIT",
  },
} as const;

const historyResponse: TransferDispatchHistoryResponse = {
  available_destination_branches: historyDestinations,
  available_scopes: historyScopes,
  available_users: historyUsers,
  created_by_user_id: null,
  destination_branch_id: null,
  records: [
    {
      committed_at_utc: "2026-04-22T18:12:00Z",
      created_at_utc: "2026-04-22T18:10:00Z",
      created_by_user_full_name: "Main Branch Cashier",
      created_by_user_id: "user-1",
      destination_branch_code: "NORTH",
      destination_branch_name: "North Branch",
      destination_bucket_code: "BACKROOM",
      document_type: "BRANCH_TRANSFER_SHIPMENT",
      folio: "ENV-000001",
      id: "transfer-1",
      line_count: 1,
      source_branch_code: "MAIN",
      source_branch_name: "Main Branch",
      source_bucket_code: "BACKROOM",
      status: "IN_TRANSIT",
      total_quantity: "3.000",
      workstation_code: "POS-01",
      workstation_name: "Front Register 01",
    },
  ],
  scope: "CURRENT_SHIFT",
  workstation_code: "POS-01",
} as const;

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
}));

vi.mock("./queries", () => ({
  useTransferDetailQuery: (transferId: string | null) => ({
    data: transferId === "transfer-1" ? committedTransfer : null,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useTransferDispatchHistoryQuery: (_filters: unknown, enabled = true) => ({
    data: enabled ? historyResponse : undefined,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock("./transfers-api", () => ({
  commitTransferDispatch: vi.fn(),
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

function changeSelect(element: HTMLSelectElement | null, value: string) {
  if (!element) {
    throw new Error("Expected select element to exist.");
  }

  act(() => {
    const valueSetter = Object.getOwnPropertyDescriptor(
      HTMLSelectElement.prototype,
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
        <>
          <TransferDispatchScreen />
          <AppShellRightPanelProbe />
        </>
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

async function addShipmentLineUsingKeyboard(container: HTMLElement) {
  const destinationSelect = container.querySelector<HTMLSelectElement>(
    "#transfer-destination-branch",
  );
  changeSelect(destinationSelect, "branch-2");
  await flush();

  const classButton = findButtonByText(container, "Pan dulce");
  focus(classButton ?? null);
  keydown(classButton, "Enter");
  await flush();

  const productButton = findButtonByText(container, "Concha vainilla");
  focus(productButton ?? null);
  keydown(productButton, "Enter");
  await flush();

  const quantityInput = container.querySelector<HTMLInputElement>('input[aria-label="Cantidad"]');
  changeInput(quantityInput, "3");
  await flush();
  keydown(quantityInput, "Enter");
  await flush();
}

let mountedRoots: Array<() => void> = [];

beforeEach(() => {
  rightPanelContent = null;
  showErrorMock.mockReset();
  showSuccessMock.mockReset();
  refetchMock.mockReset();
  vi.mocked(commitTransferDispatch).mockReset();
  vi.mocked(commitTransferDispatch).mockResolvedValue(committedTransfer);
});

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("TransferDispatchScreen", () => {
  it("requires a destination before enabling shipment registration", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const registerButton = findButtonByText(rightPanel ?? document, "Confirmar envio");

    expect(registerButton?.disabled).toBe(true);
    expect(rightPanel?.textContent).toContain("Selecciona una sucursal destino.");
  });

  it("updates the compact destination selector and route", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const destinationSelect = view.container.querySelector<HTMLSelectElement>(
      "#transfer-destination-branch",
    );
    changeSelect(destinationSelect, "branch-2");
    await flush();

    expect(destinationSelect?.value).toBe("branch-2");
    expect(view.container.textContent).toContain("Main Branch -> North Branch");
    expect(view.container.textContent).toContain("Sucursal destino");
  });

  it("cancels the confirmation dialog without persisting", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await addShipmentLineUsingKeyboard(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const registerButton = findButtonByText(rightPanel ?? document, "Confirmar envio");
    click(registerButton ?? null);

    expect(view.container.textContent).toContain("Confirmar envio a sucursal");

    const cancelButton = findButtonByText(view.container, "Cancelar");
    click(cancelButton ?? null);
    await flush();

    expect(view.container.textContent).not.toContain("Confirmar envio a sucursal");
    expect(commitTransferDispatch).not.toHaveBeenCalled();
  });

  it("registers a shipment, shows the result folio, and opens history", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await addShipmentLineUsingKeyboard(view.container);

    const rightPanel = view.container.querySelector('[data-testid="right-panel-probe"]');
    const lineQuantityButton = rightPanel?.querySelector<HTMLButtonElement>(
      'button[aria-label="Editar cantidad de Concha vainilla"]',
    );
    click(lineQuantityButton ?? null);
    await flush();

    const lineQuantityInput = rightPanel?.querySelector<HTMLInputElement>(
      'input[aria-label="Cantidad de Concha vainilla"]',
    );
    changeInput(lineQuantityInput ?? null, "4");
    keydown(lineQuantityInput ?? null, "Enter");
    await flush();

    const registerButton = findButtonByText(rightPanel ?? document, "Confirmar envio");
    focus(registerButton ?? null);
    click(registerButton ?? null);
    await flush();

    const confirmButton = findButtonByText(view.container, "Confirmar envio");
    focus(confirmButton ?? null);
    click(confirmButton ?? null);
    await flush();

    expect(commitTransferDispatch).toHaveBeenCalledWith("token", {
      destination_branch_id: "branch-2",
      lines: [{ product_id: "product-1", quantity: "4" }],
      notes: null,
      workstation_code: "POS-01",
    });
    expect(showSuccessMock).toHaveBeenCalledWith("Envio registrado. Folio ENV-000001.");
    expect(view.container.textContent).toContain("Historial de envios");
    expect(view.container.textContent).toContain("ENV-000001");
    expect(rightPanel?.textContent).toContain("Envio seleccionado");
    expect(rightPanel?.textContent).toContain("Volver a captura");
  });
});
