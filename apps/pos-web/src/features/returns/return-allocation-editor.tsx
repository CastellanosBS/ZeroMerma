import type { ReturnProductOptionView } from "../../lib/api-contracts";
import { sanitizeQuantityInput } from "../pos-terminal/model";
import type { ReturnAllocationDraft, ReturnDraftLine } from "./model";

const dispositions: { value: ReturnAllocationDraft["disposition_code"]; label: string }[] = [
  { value: "QUARANTINE", label: "Cuarentena: pendiente de inspección" },
  { value: "RESTOCK_COUNTER", label: "Reponer en mostrador" },
  { value: "RESTOCK_BACKROOM", label: "Reponer en almacén" },
  { value: "SEND_TO_WASTE", label: "Enviar a merma" },
  { value: "NO_STOCK", label: "Producto no inventariable" },
];

export function ReturnAllocationEditor({
  line,
  products,
  onChange,
}: {
  line: ReturnDraftLine;
  products: ReturnProductOptionView[];
  onChange: (allocations: ReturnAllocationDraft[]) => void;
}) {
  const productOptions = new Map(products.map((product) => [product.id, product.name]));
  line.physicalOptions.forEach((option) =>
    productOptions.set(option.product_id, option.product_name),
  );
  line.allocations.forEach((allocation) => {
    if (allocation.exact_product_id && !productOptions.has(allocation.exact_product_id))
      productOptions.set(allocation.exact_product_id, line.fixedProductName ?? line.lineName);
  });
  function update(key: string, patch: Partial<ReturnAllocationDraft>) {
    onChange(
      line.allocations.map((allocation) =>
        allocation.key === key ? { ...allocation, ...patch } : allocation,
      ),
    );
  }
  return (
    <section
      aria-label={`Disposiciones de ${line.lineName}`}
      className="grid gap-2 rounded-lg border p-2"
    >
      <h3 className="text-sm font-semibold">Destino físico: {line.lineName}</h3>
      <p className="text-xs text-slate-600">
        Distribuye {line.quantityText} unidades. La cuarentena mantiene el producto fuera de venta.
      </p>
      {line.allocations.map((allocation, index) => {
        const options = line.physicalOptions.filter(
          (option) => option.product_id === allocation.exact_product_id,
        );
        const lots = options.filter((option) => option.lot_id);
        const restock = ["RESTOCK_COUNTER", "RESTOCK_BACKROOM"].includes(
          allocation.disposition_code,
        );
        return (
          <fieldset className="grid gap-2 rounded-lg border p-2" key={allocation.key}>
            <legend className="text-xs">Disposición {index + 1}</legend>
            <label className="grid gap-1 text-xs">
              Producto de disposición {index + 1}
              <select
                aria-label={`Producto de disposición ${index + 1}`}
                className="min-h-10 rounded border px-2"
                value={allocation.exact_product_id}
                onChange={(event) =>
                  update(allocation.key, {
                    exact_product_id: event.target.value,
                    lot_id: null,
                    restock_safe_acknowledged: false,
                  })
                }
              >
                <option value="">Selecciona producto</option>
                {[...productOptions].map(([id, name]) => (
                  <option value={id} key={id}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-xs">
              Cantidad de disposición {index + 1}
              <input
                className="min-h-10 rounded border px-2"
                inputMode="decimal"
                value={allocation.quantityText}
                onChange={(event) =>
                  update(allocation.key, {
                    quantityText: sanitizeQuantityInput(event.target.value),
                  })
                }
              />
            </label>
            <label className="grid gap-1 text-xs">
              Destino de disposición {index + 1}
              <select
                aria-label={`Destino de disposición ${index + 1}`}
                className="min-h-10 rounded border px-2"
                value={allocation.disposition_code}
                onChange={(event) =>
                  update(allocation.key, {
                    disposition_code: event.target
                      .value as ReturnAllocationDraft["disposition_code"],
                    restock_safe_acknowledged: false,
                  })
                }
              >
                {dispositions
                  .filter(
                    (item) =>
                      item.value !== "NO_STOCK" ||
                      options.some((option) => !option.is_inventory_tracked),
                  )
                  .map((item) => (
                    <option value={item.value} key={item.value}>
                      {item.label}
                    </option>
                  ))}
              </select>
            </label>
            {lots.length || options.some((option) => option.lot_tracking_enabled) ? (
              <label className="grid gap-1 text-xs">
                Lote de disposición {index + 1}
                <select
                  aria-label={`Lote de disposición ${index + 1}`}
                  className="min-h-10 rounded border px-2"
                  value={allocation.lot_id ?? ""}
                  onChange={(event) =>
                    update(allocation.key, {
                      lot_id: event.target.value || null,
                      restock_safe_acknowledged: false,
                    })
                  }
                >
                  <option value="">Sin identificar: cuarentena o merma</option>
                  {lots.map((option) => (
                    <option key={option.lot_id} value={option.lot_id!}>
                      {option.lot_code} · vence {option.expires_at ?? "sin fecha"} · disponible{" "}
                      {option.remaining_quantity}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {restock ? (
              <label className="flex gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={allocation.restock_safe_acknowledged ?? false}
                  onChange={(event) =>
                    update(allocation.key, { restock_safe_acknowledged: event.target.checked })
                  }
                />
                Inspeccioné el producto y es apto para volver a venderse.
              </label>
            ) : null}
            {line.allocations.length > 1 ? (
              <button
                type="button"
                className="min-h-9 text-left text-red-700"
                onClick={() =>
                  onChange(line.allocations.filter((item) => item.key !== allocation.key))
                }
              >
                Quitar disposición {index + 1}
              </button>
            ) : null}
          </fieldset>
        );
      })}
      <button
        type="button"
        className="min-h-10 rounded border px-2 text-sm"
        onClick={() =>
          onChange([
            ...line.allocations,
            {
              key: crypto.randomUUID(),
              exact_product_id: line.allocations[0]?.exact_product_id ?? "",
              quantityText: "",
              disposition_code: "QUARANTINE",
              lot_id: null,
              restock_safe_acknowledged: false,
            },
          ])
        }
      >
        Dividir destino físico
      </button>
    </section>
  );
}
