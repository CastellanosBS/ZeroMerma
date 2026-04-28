// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  OperationalDiscountDetailResponse,
  OperationalDiscountListItemView,
} from "../../lib/api-contracts";
import { createInitialOperationalDiscountDraftState } from "./model";
import { createDiscount } from "./discounts-api";
import { DiscountsRightPanel, DiscountsScreen } from "./discounts-screen";

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
    { code: "PAYROLL", display_order: 10, name: "Nomina" },
    { code: "SUPPLIER", display_order: 20, name: "Proveedor" },
  ],
  active_discount_methods: [
    {
      affects_cash_drawer: true,
      code: "CASH",
      helper_text: "Aumenta el efectivo esperado del turno.",
      is_enabled: true,
      label: "Efectivo",
    },
    {
      affects_cash_drawer: false,
      code: "CARD",
      helper_text: "Queda auditado sin mover efectivo.",
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
  discount_controls: {
    high_value_amount_threshold: "200.00",
    high_value_requires_acknowledgement: true,
  },
  discount_registration_allowed: true,
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

type DiscountRecord = OperationalDiscountListItemView & {
  created_by_user_id: string;
  scope_tag: "CURRENT_SHIFT" | "RECENT";
};

const operationalLocation = {
  branch_code: bootstrapResponse.branch.code,
  branch_name: bootstrapResponse.branch.name,
  workstation_code: bootstrapResponse.workstation.code,
  workstation_name: bootstrapResponse.workstation.name,
} as const;

const baseDiscounts: DiscountRecord[] = [
  {
    affects_cash_drawer: true,
    ...operationalLocation,
    cash_amount: "160.00",
    category_code: "PAYROLL",
    category_name: "Nomina",
    concept: "Prestamo interno abril",
    created_at_utc: "2026-04-22T18:10:00Z",
    created_by_user_id: "user-1",
    currency_code: "MXN",
    folio: "DES-AAA001",
    id: "discount-1",
    non_cash_amount: "0.00",
    operator_full_name: "Main Branch Cashier",
    payment_method_code: "CASH",
    scope_tag: "CURRENT_SHIFT",
    status: "COMMITTED",
    subject_name: "Sergio Castellanos",
    total_amount: "160.00",
  },
  {
    affects_cash_drawer: false,
    ...operationalLocation,
    cash_amount: "0.00",
    category_code: "SUPPLIER",
    category_name: "Proveedor",
    concept: "Bonificacion proveedor",
    created_at_utc: "2026-04-21T16:00:00Z",
    created_by_user_id: "user-2",
    currency_code: "MXN",
    folio: "DES-BBB002",
    id: "discount-2",
    non_cash_amount: "90.00",
    operator_full_name: "Second Operator",
    payment_method_code: "CARD",
    scope_tag: "RECENT",
    status: "COMMITTED",
    subject_name: "Proveedor Central",
    total_amount: "90.00",
  },
];

let seededDiscounts: DiscountRecord[] = [];
let createdDiscounts: DiscountRecord[] = [];

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

function buildUserOptions(records: DiscountRecord[]) {
  const seen = new Map<string, string>();
  for (const record of records) {
    seen.set(record.created_by_user_id, record.operator_full_name);
  }

  return [...seen.entries()].map(([value, label]) => ({ label, value }));
}

function getVisibleDiscounts(
  scope: string,
  query: string,
  category: string,
  paymentMethod: string,
  createdByUserId: string,
) {
  const normalizedQuery = query.trim().toLowerCase();

  return [...seededDiscounts, ...createdDiscounts].filter((discount) => {
    if (scope === "CURRENT_SHIFT" && discount.scope_tag !== "CURRENT_SHIFT") {
      return false;
    }
    if (scope === "TODAY" && !discount.created_at_utc.startsWith("2026-04-22")) {
      return false;
    }
    if (category && discount.category_code !== category) {
      return false;
    }
    if (paymentMethod && discount.payment_method_code !== paymentMethod) {
      return false;
    }
    if (createdByUserId && discount.created_by_user_id !== createdByUserId) {
      return false;
    }
    if (normalizedQuery.length === 0) {
      return true;
    }

    return (
      discount.folio.toLowerCase().includes(normalizedQuery) ||
      discount.concept.toLowerCase().includes(normalizedQuery) ||
      discount.subject_name.toLowerCase().includes(normalizedQuery) ||
      (discount.category_name ?? "").toLowerCase().includes(normalizedQuery)
    );
  });
}

function toDiscountDetail(record: DiscountRecord): OperationalDiscountDetailResponse {
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
    notes: record.id === "discount-1" ? "Descuento validado" : null,
    payment_method_code: record.payment_method_code,
    status: record.status,
    subject_name: record.subject_name,
    total_amount: record.total_amount,
    workstation: bootstrapResponse.workstation,
  };
}

vi.mock("./queries", () => ({
  discountDetailQueryKey: (workstationCode: string, discountId: string) => {
    void workstationCode;
    return ["discount-detail", discountId];
  },
  discountsBootstrapQueryKey: () => ["discounts-bootstrap"],
  useDiscountsBootstrapQuery: () => ({
    data: bootstrapResponse,
    error: null,
    isPending: false,
    refetch: refetchMock,
  }),
  useDiscountsListQuery: (
    scope: string,
    query: string,
    category: string,
    paymentMethod: string,
    createdByUserId: string,
  ) => ({
    data: {
      available_users: buildUserOptions(getVisibleDiscounts("RECENT", "", "", "", "")),
      category: category || null,
      created_by_user_id: createdByUserId || null,
      discounts: getVisibleDiscounts(scope, query, category, paymentMethod, createdByUserId),
      payment_method: paymentMethod || null,
      query: query || null,
      scope,
      workstation_code: "POS-01",
    },
    error: null,
    isPending: false,
  }),
  useDiscountDetailQuery: (discountId: string | null) => {
    const discount = [...seededDiscounts, ...createdDiscounts].find((record) => record.id === discountId);

    return {
      data: discount ? toDiscountDetail(discount) : null,
      error: null,
      isPending: false,
    };
  },
}));

vi.mock("./discounts-api", () => ({
  createDiscount: vi.fn(),
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
  seededDiscounts = [...baseDiscounts];
  createdDiscounts = [];
  registeredShortcuts.clear();
  refetchMock.mockReset();
  showErrorMock.mockReset();
  showSuccessMock.mockReset();

  vi.mocked(createDiscount).mockImplementation(async ({ payload }) => {
    const totalAmount = String(payload.total_amount);
    const newRecord: DiscountRecord = {
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
      folio: "DES-NEW001",
      id: "discount-new",
      non_cash_amount: payload.payment_method_code === "CASH" ? "0.00" : totalAmount,
      operator_full_name: bootstrapResponse.user.full_name,
      payment_method_code: payload.payment_method_code,
      scope_tag: "CURRENT_SHIFT",
      status: "COMMITTED",
      subject_name: payload.subject_name,
      total_amount: totalAmount,
    };

    createdDiscounts = [newRecord, ...createdDiscounts];
    return toDiscountDetail(newRecord);
  });
});

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

describe("DiscountsScreen", () => {
  it("shows an explanatory empty state and opens create from the registered shortcut", async () => {
    seededDiscounts = [];
    const view = renderUi(<DiscountsScreen />);
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("Sin descuentos para esta vista");
    expect(view.container.textContent).toContain("Los descuentos operativos registran cobros internos auditables");

    triggerShortcut("discounts-new");
    await flushPromises();

    expect(view.container.textContent).toContain("Registrar descuento operativo");
    expect(view.container.textContent).toContain("Persona o entidad");
  });

  it("focuses search and supports keyboard row selection", async () => {
    const view = renderUi(<DiscountsScreen />);
    mountedRoots.push(view.unmount);

    const searchInput = view.container.querySelector(
      'input[aria-label="Buscar descuento por folio, persona o entidad, categoria o referencia"]',
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

    expect(view.container.textContent).toContain("Descuento en vista");
  });

  it("requires high-value acknowledgement before confirming and then creates the discount", async () => {
    const view = renderUi(<DiscountsScreen />);
    mountedRoots.push(view.unmount);

    triggerShortcut("discounts-new");
    await flushPromises();

    setControlValue(
      view.container.querySelector('input[aria-label="Persona o entidad del descuento"]') as HTMLInputElement,
      "Sergio Castellanos",
    );
    setControlValue(
      view.container.querySelector('select[aria-label="Categoria del descuento"]') as HTMLSelectElement,
      "PAYROLL",
    );
    setControlValue(
      view.container.querySelector('input[aria-label="Motivo o referencia del descuento"]') as HTMLInputElement,
      "Prestamo interno abril",
    );
    setControlValue(
      view.container.querySelector('input[aria-label="Monto del descuento"]') as HTMLInputElement,
      "250.00",
    );

    click(
      Array.from(view.container.querySelectorAll("button")).find((button) =>
        button.textContent?.includes("Efectivo"),
      ),
    );
    await flushPromises();

    expect(view.container.textContent).toContain("Descuento alto");

    triggerShortcut("discounts-submit");
    await flushPromises();

    expect(view.container.textContent).not.toContain("Confirmar descuento");

    click(
      view.container.querySelector('input[type="checkbox"]'),
    );
    await flushPromises();

    triggerShortcut("discounts-submit");
    await flushPromises();

    expect(view.container.textContent).toContain("Confirmar descuento con impacto en caja");
    expect(view.container.textContent).toContain("Prestamo interno abril");

    click(
      Array.from(view.container.querySelectorAll("button")).find((button) =>
        button.textContent?.includes("Confirmar descuento"),
      ),
    );
    await flushPromises();

    expect(vi.mocked(createDiscount)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(createDiscount).mock.calls[0]?.[0].payload).toMatchObject({
      category_code: "PAYROLL",
      concept: "Prestamo interno abril",
      high_value_acknowledged: true,
      payment_method_code: "CASH",
      subject_name: "Sergio Castellanos",
      total_amount: "250.00",
    });
    expect(showSuccessMock).toHaveBeenCalledWith("Descuento DES-NEW001 registrado por $250.00.");
    expect(view.container.textContent).toContain("DES-NEW001");
  });
});

describe("DiscountsRightPanel", () => {
  it("shows validation blockers in create mode", () => {
    const view = renderUi(
      <DiscountsRightPanel
        blockedMessages={[
          "Captura la persona o entidad del descuento.",
          "Selecciona la categoria del descuento.",
        ]}
        blockedReason="Captura la persona o entidad del descuento."
        categories={[...bootstrapResponse.active_categories]}
        controls={bootstrapResponse.discount_controls}
        createError={null}
        draft={createInitialOperationalDiscountDraftState()}
        discountDetail={null}
        isConfirmPending={false}
        isCreateHighValue={false}
        isDetailPending={false}
        mode="create"
        onCancelCreate={() => undefined}
        onCommitCreate={() => undefined}
        onResultAction={() => undefined}
        recentCreatedDiscountId={null}
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("Nuevo descuento");
    expect(view.container.textContent).toContain("Captura la persona o entidad del descuento.");
    expect(view.container.textContent).toContain("Selecciona la categoria del descuento.");
  });

  it("shows success result with history action for a newly created discount", () => {
    const detail = toDiscountDetail({
      ...baseDiscounts[0]!,
      concept: "Prestamo interno abril",
      folio: "DES-NEW001",
      id: "discount-new",
      subject_name: "Sergio Castellanos",
      total_amount: "250.00",
    });
    const onResultAction = vi.fn();

    const view = renderUi(
      <DiscountsRightPanel
        blockedMessages={[]}
        blockedReason={null}
        categories={[...bootstrapResponse.active_categories]}
        controls={bootstrapResponse.discount_controls}
        createError={null}
        draft={createInitialOperationalDiscountDraftState()}
        discountDetail={detail}
        isConfirmPending={false}
        isCreateHighValue={false}
        isDetailPending={false}
        mode="list"
        onCancelCreate={() => undefined}
        onCommitCreate={() => undefined}
        onResultAction={onResultAction}
        recentCreatedDiscountId="discount-new"
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("Descuento registrado");
    expect(view.container.textContent).toContain("DES-NEW001");
    expect(view.container.textContent).toContain("Ver historial");

    click(
      Array.from(view.container.querySelectorAll("button")).find((button) =>
        button.textContent?.includes("Ver historial"),
      ),
    );

    expect(onResultAction).toHaveBeenCalledWith("viewHistory");
  });
});
