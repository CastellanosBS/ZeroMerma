// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { withCapabilities } from "../../../../test-support/authorization";
import type { AdminProductionFilterOption } from "../types";
import { AdminProductionWorkflowPanel } from "./AdminProductionWorkflowPanel";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const create = vi.fn();
const branches = [
  { id: "branch-1", label: "Main" },
  { id: "branch-2", label: "Second" },
];
const products = [
  { id: "product-1", label: "Bread" },
  { id: "product-2", label: "Roll" },
];
const recipes = [{ id: "recipe-1", label: "Selected recipe" }];

function render(
  branchOptions: AdminProductionFilterOption[],
  productOptions: AdminProductionFilterOption[],
) {
  act(() =>
    root.render(
      withCapabilities(
        <AdminProductionWorkflowPanel
          mode="create"
          branchOptions={branchOptions}
          productOptions={productOptions}
          recipeOptions={recipes}
          onCreate={create}
          onCancelProduction={vi.fn()}
          onClose={vi.fn()}
          onComplete={vi.fn()}
          onStart={vi.fn()}
          onUpdate={vi.fn()}
        />,
        ["production.manage", "production.execute"],
      ),
    ),
  );
}

function field(label: string) {
  const element = [...host.querySelectorAll("label")]
    .find((item) => item.textContent?.trim().startsWith(label))
    ?.querySelector<HTMLInputElement | HTMLSelectElement>("input, select");
  if (!element) throw new Error(`Missing field: ${label}`);
  return element;
}

function change(label: string, value: string) {
  const element = field(label);
  act(() => {
    Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value")!.set!.call(
      element,
      value,
    );
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function click(label: string) {
  const button = [...host.querySelectorAll("button")].find(
    (item) => item.textContent?.trim() === label,
  );
  if (!button) throw new Error(`Missing button: ${label}`);
  act(() => button.click());
}

beforeEach(() => {
  create.mockReset();
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
});

afterEach(() => {
  act(() => root.unmount());
  host.remove();
});

it.each([
  ["Guardar borrador", false],
  ["Guardar e iniciar", true],
] as const)(
  "uses options arriving after opening for %s without selecting the intentional recipe placeholder",
  (button, startNow) => {
    render([], []);
    change("Cantidad", "20");
    click(button);
    expect(create).not.toHaveBeenCalled();

    render(branches, []);
    render(branches, products);
    expect(field("Sucursal").value).toBe("branch-1");
    expect(field("Producto terminado").value).toBe("product-1");
    expect(field("Receta activa").value).toBe("");
    click(button);

    expect(create).toHaveBeenCalledTimes(1);
    expect(create).toHaveBeenCalledWith(
      {
        branchId: "branch-1",
        productId: "product-1",
        plannedOutputQty: "20",
        recipeId: null,
        notes: null,
        plannedAt: null,
      },
      startNow,
    );
  },
);

it("preserves explicit choices and the draft when refreshed options change their first entries", () => {
  render([], []);
  render(branches, products);
  change("Sucursal", "branch-2");
  change("Producto terminado", "product-2");
  change("Receta activa", "recipe-1");
  change("Cantidad", "8");

  render(
    [{ id: "branch-3", label: "New first branch" }, ...branches],
    [{ id: "product-3", label: "New first product" }, ...products],
  );
  expect(field("Sucursal").value).toBe("branch-2");
  expect(field("Producto terminado").value).toBe("product-2");
  expect(field("Receta activa").value).toBe("recipe-1");
  expect(field("Cantidad").value).toBe("8");
  click("Guardar borrador");
  expect(create).toHaveBeenCalledTimes(1);
  expect(create).toHaveBeenCalledWith(
    expect.objectContaining({
      branchId: "branch-2",
      productId: "product-2",
      plannedOutputQty: "8",
      recipeId: "recipe-1",
    }),
    false,
  );
});
