import { AdminActionButton } from "../../components/AdminActionButton";
import type { ReactNode } from "react";

import type {
  AdminInventoryDetail,
  AdminInventoryListItem,
  AdminInventoryMovement,
  AdminInventoryProductKind,
  AdminInventoryStockState,
  AdminInventoryWarning,
} from "../types";

function formatProductKind(kind: AdminInventoryProductKind): string {
  const labels: Record<AdminInventoryProductKind, string> = {
    CONSUMABLE: "Consumible",
    DISPOSABLE: "Desechable",
    FINISHED_GOOD: "Producto terminado",
    RAW_MATERIAL: "Materia prima",
  };

  return labels[kind];
}

function formatStockState(state: AdminInventoryStockState): string {
  const labels: Record<AdminInventoryStockState, string> = {
    in_stock: "Con existencia",
    low_stock: "Stock bajo",
    negative_stock: "Stock negativo",
    out_of_stock: "Sin existencia",
  };

  return labels[state];
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin registro";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatMovementType(value: string): string {
  const labels: Record<string, string> = {
    MANUAL_ADJUSTMENT: "Ajuste manual",
    STOCK_COUNT_ADJUSTMENT: "Ajuste por conteo",
  };

  return labels[value] ?? value;
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="grid min-w-0 grid-cols-[7.25rem_minmax(0,1fr)] gap-2 text-xs">
      <span
        className="truncate font-semibold uppercase tracking-[0.08em] text-slate-500"
        title={label}
      >
        {label}
      </span>
      <span
        className="min-w-0 truncate font-medium text-slate-900"
        title={String(value ?? "No disponible")}
      >
        {value ?? "No disponible"}
      </span>
    </div>
  );
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h4
        className="mb-2 truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500"
        title={title}
      >
        {title}
      </h4>
      {children}
    </div>
  );
}

function WarningItem({ warning }: { warning: AdminInventoryWarning }) {
  const toneClass =
    warning.severity === "critical"
      ? "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]"
      : warning.severity === "warning"
        ? "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]"
        : "border-[var(--ui-color-border)] bg-slate-50 text-slate-600";

  return (
    <li
      className={`rounded-[14px] border px-3 py-2 text-xs leading-5 ${toneClass}`}
      title={warning.message}
    >
      <span className="font-semibold">{warning.code}</span>: {warning.message}
    </li>
  );
}

function MovementRow({ movement }: { movement: AdminInventoryMovement }) {
  const directionClass =
    movement.direction === "IN"
      ? "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]"
      : "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";

  return (
    <li className="grid min-w-0 gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs">
      <div className="flex min-w-0 items-center justify-between gap-2">
        <span
          className="truncate font-semibold text-slate-950"
          title={formatMovementType(movement.movementType)}
        >
          {formatMovementType(movement.movementType)}
        </span>
        <span
          className={`shrink-0 rounded-full border px-2 py-0.5 font-semibold ${directionClass}`}
        >
          {movement.direction}
        </span>
      </div>
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_5rem] gap-2">
        <span className="truncate text-slate-500" title={formatDate(movement.occurredAt)}>
          {formatDate(movement.occurredAt)}
        </span>
        <span
          className="truncate text-right font-semibold text-slate-900"
          title={movement.quantity}
        >
          {movement.quantity}
        </span>
      </div>
      <p className="truncate text-slate-500" title={movement.reason ?? "Sin razon registrada"}>
        {movement.reason ?? "Sin razon registrada"}
      </p>
      <p className="truncate text-slate-500" title={movement.operatorName ?? "Sin operador"}>
        {movement.operatorName ?? "Sin operador"}
      </p>
    </li>
  );
}

interface AdminInventoryDetailPanelProps {
  errorMessage?: string | null;
  inventoryDetail?: AdminInventoryDetail | null;
  inventoryPreview?: AdminInventoryListItem | null;
  isLoading?: boolean;
  onAdjust: (item: AdminInventoryDetail | AdminInventoryListItem) => void;
  onOpenBranch: (branchId: string) => void;
  onOpenProduct: (productId: string) => void;
}

