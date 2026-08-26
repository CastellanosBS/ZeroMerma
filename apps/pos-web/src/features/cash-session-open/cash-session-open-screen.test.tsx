// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, type ReactElement, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CashSessionView, PosBootstrapResponse } from "../../lib/api-contracts";
import { openCashSession } from "./cash-session-api";
import { CashSessionOpenScreen } from "./cash-session-open-screen";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const routerMocks = vi.hoisted(() => ({
  navigate: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
}));

const queryState = vi.hoisted(() => ({
  bootstrap: null as unknown as QueryState<PosBootstrapResponse>,
  cashSession: null as unknown as QueryState<CashSessionView | null>,
}));

const authStoreMock = vi.hoisted(() => ({
  accessToken: "token",
}));

const statusMessageMocks = vi.hoisted(() => ({
  showSuccess: vi.fn(),
}));

type QueryState<TData> = {
  data: TData;
  error: unknown;
  isPending: boolean;
  refetch: () => void;
};

vi.mock("@tanstack/react-router", () => ({
  Navigate: ({ to }: { to: string }) => <div data-testid="navigate">{to}</div>,
  useNavigate: () => routerMocks.navigate,
}));

vi.mock("../auth/auth-store", () => ({
  usePosAuthStore: (selector: (state: { accessToken: string | null }) => unknown) =>
    selector({ accessToken: authStoreMock.accessToken }),
}));

vi.mock("../pos-bootstrap/queries", () => ({
  bootstrapQueryKey: () => ["pos-bootstrap", "POS-01"],
  usePosBootstrapQuery: () => queryState.bootstrap,
}));

vi.mock("../status-messages/store", () => ({
  useStatusMessageStore: (
    selector: (state: { showSuccess: typeof statusMessageMocks.showSuccess }) => unknown,
  ) => selector({ showSuccess: statusMessageMocks.showSuccess }),
}));

vi.mock("./cash-session-api", () => ({
  openCashSession: vi.fn(),
}));

vi.mock("./queries", () => ({
  currentCashSessionQueryKey: () => ["current-cash-session", "POS-01"],
  useCurrentCashSessionQuery: () => queryState.cashSession,
}));

