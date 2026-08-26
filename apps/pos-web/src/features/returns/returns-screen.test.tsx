// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";
import { act, type ReactElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { KeyboardShortcutRegistry } from "../pos-shell/keyboard";
import { ReturnsScreen } from "./returns-screen";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const refetchMock = vi.fn();
const showErrorMock = vi.fn();
const showSuccessMock = vi.fn();
const navigateMock = vi.fn();
const commitSaleReturnMock = vi.fn();
let publishRightPanel: ((node: React.ReactNode) => void) | null = null;

let routerSearch: Record<string, unknown> = {};

const bootstrapResponse = {
  available_scopes: [
    { code: "CURRENT_SHIFT", label: "Turno actual" },
    { code: "TODAY", label: "Hoy" },
    { code: "RECENT", label: "Recientes" },
  ],
  branch: {
    code: "MAIN",
    id: "branch-1",
    is_active: true,
    name: "Main Branch",
    timezone: "America/Hermosillo",
  },
  current_open_cash_session: null,
  default_scope: "CURRENT_SHIFT",
  local_timestamp: "2026-04-22T18:00:00Z",
  refund_methods: [
    { availability_note: null, code: "CASH", is_enabled: true, label: "Efectivo" },
    {
      availability_note: "Reverso de tarjeta pendiente de integracion.",
      code: "CARD",
      is_enabled: false,
      label: "Tarjeta",
    },
  ],
  return_controls: {
    high_refund_amount_threshold: "200.00",
    high_risk_requires_acknowledgement: true,
    old_sale_days_threshold: 7,
  },
  return_operations_allowed: true,
  return_reasons: [
    { code: "WRONG_ITEM", label: "Producto incorrecto" },
    { code: "QUALITY_ISSUE", label: "Problema de calidad" },
  ],
  user: {
    email: "cashier@zeromerma.local",
    full_name: "Main Branch Cashier",
    id: "user-1",
  },
  workstation: {
    code: "POS-01",
    id: "workstation-1",
    is_active: true,
    name: "Front Register 01",
  },
} as const;

const saleRecords = [
  {
    confirmed_at: "2026-04-22T18:00:00Z",
    currency_code: "MXN",
    folio: "TCK-OTHER",
    has_returnable_quantity: true,
    id: "sale-other",
    item_count: 1,
    operator_full_name: "Main Branch Cashier",
    return_count: 0,
    return_status: "NOT_RETURNED",
    returned_amount: "0.00",
    total_amount: "36.00",
    total_quantity: "3.000",
  },
  {
    confirmed_at: "2026-04-22T19:30:00Z",
    currency_code: "MXN",
    folio: "TCK-SEARCH",
    has_returnable_quantity: true,
    id: "sale-search",
    item_count: 1,
    operator_full_name: "Main Branch Cashier",
    return_count: 1,
    return_status: "PARTIALLY_RETURNED",
    returned_amount: "10.00",
    total_amount: "20.00",
    total_quantity: "2.000",
  },
] as const;

const saleDetailsById = {
  "sale-other": {
    branch: bootstrapResponse.branch,
    cash_session_id: "cash-session-1",
    change_amount: "0.00",
    confirmed_at: "2026-04-22T18:00:00Z",
    currency_code: "MXN",
    folio: "TCK-OTHER",
    has_returnable_lines: true,
    id: "sale-other",
    lines: [
      {
        already_returned_quantity: "0.000",
        capture_mode: "PRODUCT_DIRECT",
        catalog_code_snapshot: "BOL-001",
        catalog_name_snapshot: "Bolillo",
        id: "sale-line-1",
        line_total_amount: "36.00",
        product_class_code: "BREAD",
        product_class_id: "class-bread",
        product_class_name: "Bread",
        product_code: "BOL-001",
        product_id: "product-bolillo",
        product_name: "Bolillo",
        quantity: "3.000",
        remaining_returnable_quantity: "3.000",
        requires_exact_product_selection: false,
        sequence: 1,
        unit_price: "12.00",
      },
    ],
    operator: bootstrapResponse.user,
    paid_amount: "36.00",
    payments: [
      {
        applied_amount: "36.00",
        change_amount: "0.00",
        currency_code: "MXN",
        payment_method_code: "CASH",
        received_at: "2026-04-22T18:00:00Z",
        tendered_amount: "36.00",
      },
    ],
    return_count: 0,
    return_status: "NOT_RETURNED",
    returned_amount: "0.00",
    status: "CONFIRMED",
    subtotal_amount: "36.00",
    total_amount: "36.00",
    workstation: bootstrapResponse.workstation,
  },
  "sale-preloaded": {
    branch: bootstrapResponse.branch,
    cash_session_id: "cash-session-1",
    change_amount: "0.00",
    confirmed_at: "2026-04-20T16:00:00Z",
    currency_code: "MXN",
    folio: "TCK-PRELOADED",
    has_returnable_lines: true,
    id: "sale-preloaded",
    lines: [
      {
        already_returned_quantity: "0.000",
        capture_mode: "PRODUCT_DIRECT",
        catalog_code_snapshot: "BOL-001",
        catalog_name_snapshot: "Bolillo",
        id: "sale-line-preloaded",
        line_total_amount: "40.00",
        product_class_code: "BREAD",
        product_class_id: "class-bread",
        product_class_name: "Bread",
        product_code: "BOL-001",
        product_id: "product-bolillo",
        product_name: "Bolillo",
        quantity: "4.000",
        remaining_returnable_quantity: "4.000",
        requires_exact_product_selection: false,
        sequence: 1,
        unit_price: "10.00",
      },
    ],
    operator: bootstrapResponse.user,
    paid_amount: "40.00",
    payments: [
      {
        applied_amount: "40.00",
        change_amount: "0.00",
        currency_code: "MXN",
        payment_method_code: "CASH",
        received_at: "2026-04-20T16:00:00Z",
        tendered_amount: "40.00",
      },
    ],
    return_count: 0,
    return_status: "NOT_RETURNED",
    returned_amount: "0.00",
    status: "CONFIRMED",
    subtotal_amount: "40.00",
    total_amount: "40.00",
    workstation: bootstrapResponse.workstation,
  },
} as const;

const historyRecords = [
  {
    branch_code: "MAIN",
    branch_name: "Main Branch",
    created_at_utc: "2026-04-22T20:00:00Z",
    created_by_user_full_name: "Main Branch Cashier",
    created_by_user_id: "user-1",
    currency_code: "MXN",
    folio: "RET-0001",
    id: "return-1",
    line_count: 1,
    original_sale_folio: "TCK-OTHER",
    original_sale_id: "sale-other",
    reason_code: "WRONG_ITEM",
    reason_name: "Producto incorrecto",
    refund_method_code: "CASH",
    status: "COMMITTED",
    total_refund_amount: "12.00",
    workstation_code: "POS-01",
    workstation_name: "Front Register 01",
  },
  {
    branch_code: "MAIN",
    branch_name: "Main Branch",
    created_at_utc: "2026-04-21T20:00:00Z",
    created_by_user_full_name: "Main Branch Cashier",
    created_by_user_id: "user-1",
    currency_code: "MXN",
    folio: "RET-OLD",
    id: "return-old",
    line_count: 1,
    original_sale_folio: "TCK-SEARCH",
    original_sale_id: "sale-search",
    reason_code: "QUALITY_ISSUE",
    reason_name: "Problema de calidad",
    refund_method_code: "CASH",
    status: "COMMITTED",
    total_refund_amount: "10.00",
    workstation_code: "POS-01",
    workstation_name: "Front Register 01",
  },
] as const;

const returnDetailsById = {
  "return-1": {
    audit_summary: {
      acknowledged_at_utc: null,
      acknowledged_by: null,
      acknowledgement_label: null,
      backoffice_notification: null,
      confirmed_at_utc: "2026-04-22T20:00:00Z",
      confirmed_by: bootstrapResponse.user,
      created_at_utc: "2026-04-22T20:00:00Z",
      created_by: bootstrapResponse.user,
      notes: "Cliente devolvio refresco",
      reason_label: "Producto incorrecto",
    },
    branch: bootstrapResponse.branch,
    cash_session_id: "cash-session-1",
    created_at_utc: "2026-04-22T20:00:00Z",
    created_by: bootstrapResponse.user,
    currency_code: "MXN",
    folio: "RET-0001",
    id: "return-1",
    lines: [
      {
        disposition_code: "RESTOCK_COUNTER",
        id: "return-line-1",
        line_number: 1,
        original_catalog_name_snapshot: "Bolillo",
        original_sale_line_id: "sale-line-1",
        refund_line_total_amount: "12.00",
        refund_unit_price: "12.00",
        returned_product_name_snapshot: "Bolillo",
        returned_quantity: "1.000",
      },
    ],
    notes: "Cliente devolvio refresco",
    original_sale_folio: "TCK-OTHER",
    original_sale_id: "sale-other",
    reason_code: "WRONG_ITEM",
    reason_name: "Producto incorrecto",
    refund_method_code: "CASH",
    total_refund_amount: "12.00",
    workstation: bootstrapResponse.workstation,
  },
  "return-old": {
    audit_summary: {
      acknowledged_at_utc: null,
      acknowledged_by: null,
      acknowledgement_label: null,
      backoffice_notification: null,
      confirmed_at_utc: "2026-04-21T20:00:00Z",
      confirmed_by: bootstrapResponse.user,
      created_at_utc: "2026-04-21T20:00:00Z",
      created_by: bootstrapResponse.user,
      notes: null,
      reason_label: "Problema de calidad",
    },
    branch: bootstrapResponse.branch,
    cash_session_id: "cash-session-1",
    created_at_utc: "2026-04-21T20:00:00Z",
    created_by: bootstrapResponse.user,
    currency_code: "MXN",
    folio: "RET-OLD",
    id: "return-old",
    lines: [
      {
        disposition_code: "SEND_TO_WASTE",
        id: "return-line-old",
        line_number: 1,
        original_catalog_name_snapshot: "Bolillo",
        original_sale_line_id: "sale-line-search",
        refund_line_total_amount: "10.00",
        refund_unit_price: "10.00",
        returned_product_name_snapshot: "Bolillo",
        returned_quantity: "1.000",
      },
    ],
    notes: null,
    original_sale_folio: "TCK-SEARCH",
    original_sale_id: "sale-search",
    reason_code: "QUALITY_ISSUE",
    reason_name: "Problema de calidad",
    refund_method_code: "CASH",
    total_refund_amount: "10.00",
    workstation: bootstrapResponse.workstation,
  },
} as const;

vi.mock("@tanstack/react-router", () => ({
  Navigate: ({ to }: { to: string }) => <div data-testid="navigate">{to}</div>,
  useNavigate: () => navigateMock,
  useRouterState: ({
    select,
  }: {
    select: (state: { location: { search: Record<string, unknown> } }) => unknown;
  }) => select({ location: { search: routerSearch } }),
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
  returnSaleDetailQueryKey: vi.fn((workstationCode: string, saleId: string) => [
    "returns",
    "sale-detail",
    workstationCode,
    saleId,
  ]),
  saleReturnDetailQueryKey: vi.fn((workstationCode: string, returnId: string) => [
    "returns",
    "return-detail",
    workstationCode,
    returnId,
  ]),
  returnsBootstrapQueryKey: vi.fn((workstationCode: string) => [
    "returns",
    "bootstrap",
    workstationCode,
  ]),
  useReturnsBootstrapQuery: () => ({
    data: bootstrapResponse,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useReturnSalesQuery: (_scope: string, query: string, dateFrom: string, dateTo: string) => {
    const normalizedQuery = query.trim().toLowerCase();
    const filteredSales = saleRecords.filter((sale) => {
      const matchesQuery =
        normalizedQuery.length === 0 || sale.folio.toLowerCase().includes(normalizedQuery);
      const matchesDateFrom =
        dateFrom.length === 0 || sale.confirmed_at.slice(0, 10) >= dateFrom;
      const matchesDateTo =
        dateTo.length === 0 || sale.confirmed_at.slice(0, 10) <= dateTo;
      return matchesQuery && matchesDateFrom && matchesDateTo;
    });

    return {
      data: { sales: filteredSales },
      error: null,
      isPending: false,
      refetch: refetchMock,
    };
  },
  useReturnSaleDetailQuery: (saleId: string | null) => ({
    data: saleId ? saleDetailsById[saleId as keyof typeof saleDetailsById] ?? null : null,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useSaleReturnDetailQuery: (returnId: string | null) => ({
    data: returnId ? returnDetailsById[returnId as keyof typeof returnDetailsById] ?? null : null,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useReturnsHistoryQuery: (
    scope: string,
    query: string,
    dateFrom: string,
    dateTo: string,
    createdByUserId: string,
    reasonCode: string,
  ) => {
    const normalizedQuery = query.trim().toLowerCase();
    const filteredRecords = historyRecords.filter((record) => {
      const matchesScope = scope.length > 0;
      const matchesQuery =
        normalizedQuery.length === 0 ||
        [record.folio, record.original_sale_folio, record.reason_name]
          .join(" ")
          .toLowerCase()
          .includes(normalizedQuery);
      const matchesDateFrom =
        dateFrom.length === 0 || record.created_at_utc.slice(0, 10) >= dateFrom;
      const matchesDateTo =
        dateTo.length === 0 || record.created_at_utc.slice(0, 10) <= dateTo;
      const matchesUser =
        createdByUserId.length === 0 || record.created_by_user_id === createdByUserId;
      const matchesReason = reasonCode.length === 0 || record.reason_code === reasonCode;
      return matchesScope && matchesQuery && matchesDateFrom && matchesDateTo && matchesUser && matchesReason;
    });

    return {
      data: {
        available_reasons: bootstrapResponse.return_reasons.map((reason) => ({
          value: reason.code,
          label: reason.label,
        })),
        available_scopes: bootstrapResponse.available_scopes,
        available_users: [{ value: "user-1", label: "Main Branch Cashier" }],
        created_by_user_id: createdByUserId || null,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        query: query || null,
        reason_code: reasonCode || null,
        records: filteredRecords,
        scope,
        workstation_code: "POS-01",
      },
      error: null,
      isPending: false,
      refetch: refetchMock,
    };
  },
  useReturnClassProductsQueries: () => [],
}));

vi.mock("./returns-api", () => ({
  commitSaleReturn: (...args: unknown[]) => commitSaleReturnMock(...args),
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
      <KeyboardShortcutRegistry>
        <QueryClientProvider client={queryClient}>
          <TestShell>{element}</TestShell>
        </QueryClientProvider>
      </KeyboardShortcutRegistry>,
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

function setInputValue(input: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const descriptor = Object.getOwnPropertyDescriptor(
    Object.getPrototypeOf(input),
    "value",
  )?.set;

  act(() => {
    descriptor?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function setSelectValue(select: HTMLSelectElement, value: string) {
  act(() => {
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

let mountedRoots: Array<() => void> = [];

beforeEach(() => {
  routerSearch = { saleId: "sale-preloaded" };
  showErrorMock.mockReset();
  showSuccessMock.mockReset();
  navigateMock.mockReset();
  commitSaleReturnMock.mockReset();
  commitSaleReturnMock.mockResolvedValue({
    branch: bootstrapResponse.branch,
    cash_session_id: "cash-session-1",
    created_at_utc: "2026-04-22T20:00:00Z",
    created_by: bootstrapResponse.user,
    currency_code: "MXN",
    folio: "RET-0001",
    id: "return-1",
    lines: [
      {
        disposition_code: "RESTOCK_COUNTER",
        id: "return-line-1",
        line_number: 1,
        original_catalog_name_snapshot: "Bolillo",
        original_sale_line_id: "sale-line-1",
        refund_line_total_amount: "12.00",
        refund_unit_price: "12.00",
        returned_product_name_snapshot: "Bolillo",
        returned_quantity: "1.000",
      },
    ],
    notes: null,
    original_sale_folio: "TCK-OTHER",
    original_sale_id: "sale-other",
    reason_code: "WRONG_ITEM",
    reason_name: "Producto incorrecto",
    refund_method_code: "CASH",
    total_refund_amount: "12.00",
    workstation: bootstrapResponse.workstation,
  });
});

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
  vi.useRealTimers();
});

describe("ReturnsScreen", () => {
  it("keeps a route-preloaded sale selected even when it is outside the current visible list", async () => {
    const view = renderUi(<ReturnsScreen />);
    mountedRoots.push(view.unmount);
    await flush();

    expect(view.container.textContent).toContain("Venta TCK-PRELOADED");
    expect(view.container.textContent).toContain("TCK-PRELOADED");
    expect(view.container.textContent).toContain("Bolillo");
  });

  it("filters sales by folio search", async () => {
    vi.useFakeTimers();
    routerSearch = {};

    const view = renderUi(<ReturnsScreen />);
    mountedRoots.push(view.unmount);
    await flush();

    const searchInput = view.container.querySelector(
      'input[aria-label="Buscar venta por folio"]',
    ) as HTMLInputElement;

    setInputValue(searchInput, "SEARCH");
    await act(async () => {
      vi.advanceTimersByTime(250);
      await Promise.resolve();
    });

    expect(view.container.textContent).toContain("TCK-SEARCH");
    expect(view.container.textContent).not.toContain("TCK-OTHER");
  });

  it("blocks confirmation until reason and refund method are selected", async () => {
    routerSearch = {};

    const view = renderUi(<ReturnsScreen />);
    mountedRoots.push(view.unmount);
    await flush();

    const saleRows = Array.from(view.container.querySelectorAll<HTMLTableRowElement>("tbody tr"));
    act(() => {
      saleRows[0]?.click();
    });
    await flush();

    const lineRow = Array.from(view.container.querySelectorAll<HTMLTableRowElement>("tbody tr")).find(
      (row) => row.textContent?.includes("Bolillo"),
    ) as HTMLTableRowElement;
    act(() => {
      lineRow.click();
    });
    await flush();

    const rightPanelHost = view.container.querySelector(
      '[data-testid="right-panel-host"]',
    ) as HTMLDivElement;
    const commitButton = Array.from(rightPanelHost.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Confirmar devolucion"),
    ) as HTMLButtonElement;

    expect(commitButton.disabled).toBe(true);
    expect(view.container.textContent).toContain("Selecciona un motivo para continuar.");
    expect(view.container.textContent).not.toContain("Selecciona el metodo de reembolso.");
  });

  it("commits a partial return and navigates to the original ticket", async () => {
    routerSearch = {};

    const view = renderUi(<ReturnsScreen />);
    mountedRoots.push(view.unmount);
    await flush();

    const saleRows = Array.from(view.container.querySelectorAll<HTMLTableRowElement>("tbody tr"));
    act(() => {
      saleRows[0]?.click();
    });
    await flush();

    const lineRow = Array.from(view.container.querySelectorAll<HTMLTableRowElement>("tbody tr")).find(
      (row) => row.textContent?.includes("Bolillo"),
    ) as HTMLTableRowElement;
    act(() => {
      lineRow.click();
    });
    await flush();

    const rightPanelHost = view.container.querySelector(
      '[data-testid="right-panel-host"]',
    ) as HTMLDivElement;
    const quantityInput = Array.from(view.container.querySelectorAll("input")).find(
      (input) => (input as HTMLInputElement).inputMode === "decimal",
    ) as HTMLInputElement;
    setInputValue(quantityInput, "1");

    const selects = Array.from(rightPanelHost.querySelectorAll("select")) as HTMLSelectElement[];
    const dispositionSelect = selects[0]!;
    const reasonSelect = selects[1]!;
    const refundMethodSelect = selects[2]!;
    setSelectValue(dispositionSelect, "RESTOCK_COUNTER");
    setSelectValue(reasonSelect, "WRONG_ITEM");
    setSelectValue(refundMethodSelect, "CASH");
    await flush();

    const commitButton = Array.from(rightPanelHost.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Confirmar devolucion"),
    ) as HTMLButtonElement;
    expect(commitButton.disabled).toBe(false);

    act(() => {
      commitButton.click();
    });
    await flush();
    await flush();
    await flush();

    expect(commitSaleReturnMock).toHaveBeenCalledWith(
      expect.objectContaining({
        payload: expect.objectContaining({
          high_risk_acknowledged: false,
          original_sale_id: "sale-other",
          reason_code: "WRONG_ITEM",
          refund_method_code: "CASH",
          lines: [
            expect.objectContaining({
              disposition_code: "RESTOCK_COUNTER",
              returned_quantity: "1",
            }),
          ],
        }),
      }),
    );
    expect(view.container.textContent).toContain("RET-0001");
    expect(view.container.textContent).toContain("Historial de devoluciones");
    expect(showSuccessMock).toHaveBeenCalledWith("Devolucion registrada. Folio RET-0001.");

    const viewTicketButton = Array.from(rightPanelHost.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Ver ticket"),
    ) as HTMLButtonElement;
    act(() => {
      viewTicketButton.click();
    });

    expect(navigateMock).toHaveBeenCalledWith({
      search: { ticketId: "sale-other" },
      to: "/tickets",
    });
  });
});
