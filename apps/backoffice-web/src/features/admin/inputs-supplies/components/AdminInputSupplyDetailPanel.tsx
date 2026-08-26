import type { ReactNode } from "react";

import type {
  AdminInputSupplyDetail,
  AdminInputSupplyKind,
  AdminInputSupplyListItem,
  AdminInputSupplyStockState,
  AdminInputSupplyWarningSeverity,
  AdminInputSupplyWarningState,
} from "../types";

interface AdminInputSupplyDetailPanelProps {
  errorMessage?: string | null;
  inputDetail?: AdminInputSupplyDetail | null;
  inputPreview?: AdminInputSupplyListItem | null;
  isLoading: boolean;
  onOpenInventory: (productId: string) => void;
  onOpenProduct: (productId: string) => void;
  onOpenRecipes: (productId: string) => void;
  onOpenSupplier: (supplierId: string) => void;
}

function formatDate(value?: string | null) {
  if (!value) {
    return "No disponible";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatKind(kind: AdminInputSupplyKind): string {
  const labels: Record<AdminInputSupplyKind, string> = {
    CONSUMABLE: "Consumible",
    DISPOSABLE: "Desechable / empaque",
    RAW_MATERIAL: "Materia prima",
  };
  return labels[kind];
}

function formatStockState(state: AdminInputSupplyStockState): string {
  const labels: Record<AdminInputSupplyStockState, string> = {
    in_stock: "Con existencia",
    low_stock: "Stock bajo",
    negative_stock: "Stock negativo",
    no_inventory: "Sin inventario",
    out_of_stock: "Sin existencia",
  };
  return labels[state];
}

function toneClass(
  tone?: AdminInputSupplyWarningSeverity | AdminInputSupplyWarningState | string | null,
) {
  if (tone === "critical" || tone === "negative_stock") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (tone === "warning" || tone === "low_stock") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  if (tone === "ok" || tone === "in_stock" || tone === "active") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function DetailBlock({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h3
        className="mb-2 truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500"
        title={title}
      >
        {title}
      </h3>
      {children}
    </section>
  );
}

function Definition({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="truncate text-xs text-slate-500">{label}</dt>
      <dd
        className="truncate font-semibold text-slate-950"
        title={typeof value === "string" ? value : undefined}
      >
        {value}
      </dd>
    </div>
  );
}

export function AdminInputSupplyDetailPanel({
  errorMessage,
  inputDetail,
  inputPreview,
  isLoading,
  onOpenInventory,
  onOpenProduct,
  onOpenRecipes,
  onOpenSupplier,
}: AdminInputSupplyDetailPanelProps) {
  if (!inputPreview && !inputDetail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col justify-center rounded-[20px] border border-dashed border-slate-200 bg-slate-50 p-5 text-sm font-semibold leading-6 text-slate-500">
        Selecciona un insumo para revisar proveedores, costos, inventario y uso operativo.
      </aside>
    );
  }

  if (isLoading) {
    return (
      <aside className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-4 text-sm font-semibold text-slate-500">
        Cargando detalle de insumo.
      </aside>
    );
  }

  if (errorMessage) {
    return (
      <aside className="rounded-[20px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-4 text-sm font-semibold text-[var(--ui-color-danger)]">
        {errorMessage}
      </aside>
    );
  }

  if (!inputDetail) {
    return null;
  }

  const overview = inputDetail.overview;
  const isRawMaterial = overview.productKind === "RAW_MATERIAL";

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50">
      <div className="border-b border-[var(--ui-color-border)] bg-white p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Detalle de insumo
            </p>
            <h2 className="truncate text-lg font-semibold text-slate-950" title={overview.name}>
              {overview.name}
            </h2>
            <p className="truncate font-mono text-sm text-slate-600" title={overview.code}>
              {overview.code} - {formatKind(overview.productKind)}
            </p>
          </div>
          <span
            className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClass(
              overview.readinessState,
            )}`}
          >
            {overview.readinessState === "ok" ? "Listo" : "Con revision"}
          </span>
        </div>
        <div className="mt-3 flex min-w-0 flex-wrap gap-2">
          <button
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700"
            type="button"
            onClick={() => onOpenProduct(overview.id)}
          >
            Abrir producto
          </button>
          <button
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700"
            type="button"
            onClick={() => onOpenInventory(overview.id)}
          >
            Abrir inventario
          </button>
          <button
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700"
            type="button"
            onClick={() => onOpenRecipes(overview.id)}
          >
            Recetas
          </button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-auto p-3">
        <DetailBlock title="Resumen">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <Definition label="Tipo" value={formatKind(overview.productKind)} />
            <Definition label="Categoria" value={overview.categoryName} />
            <Definition label="Estado" value={overview.isActive ? "Activo" : "Inactivo"} />
            <Definition label="Inventariable" value={overview.isInventoryTracked ? "Si" : "No"} />
            <Definition label="Comprable" value={overview.isPurchasable ? "Si" : "No"} />
            <Definition label="Actualizado" value={formatDate(overview.updatedAt)} />
          </dl>
        </DetailBlock>

        <DetailBlock title="Clasificacion">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <Definition
              label="Familia"
              value={inputDetail.classification.storageGroup ?? overview.categoryName}
            />
            <Definition label="Uso" value={inputDetail.classification.usageType ?? "No definido"} />
            <Definition label="Estado catalogo" value={inputDetail.classification.status} />
            <Definition label="Notas" value={inputDetail.classification.notes ?? "Sin notas"} />
          </dl>
        </DetailBlock>

        <DetailBlock title="Unidades y conversion">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <Definition label="Unidad base" value={inputDetail.unitsConversion.baseUom} />
            <Definition
              label="Unidad compra"
              value={inputDetail.unitsConversion.purchaseUom ?? "No definida"}
            />
            <Definition label="Unidad consumo" value={inputDetail.unitsConversion.consumptionUom} />
            <Definition
              label="Factor"
              value={inputDetail.unitsConversion.conversionFactor ?? "Sin conversion"}
            />
            <Definition
              label="Compra minima"
              value={inputDetail.unitsConversion.minimumPurchaseQuantity ?? "No definida"}
            />
            <Definition
              label="Soporte conversion"
              value={
                inputDetail.unitsConversion.unitConversionSupported
                  ? "Configurado"
                  : "No configurado"
              }
            />
          </dl>
        </DetailBlock>

        <DetailBlock title="Proveedores">
          {inputDetail.suppliers.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">
              Este insumo no tiene proveedores asociados.
            </p>
          ) : (
            <div className="space-y-2">
              {inputDetail.suppliers.map((supplier) => (
                <button
                  className="w-full rounded-xl border border-slate-100 bg-slate-50 p-2 text-left text-sm hover:border-[var(--ui-color-primary)]"
                  key={supplier.id}
                  type="button"
                  onClick={() => onOpenSupplier(supplier.supplierId)}
                >
                  <p
                    className="truncate font-semibold text-slate-950"
                    title={supplier.supplierName}
                  >
                    {supplier.supplierName}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    {supplier.supplierSku ?? "Sin SKU proveedor"} -{" "}
                    {supplier.purchaseUom ?? "Sin unidad"} -{" "}
                    {supplier.lastKnownPrice ?? "Sin precio"} {supplier.currency}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    Lead time {supplier.leadTimeDays} dias -{" "}
                    {supplier.isActive ? "Relacion activa" : "Inactiva"}
                  </p>
                </button>
              ))}
            </div>
          )}
        </DetailBlock>

        <DetailBlock title="Costos">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <Definition
              label="Costo estandar"
              value={inputDetail.cost.standardCost ?? "Sin costo"}
            />
            <Definition
              label="Ultima compra"
              value={inputDetail.cost.lastPurchaseCost ?? "No disponible"}
            />
            <Definition
              label="Rango proveedor"
              value={`${inputDetail.cost.supplierPriceMin ?? "N/D"} - ${inputDetail.cost.supplierPriceMax ?? "N/D"}`}
            />
            <Definition label="Moneda" value={inputDetail.cost.currency} />
          </dl>
          {inputDetail.cost.warnings.length > 0 ? (
            <div className="mt-2 space-y-1">
              {inputDetail.cost.warnings.map((warning) => (
                <p
                  className={`rounded-xl border px-3 py-2 text-xs font-semibold ${toneClass(warning.severity)}`}
                  key={warning.code}
                >
                  {warning.message}
                </p>
              ))}
            </div>
          ) : null}
        </DetailBlock>

        <DetailBlock title="Inventario">
          {inputDetail.inventoryStatus.integrationAvailable ? (
            <div className="space-y-2 text-sm">
              <dl className="grid grid-cols-2 gap-2">
                <Definition
                  label="Total"
                  value={`${inputDetail.inventoryStatus.totalStock ?? "0"} ${inputDetail.inventoryStatus.unitOfMeasure}`}
                />
                <Definition
                  label="Estado"
                  value={formatStockState(inputDetail.inventoryStatus.stockState)}
                />
                <Definition
                  label="Minimo"
                  value={inputDetail.inventoryStatus.minimumStock ?? "No definido"}
                />
                <Definition
                  label="Reorden"
                  value={inputDetail.inventoryStatus.reorderPoint ?? "No definido"}
                />
                <Definition
                  label="Pedido preferido"
                  value={inputDetail.inventoryStatus.preferredOrderQuantity ?? "No definido"}
                />
                <Definition
                  label="Ultimo movimiento"
                  value={formatDate(inputDetail.inventoryStatus.lastMovementAt)}
                />
              </dl>
              <div className="space-y-1">
                {inputDetail.inventoryStatus.stockByBranch.map((branch) => (
                  <div
                    className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2"
                    key={branch.branchId}
                  >
                    <p className="font-semibold text-slate-950">{branch.branchName}</p>
                    <p className="text-xs text-slate-500">
                      {branch.quantityOnHand} - {formatStockState(branch.stockState)} -{" "}
                      {formatDate(branch.lastMovementAt)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm font-semibold text-slate-500">
              No hay informacion de inventario disponible para este insumo.
            </p>
          )}
        </DetailBlock>

        <DetailBlock title={isRawMaterial ? "Uso en recetas" : "Uso operativo"}>
          {inputDetail.recipeUsage.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">
              Este insumo no esta asociado a recetas.
            </p>
          ) : (
            <div className="space-y-2">
              {inputDetail.recipeUsage.map((usage) => (
                <button
                  className="w-full rounded-xl border border-slate-100 bg-slate-50 p-2 text-left text-sm hover:border-[var(--ui-color-primary)]"
                  key={`${usage.recipeId}-${usage.finishedProductId}`}
                  type="button"
                  onClick={() => onOpenRecipes(overview.id)}
                >
                  <p className="truncate font-semibold text-slate-950">
                    {usage.finishedProductName}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    {usage.finishedProductCode} - {usage.quantity} {usage.unitOfMeasure} -{" "}
                    {usage.recipeVersionName ?? "Receta activa"}
                  </p>
                </button>
              ))}
            </div>
          )}
        </DetailBlock>

        <DetailBlock title="Preparacion y advertencias">
          {inputDetail.procurementWarnings.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">
              No hay advertencias para este insumo.
            </p>
          ) : (
            <div className="space-y-2">
              {inputDetail.procurementWarnings.map((warning) => (
                <p
                  className={`rounded-xl border px-3 py-2 text-sm font-semibold ${toneClass(warning.severity)}`}
                  key={warning.code}
                >
                  {warning.message}
                </p>
              ))}
            </div>
          )}
        </DetailBlock>

        <DetailBlock title="Documentos relacionados">
          {inputDetail.relatedDocuments.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">
              Este insumo no tiene documentos relacionados.
            </p>
          ) : (
            <div className="space-y-2">
              {inputDetail.relatedDocuments.map((document) => (
                <div
                  className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-sm"
                  key={`${document.documentType}-${document.documentId}`}
                >
                  <p className="font-semibold text-slate-950">{document.documentType}</p>
                  <p className="text-xs text-slate-500">
                    {document.folio} - {document.status}
                  </p>
                </div>
              ))}
            </div>
          )}
        </DetailBlock>

        <DetailBlock title="Acciones disponibles">
          <p className="text-sm font-semibold text-slate-500">
            El stock se modifica desde Compras / entradas, Produccion, Merma, Transferencias o
            ajustes auditados de Inventario. Este modulo no edita existencias directamente.
          </p>
        </DetailBlock>
      </div>
    </aside>
  );
}
