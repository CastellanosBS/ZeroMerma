// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FlowGuide, ProgressStepper } from "./pos-module-primitives";

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
    unmount: () => {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
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

let mountedRoots: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

describe("ProgressStepper", () => {
  it("renders compact current and total progress text", () => {
    const view = renderUi(
      <ProgressStepper
        currentLabel="Cantidad"
        currentStep={2}
        stepLabels={["Clase", "Cantidad", "Resumen"]}
        totalSteps={3}
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("Paso 2 de 3");
    expect(view.container.textContent).toContain("Cantidad");
    expect(view.container.querySelector("[role='progressbar']")).not.toBeNull();
  });

  it("does not add focusable controls when it is progress-only", () => {
    const onStepClick = vi.fn();
    const view = renderUi(
      <ProgressStepper
        currentStep={1}
        onStepClick={onStepClick}
        stepLabels={["Cajero", "Estacion", "Apertura"]}
        totalSteps={3}
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.querySelectorAll("button")).toHaveLength(0);
    expect(onStepClick).not.toHaveBeenCalled();
  });

  it("preserves click and keyboard activation when it is navigational", () => {
    const onStepClick = vi.fn();
    const view = renderUi(
      <ProgressStepper
        clickable
        currentStep={1}
        onStepClick={onStepClick}
        steps={[
          { id: "sale", label: "Venta", state: "current" },
          { id: "payment", label: "Cobro" },
          { disabled: true, id: "confirm", label: "Confirmacion", state: "blocked" },
        ]}
      />,
    );
    mountedRoots.push(view.unmount);

    const buttons = view.container.querySelectorAll("button");
    expect(buttons).toHaveLength(3);
    expect(buttons[2].disabled).toBe(true);

    act(() => {
      buttons[1].click();
    });
    dispatchKey(buttons[0], "Enter");

    expect(onStepClick).toHaveBeenCalledWith("payment");
    expect(onStepClick).toHaveBeenCalledWith("sale");
    expect(onStepClick).not.toHaveBeenCalledWith("confirm");
  });
});

describe("FlowGuide", () => {
  it("uses the compact progress pattern for existing flow-guide callers", () => {
    const view = renderUi(
      <FlowGuide
        activeStepKey="product"
        steps={[
          { key: "class", label: "Clase" },
          { key: "product", label: "Producto" },
          { key: "quantity", label: "Cantidad" },
        ]}
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("Paso 2 de 3");
    expect(view.container.textContent).toContain("Producto");
    expect(view.container.querySelectorAll("button")).toHaveLength(0);
  });

  it("keeps FlowGuide navigable only when onStepSelect is provided", () => {
    const onStepSelect = vi.fn();
    const view = renderUi(
      <FlowGuide
        activeStepKey="class"
        onStepSelect={onStepSelect}
        steps={[
          { key: "class", label: "Clase" },
          { key: "product", label: "Producto" },
        ]}
      />,
    );
    mountedRoots.push(view.unmount);

    const buttons = view.container.querySelectorAll("button");
    expect(buttons).toHaveLength(2);

    dispatchKey(buttons[1], " ");

    expect(onStepSelect).toHaveBeenCalledWith("product");
  });
});
