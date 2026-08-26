// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  OperationalPaymentDetailResponse,
  OperationalPaymentListItemView,
} from "../../lib/api-contracts";
import { createInitialOperationalPaymentDraftState } from "./model";
import { createPayment } from "./payments-api";
import { PaymentsRightPanel, PaymentsScreen } from "./payments-screen";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const refetchMock = vi.fn();
const showErrorMock = vi.fn();
const showSuccessMock = vi.fn();
const registeredShortcuts = new Map<
  string,
  {
    description: string;
    group: string;
    handler: (event: KeyboardEvent) => void;
    id: string;
    label: string;
  }
>();

const bootstrapResponse = {
  active_categories: [
    { code: "SERVICES", display_order: 10, name: "Servicios" },
    { code: "SUPPLIER", display_order: 20, name: "Proveedor" },
  ],
  active_payment_methods: [
    {
      affects_cash_drawer: true,
      code: "CASH",
      helper_text: "Reduce efectivo esperado.",
      is_enabled: true,
      label: "Efectivo",
    },
    {
      affects_cash_drawer: false,
      code: "CARD",
      helper_text: "No reduce efectivo esperado.",
      is_enabled: true,
      label: "Tarjeta",
    },
    {
      affects_cash_drawer: false,
      code: "MIXED",
      helper_text: "No disponible en esta fase.",
      is_enabled: false,
      label: "Mixto",
    },
  ],
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
  branch_brand_key: "EL_MEJOR_PAN",
  current_open_cash_session: {
    branch_code: "MAIN",
    branch_id: "branch-1",
    branch_name: "Main Branch",
    id: "cash-session-1",
    opening_amount: "300.00",
    opened_at: "2026-04-22T18:00:00Z",
    status: "OPEN",
    user_email: "cashier@zeromerma.local",
    user_full_name: "Main Branch Cashier",
    user_id: "user-1",
    workstation_code: "POS-01",
    workstation_id: "workstation-1",
    workstation_name: "Front Register 01",
  },
  default_scope: "CURRENT_SHIFT",
  local_timestamp: "2026-04-22T18:00:00Z",
  payment_registration_allowed: true,
  user: {
    default_surface: "POS",
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

type PaymentRecord = OperationalPaymentListItemView & {
  created_by_user_id: string;
  scope_tag: "CURRENT_SHIFT" | "RECENT";
};

const operationalLocation = {
  branch_code: bootstrapResponse.branch.code,
  branch_name: bootstrapResponse.branch.name,
  workstation_code: bootstrapResponse.workstation.code,
  workstation_name: bootstrapResponse.workstation.name,
} as const;

const basePayments: PaymentRecord[] = [
  {
    affects_cash_drawer: true,
    ...operationalLocation,
    cash_amount: "160.00",
    category_code: "SUPPLIER",
    category_name: "Proveedor",
    concept: "REF-PROV-01",
    created_at_utc: "2026-04-22T18:10:00Z",
    created_by_user_id: "user-1",
    currency_code: "MXN",
    folio: "PAG-AAA001",
    id: "payment-1",
    non_cash_amount: "0.00",
    operator_full_name: "Main Branch Cashier",
    payee_name: "Proveedor Central",
    payment_method_code: "CASH",
    scope_tag: "CURRENT_SHIFT",
    status: "COMMITTED",
    total_amount: "160.00",
  },
  {
    affects_cash_drawer: false,
    ...operationalLocation,
    cash_amount: "0.00",
    category_code: "SERVICES",
    category_name: "Servicios",
    concept: "REF-LIMPIEZA",
    created_at_utc: "2026-04-21T16:00:00Z",
    created_by_user_id: "user-2",
    currency_code: "MXN",
    folio: "PAG-BBB002",
    id: "payment-2",
    non_cash_amount: "90.00",
    operator_full_name: "Second Operator",
    payee_name: "Servicio Limpieza",
    payment_method_code: "CARD",
    scope_tag: "RECENT",
    status: "COMMITTED",
    total_amount: "90.00",
  },
];

let seededPayments: PaymentRecord[] = [];
let createdPayments: PaymentRecord[] = [];

vi.mock("@tanstack/react-router", () => ({
  Navigate: ({ to }: { to: string }) => <div data-testid="navigate">{to}</div>,
}));

vi.mock("../../components/app-shell-right-panel", () => ({
  useAppShellRightPanel: () => undefined,
}));

vi.mock("../auth/auth-store", () => ({
  usePosAuthStore: (selector: (state: { accessToken: string }) => unknown) =>
    selector({ accessToken: "token" }),
}));

vi.mock("../cash-session-open/queries", () => ({
  currentCashSessionQueryKey: () => ["cash-session"],
  useCurrentCashSessionQuery: () => ({
    data: { user_id: "user-1" },
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
}));

vi.mock("../cash-close/queries", () => ({
  cashCloseBootstrapQueryKey: () => ["cash-close-bootstrap"],
  cashCloseReconciliationQueryKey: () => ["cash-close-reconciliation"],
  cashCloseSummaryQueryKey: () => ["cash-close-summary"],
}));

vi.mock("../pos-shell/keyboard", async () => {
  const actual = await vi.importActual<typeof import("../pos-shell/keyboard")>("../pos-shell/keyboard");

  return {
    ...actual,
    KeyboardShortcutRegistry: ({ children }: { children: ReactNode }) => <>{children}</>,
    useModuleHotkeys(
      shortcuts: ReadonlyArray<{
        description: string;
        group: string;
        handler: (event: KeyboardEvent) => void;
        id: string;
        label: string;
      }>,
    ) {
      for (const shortcut of shortcuts) {
        registeredShortcuts.set(shortcut.id, shortcut);
      }
    },
  };
});

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

function buildUserOptions(records: PaymentRecord[]) {
  const seen = new Map<string, string>();
  for (const record of records) {
    seen.set(record.created_by_user_id, record.operator_full_name);
  }

  return [...seen.entries()].map(([value, label]) => ({ label, value }));
}

function getVisiblePayments(
  scope: string,
  query: string,
  category: string,
  paymentMethod: string,
  createdByUserId: string,
) {
  const normalizedQuery = query.trim().toLowerCase();

  return [...seededPayments, ...createdPayments].filter((payment) => {
    if (scope === "CURRENT_SHIFT" && payment.scope_tag !== "CURRENT_SHIFT") {
      return false;
    }
    if (scope === "TODAY" && !payment.created_at_utc.startsWith("2026-04-22")) {
      return false;
    }
    if (category && payment.category_code !== category) {
      return false;
    }
    if (paymentMethod && payment.payment_method_code !== paymentMethod) {
      return false;
    }
    if (createdByUserId && payment.created_by_user_id !== createdByUserId) {
      return false;
    }
    if (normalizedQuery.length === 0) {
      return true;
    }

    return (
      payment.folio.toLowerCase().includes(normalizedQuery) ||
      payment.concept.toLowerCase().includes(normalizedQuery) ||
      payment.payee_name.toLowerCase().includes(normalizedQuery)
    );
  });
}

function toPaymentDetail(record: PaymentRecord): OperationalPaymentDetailResponse {
  return {
    active_cash_session_id: "cash-session-1",
    affects_cash_drawer: record.affects_cash_drawer,
    branch: bootstrapResponse.branch,
    category_code: record.category_code,
    category_name: record.category_name,
    cash_amount: record.cash_amount,
    committed_at_utc: record.created_at_utc,
    concept: record.concept,
    created_at_utc: record.created_at_utc,
    created_by: bootstrapResponse.user,
    currency_code: record.currency_code,
    folio: record.folio,
    id: record.id,
    non_cash_amount: record.non_cash_amount,
    notes: record.id === "payment-1" ? "Pago validado" : null,
    payee_name: record.payee_name,
    payment_method_code: record.payment_method_code,
    status: record.status,
    total_amount: record.total_amount,
    workstation: bootstrapResponse.workstation,
  };
}

vi.mock("./queries", () => ({
  paymentDetailQueryKey: (workstationCode: string, paymentId: string) => {
    void workstationCode;
    return ["payment-detail", paymentId];
  },
  paymentsBootstrapQueryKey: () => ["payments-bootstrap"],
  usePaymentsBootstrapQuery: () => ({
    data: bootstrapResponse,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  usePaymentsListQuery: (
    scope: string,
    query: string,
    category: string,
    paymentMethod: string,
    createdByUserId: string,
  ) => ({
    data: {
      available_users: buildUserOptions(getVisiblePayments("RECENT", "", "", "", "")),
      category: category || null,
      created_by_user_id: createdByUserId || null,
      payment_method: paymentMethod || null,
      payments: getVisiblePayments(scope, query, category, paymentMethod, createdByUserId),
      query: query || null,
      scope,
      workstation_code: "POS-01",
    },
    error: null,
    isPending: false,
  }),
  usePaymentDetailQuery: (paymentId: string | null) => {
    const payment = [...seededPayments, ...createdPayments].find((record) => record.id === paymentId);

    return {
      data: payment ? toPaymentDetail(payment) : null,
      error: null,
      isPending: false,
    };
  },
}));

vi.mock("./payments-api", () => ({
  createPayment: vi.fn(),
}));

function renderUi(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);

  const root = createRoot(container);
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

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

function setControlValue(
  input: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement,
  value: string,
) {
  const prototype =
    input instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : input instanceof HTMLSelectElement
        ? HTMLSelectElement.prototype
        : HTMLInputElement.prototype;

  const valueSetter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;

  act(() => {
    valueSetter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

async function flushPromises() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function triggerShortcut(shortcutId: string) {
  const shortcut = registeredShortcuts.get(shortcutId);
  if (!shortcut) {
    throw new Error(`Shortcut ${shortcutId} was not registered.`);
  }

  act(() => {
    shortcut.handler(new KeyboardEvent("keydown", { bubbles: true, cancelable: true }));
  });
}

function triggerShortcutByLabel(label: string) {
  const shortcut = [...registeredShortcuts.values()].find((candidate) => candidate.label === label);
  if (!shortcut) {
    throw new Error(`Shortcut ${label} was not registered.`);
  }

  act(() => {
    shortcut.handler(new KeyboardEvent("keydown", { bubbles: true, cancelable: true }));
  });
}

let mountedRoots: Array<() => void> = [];

beforeEach(() => {
  seededPayments = [...basePayments];
  createdPayments = [];
  registeredShortcuts.clear();
  refetchMock.mockReset();
  showErrorMock.mockReset();
  showSuccessMock.mockReset();

  vi.mocked(createPayment).mockImplementation(async ({ payload }) => {
    const totalAmount = String(payload.total_amount);
    const newRecord: PaymentRecord = {
      affects_cash_drawer: payload.payment_method_code === "CASH",
      ...operationalLocation,
      cash_amount: payload.payment_method_code === "CASH" ? totalAmount : "0.00",
      category_code: payload.category_code ?? null,
      category_name:
        bootstrapResponse.active_categories.find((category) => category.code === payload.category_code)
          ?.name ?? null,
      concept: payload.concept,
      created_at_utc: "2026-04-22T19:30:00Z",
      created_by_user_id: bootstrapResponse.user.id,
      currency_code: "MXN",
      folio: "PAG-NEW001",
      id: "payment-new",
      non_cash_amount: payload.payment_method_code === "CASH" ? "0.00" : totalAmount,
      operator_full_name: bootstrapResponse.user.full_name,
      payee_name: payload.payee_name,
      payment_method_code: payload.payment_method_code,
      scope_tag: "CURRENT_SHIFT",
      status: "COMMITTED",
      total_amount: totalAmount,
    };

    createdPayments = [newRecord, ...createdPayments];
    return toPaymentDetail(newRecord);
  });
});

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

describe("PaymentsScreen", () => {
  it("shows a compact empty state and opens create from the registered shortcut", async () => {
    seededPayments = [];
    const view = renderUi(<PaymentsScreen />);
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("Sin pagos registrados");
    expect(view.container.textContent).toContain("Sin pagos registrados en turno actual.");

    triggerShortcut("payments-new");
    await flushPromises();

    expect(view.container.textContent).toContain("Registrar pago operativo");
    expect(view.container.textContent).toContain("Beneficiario");
  });

  it("focuses search and supports keyboard row selection", async () => {
    const view = renderUi(<PaymentsScreen />);
    mountedRoots.push(view.unmount);

    const searchInput = view.container.querySelector(
      'input[aria-label="Buscar pago por folio, referencia o beneficiario"]',
    ) as HTMLInputElement | null;
    expect(searchInput).not.toBeNull();

    triggerShortcutByLabel("Buscar en lista");
    await flushPromises();

    expect(document.activeElement).toBe(searchInput);

    click(
      Array.from(view.container.querySelectorAll("button")).find((button) =>
        button.textContent?.includes("Recientes"),
      ),
    );
    await flushPromises();

    const rows = Array.from(view.container.querySelectorAll("tbody tr"));
    expect(rows).toHaveLength(2);

    const firstRow = rows[0] as HTMLTableRowElement;
    firstRow.focus();
    dispatchElementKey(firstRow, "ArrowDown");
    await flushPromises();

    const secondRow = view.container.querySelectorAll("tbody tr")[1] as HTMLTableRowElement;
    expect(document.activeElement).toBe(secondRow);

    dispatchElementKey(secondRow, "Enter");
    await flushPromises();

    expect(secondRow.getAttribute("aria-selected")).toBe("true");
  });

  it("creates a cash payment with confirmation and success feedback", async () => {
    const view = renderUi(<PaymentsScreen />);
    mountedRoots.push(view.unmount);

    triggerShortcut("payments-new");
    await flushPromises();

    setControlValue(
      view.container.querySelector('input[aria-label="Beneficiario del pago"]') as HTMLInputElement,
      "Proveedor Norte",
    );
    setControlValue(
      view.container.querySelector('select[aria-label="Categoria del pago"]') as HTMLSelectElement,
      "SUPPLIER",
    );
    setControlValue(
      view.container.querySelector('input[aria-label="Referencia del pago"]') as HTMLInputElement,
      "REF-9001",
    );
    setControlValue(
      view.container.querySelector('input[aria-label="Monto del pago"]') as HTMLInputElement,
      "250.00",
    );

    click(
      Array.from(view.container.querySelectorAll("button")).find((button) =>
        button.textContent?.includes("Efectivo"),
      ),
    );
    await flushPromises();

    triggerShortcut("payments-submit");
    await flushPromises();

    expect(view.container.textContent).toContain("Confirmar salida de caja");
    expect(view.container.textContent).toContain("REF-9001");

    click(
      Array.from(view.container.querySelectorAll("button")).find((button) =>
        button.textContent?.includes("Confirmar pago"),
      ),
    );
    await flushPromises();

    expect(vi.mocked(createPayment)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(createPayment).mock.calls[0]?.[0].payload).toMatchObject({
      category_code: "SUPPLIER",
      concept: "REF-9001",
      payee_name: "Proveedor Norte",
      payment_method_code: "CASH",
      total_amount: "250.00",
    });
    expect(showSuccessMock).toHaveBeenCalledWith("Pago PAG-NEW001 registrado por $250.00.");
    expect(view.container.textContent).toContain("PAG-NEW001");
  });
});

describe("PaymentsRightPanel", () => {
  it("shows validation blockers in create mode", () => {
    const view = renderUi(
      <PaymentsRightPanel
        blockedReason="Captura el beneficiario del pago."
        categories={[...bootstrapResponse.active_categories]}
        createError={null}
        draft={createInitialOperationalPaymentDraftState()}
        isConfirmPending={false}
        isDetailPending={false}
        mode="create"
        onCancelCreate={() => undefined}
        onCommitCreate={() => undefined}
        onResultAction={() => undefined}
        paymentCount={0}
        paymentDetail={null}
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("Nuevo pago");
    expect(view.container.textContent).toContain("Captura el beneficiario del pago.");
    expect(view.container.textContent).toContain("Monto");
  });

  it("shows compact detail for a selected payment", () => {
    const detail = toPaymentDetail({
      ...basePayments[0]!,
      concept: "REF-9001",
      folio: "PAG-NEW001",
      id: "payment-new",
      payee_name: "Proveedor Norte",
      total_amount: "250.00",
    });
    const onResultAction = vi.fn();

    const view = renderUi(
      <PaymentsRightPanel
        blockedReason={null}
        categories={[...bootstrapResponse.active_categories]}
        createError={null}
        draft={createInitialOperationalPaymentDraftState()}
        isConfirmPending={false}
        isDetailPending={false}
        mode="list"
        onCancelCreate={() => undefined}
        onCommitCreate={() => undefined}
        onResultAction={onResultAction}
        paymentCount={1}
        paymentDetail={detail}
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("PAG-NEW001");
    expect(view.container.textContent).toContain("Proveedor Norte");

    click(
      Array.from(view.container.querySelectorAll("button")).find((button) =>
        button.textContent?.includes("Nuevo pago"),
      ),
    );

    expect(onResultAction).toHaveBeenCalledWith("newOperation");
  });
});
