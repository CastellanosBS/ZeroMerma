// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { AdminOrderCancellationForm } from "./AdminOrderCancellationForm";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("requires explicit responsibility and a useful cause before submitting", () => {
  const container = document.createElement("div"); document.body.append(container);
  const root = createRoot(container);
  const confirm = vi.fn();
  const cancel = vi.fn();
  try {
    act(() => root.render(<AdminOrderCancellationForm folio="PED-001" busy={false} onCancel={cancel} onConfirm={confirm} />));
    const reason = container.querySelector("textarea")!;
    const responsibility = container.querySelector("select")!;
    const submit = container.querySelector<HTMLButtonElement>("button[type='submit']")!;
    expect(document.activeElement).toBe(reason);
    expect(responsibility.value).toBe("");
    expect(submit.disabled).toBe(true);
    act(() => {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(reason, "  El negocio no podrá cumplir  ");
      reason.dispatchEvent(new Event("input", { bubbles: true }));
      responsibility.value = "MERCHANT";
      responsibility.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(submit.disabled).toBe(false);
    act(() => container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(confirm).toHaveBeenCalledWith({ cancellation_reason: "El negocio no podrá cumplir", cancellation_responsibility: "MERCHANT" });
    act(() => root.render(<AdminOrderCancellationForm folio="PED-001" busy onCancel={cancel} onConfirm={confirm} />));
    expect(submit.disabled).toBe(true);
    expect(responsibility.disabled).toBe(true);
  } finally { act(() => root.unmount()); container.remove(); }
});
