import type { ReactNode } from "react";

import type {
  AdminProductionDetail,
  AdminProductionInventoryMovement,
  AdminProductionListItem,
  AdminProductionStatus,
  AdminProductionWarning,
} from "../types";

function formatStatus(status: AdminProductionStatus): string {
  const labels: Record<AdminProductionStatus, string> = {
    CANCELLED: "Cancelada",
    COMPLETED: "Completada",
    DRAFT: "Pendiente",
    IN_PROGRESS: "En proceso",
  };
  return labels[status];
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Pendiente";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="grid min-w-0 grid-cols-[7.5rem_minmax(0,1fr)] gap-2 text-xs">
      <span className="truncate font-semibold uppercase tracking-[0.08em] text-slate-500" title={label}>
        {label}
      </span>
      <span className="min-w-0 truncate font-medium text-slate-900" title={String(value ?? "No disponible")}>
        {value ?? "No disponible"}
      </span>
    </div>
  );
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h4 className="mb-2 truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500" title={title}>
        {title}
      </h4>
      {children}
    </div>
  );
}

function WarningItem({ warning }: { warning: AdminProductionWarning }) {
  const toneClass =
    warning.severity === "critical"
      ? "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]"
      : warning.severity === "warning"
        ? "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]"
        : "border-[var(--ui-color-border)] bg-slate-50 text-slate-600";

  return (
    <li className={`rounded-[14px] border px-3 py-2 text-xs leading-5 ${toneClass}`} title={warning.message}>
      <span className="font-semibold">{warning.code}</span>: {warning.message}
    </li>
  );
}

function MovementRow({ movement }: { movement: AdminProductionInventoryMovement }) {
  const directionClass =
    movement.direction === "IN"
      ? "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]"
      : "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";

  return (
    <li className="grid min-w-0 gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs">
      <div className="flex min-w-0 items-center justify-between gap-2">
        <span className="truncate font-semibold text-slate-950" title={movement.movementType}>
          {movement.movementType}
        </span>
        <span className={`shrink-0 rounded-full border px-2 py-0.5 font-semibold ${directionClass}`}>
          {movement.direction}
        </span>
      </div>
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_5rem] gap-2">
        <span className="truncate text-slate-500" title={`${movement.locationCode} - ${movement.sourceDocumentType ?? ""}`}>
          {movement.locationCode}
        </span>
        <span className="truncate text-right font-semibold text-slate-900" title={movement.quantity}>
          {movement.quantity}
        </span>
      </div>
      <p className="truncate text-slate-500" title={movement.sourceDocumentId ?? "Sin documento"}>
        {movement.sourceDocumentType ?? "Sin documento"}
      </p>
    </li>
  );
}

interface AdminProductionDetailPanelProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  isSubmitting?: boolean;
  onCancel: (detail: AdminProductionDetail) => void;
  onComplete: (detail: AdminProductionDetail) => void;
  onEdit: (detail: AdminProductionDetail) => void;
  onOpenBranch: (branchId: string) => void;
  onOpenInventory: (productId: string, branchId: string) => void;
  onOpenProduct: (productId: string) => void;
  onOpenRecipe: (productId: string) => void;
  onStart: (detail: AdminProductionDetail) => void;
  productionDetail?: AdminProductionDetail | null;
  productionPreview?: AdminProductionListItem | null;
}