function renderUi(element: ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  const root = createRoot(container);

  act(() => {
    root.render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
  });

  return {
    container,
    queryClient,
    unmount: () => {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

function setInputValue(target: HTMLInputElement, value: string) {
  const setNativeValue = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value",
  )?.set;

  act(() => {
    setNativeValue?.call(target, value);
    target.dispatchEvent(new Event("input", { bubbles: true }));
    target.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function clickButton(button: HTMLButtonElement) {
  act(() => {
    button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  });
}

async function flushAsync() {
  await act(async () => {
    await Promise.resolve();
  });
}

const bootstrap = {
  active_cash_session: null,
  branch: {
    code: "MAIN",
    id: "branch-1",
    is_active: true,
    name: "Main Branch",
    timezone: "America/Hermosillo",
  },
  local_timestamp: "2026-04-13T10:00:00Z",
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
} satisfies PosBootstrapResponse;

const openCashSessionView = {
  branch_code: "MAIN",
  branch_id: "branch-1",
  branch_name: "Main Branch",
  id: "cash-session-1",
  opening_amount: "250.00",
  opened_at: "2026-04-13T10:01:00Z",
  status: "OPEN",
  user_email: "cashier@zeromerma.local",
  user_full_name: "Main Branch Cashier",
  user_id: "user-1",
  workstation_code: "POS-01",
  workstation_id: "workstation-1",
  workstation_name: "Front Register 01",
} satisfies CashSessionView;

let mountedRoots: Array<() => void> = [];

beforeEach(() => {
  queryState.bootstrap = {
    data: bootstrap,
    error: null,
    isPending: false,
    refetch: vi.fn(),
  };
  queryState.cashSession = {
    data: null,
    error: null,
    isPending: false,
    refetch: vi.fn(),
  };
  authStoreMock.accessToken = "token";
  routerMocks.navigate.mockClear();
  statusMessageMocks.showSuccess.mockClear();
  vi.mocked(openCashSession).mockReset();
});

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

function screenWithProviders(): ReactNode {
  return <CashSessionOpenScreen />;
}

describe("CashSessionOpenScreen", () => {
  it("routes directly to POS when a cash session is already open", () => {
    queryState.cashSession = {
      data: openCashSessionView,
      error: null,
      isPending: false,
      refetch: vi.fn(),
    };

    const view = renderUi(<>{screenWithProviders()}</>);
    mountedRoots.push(view.unmount);

    expect(view.container.querySelector("[data-testid='navigate']")?.textContent).toBe("/pos");
    expect(view.container.textContent).not.toContain("Esta caja ya esta abierta");
  });

  it("shows the opening amount step when there is no active cash session", () => {
    const view = renderUi(<>{screenWithProviders()}</>);
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("Registrar apertura");
    expect(view.container.querySelector("#opening-amount")).not.toBeNull();
  });

  it("opens the cash session and navigates directly to POS without a success panel", async () => {
    vi.mocked(openCashSession).mockResolvedValue(openCashSessionView);
    const view = renderUi(<>{screenWithProviders()}</>);
    mountedRoots.push(view.unmount);

    const input = view.container.querySelector("#opening-amount") as HTMLInputElement;
    const button = [...view.container.querySelectorAll("button")].find(
      (candidate) => candidate.textContent === "Abrir caja",
    ) as HTMLButtonElement;

    setInputValue(input, "250.00");
    clickButton(button);

    await flushAsync();
    await flushAsync();

    expect(openCashSession).toHaveBeenCalledWith({
      accessToken: "token",
      payload: {
        opening_amount: "250.00",
        workstation_code: "POS-01",
      },
      requestId: expect.stringMatching(/^cash-session-open-/),
    });
    expect(statusMessageMocks.showSuccess).toHaveBeenCalledWith("Caja abierta \u00b7 Turno iniciado");
    expect(routerMocks.navigate).toHaveBeenCalledWith({ to: "/pos" });
    expect(view.container.textContent).not.toContain("La apertura quedo registrada");
    expect(view.container.textContent).not.toContain("Ir al POS");
  });

  it("keeps the cashier on the opening screen with the typed amount when opening fails", async () => {
    vi.mocked(openCashSession).mockRejectedValue(new Error("backend unavailable"));
    const view = renderUi(<>{screenWithProviders()}</>);
    mountedRoots.push(view.unmount);

    const input = view.container.querySelector("#opening-amount") as HTMLInputElement;
    const button = [...view.container.querySelectorAll("button")].find(
      (candidate) => candidate.textContent === "Abrir caja",
    ) as HTMLButtonElement;

    setInputValue(input, "150.00");
    clickButton(button);

    await flushAsync();
    await flushAsync();

    expect(routerMocks.navigate).not.toHaveBeenCalled();
    expect(input.value).toBe("150.00");
    expect(view.container.textContent).toContain("backend unavailable");
  });

  it("disables the submit button while the opening request is in flight", async () => {
    let resolveOpening: (value: CashSessionView) => void = () => undefined;
    vi.mocked(openCashSession).mockReturnValue(
      new Promise<CashSessionView>((resolve) => {
        resolveOpening = resolve;
      }),
    );
    const view = renderUi(<>{screenWithProviders()}</>);
    mountedRoots.push(view.unmount);

    const input = view.container.querySelector("#opening-amount") as HTMLInputElement;
    const button = [...view.container.querySelectorAll("button")].find(
      (candidate) => candidate.textContent === "Abrir caja",
    ) as HTMLButtonElement;

    setInputValue(input, "100.00");
    clickButton(button);
    await flushAsync();

    expect(openCashSession).toHaveBeenCalledTimes(1);
    expect(button.disabled).toBe(true);

    clickButton(button);
    expect(openCashSession).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveOpening(openCashSessionView);
      await Promise.resolve();
    });
  });
});
