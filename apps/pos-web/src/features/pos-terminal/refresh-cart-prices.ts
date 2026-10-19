import { getPosCatalog, getPosClassProducts } from "./pos-terminal-api";
import { CLASS_CAPTURE_MODE, parseMoneyToCents, type PosCartLine } from "./model";

/** Refresh a draft for explicit review; this never sends a sale or payment. */
export async function refreshCartPrices(workstationCode: string, lines: PosCartLine[]): Promise<PosCartLine[]> {
  const catalog = await getPosCatalog(workstationCode, undefined);
  const classes = new Map(catalog.classes.map((entry) => [entry.id, entry]));
  const directClasses = [...new Set(lines.filter((line) => line.captureMode !== CLASS_CAPTURE_MODE).map((line) => line.productClassId!))];
  const products = new Map((await Promise.all(directClasses.map((id) => getPosClassProducts(workstationCode, id, undefined)))).flatMap((response) => response.products.map((product) => [product.id, product] as const)));
  return lines.map((line) => {
    const productClass = classes.get(line.productClassId!);
    const product = line.productId ? products.get(line.productId) : null;
    if (!productClass || productClass.capture_mode_default !== line.captureMode || (line.productId && !product)) {
      throw new Error(`Retira ${line.catalogNameSnapshot}: ya no está disponible en el catálogo.`);
    }
    const price = line.captureMode === CLASS_CAPTURE_MODE ? productClass.class_capture_unit_price : product?.unit_price;
    // Catalog prices may be zero; tendered payment amounts must remain positive.
    const cents = price == null ? null : /^0(?:\.0{1,2})?$/.test(price) ? 0 : parseMoneyToCents(price);
    if (cents === null || price == null) throw new Error("El catálogo no tiene un precio válido. Revisa la configuración.");
    return {
      ...line,
      unitPriceCents: cents,
      unitPriceText: price,
      currencyCode: product?.currency_code ?? productClass.currency_code,
      catalogNameSnapshot: product?.name ?? productClass.name,
      catalogCodeSnapshot: product?.code ?? productClass.code,
      productName: product?.name ?? null,
      productClassName: productClass.name,
    };
  });
}
