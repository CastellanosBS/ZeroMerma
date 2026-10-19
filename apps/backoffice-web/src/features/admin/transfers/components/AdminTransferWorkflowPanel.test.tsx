// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { withCapabilities } from "../../../../test-support/authorization";
import type { AdminTransferFilterOption } from "../types";
import { AdminTransferWorkflowPanel } from "./AdminTransferWorkflowPanel";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

const branches = [
  { id: "origin", label: "Origin" },
  { id: "destination", label: "Destination" },
  { id: "another", label: "Another" },
];
let root: Root;
let host: HTMLDivElement;
const onCreate = vi.fn();

function render(options: AdminTransferFilterOption[]) {
  act(() =>
    root.render(
      withCapabilities(
        <AdminTransferWorkflowPanel
          mode="create"
          branchOptions={options}
          productOptions={[{ id: "product", label: "Product" }]}
          onCreate={onCreate}
          onClose={vi.fn()}
          onUpdate={vi.fn()}
          onDispatch={vi.fn()}
          onReceive={vi.fn()}
          onCancelTransfer={vi.fn()}
        />,
        ["transfers.manage"],
      ),
    ),
  );
}

function change(label: string, value: string) {
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

function submit() {
  change("Producto", "product");
  change("Cantidad", "2");
  act(() => host.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true })));
}

beforeEach(() => {
  onCreate.mockReset();
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
});
afterEach(() => {
  act(() => root.unmount());
  host.remove();
});

it("initializes branch state when options arrive after the create form mounted", () => {
  render([]);
  render(branches);
  submit();
  expect(onCreate).toHaveBeenCalledWith({
    originBranchId: "origin",
    destinationBranchId: "destination",
    notes: null,
    lines: [{ productId: "product", quantity: "2", notes: null }],
  });
});

it("preserves explicit branch choices when options refresh in another order", () => {
  render([]);
  render(branches);
  change("Origen", "destination");
  change("Destino", "another");
  render([...branches].reverse());
  submit();
  expect(onCreate).toHaveBeenCalledWith(
    expect.objectContaining({ originBranchId: "destination", destinationBranchId: "another" }),
  );
});
