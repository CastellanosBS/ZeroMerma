// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShellSidebar } from "./app-shell-sidebar";
import { posModules } from "../features/pos-shell/modules";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

function renderUi(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);

  const root = createRoot(container);
  act(() => {
    root.render(element);
  });

  return {
    container,
    root,
    unmount: () => {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

let mountedRoots: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

describe("AppShellSidebar", () => {
  it("does not render the release-hidden operational discounts module", () => {
    const view = renderUi(
      <AppShellSidebar
        activeModuleKey="pos"
        collapsed={false}
        hasCashSession={true}
        isKeyboardNavigationEnabled={true}
        modules={posModules}
        onNavigate={() => undefined}
        onNavigationModeChange={() => undefined}
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).not.toContain("Descuentos");
    expect(view.container.querySelector('[title*="Ctrl+Alt+F"]')).toBeNull();
  });

  it("marks the active module accessibly and preserves collapsed labels via aria", () => {
    const view = renderUi(
      <AppShellSidebar
        activeModuleKey="orders"
        collapsed={true}
        hasCashSession={true}
        isKeyboardNavigationEnabled={false}
        modules={posModules}
        onNavigate={() => undefined}
        onNavigationModeChange={() => undefined}
      />,
    );
    mountedRoots.push(view.unmount);

    const activeButton = view.container.querySelector<HTMLButtonElement>(
      '[data-pos-shell-nav-item][aria-current="page"]',
    );

    expect(activeButton?.getAttribute("aria-label")).toContain("Pedidos");
    expect(activeButton?.getAttribute("title")).toContain("Pedidos");
    expect(
      activeButton?.querySelector(".pos-shell-nav-item__tooltip")?.textContent,
    ).toContain("Ctrl+Alt+O");
  });

  it("keeps sidebar items out of tab order until keyboard navigation is enabled", () => {
    const onNavigate = vi.fn();

    const view = renderUi(
      <AppShellSidebar
        activeModuleKey="pos"
        collapsed={false}
        hasCashSession={false}
        isKeyboardNavigationEnabled={false}
        modules={posModules}
        onNavigate={onNavigate}
        onNavigationModeChange={() => undefined}
      />,
    );
    mountedRoots.push(view.unmount);

    const buttons = Array.from(
      view.container.querySelectorAll<HTMLButtonElement>('[data-pos-shell-nav-item="true"]'),
    );

    expect(buttons[0]?.tabIndex).toBe(-1);
    expect(buttons[1]?.tabIndex).toBe(-1);
    expect(buttons[1]?.disabled).toBe(true);

    act(() => {
      view.root.render(
        <AppShellSidebar
          activeModuleKey="pos"
          collapsed={false}
          hasCashSession={false}
          isKeyboardNavigationEnabled={true}
          modules={posModules}
          onNavigate={onNavigate}
          onNavigationModeChange={() => undefined}
        />,
      );
    });

    const rerenderedButtons = Array.from(
      view.container.querySelectorAll<HTMLButtonElement>('[data-pos-shell-nav-item="true"]'),
    );

    expect(rerenderedButtons[0]?.tabIndex).toBe(0);
    expect(rerenderedButtons[1]?.tabIndex).toBe(-1);
  });
});
