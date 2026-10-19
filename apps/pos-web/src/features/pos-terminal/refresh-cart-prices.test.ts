import { describe, expect, it, vi } from "vitest";
import type { PosCartLine } from "./model";
import { refreshCartPrices } from "./refresh-cart-prices";
import { usePosTerminalStore } from "./store";

const mocks = vi.hoisted(() => ({ catalog: vi.fn(), products: vi.fn() }));
vi.mock("./pos-terminal-api", () => ({ getPosCatalog: mocks.catalog, getPosClassProducts: mocks.products }));
const line: PosCartLine = {
  captureMode: "PRODUCT_DIRECT", catalogCodeSnapshot: "BREAD", catalogNameSnapshot: "Pan",
  currencyCode: "MXN", key: "PRODUCT_DIRECT:product", productClassId: "class", productClassCode: "DIRECT",
  productClassName: "Directos", productCode: "BREAD", productId: "product", productName: "Pan",
  quantityMilliUnits: 2500, quantityText: "2.5", unitPriceCents: 1000, unitPriceText: "10.00",
};

describe("explicit cart price review", () => {
  it("reads current backend prices without changing quantity or sending a sale", async () => {
    mocks.catalog.mockResolvedValue({classes: [{id: "class", code: "DIRECT", name: "Directos", capture_mode_default: "PRODUCT_DIRECT", currency_code: "MXN"}]});
    mocks.products.mockResolvedValue({products: [{id: "product", code: "BREAD", name: "Pan nuevo", unit_price: "12.34", currency_code: "MXN"}]});
    const result = await refreshCartPrices("POS", [line]);
    expect(result[0]).toMatchObject({unitPriceText: "12.34", unitPriceCents: 1234, quantityMilliUnits: 2500, catalogNameSnapshot: "Pan nuevo"});
    expect(line.unitPriceText).toBe("10.00");
  });

  it("requires removing a reference no longer in the active catalog", async () => {
    mocks.catalog.mockResolvedValue({classes: []});
    mocks.products.mockResolvedValue({products: []});
    await expect(refreshCartPrices("POS", [line])).rejects.toThrow("ya no está disponible");
  });

  it("accepts a backend price reduced to zero without changing the quantity", async () => {
    mocks.catalog.mockResolvedValue({classes: [{id: "class", code: "DIRECT", name: "Directos", capture_mode_default: "PRODUCT_DIRECT", currency_code: "MXN"}]});
    mocks.products.mockResolvedValue({products: [{id: "product", code: "BREAD", name: "Pan", unit_price: "0.00", currency_code: "MXN"}]});
    const result = await refreshCartPrices("POS", [line]);
    expect(result[0]).toMatchObject({unitPriceText: "0.00", unitPriceCents: 0, quantityMilliUnits: 2500});
  });

  it("cannot restore an edited or cleared draft from a delayed catalog read", () => {
    usePosTerminalStore.setState({cartLines: [line]});
    const original = usePosTerminalStore.getState().cartLines;
    usePosTerminalStore.getState().incrementLineQuantity(line.key);
    expect(usePosTerminalStore.getState().replaceReviewedPrices(original, [{...line, unitPriceCents: 2000}])).toBe(false);
    expect(usePosTerminalStore.getState().cartLines[0]?.quantityMilliUnits).toBe(3500);
    usePosTerminalStore.getState().reset();
    expect(usePosTerminalStore.getState().replaceReviewedPrices(original, [line])).toBe(false);
    expect(usePosTerminalStore.getState().cartLines).toEqual([]);
  });
});