export function AdminInventoryDetailPanel({
  errorMessage,
  inventoryDetail,
  inventoryPreview,
  isLoading = false,
  onAdjust,
  onOpenBranch,
  onOpenProduct,
}: AdminInventoryDetailPanelProps) {
  if (!inventoryPreview && !inventoryDetail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-3 py-2.5">
          <h3 className="truncate text-base font-semibold text-slate-950">Detalle de inventario</h3>
        </div>
        <div className="flex min-h-0 flex-1 items-center p-3">
          <div className="rounded-[18px] border border-dashed border-[var(--ui-color-border)] bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            <p className="font-semibold text-slate-950">Sin producto seleccionado</p>
            <p>Selecciona un producto para revisar existencias, movimientos y alertas.</p>
          </div>
        </div>
      </aside>
    );
  }

  const productName = inventoryDetail?.product.name ?? inventoryPreview?.productName ?? "";
  const productCode = inventoryDetail?.product.code ?? inventoryPreview?.productCode ?? "";
  const productId = inventoryDetail?.product.id ?? inventoryPreview?.productId ?? "";
  const branchId = inventoryDetail?.branchLocation.branchId ?? inventoryPreview?.branchId ?? "";
  const branchName =
    inventoryDetail?.branchLocation.branchName ?? inventoryPreview?.branchName ?? "";
  const locationName =
    inventoryDetail?.branchLocation.locationName ?? inventoryPreview?.locationName ?? "";
  const stockState = inventoryDetail?.stockState ?? inventoryPreview?.stockState ?? "out_of_stock";
  const warnings = inventoryDetail?.warnings ?? inventoryPreview?.warnings ?? [];

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-start justify-between gap-2 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title={productName}>
            {productName}
          </h3>
          <p className="truncate font-mono text-xs text-slate-500" title={productCode}>
            {productCode}
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-600">
          {formatStockState(stockState)}
        </span>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2.5">
        {isLoading ? (
          <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 p-3 text-sm text-slate-600">
            Cargando detalle de inventario.
          </div>
        ) : null}
        {errorMessage ? (
          <div className="rounded-[18px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-3 text-sm text-[var(--ui-color-danger)]">
            {errorMessage}
          </div>
        ) : null}

        <Section title="Resumen">
          <div className="grid gap-1.5">
            <InfoRow label="Sucursal" value={branchName} />
            <InfoRow label="Ubicacion" value={locationName} />
            <InfoRow
              label="Existencia"
              value={`${inventoryDetail?.stockBreakdown.quantityOnHand ?? inventoryPreview?.quantityOnHand ?? "0"} ${
                inventoryDetail?.stockBreakdown.unitOfMeasure ??
                inventoryPreview?.unitOfMeasure ??
                ""
              }`}
            />
            <InfoRow label="Ult. mov." value={formatDate(inventoryPreview?.lastMovementAt)} />
          </div>
        </Section>

        {inventoryDetail ? (
          <>
            <Section title="Producto">
              <div className="grid gap-1.5">
                <InfoRow
                  label="Tipo"
                  value={formatProductKind(inventoryDetail.product.productKind)}
                />
                <InfoRow label="Clase" value={inventoryDetail.product.className} />
                <InfoRow
                  label="Estado"
                  value={inventoryDetail.product.isActive ? "Activo" : "Inactivo"}
                />
                <InfoRow
                  label="Costo est."
                  value={inventoryDetail.product.standardCost ?? "No disponible"}
                />
              </div>
            </Section>

            <Section title="Sucursal / ubicacion">
              <div className="grid gap-1.5">
                <InfoRow label="Sucursal" value={inventoryDetail.branchLocation.branchName} />
                <InfoRow
                  label="Estado"
                  value={inventoryDetail.branchLocation.branchIsActive ? "Activa" : "Inactiva"}
                />
                <InfoRow label="Ubicacion" value={inventoryDetail.branchLocation.locationName} />
                <InfoRow
                  label="Modelo ubic."
                  value={
                    inventoryDetail.branchLocation.locationModelSupported
                      ? "Soportado"
                      : "Nivel sucursal"
                  }
                />
              </div>
            </Section>

            <Section title="Desglose de stock">
              <div className="grid gap-1.5">
                <InfoRow label="En mano" value={inventoryDetail.stockBreakdown.quantityOnHand} />
                <InfoRow
                  label="Reservado"
                  value={inventoryDetail.stockBreakdown.reservedQuantity ?? "No conectado"}
                />
                <InfoRow
                  label="Transito"
                  value={inventoryDetail.stockBreakdown.inTransitQuantity ?? "No conectado"}
                />
                <InfoRow
                  label="Disponible"
                  value={inventoryDetail.stockBreakdown.availableQuantity ?? "No disponible"}
                />
                <InfoRow
                  label="Valor est."
                  value={inventoryDetail.stockBreakdown.estimatedValue ?? "No disponible"}
                />
              </div>
            </Section>

            <Section title="Resumen de movimientos">
              <div className="grid gap-1.5">
                <InfoRow
                  label="Ultimo"
                  value={formatDate(inventoryDetail.movementSummary.lastMovementAt)}
                />
                <InfoRow
                  label="Entrada"
                  value={formatDate(inventoryDetail.movementSummary.lastInboundAt)}
                />
                <InfoRow
                  label="Salida"
                  value={formatDate(inventoryDetail.movementSummary.lastOutboundAt)}
                />
                <InfoRow
                  label="Ajuste"
                  value={formatDate(inventoryDetail.movementSummary.lastAdjustmentAt)}
                />
              </div>
            </Section>

            <Section title="Kardex reciente">
              {inventoryDetail.movements.length > 0 ? (
                <ul className="grid gap-1.5">
                  {inventoryDetail.movements.map((movement) => (
                    <MovementRow key={movement.id} movement={movement} />
                  ))}
                </ul>
              ) : (
                <p className="text-sm leading-6 text-slate-600">
                  Este producto no tiene movimientos registrados en esta sucursal.
                </p>
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
            <p className="text-sm leading-6 text-slate-600">
              No hay advertencias de inventario para este registro.
            </p>
          )}
        </Section>
      </div>

      <div className="flex shrink-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] p-3 text-xs">
        <AdminActionButton
          capability="inventory.adjust"
          branchIds={[branchId]}
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onAdjust(inventoryDetail ?? inventoryPreview!)}
        >
          Nuevo ajuste
        </AdminActionButton>
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
          onClick={() => onOpenBranch(branchId)}
        >
          Abrir sucursal
        </button>
      </div>
    </aside>
  );
}
