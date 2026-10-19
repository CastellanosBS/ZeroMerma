// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { withCapabilities } from "../../../../test-support/authorization";
import type { AdminProductionDetail, AdminProductionFilterOption } from "../types";
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
          onRelease={vi.fn()}
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
  ["Guardar y liberar", true],
] as const)(
  "uses options arriving after opening for %s without selecting the intentional recipe placeholder",
  (button, releaseNow) => {
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
      releaseNow,
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

it("restores pending manual quantities and sends explicit reconciliation instead of assuming the plan", () => {
  const complete = vi.fn();
  const production = {
    overview: {
      id: "run",
      folio: "RUN-1",
      branchId: "branch-1",
      status: "PENDING_RECONCILIATION",
      plannedOutputQty: "20",
      actualOutputQty: "18",
      varianceReason: "Confirmed measured yield",
      outputLotCode: "BREAD-PENDING",
      outputExpiresAt: "2026-11-20T18:30:00.000Z",
      reconciliationFinishAs: "CANCELLED",
    },
    productRecipe: { productId: "product-1", recipeId: "recipe-1" },
    plannedInputs: [{ inputProductId: "raw", inputProductName: "Flour", requiredQty: "4" }],
    actualConsumption: [
      {
        inputProductId: "raw",
        consumedQty: "3",
        returnedQty: "0",
        wasteQty: "0",
        remainderQty: "1",
        reconciliationReason: "Count pending",
      },
    ],
  } as AdminProductionDetail;
  act(() =>
    root.render(
      withCapabilities(
        <AdminProductionWorkflowPanel
          mode="complete"
          production={production}
          branchOptions={branches}
          productOptions={products}
          recipeOptions={recipes}
          onComplete={complete}
          onCreate={create}
          onCancelProduction={vi.fn()}
          onClose={vi.fn()}
          onRelease={vi.fn()}
          onUpdate={vi.fn()}
        />,
        ["production.execute"],
      ),
    ),
  );
  expect(field("Salida real").value).toBe("18");
  expect(field("Consumo real").value).toBe("3");
  expect(field("Por conciliar").value).toBe("1");
  expect(field("Razon de variacion").value).toBe("Confirmed measured yield");
  expect(field("Lote de salida").value).toBe("BREAD-PENDING");
  expect(new Date(field("Caducidad de salida").value).toISOString()).toBe(
    "2026-11-20T18:30:00.000Z",
  );
  expect(field("Resultado").value).toBe("CANCELLED");
  change("Consumo real", "3.5");
  change("Sin usar / devolver", "0.5");
  change("Por conciliar", "0");
  click("Completar produccion");
  expect(complete).toHaveBeenCalledWith(
    expect.objectContaining({
      actualOutputQty: "18",
      confirmWithoutDifferences: false,
      outputLotCode: "BREAD-PENDING",
      outputExpiresAt: "2026-11-20T18:30:00.000Z",
      finishAs: "CANCELLED",
      inputs: [
        {
          input_product_id: "raw",
          consumed_qty: "3.5",
          returned_qty: "0.5",
          waste_qty: "0",
          remainder_qty: "0",
          reason: "Count pending",
        },
      ],
    }),
  );
});
