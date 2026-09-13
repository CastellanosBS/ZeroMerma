import { AdminActionButton } from "../../components/AdminActionButton";
import type { AdminRecipe, AdminRecipeCostDetail, AdminRecipeCostProduct } from "../types";

function formatMoney(value: string | null | undefined, currencyCode: string): string {
  if (!value) {
    return "Pendiente";
  }

  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} ${currencyCode}`;
  }

  return new Intl.NumberFormat("es-MX", {
    currency: currencyCode,
    style: "currency",
  }).format(numericValue);
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 border-b border-[var(--ui-color-border)] py-2 last:border-b-0">
      <p
        className="truncate text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-slate-500"
        title={label}
      >
        {label}
      </p>
      <p className="mt-0.5 truncate text-sm font-semibold text-slate-950" title={value}>
        {value}
      </p>
    </div>
  );
}

function RecipeVersion({
  recipe,
  onActivate,
  onDuplicate,
}: {
  onActivate: (recipe: AdminRecipe) => void;
  onDuplicate: (recipe: AdminRecipe) => void;
  recipe: AdminRecipe;
}) {
  return (
    <div className="grid min-w-0 gap-1.5 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-2 py-2 text-xs">
      <div className="flex min-w-0 items-center justify-between gap-2">
        <span
          className="truncate font-semibold text-slate-900"
          title={recipe.versionName ?? "Receta sin nombre"}
        >
          {recipe.versionName ?? "Receta sin nombre"}
        </span>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-0.5 font-semibold text-slate-600">
          {recipe.isActive ? "Activa" : "Inactiva"}
        </span>
      </div>
      <p className="truncate text-slate-500">
        {recipe.inputCount} insumos - {recipe.yieldQty} {recipe.yieldUom}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {!recipe.isActive ? (
          <AdminActionButton
            globalOnly
            capability="recipes.manage"
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-[var(--ui-color-info)]"
            type="button"
            onClick={() => onActivate(recipe)}
          >
            Activar
          </AdminActionButton>
        ) : null}
        <AdminActionButton
          globalOnly
          capability="recipes.manage"
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600"
          type="button"
          onClick={() => onDuplicate(recipe)}
        >
          Duplicar
        </AdminActionButton>
      </div>
    </div>
  );
}

interface AdminRecipeCostDetailPanelProps {
  detail?: AdminRecipeCostDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onActivateRecipe: (recipe: AdminRecipe) => void;
  onApplyStandardCost: (recipe: AdminRecipe) => void;
  onCreateRecipe: (product: AdminRecipeCostProduct) => void;
  onDuplicateRecipe: (recipe: AdminRecipe) => void;
}

export function AdminRecipeCostDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onActivateRecipe,
  onApplyStandardCost,
  onCreateRecipe,
  onDuplicateRecipe,
}: AdminRecipeCostDetailPanelProps) {
  const product = detail?.product ?? null;
  const activeRecipe = detail?.activeRecipe ?? null;

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Detalle</p>
        <h3
          className="mt-1 truncate text-base font-semibold text-slate-950"
          title={product?.productName ?? "Sin producto seleccionado"}
        >
          {product ? product.productName : "Sin producto seleccionado"}
        </h3>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <article className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
            <p className="text-sm font-semibold text-slate-950">Cargando detalle</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">
              Consultando receta y costo del producto.
            </p>
          </article>
        ) : errorMessage ? (
          <article className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-3">
            <p className="text-sm font-semibold text-[var(--ui-color-danger)]">
              No se pudo cargar el detalle
            </p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{errorMessage}</p>
          </article>
        ) : product ? (
          <div className="grid min-w-0 gap-3">
            <section className="min-w-0 rounded-[16px] border border-[var(--ui-color-border)] bg-white px-3">
              <Field label="Producto" value={`${product.productCode} - ${product.className}`} />
              <Field label="Unidad" value={product.unitOfMeasure} />
              <Field
                label="Costo estandar"
                value={formatMoney(product.productStandardCost, product.currencyCode)}
              />
              <Field
                label="Precio venta"
                value={formatMoney(product.productUnitPrice, product.currencyCode)}
              />
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <div className="flex min-w-0 items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Costo calculado
                </p>
                <AdminActionButton
                  globalOnly
                  capability="recipes.manage"
                  additionalCapabilities={["pricing.manage"]}
                  className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                  disabled={!activeRecipe || !activeRecipe.calculatedUnitCost}
                  type="button"
                  onClick={() => activeRecipe && onApplyStandardCost(activeRecipe)}
                >
                  Usar como costo
                </AdminActionButton>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-[14px] bg-slate-100 px-3 py-2">
                  <p className="text-xs font-semibold text-slate-500">Lote</p>
                  <p className="font-semibold text-slate-950">
                    {formatMoney(product.totalBatchCost, product.currencyCode)}
                  </p>
                </div>
                <div className="rounded-[14px] bg-slate-100 px-3 py-2">
                  <p className="text-xs font-semibold text-slate-500">Unitario</p>
                  <p className="font-semibold text-slate-950">
                    {formatMoney(product.calculatedUnitCost, product.currencyCode)}
                  </p>
                </div>
              </div>
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <div className="flex min-w-0 items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Receta activa
                </p>
                <AdminActionButton
                  globalOnly
                  capability="recipes.manage"
                  className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-[var(--ui-color-info)]"
                  type="button"
                  onClick={() => onCreateRecipe(product)}
                >
                  Nueva version
                </AdminActionButton>
              </div>
              {activeRecipe ? (
                <div className="mt-2 grid gap-1.5">
                  <p className="text-sm font-semibold text-slate-950">
                    {activeRecipe.versionName ?? "Receta sin nombre"} - {activeRecipe.yieldQty}{" "}
                    {activeRecipe.yieldUom}
                  </p>
                  {activeRecipe.inputs.map((input) => (
                    <div
                      className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-2 py-1.5 text-xs"
                      key={input.id}
                    >
                      <span
                        className="min-w-0 truncate font-semibold text-slate-800"
                        title={input.inputProductName}
                      >
                        {input.inputProductName}
                      </span>
                      <span className="shrink-0 text-slate-600">
                        {input.quantity} {input.unitOfMeasure}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-2 rounded-[14px] border border-dashed border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-600">
                  Este producto no tiene receta activa.
                </p>
              )}
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Advertencias
              </p>
              {product.warnings.messages.length > 0 ? (
                <ul className="mt-2 grid gap-1.5 text-sm leading-5 text-slate-700">
                  {product.warnings.messages.map((message) => (
                    <li
                      className="rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2"
                      key={message}
                    >
                      {message}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-sm leading-5 text-slate-600">
                  Sin advertencias de receta/costo.
                </p>
              )}
            </section>

            <section className="rounded-[16px] border border-[var(--ui-color-border)] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Versiones
              </p>
              <div className="mt-2 grid gap-1.5">
                {detail?.recipeVersions.length ? (
                  detail.recipeVersions.map((recipe) => (
                    <RecipeVersion
                      key={recipe.id}
                      recipe={recipe}
                      onActivate={onActivateRecipe}
                      onDuplicate={onDuplicateRecipe}
                    />
                  ))
                ) : (
                  <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-600">
                    No hay versiones registradas.
                  </p>
                )}
              </div>
            </section>
          </div>
        ) : (
          <article className="rounded-[16px] border border-dashed border-[var(--ui-color-border)] bg-white p-4">
            <p className="text-sm font-semibold text-slate-950">Sin producto seleccionado</p>
            <p className="mt-1 text-sm leading-5 text-slate-600">
              Selecciona un producto para revisar receta activa, insumos, costo calculado y
              versiones.
            </p>
          </article>
        )}
      </div>
    </aside>
  );
}
