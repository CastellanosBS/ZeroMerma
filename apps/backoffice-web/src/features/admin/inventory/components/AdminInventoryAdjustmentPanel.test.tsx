// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { withCapabilities } from "../../../../test-support/authorization";
import { AdminInventoryAdjustmentPanel } from "./AdminInventoryAdjustmentPanel";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const submit = vi.fn();
function renderOptions(ids: string[]) {
  const options = ids.map((id) => ({ id, label: id }));
  act(() =>
    root.render(
      withCapabilities(
        <AdminInventoryAdjustmentPanel
          branchOptions={options}
          productOptions={options}
          locationOptions={ids.length ? [{ id: "BACKROOM", label: "Backroom" }] : []}
          onClose={() => undefined}
          onSubmit={submit}
        />,
        ["inventory.adjust"],
      ),
    ),
  );
}
function fill(label: string, value: string) {
  const element = [...host.querySelectorAll("label")]
    .find((item) => item.textContent?.trim().startsWith(label))!
    .querySelector<HTMLInputElement | HTMLSelectElement>("input,select")!;
  act(() => {
    Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value")!.set!.call(
      element,
      value,
    );
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
}
function save() {
  act(() => host.querySelector<HTMLButtonElement>('button[type="submit"]')!.click());
}
beforeEach(() => {
  submit.mockClear();
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
});
afterEach(() => {
  act(() => root.unmount());
  host.remove();
});

it("initializes late options in React state and submits the preserved quantity and reason", () => {
  renderOptions([]);
  fill("Cantidad", "4.000");
  fill("Razon obligatoria", "Physical count");
  renderOptions(["first"]);
  save();
  expect(submit).toHaveBeenCalledTimes(1);
  expect(submit).toHaveBeenCalledWith({
    adjustmentType: "INCREASE",
    branchId: "first",
    productId: "first",
    locationCode: "BACKROOM",
    notes: null,
    quantity: "4.000",
    reason: "Physical count",
  });
});

it("keeps an explicit selection when options are refreshed or reordered", () => {
  renderOptions(["first", "second"]);
  fill("Producto", "second");
  fill("Sucursal", "second");
  fill("Cantidad", "2.000");
  fill("Razon obligatoria", "Physical count");
  renderOptions(["first", "second", "third"]);
  save();
  expect(submit).toHaveBeenCalledTimes(1);
  expect(submit).toHaveBeenCalledWith(
    expect.objectContaining({
      branchId: "second",
      productId: "second",
      quantity: "2.000",
    }),
  );
});
