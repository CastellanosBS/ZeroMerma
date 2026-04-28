// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { PosCatalogClassView, PosCatalogProductView } from "../../lib/api-contracts";
import {
  CLASS_CAPTURE_MODE,
  CONTROL_STATE_CLASS_SELECTION,
  CONTROL_STATE_PAYMENT_CAPTURE,
  CONTROL_STATE_QUANTITY_CAPTURE,
  PRODUCT_DIRECT_MODE,
} from "./model";
import { PosTerminalWorkspace } from "./pos-terminal-workspace";
import { usePosTerminalStore } from "./store";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const catalogRefetch = vi.fn();
const productsRefetch = vi.fn();

let catalogQueryState: {
  data: { classes: PosCatalogClassView[] } | undefined;
  error: Error | null;
  isPending: boolean;
  refetch: typeof catalogRefetch;
};
let productsQueryState: {
  data: { products: PosCatalogProductView[] } | undefined;
  error: Error | null;
  isPending: boolean;
  refetch: typeof productsRefetch;
};

vi.mock("./queries", () => ({
  usePosCatalogQuery: () => catalogQueryState,
  usePosClassProductsQuery: () => productsQueryState,
}));

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

function dispatchKey(target: EventTarget, key: string, options?: KeyboardEventInit) {
  act(() => {
    target.dispatchEvent(
      new KeyboardEvent("keydown", {
        bubbles: true,
        cancelable: true,
        key,
        ...options,
      }),
    );
  });
}

function setInputValue(input: HTMLInputElement, value: string) {
  const valueSetter = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value",
  )?.set;

  act(() => {
    valueSetter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

const bolilloClass: PosCatalogClassView = {
  capture_mode_default: CLASS_CAPTURE_MODE,
  class_capture_unit_price: "3.00",
  code: "BOLILLO",
  currency_code: "MXN",
  display_order: 10,
  id: "class-bolillo",
  name: "Bolillo",
  product_count: 0,
  quick_name: "Bolillo",
};

const panDulceClass: PosCatalogClassView = {
  capture_mode_default: CLASS_CAPTURE_MODE,
  class_capture_unit_price: "12.00",
  code: "PAN-DULCE",
  currency_code: "MXN",
  display_order: 20,
  id: "class-pan-dulce",
  name: "Pan dulce",
  product_count: 0,
  quick_name: "Dulce",
};

const bebidasClass: PosCatalogClassView = {
  capture_mode_default: PRODUCT_DIRECT_MODE,
  class_capture_unit_price: null,
  code: "BEBIDAS",
  currency_code: "MXN",
  display_order: 40,
  id: "class-bebidas",
  name: "Bebidas",
  product_count: 2,
  quick_name: "Bebidas",
};

const cocaProduct: PosCatalogProductView = {
  code: "COCA-355",
  currency_code: "MXN",
  display_order: 10,
  id: "product-coca-355",
  name: "Coca-Cola 355 ml",
  quick_name: "Coca 355",
  unit_price: "18.00",
};

const aguaProduct: PosCatalogProductView = {
  code: "AGUA-600",
  currency_code: "MXN",
  display_order: 20,
  id: "product-agua-600",
  name: "Agua natural 600 ml",
  quick_name: "Agua 600",
  unit_price: "12.00",
};

catalogQueryState = {
  data: { classes: [bolilloClass, panDulceClass, bebidasClass] },
  error: null,
  isPending: false,
  refetch: catalogRefetch,
};

productsQueryState = {
  data: { products: [cocaProduct, aguaProduct] },
  error: null,
  isPending: false,
  refetch: productsRefetch,
};

let mountedRoots: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
  catalogRefetch.mockReset();
  productsRefetch.mockReset();
  act(() => {
    usePosTerminalStore.getState().reset();
  });
  catalogQueryState = {
    data: { classes: [bolilloClass, panDulceClass, bebidasClass] },
    error: null,
    isPending: false,
    refetch: catalogRefetch,
  };
  productsQueryState = {
    data: { products: [cocaProduct, aguaProduct] },
    error: null,
    isPending: false,
    refetch: productsRefetch,
  };
});

