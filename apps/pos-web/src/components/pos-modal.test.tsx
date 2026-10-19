// @vitest-environment jsdom
import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PosModal } from "./pos-modal";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let container: HTMLDivElement;
let root: Root;
beforeEach(() => { container = document.createElement("div"); document.body.append(container); root = createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); });
function key(target: EventTarget, value: string, shiftKey = false) {
  act(() => { target.dispatchEvent(new KeyboardEvent("keydown", { key: value, shiftKey, bubbles: true, cancelable: true })); });
}

function Example({ busy = false }: { busy?: boolean }) {
  const [open, setOpen] = useState(false);
  return <>
    <button onClick={() => setOpen(true)}>Abrir</button>
    {open ? <PosModal label="Confirmar operación" onClose={() => setOpen(false)} busy={busy}>
      <div><input aria-label="Nota" /><button>Cancelar</button><button>Confirmar</button></div>
    </PosModal> : null}
  </>;
}

describe("POS modal interaction", () => {
  it("announces its name, contains focus and restores the invoking control", () => {
    act(() => root.render(<Example />));
    const opener = container.querySelector("button")!;
    act(() => { opener.focus(); opener.click(); });
    const dialog = container.querySelector("[role='dialog']")!;
    expect(dialog.getAttribute("aria-label")).toBe("Confirmar operación");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    const input = dialog.querySelector("input")!;
    const buttons = dialog.querySelectorAll("button");
    expect(document.activeElement).toBe(input);
    key(input, "Tab", true);
    expect(document.activeElement).toBe(buttons[1]);
    key(buttons[1]!, "Tab");
    expect(document.activeElement).toBe(input);
    act(() => opener.focus());
    expect(document.activeElement).toBe(input);
    key(input, "Escape");
    expect(container.querySelector("[role='dialog']")).toBeNull();
    expect(document.activeElement).toBe(opener);
  });

  it("keeps text editing inside the dialog and prevents underlying global commands", () => {
    const businessHotkey = vi.fn();
    window.addEventListener("keydown", businessHotkey);
    try {
      act(() => root.render(<Example />));
      act(() => container.querySelector("button")!.click());
      key(container.querySelector("input")!, "Enter");
      key(window, "F9");
      expect(businessHotkey).not.toHaveBeenCalled();
    } finally { window.removeEventListener("keydown", businessHotkey); }
  });

  it("does not dismiss an in-flight operation with Escape", () => {
    act(() => root.render(<Example busy />));
    act(() => container.querySelector("button")!.click());
    key(container.querySelector("input")!, "Escape");
    expect(container.querySelector("[role='dialog']")?.getAttribute("aria-busy")).toBe("true");
  });

  it("runs only the active dialog confirmation shortcut and blocks it while busy", () => {
    const confirm = vi.fn();
    const underlying = vi.fn();
    window.addEventListener("keydown", underlying);
    try {
      const render = (busy: boolean) => act(() => root.render(<PosModal label="Confirmar envío" onClose={() => {}} onConfirm={confirm} busy={busy}><input /></PosModal>));
      const press = () => act(() => { window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", ctrlKey: true, bubbles: true, cancelable: true })); });
      render(false);
      press();
      expect(confirm).toHaveBeenCalledTimes(1);
      expect(underlying).not.toHaveBeenCalled();
      render(true);
      press();
      expect(confirm).toHaveBeenCalledTimes(1);
    } finally { window.removeEventListener("keydown", underlying); }
  });
});
