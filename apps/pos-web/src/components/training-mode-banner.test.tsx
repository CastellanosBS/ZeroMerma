// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import { TrainingModeBanner } from "./training-mode-banner";

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

let mountedRoots: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

describe("TrainingModeBanner", () => {
  it("renders nothing when training mode is disabled", () => {
    const view = renderUi(<TrainingModeBanner trainingMode={null} />);
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toBe("");
  });

  it("shows the explicit training banner and safeguard note", () => {
    const view = renderUi(
      <TrainingModeBanner
        trainingMode={{
          is_enabled: true,
          label: "Modo entrenamiento",
          safeguard_note: "Usa una base de datos separada para entrenamiento.",
        }}
      />,
    );
    mountedRoots.push(view.unmount);

    expect(view.container.textContent).toContain("Modo entrenamiento");
    expect(view.container.textContent).toContain("base de datos separada");
  });
});
