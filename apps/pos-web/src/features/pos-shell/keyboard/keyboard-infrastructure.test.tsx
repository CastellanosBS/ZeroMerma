// @vitest-environment jsdom

import { act, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import { KeyboardHelpOverlay } from "./keyboard-help-overlay";
import { KeyboardShortcutRegistry } from "./keyboard-shortcut-registry";
import { useFocusFlow } from "./use-focus-flow";
import { useModuleHotkeys } from "./use-module-hotkeys";
import { useRovingFocusGrid } from "./use-roving-focus-grid";

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

function dispatchKey(
  target: EventTarget,
  key: string,
  options?: Partial<KeyboardEventInit>,
) {
  const event = new KeyboardEvent("keydown", {
    bubbles: true,
    cancelable: true,
    key,
    ...options,
  });

  act(() => {
    target.dispatchEvent(event);
  });

  return event;
}

function focusElement(element: HTMLElement) {
  act(() => {
    element.focus();
  });
}

function RovingGridDemo() {
  const labels = ["Uno", "Dos", "Tres", "Cuatro"];
  const [activated, setActivated] = useState("");
  const { getItemProps } = useRovingFocusGrid({
    columnCount: 2,
    itemCount: labels.length,
    onActivate: (index) => setActivated(labels[index]!),
  });

  return (
    <div>
      <div role="grid">
        {labels.map((label, index) => (
          <button key={label} type="button" {...getItemProps(index)}>
            {label}
          </button>
        ))}
      </div>
      <output data-testid="activated">{activated}</output>
    </div>
  );
}

function FocusFlowDemo() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scopeProps } = useFocusFlow({ containerRef });

  return (
    <div ref={containerRef} {...scopeProps}>
      <button type="button">Primero</button>
      <button type="button">Segundo</button>
    </div>
  );
}

function RegistryDemo() {
  const shortcuts = useMemo(
    () => [
      {
        chords: ["Ctrl+K"],
        description: "Abre una accion de ejemplo.",
        group: "Modulo",
        handler: () => undefined,
        id: "demo-shortcut",
        label: "Abrir demo",
      },
    ],
    [],
  );

  useModuleHotkeys(shortcuts);

  return <KeyboardHelpOverlay />;
}

let mountedRoots: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

describe("keyboard infrastructure", () => {
  it("moves roving focus with arrows and activates the selected item with Enter", () => {
    const view = renderUi(<RovingGridDemo />);
    mountedRoots.push(view.unmount);

    const buttons = Array.from(view.container.querySelectorAll("button"));
    const activated = view.container.querySelector('[data-testid="activated"]');

    expect(buttons).toHaveLength(4);

    focusElement(buttons[0]!);
    expect(document.activeElement).toBe(buttons[0]);

    dispatchKey(buttons[0]!, "ArrowRight");
    expect(document.activeElement).toBe(buttons[1]);

    dispatchKey(buttons[1]!, "ArrowDown");
    expect(document.activeElement).toBe(buttons[3]);

    dispatchKey(buttons[3]!, "Enter");
    expect(activated?.textContent).toBe("Cuatro");
  });

  it("keeps Tab navigation inside the focus flow scope at the boundaries", () => {
    const view = renderUi(<FocusFlowDemo />);
    mountedRoots.push(view.unmount);

    const buttons = Array.from(view.container.querySelectorAll("button"));

    focusElement(buttons[1]!);
    dispatchKey(buttons[1]!, "Tab");
    expect(document.activeElement).toBe(buttons[0]);

    focusElement(buttons[0]!);
    dispatchKey(buttons[0]!, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(buttons[1]);
  });

  it("opens the keyboard help overlay with F1 and shows registered shortcuts", () => {
    const view = renderUi(
      <KeyboardShortcutRegistry>
        <RegistryDemo />
      </KeyboardShortcutRegistry>,
    );
    mountedRoots.push(view.unmount);

    dispatchKey(window, "F1");

    expect(view.container.textContent).toContain("Atajos del POS");
    expect(view.container.textContent).toContain("Abrir demo");
    expect(view.container.textContent).toContain("Abrir ayuda de teclado");
  });
});