describe("PosTerminalWorkspace", () => {
  it("supports keyboard-only class selection with roving focus", async () => {
    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    const cards = Array.from(
      view.container.querySelectorAll("button[data-pos-catalog-card='true']"),
    ) as HTMLButtonElement[];

    await act(async () => {
      await Promise.resolve();
    });

    expect(view.container.textContent).toContain(".+Enter: cobrar");
    expect(document.activeElement).toBe(cards[0]);
    expect(cards[0]?.tabIndex).toBe(0);
    expect(cards[1]?.tabIndex).toBe(-1);

    dispatchKey(cards[0]!, "ArrowRight");
    expect(document.activeElement).toBe(cards[1]);

    dispatchKey(cards[1]!, "Enter");

    const state = usePosTerminalStore.getState();
    expect(state.controlState).toBe(CONTROL_STATE_QUANTITY_CAPTURE);
    expect(state.pendingSelection?.productClass.id).toBe(panDulceClass.id);
  });

  it("supports keyboard-only product selection and keeps direct mode visible", async () => {
    act(() => {
      usePosTerminalStore.getState().selectClass(bebidasClass);
    });

    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    const cards = Array.from(
      view.container.querySelectorAll("button[data-pos-catalog-card='true']"),
    ) as HTMLButtonElement[];

    await act(async () => {
      await Promise.resolve();
    });

    expect(view.container.textContent).toContain("Producto directo");
    expect(document.activeElement).toBe(cards[0]);

    dispatchKey(cards[0]!, "ArrowRight");
    expect(document.activeElement).toBe(cards[1]);

    dispatchKey(cards[1]!, "Enter");

    const state = usePosTerminalStore.getState();
    expect(state.controlState).toBe(CONTROL_STATE_QUANTITY_CAPTURE);
    expect(state.pendingSelection?.product?.id).toBe(aguaProduct.id);
  });

  it("returns from product selection to class selection with Escape", async () => {
    act(() => {
      usePosTerminalStore.getState().selectClass(bebidasClass);
    });

    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    await act(async () => {
      await Promise.resolve();
    });

    dispatchKey(window, "Escape");

    const state = usePosTerminalStore.getState();
    expect(state.controlState).toBe(CONTROL_STATE_CLASS_SELECTION);
    expect(state.pendingSelection).toBeNull();
  });

  it("keeps mouse class selection working and lets Ctrl+F focus search", async () => {
    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    const searchInput = view.container.querySelector(
      'input[aria-label="Buscar en la etapa actual"]',
    ) as HTMLInputElement;
    const cards = Array.from(
      view.container.querySelectorAll("button[data-pos-catalog-card='true']"),
    ) as HTMLButtonElement[];

    await act(async () => {
      await Promise.resolve();
    });

    dispatchKey(window, "f", { ctrlKey: true });
    expect(document.activeElement).toBe(searchInput);

    act(() => {
      cards[0]?.click();
    });

    const state = usePosTerminalStore.getState();
    expect(state.controlState).toBe(CONTROL_STATE_QUANTITY_CAPTURE);
    expect(state.pendingSelection?.productClass.id).toBe(bolilloClass.id);
  });

  it("accepts an exact class code in the scanner input", async () => {
    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    await act(async () => {
      await Promise.resolve();
    });

    const scannerInput = view.container.querySelector(
      'input[aria-label="Escanear codigo de producto o clase"]',
    ) as HTMLInputElement;

    expect(scannerInput).toBeDefined();

    act(() => {
      usePosTerminalStore.getState().setSearchText("");
    });
    setInputValue(scannerInput, "PAN-DULCE");

    dispatchKey(scannerInput, "Enter");

    const state = usePosTerminalStore.getState();
    expect(state.controlState).toBe(CONTROL_STATE_QUANTITY_CAPTURE);
    expect(state.pendingSelection?.productClass.id).toBe(panDulceClass.id);
  });

  it("adds a class-capture line with keyboard and returns focus to the grid", async () => {
    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    const cards = Array.from(
      view.container.querySelectorAll("button[data-pos-catalog-card='true']"),
    ) as HTMLButtonElement[];

    await act(async () => {
      await Promise.resolve();
    });

    dispatchKey(cards[0]!, "Enter");

    const quantityInput = view.container.querySelector(
      'input[aria-label="Cantidad"]',
    ) as HTMLInputElement;

    expect(document.activeElement).toBe(quantityInput);

    act(() => {
      usePosTerminalStore.getState().setQuantityText("2");
    });
    dispatchKey(quantityInput, "NumpadEnter");

    await act(async () => {
      await Promise.resolve();
    });

    const state = usePosTerminalStore.getState();
    expect(state.cartLines).toHaveLength(1);
    expect(state.cartLines[0]?.productClassId).toBe(bolilloClass.id);
    expect(state.controlState).toBe(CONTROL_STATE_CLASS_SELECTION);

    const updatedCards = Array.from(
      view.container.querySelectorAll("button[data-pos-catalog-card='true']"),
    ) as HTMLButtonElement[];
    expect(document.activeElement).toBe(updatedCards[0]);
  });

  it("adds a product-direct line with keyboard", async () => {
    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    const cards = Array.from(
      view.container.querySelectorAll("button[data-pos-catalog-card='true']"),
    ) as HTMLButtonElement[];

    await act(async () => {
      await Promise.resolve();
    });

    act(() => {
      cards[2]?.click();
    });

    const productCards = Array.from(
      view.container.querySelectorAll("button[data-pos-catalog-card='true']"),
    ) as HTMLButtonElement[];

    dispatchKey(productCards[0]!, "Enter");

    const quantityInput = view.container.querySelector(
      'input[aria-label="Cantidad"]',
    ) as HTMLInputElement;
    act(() => {
      usePosTerminalStore.getState().setQuantityText("1");
    });
    dispatchKey(quantityInput, "Enter");

    await act(async () => {
      await Promise.resolve();
    });

    const state = usePosTerminalStore.getState();
    expect(state.cartLines).toHaveLength(1);
    expect(state.cartLines[0]?.productId).toBe(cocaProduct.id);
    expect(state.controlState).toBe(CONTROL_STATE_CLASS_SELECTION);
  });

  it("accepts an exact product code in the scanner input during product selection", async () => {
    act(() => {
      usePosTerminalStore.getState().selectClass(bebidasClass);
    });

    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    await act(async () => {
      await Promise.resolve();
    });

    const scannerInput = view.container.querySelector(
      'input[aria-label="Escanear codigo de producto"]',
    ) as HTMLInputElement;

    setInputValue(scannerInput, "AGUA-600");

    dispatchKey(scannerInput, "Enter");

    const state = usePosTerminalStore.getState();
    expect(state.controlState).toBe(CONTROL_STATE_QUANTITY_CAPTURE);
    expect(state.pendingSelection?.product?.id).toBe(aguaProduct.id);
  });

  it("jumps to payment capture with F2 when the ticket has lines", async () => {
    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    await act(async () => {
      await Promise.resolve();
    });

    act(() => {
      const store = usePosTerminalStore.getState();
      store.selectClass(bolilloClass);
      store.setQuantityText("1");
      store.addPendingLine();
    });

    dispatchKey(window, "F2");

    expect(usePosTerminalStore.getState().controlState).toBe(CONTROL_STATE_PAYMENT_CAPTURE);
  });

  it("jumps to payment capture with NumpadDecimal plus NumpadEnter", async () => {
    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    await act(async () => {
      await Promise.resolve();
    });

    act(() => {
      const store = usePosTerminalStore.getState();
      store.selectClass(bolilloClass);
      store.setQuantityText("1");
      store.addPendingLine();
    });

    dispatchKey(window, ".", { code: "NumpadDecimal" });
    dispatchKey(window, "NumpadEnter", { code: "NumpadEnter" });

    expect(usePosTerminalStore.getState().controlState).toBe(CONTROL_STATE_PAYMENT_CAPTURE);
  });

  it("shows a warning when payment is requested with an empty ticket", async () => {
    const view = renderUi(<PosTerminalWorkspace />);
    mountedRoots.push(view.unmount);

    await act(async () => {
      await Promise.resolve();
    });

    dispatchKey(window, ".", { code: "NumpadDecimal" });
    dispatchKey(window, "NumpadEnter", { code: "NumpadEnter" });

    expect(usePosTerminalStore.getState().controlState).toBe(CONTROL_STATE_CLASS_SELECTION);
    expect(view.container.textContent).toContain("Agrega al menos un producto antes de cobrar");
  });
});