export function AdminProductionDetailPanel({
  errorMessage,
  isLoading = false,
  isSubmitting = false,
  onCancel,
  onComplete,
  onEdit,
  onOpenBranch,
  onOpenInventory,
  onOpenProduct,
  onOpenRecipe,
  onStart,
  productionDetail,
  productionPreview,
}: AdminProductionDetailPanelProps) {
  if (!productionPreview && !productionDetail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-3 py-2.5">
          <h3 className="truncate text-base font-semibold text-slate-950">Detalle de produccion</h3>
        </div>
        <div className="flex min-h-0 flex-1 items-center p-3">
          <div className="rounded-[18px] border border-dashed border-[var(--ui-color-border)] bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            <p className="font-semibold text-slate-950">Sin produccion seleccionada</p>
            <p>Selecciona una produccion para revisar receta, insumos, avance e impacto en inventario.</p>
          </div>
        </div>
      </aside>
    );
  }

  const folio = productionDetail?.overview.folio ?? productionPreview?.folio ?? "";
  const status = productionDetail?.overview.status ?? productionPreview?.status ?? "DRAFT";
  const warnings = productionDetail?.warnings ?? productionPreview?.warnings ?? [];
  const branchId = productionDetail?.overview.branchId ?? productionPreview?.branchId ?? "";
  const productId = productionDetail?.productRecipe.productId ?? productionPreview?.productId ?? "";
  const hasVariance =
    Boolean(productionDetail?.overview.varianceQty && productionDetail.overview.varianceQty !== "0.000") ||
    Boolean(productionPreview?.varianceQty && productionPreview.varianceQty !== "0.000");

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-start justify-between gap-2 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate font-mono text-base font-semibold text-slate-950" title={folio}>
            {folio}
          </h3>
          <p className="truncate text-xs text-slate-500" title={formatStatus(status)}>
            {formatStatus(status)}
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${
            hasVariance
              ? "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]"
              : "border-[var(--ui-color-border)] bg-white text-slate-600"
          }`}
        >
          {hasVariance ? "Con variacion" : "Sin variacion"}
        </span>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2.5">
        {isLoading ? (
          <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 p-3 text-sm text-slate-600">
            Cargando detalle de produccion.
          </div>
        ) : null}
        {errorMessage ? (
          <div className="rounded-[18px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-3 text-sm text-[var(--ui-color-danger)]">
            {errorMessage}
          </div>
        ) : null}

        <Section title="Resumen">
          <div className="grid gap-1.5">
            <InfoRow label="Estado" value={formatStatus(status)} />
            <InfoRow label="Sucursal" value={productionDetail?.overview.branchName ?? productionPreview?.branchName} />
            <InfoRow label="Planeado" value={productionDetail?.overview.plannedOutputQty ?? productionPreview?.plannedOutputQty} />
            <InfoRow label="Producido" value={productionDetail?.overview.actualOutputQty ?? productionPreview?.actualOutputQty ?? "Pendiente"} />
            <InfoRow label="Inicio" value={formatDate(productionDetail?.overview.startedAt ?? productionPreview?.startedAt)} />
            <InfoRow label="Cierre" value={formatDate(productionDetail?.overview.completedAt ?? productionPreview?.completedAt)} />
            <InfoRow label="Operador" value={productionDetail?.overview.createdByUserName ?? productionPreview?.operatorName} />
          </div>
        </Section>

        <Section title="Producto / receta">
          <div className="grid gap-1.5">
            <InfoRow
              label="Producto"
              value={
                productionDetail
                  ? `${productionDetail.productRecipe.productName} (${productionDetail.productRecipe.productCode})`
                  : `${productionPreview?.productName} (${productionPreview?.productCode})`
              }
            />
            <InfoRow label="Tipo" value={productionDetail?.productRecipe.productKind ?? "FINISHED_GOOD"} />
            <InfoRow label="Unidad" value={productionDetail?.productRecipe.productUnitOfMeasure ?? "No disponible"} />
            <InfoRow label="Receta" value={productionDetail?.productRecipe.recipeName ?? productionPreview?.recipeName} />
            <InfoRow label="Rendimiento" value={productionDetail ? `${productionDetail.productRecipe.recipeYieldQty} ${productionDetail.productRecipe.recipeYieldUom}` : null} />
          </div>
        </Section>

        {productionDetail ? (
          <>
            <Section title="Insumos planeados">
              {productionDetail.plannedInputs.length > 0 ? (
                <ul className="grid gap-1.5">
                  {productionDetail.plannedInputs.map((line) => (
                    <li
                      className="grid min-w-0 gap-1.5 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs"
                      key={line.inputProductId}
                    >
                      <div className="flex min-w-0 items-center justify-between gap-2">
                        <span className="truncate font-semibold text-slate-950" title={line.inputProductName}>
                          {line.inputProductName}
                        </span>
                        <span className="shrink-0 font-mono text-slate-500">{line.inputProductCode}</span>
                      </div>
                      <div className="grid min-w-0 grid-cols-3 gap-2 text-slate-600">
                        <span className="truncate">Req. {line.requiredQty}</span>
                        <span className="truncate">Disp. {line.availableQty ?? "N/D"}</span>
                        <span className="truncate">Falt. {line.shortageQty ?? "0.000"}</span>
                      </div>
                      {line.status !== "available" ? (
                        <p className="rounded-[12px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-2 py-1 font-semibold text-[var(--ui-color-danger)]">
                          Insumo insuficiente o no disponible.
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm leading-6 text-slate-600">Esta produccion no tiene insumos planeados.</p>
              )}
            </Section>

            <Section title="Consumo real">
              {productionDetail.actualConsumption.length > 0 ? (
                <ul className="grid gap-1.5">
                  {productionDetail.actualConsumption.map((line) => (
                    <li
                      className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs"
                      key={line.inputProductId}
                    >
                      <span className="block truncate font-semibold text-slate-950" title={line.inputProductName}>
                        {line.inputProductName}
                      </span>
                      <span className="block truncate text-slate-500">
                        Esperado {line.expectedQty} - Consumido {line.consumedQty ?? "Pendiente"} {line.uom}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm leading-6 text-slate-600">
                  El consumo real se captura por backend al completar la produccion.
                </p>
              )}
            </Section>

            <Section title="Salida / rendimiento">
              <div className="grid gap-1.5">
                <InfoRow label="Planeado" value={`${productionDetail.outputYield.plannedOutputQty} ${productionDetail.outputYield.uom}`} />
                <InfoRow label="Real" value={productionDetail.outputYield.actualOutputQty ?? "Pendiente"} />
                <InfoRow label="Variacion" value={productionDetail.outputYield.varianceQty ?? "Pendiente"} />
                <InfoRow label="Porcentaje" value={productionDetail.outputYield.variancePercent ?? "Pendiente"} />
                <InfoRow label="Razon" value={productionDetail.outputYield.varianceReason ?? "No registrada"} />
              </div>
            </Section>

            <Section title="Merma / scrap">
              <p className="text-sm leading-6 text-slate-600">
                {productionDetail.wasteScrap.integrationAvailable
                  ? "Merma integrada con documentos dedicados."
                  : productionDetail.wasteScrap.notes}
              </p>
            </Section>

            <Section title="Impacto en inventario">
              {productionDetail.inventoryImpact.integrationAvailable ? (
                productionDetail.inventoryImpact.movements.length > 0 ? (
                  <ul className="grid gap-1.5">
                    {productionDetail.inventoryImpact.movements.map((movement) => (
                      <MovementRow key={movement.id} movement={movement} />
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm leading-6 text-slate-600">
                    El backend integra inventario; aun no hay movimientos porque el lote no se ha completado.
                  </p>
                )
              ) : (
                <p className="text-sm leading-6 text-slate-600">
                  {productionDetail.inventoryImpact.notes ?? "Contrato de movimientos pendiente."}
                </p>
              )}
            </Section>

            <Section title="Documentos relacionados">
              {productionDetail.relatedDocuments.length > 0 ? (
                <ul className="grid gap-1.5">
                  {productionDetail.relatedDocuments.map((document) => (
                    <li
                      className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs"
                      key={`${document.documentType}-${document.documentId}`}
                    >
                      <span className="block truncate font-semibold text-slate-950" title={document.folio}>
                        {document.folio}
                      </span>
                      <span className="block truncate text-slate-500" title={`${document.documentType} - ${document.status}`}>
                        {document.documentType} - {document.status}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm leading-6 text-slate-600">Esta produccion no tiene documentos relacionados.</p>
              )}
            </Section>
          </>
        ) : null}

        <Section title="Advertencias">
          {warnings.length > 0 ? (
            <ul className="grid gap-1.5">
              {warnings.map((warning) => (
                <WarningItem key={warning.code} warning={warning} />
              ))}
            </ul>
          ) : (
            <p className="text-sm leading-6 text-slate-600">No hay faltantes de insumos para esta produccion.</p>
          )}
        </Section>
      </div>

      <div className="flex shrink-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] p-3 text-xs">
        {productionDetail?.availableActions.canStart ? (
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={isSubmitting}
            type="button"
            onClick={() => onStart(productionDetail)}
          >
            Iniciar
          </button>
        ) : null}
        {productionDetail?.availableActions.canEdit ? (
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={isSubmitting}
            type="button"
            onClick={() => onEdit(productionDetail)}
          >
            Editar
          </button>
        ) : null}
        {productionDetail?.availableActions.canComplete ? (
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={isSubmitting}
            type="button"
            onClick={() => onComplete(productionDetail)}
          >
            Completar
          </button>
        ) : null}
        {productionDetail?.availableActions.canCancel ? (
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={isSubmitting}
            type="button"
            onClick={() => onCancel(productionDetail)}
          >
            Cancelar
          </button>
        ) : null}
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onOpenBranch(branchId)}
        >
          Abrir sucursal
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onOpenProduct(productId)}
        >
          Abrir producto
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onOpenRecipe(productId)}
        >
          Abrir receta
        </button>
        {productionDetail?.plannedInputs[0] ? (
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={() => onOpenInventory(productionDetail.plannedInputs[0].inputProductId, branchId)}
          >
            Ver insumo
          </button>
        ) : null}
      </div>
    </aside>
  );
}
