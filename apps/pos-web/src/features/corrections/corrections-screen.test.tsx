// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, useSyncExternalStore, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CorrectionsScreen } from "./corrections-screen";
import { commitCorrection, getCorrectionTargetDetail } from "./corrections-api";
import { KeyboardShortcutRegistry } from "../pos-shell/keyboard";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const refetchMock = vi.fn();
const showErrorMock = vi.fn();
const showSuccessMock = vi.fn();
let rightPanelContent: ReactNode = null;
const rightPanelListeners = new Set<() => void>();

const correctionsBootstrapResponse = {
  branch: {
    code: "MAIN",
    id: "branch-1",
    is_active: true,
    name: "Main Branch",
    timezone: "America/Hermosillo",
  },
  branch_brand_key: "EL_MEJOR_PAN",
  correction_controls: {
    high_impact_quantity_threshold: "10",
    high_impact_requires_acknowledgement: true,
  },
  correction_operations_allowed: true,
  correction_reasons: [
    { code: "WRONG_QUANTITY", display_order: 10, name: "Wrong quantity" },
    { code: "WRONG_DESTINATION", display_order: 20, name: "Wrong destination" },
  ],
  current_open_cash_session: null,
  destination_branches: [
    {
      brand_key: null,
      code: "NORTH",
      id: "branch-2",
      name: "North Branch",
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
  workstation: {
    code: "POS-01",
    id: "workstation-1",
    is_active: true,
    name: "Front Register 01",
  },
} as const;

const searchableDocuments = [
  {
    committed_at_utc: "2026-04-22T17:10:00Z",
    correction_count: 1,
    destination_branch_code: null,
    destination_branch_name: null,
    display_title: "Paso a mostrador del turno",
    document_type: "COUNTER_TRANSFER",
    folio: "CTR-000001",
    id: "target-1",
    source_branch_code: "MAIN",
    source_branch_name: "Main Branch",
    status: "COMMITTED",
    workstation_code: "POS-01",
    workstation_name: "Front Register 01",
  },
] as const;

const selectedTargetDetail = {
  applied_corrections: [
    {
      committed_at_utc: "2026-04-22T18:20:00Z",
      corrected_destination_branch_code: null,
      corrected_destination_branch_name: null,
      folio: "COR-000123",
      id: "correction-1",
      line_count: 1,
      lines: [
        {
          delta_quantity: "-1.000",
          line_number: 1,
          product_code_snapshot: "CONCHA-VAN",
          product_name_snapshot: "Concha vainilla",
          target_line_id: "target-line-1",
        },
      ],
      reason_code: "WRONG_QUANTITY",
      reason_name: "Wrong quantity",
      status: "COMMITTED",
    },
  ],
  blocking_reason: null,
  document_title: "Paso a mostrador del turno",
  is_correctable: true,
  target_document: {
    committed_at_utc: "2026-04-22T17:10:00Z",
    created_at_utc: "2026-04-22T17:00:00Z",
    created_by_user_email: "cashier@zeromerma.local",
    created_by_user_full_name: "Main Branch Cashier",
    created_by_user_id: "user-1",
    destination_branch_code: null,
    destination_branch_id: null,
    destination_branch_name: null,
    destination_bucket_code: "COUNTER",
    document_type: "COUNTER_TRANSFER",
    folio: "CTR-000001",
    id: "target-1",
    lines: [
      {
        expected_quantity: null,
        id: "target-line-1",
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
    status: "COMMITTED",
    workstation_code: "POS-01",
    workstation_id: "workstation-1",
    workstation_name: "Front Register 01",
  },
} as const;

const committedCorrectionResponse = {
  audit_summary: {
    acknowledged_at_utc: null,
    acknowledged_by: null,
    acknowledgement_label: null,
    backoffice_notification: null,
    confirmed_at_utc: "2026-04-22T18:25:00Z",
    confirmed_by: {
      email: "cashier@zeromerma.local",
      full_name: "Main Branch Cashier",
      user_id: "user-1",
    },
    created_at_utc: "2026-04-22T18:25:00Z",
    created_by: {
      email: "cashier@zeromerma.local",
      full_name: "Main Branch Cashier",
      user_id: "user-1",
    },
    notes: null,
    reason_label: "Wrong quantity",
  },
  committed_at_utc: "2026-04-22T18:25:00Z",
  corrected_destination_branch_code: null,
  corrected_destination_branch_id: null,
  corrected_destination_branch_name: null,
  correction_type: "DOCUMENT_ADJUSTMENT",
  created_at_utc: "2026-04-22T18:25:00Z",
  created_by_user_email: "cashier@zeromerma.local",
  created_by_user_full_name: "Main Branch Cashier",
  created_by_user_id: "user-1",
  folio: "COR-000123",
  id: "correction-1",
  lines: [
    {
      delta_quantity: "-2.000",
      id: "correction-line-1",
      line_number: 1,
      notes: null,
      product_class_code_snapshot: "PAN-DULCE",
      product_class_id: "class-1",
      product_class_name_snapshot: "Pan dulce",
      product_code_snapshot: "CONCHA-VAN",
      product_id: "product-1",
      product_name_snapshot: "Concha vainilla",
      target_line_id: "target-line-1",
      unit_of_measure_code: "EACH",
    },
  ],
  notes: null,
  reason_code: "WRONG_QUANTITY",
  reason_name: "Wrong quantity",
  source_branch_code: "MAIN",
  source_branch_id: "branch-1",
  source_branch_name: "Main Branch",
  status: "COMMITTED",
  target_document_id: "target-1",
  target_document_type: "COUNTER_TRANSFER",
  workstation_code: "POS-01",
  workstation_id: "workstation-1",
  workstation_name: "Front Register 01",
} as const;

const correctionHistoryRecords = [
  {
    committed_at_utc: "2026-04-22T18:25:00Z",
    corrected_destination_branch_code: null,
    corrected_destination_branch_name: null,
    correction_type: "DOCUMENT_ADJUSTMENT",
    created_at_utc: "2026-04-22T18:25:00Z",
    created_by_user_full_name: "Main Branch Cashier",
    created_by_user_id: "user-1",
    folio: "COR-000123",
    id: "correction-1",
    line_count: 1,
    net_effect_quantity: "-2.000",
    reason_code: "WRONG_QUANTITY",
    reason_name: "Wrong quantity",
    source_branch_code: "MAIN",
    source_branch_name: "Main Branch",
    status: "COMMITTED",
    target_document_folio: "CTR-000001",
    target_document_id: "target-1",
    target_document_type: "COUNTER_TRANSFER",
    workstation_code: "POS-01",
    workstation_name: "Front Register 01",
  },
] as const;

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

vi.mock("./queries", () => ({
  correctionDocumentDetailQueryKey: vi.fn((workstationCode: string, correctionId: string) => [
    "corrections",
    "history-detail",
    workstationCode,
    correctionId,
  ]),
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
    data: correctionsBootstrapResponse,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useCorrectionProductsQuery: () => ({
    data: { products: [], query: "", workstation_code: "POS-01" },
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useCorrectionDocumentDetailQuery: (correctionId: string | null) => ({
    data:
      correctionId === committedCorrectionResponse.id
        ? committedCorrectionResponse
        : null,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useCorrectionTargetDetailQuery: (targetDocumentId: string | null) => ({
    data: targetDocumentId === "target-1" ? selectedTargetDetail : null,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useCorrectionsHistoryQuery: (
    scope: string,
    query: string,
    createdByUserId: string,
    targetDocumentType: string,
    reasonCode: string,
  ) => {
    const normalizedQuery = query.trim().toLowerCase();
    const filteredRecords = correctionHistoryRecords.filter((record) => {
      const matchesScope = scope.length > 0;
      const matchesQuery =
        normalizedQuery.length === 0 ||
        [record.folio, record.target_document_folio, record.reason_name]
          .join(" ")
          .toLowerCase()
          .includes(normalizedQuery);
      const matchesUser =
        createdByUserId.length === 0 || record.created_by_user_id === createdByUserId;
      const matchesType =
        targetDocumentType.length === 0 || record.target_document_type === targetDocumentType;
      const matchesReason =
        reasonCode.length === 0 || record.reason_code === reasonCode;
      return matchesScope && matchesQuery && matchesUser && matchesType && matchesReason;
    });

    return {
      data: {
        available_document_types: [
          { label: "Paso a mostrador", value: "COUNTER_TRANSFER" },
        ],
        available_reasons: [{ label: "Wrong quantity", value: "WRONG_QUANTITY" }],
        available_scopes: [
          { code: "CURRENT_SHIFT", label: "Turno actual" },
          { code: "TODAY", label: "Hoy" },
          { code: "RECENT", label: "Recientes" },
        ],
        available_users: [{ label: "Main Branch Cashier", value: "user-1" }],
        created_by_user_id: createdByUserId || null,
        query: query || null,
        reason_code: reasonCode || null,
        records: filteredRecords,
        scope,
        target_document_type: targetDocumentType || null,
        workstation_code: "POS-01",
      },
      error: null,
      isPending: false,
      refetch: refetchMock,
    };
  },
  useCorrectionTargetsQuery: (documentType: string) => ({
    data: {
      document_type: documentType || null,
      documents: searchableDocuments,
      query: null,
      workstation_code: "POS-01",
    },
    error: null,
    isFetching: false,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock("./corrections-api", () => ({
  commitCorrection: vi.fn(),
  getCorrectionTargetDetail: vi.fn(),
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

function getRightPanel(container: HTMLElement) {
  return container.querySelector('[data-testid="right-panel-probe"]');
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
  });
}

async function selectTargetDocumentWithKeyboard(container: HTMLElement) {
  const firstDocumentRow = container.querySelector<HTMLTableRowElement>("tbody tr");
  if (!firstDocumentRow) {
    throw new Error("Expected a correction target record.");
  }

  firstDocumentRow.focus();
  keydown(firstDocumentRow, "Enter");
  await flush();
}

async function addDraftAdjustment(container: HTMLElement, quantity = "2") {
  const rightPanel = getRightPanel(container);
  const quantityButton = rightPanel?.querySelector<HTMLButtonElement>(
    '[data-correction-line-quantity-button="target-line-1"]',
  );
  click(quantityButton);
  await flush();

  const lineRow = rightPanel?.querySelector('[data-correction-line-row="target-line-1"]');
  if (!(lineRow instanceof HTMLElement)) {
    throw new Error("Expected correction line row.");
  }

  const quantityInput = lineRow.querySelector<HTMLInputElement>('input[inputmode="decimal"]');
  changeInput(quantityInput, quantity);
  await flush();

  keydown(quantityInput, "Enter");
  await flush();
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
            <CorrectionsScreen />
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

let mountedRoots: Array<() => void> = [];

beforeEach(() => {
  rightPanelContent = null;
  showErrorMock.mockReset();
  showSuccessMock.mockReset();
  refetchMock.mockReset();
  vi.mocked(commitCorrection).mockReset();
  vi.mocked(getCorrectionTargetDetail).mockReset();
  vi.mocked(getCorrectionTargetDetail).mockResolvedValue(selectedTargetDetail as never);
  vi.mocked(commitCorrection).mockResolvedValue(committedCorrectionResponse as never);
});

afterEach(() => {
  mountedRoots.forEach((unmount) => unmount());
  mountedRoots = [];
});

describe("CorrectionsScreen", () => {
  it("shows a blocker when no source document is selected", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    const rightPanel = getRightPanel(view.container);
    expect(rightPanel?.textContent).toContain("Selecciona un movimiento para ajustar.");
  });

  it("selects the source document with keyboard and shows the original detail", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    await selectTargetDocumentWithKeyboard(view.container);

    expect(view.container.textContent).toContain("Paso a mostrador del turno");
    expect(getRightPanel(view.container)?.textContent).toContain("Concha vainilla");
  });

  it("captures an adjustment line and blocks commit until a reason is selected", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    await selectTargetDocumentWithKeyboard(view.container);
    await addDraftAdjustment(view.container);

    const rightPanel = getRightPanel(view.container);
    expect(rightPanel?.textContent).toContain("Selecciona un motivo para continuar.");
    expect(rightPanel?.textContent).toContain("-1");
  });

  it("confirms an adjustment and shows the success result with folio", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    await selectTargetDocumentWithKeyboard(view.container);
    await addDraftAdjustment(view.container);

    const reasonSelect = Array.from(view.container.querySelectorAll("select")).find((element) =>
      Array.from(element.options).some((option) => option.value === "WRONG_QUANTITY"),
    );
    changeSelect(reasonSelect ?? null, "WRONG_QUANTITY");
    await flush();

    const rightPanel = getRightPanel(view.container);
    const registerButton = Array.from(rightPanel?.querySelectorAll("button") ?? []).find((button) =>
      button.textContent?.includes("Guardar ajuste"),
    );
    click(registerButton);
    await flush();
    await flush();

    expect(commitCorrection).toHaveBeenCalledTimes(1);
    expect(showSuccessMock).toHaveBeenCalledWith(
      "Ajuste COR-000123 registrado correctamente.",
    );
    expect(view.container.textContent).toContain("Movimientos");
    expect(getRightPanel(view.container)?.textContent).toContain("Da click en una cantidad nueva");
  });

  it("opens the adjustment history from the result state", async () => {
    const view = renderUi();
    mountedRoots.push(view.unmount);
    await flush();

    await selectTargetDocumentWithKeyboard(view.container);
    await addDraftAdjustment(view.container);

    const reasonSelect = Array.from(view.container.querySelectorAll("select")).find((element) =>
      Array.from(element.options).some((option) => option.value === "WRONG_QUANTITY"),
    );
    changeSelect(reasonSelect ?? null, "WRONG_QUANTITY");
    await flush();

    const rightPanel = getRightPanel(view.container);
    const registerButton = Array.from(rightPanel?.querySelectorAll("button") ?? []).find((button) =>
      button.textContent?.includes("Guardar ajuste"),
    );
    click(registerButton);
    await flush();
    await flush();

    const historyButton = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Historial de ajustes"),
    );
    click(historyButton);
    await flush();

    expect(view.container.textContent).toContain("Historial de ajustes");
    expect(view.container.textContent).toContain("COR-000123");
    expect(view.container.textContent).toContain("Cantidad incorrecta");
  });
});
