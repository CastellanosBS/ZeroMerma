// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  CopyFolioAction,
  DocumentActionsMenu,
  PrintAction,
} from "./document-actions";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

let mountedRoots: Array<() => void> = [];
const writeTextMock = vi.fn();

beforeEach(() => {
  vi.useFakeTimers();
  writeTextMock.mockReset();
  Object.defineProperty(window.navigator, "clipboard", {
    configurable: true,
    value: {
      writeText: writeTextMock,
    },
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

function renderUi(element: ReactElement) {
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

describe("document action framework", () => {
  it("copies the folio through the shared copy action", async () => {
    writeTextMock.mockResolvedValue(undefined);

    const view = renderUi(<CopyFolioAction referenceValue="TCK-001" />);
    mountedRoots.push(view.unmount);

    const copyButton = view.container.querySelector("button");
    expect(copyButton?.textContent).toContain("Copiar folio");

    act(() => {
      copyButton?.click();
    });

    await act(async () => {
      await Promise.resolve();
    });

    expect(writeTextMock).toHaveBeenCalledWith("TCK-001");
  });

  it("renders the shared print action as disabled when print is unavailable", () => {
    const view = renderUi(
      <PrintAction
        availabilityNote="El reporte imprimible sigue pendiente de contrato backend."
        disabled
        label="Imprimir reporte"
      />,
    );
    mountedRoots.push(view.unmount);

    const printButton = view.container.querySelector("button");
    expect(printButton).not.toBeNull();
    expect(printButton?.textContent).toContain("Imprimir reporte");
    expect((printButton as HTMLButtonElement).disabled).toBe(true);
    expect(printButton?.getAttribute("title")).toContain("pendiente de contrato backend");
  });

  it("opens the document action menu with keyboard and triggers a menu action", () => {
    const onCopy = vi.fn();

    const view = renderUi(
      <DocumentActionsMenu
        actions={[
          {
            key: "copy",
            label: "Copiar folio",
            onSelect: onCopy,
          },
          {
            disabled: true,
            disabledReason: "La exportacion PDF sigue pendiente de un contrato backend.",
            key: "pdf",
            label: "Exportar PDF",
            onSelect: () => undefined,
          },
        ]}
      />,
    );
    mountedRoots.push(view.unmount);

    const summary = view.container.querySelector("summary");
    expect(summary).not.toBeNull();

    act(() => {
      summary?.dispatchEvent(
        new KeyboardEvent("keydown", {
          bubbles: true,
          cancelable: true,
          key: "Enter",
        }),
      );
      vi.runAllTimers();
    });

    const menuItems = Array.from(view.container.querySelectorAll('[role="menuitem"]'));
    expect(menuItems).toHaveLength(2);
    expect(document.activeElement).toBe(menuItems[0]);

    act(() => {
      (menuItems[0] as HTMLButtonElement).click();
    });

    expect(onCopy).toHaveBeenCalledTimes(1);
  });
});
