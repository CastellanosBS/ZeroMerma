// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CashSessionOpenForm } from "./cash-session-open-form";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

function renderUi(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);

  const root = createRoot(container);
  act(() => {
    root.render(element);
  });

  return {
    container,
    unmount: () => {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

function dispatchInput(target: HTMLInputElement, value: string) {
  const setNativeValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;

  act(() => {
    setNativeValue?.call(target, value);
    target.dispatchEvent(new Event("input", { bubbles: true }));
    target.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function dispatchKey(target: EventTarget, key: string) {
  act(() => {
    target.dispatchEvent(
      new KeyboardEvent("keydown", {
        bubbles: true,
        cancelable: true,
        key,
      }),
    );
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
    authorization_surface: "POS" as const,
    authorization_version: "test-authorization-v1",
    is_superadministrator: false,
    default_surface: "POS" as const,
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
};

const longBootstrap = {
  ...bootstrap,
  branch: {
    ...bootstrap.branch,
    name: "Main Branch With A Very Long Operational Name",
  },
  local_timestamp: "2026-04-13T10:00:00Z",
  user: {
    ...bootstrap.user,
    full_name: "Main Branch Cashier With A Very Long Full Name",
  },
  workstation: {
    ...bootstrap.workstation,
    name: "Front Register 01 With Long Workstation Name",
  },
};

let mountedRoots: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

describe("CashSessionOpenForm", () => {
  it("focuses opening amount on mount and submits zero amount with NumpadEnter", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const view = renderUi(
      <CashSessionOpenForm
        bootstrap={bootstrap}
        isSubmitDisabled={false}
        onSubmit={onSubmit}
        submitError={null}
      />,
    );
    mountedRoots.push(view.unmount);

    const input = view.container.querySelector("#opening-amount") as HTMLInputElement;

    await act(async () => {
      await Promise.resolve();
    });

    expect(document.activeElement).toBe(input);
    expect(view.container.textContent).toContain("Cajero");
    expect(view.container.textContent).toContain("Sucursal");
    expect(view.container.textContent).toContain("Caja");
    expect(view.container.textContent).toContain("Estado");
    expect(view.container.textContent).toContain("Main Branch Cashier");
    expect(view.container.textContent).toContain("Front Register 01");
    expect(view.container.textContent).toContain("Pendiente");

    dispatchInput(input, "0.00");
    dispatchKey(input, "NumpadEnter");

    await act(async () => {
      await Promise.resolve();
    });

    expect(onSubmit).toHaveBeenCalledWith({ openingAmount: "0.00" });
  });

  it("submits a positive amount with Enter and keeps helper copy visible", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const view = renderUi(
      <CashSessionOpenForm
        bootstrap={bootstrap}
        isSubmitDisabled={false}
        onSubmit={onSubmit}
        submitError={null}
      />,
    );
    mountedRoots.push(view.unmount);

    const input = view.container.querySelector("#opening-amount") as HTMLInputElement;
    expect(view.container.textContent).toContain(
      "Captura el efectivo contado antes de la primera venta.",
    );

    await act(async () => {
      await Promise.resolve();
    });

    dispatchInput(input, "150.00");
    dispatchKey(input, "Enter");

    await act(async () => {
      await Promise.resolve();
    });

    expect(onSubmit).toHaveBeenCalledWith({ openingAmount: "150.00" });
  });

  it("keeps long context values available through title attributes", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const view = renderUi(
      <CashSessionOpenForm
        bootstrap={longBootstrap}
        isSubmitDisabled={false}
        onSubmit={onSubmit}
        submitError={null}
      />,
    );
    mountedRoots.push(view.unmount);

    await act(async () => {
      await Promise.resolve();
    });

    expect(
      view.container.querySelector('[title="Main Branch Cashier With A Very Long Full Name"]'),
    ).not.toBeNull();
    expect(
      view.container.querySelector('[title="Main Branch With A Very Long Operational Name"]'),
    ).not.toBeNull();
    expect(
      view.container.querySelector('[title="Front Register 01 With Long Workstation Name"]'),
    ).not.toBeNull();
    expect(view.container.textContent).toContain("Pendiente");
  });
});
