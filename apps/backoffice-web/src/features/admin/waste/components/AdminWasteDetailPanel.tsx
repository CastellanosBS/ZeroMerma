import type { ReactNode } from "react";

import type { AdminWasteDetail, AdminWasteListItem } from "../types";

interface AdminWasteDetailPanelProps {
  errorMessage?: string | null;
  isLoading: boolean;
  wasteDetail?: AdminWasteDetail | null;
  wastePreview?: AdminWasteListItem | null;
  onOpenBranch: (branchId: string) => void;
  onOpenCorrection: (wasteId: string) => void;
  onOpenInventory: (productId: string, branchId: string) => void;
  onOpenProduct: (productId: string) => void;
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

function toneClass(tone?: string | null) {
  if (tone === "critical") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (tone === "warning") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function DetailBlock({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{title}</h3>
      {children}
    </section>
  );
}

export function AdminWasteDetailPanel({
  errorMessage,
  isLoading,
  wasteDetail,
  wastePreview,
  onOpenBranch,
  onOpenCorrection,
  onOpenInventory,
  onOpenProduct,
}: AdminWasteDetailPanelProps) {
  if (!wastePreview && !wasteDetail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col justify-center rounded-[20px] border border-dashed border-slate-200 bg-slate-50 p-5 text-sm font-semibold text-slate-500">
        Selecciona una merma para revisar producto, motivo, evidencia e impacto en inventario.
      </aside>
    );
  }

  if (isLoading) {
    return (
      <aside className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-4 text-sm font-semibold text-slate-500">
        Cargando detalle de merma.
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

  if (!wasteDetail) {
    return null;
  }

  const overview = wasteDetail.overview;
  const product = wasteDetail.productInventoryContext;

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50">
      <div className="border-b border-[var(--ui-color-border)] bg-white p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Detalle de merma</p>
            <h2 className="truncate text-lg font-semibold text-slate-950">{overview.folio}</h2>
            <p className="text-sm text-slate-600">
              {overview.branchName} - {overview.locationName}
            </p>
          </div>
          <span className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClass(overview.warningState)}`}>
            {overview.impactLevel === "high" ? "Alto impacto" : "Normal"}
          </span>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-auto p-3">
        <DetailBlock title="Resumen">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-xs text-slate-500">Estado</dt>
              <dd className="font-semibold text-slate-950">{overview.status}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Confirmada</dt>
              <dd className="font-semibold text-slate-950">{formatDate(overview.confirmedAt)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Cantidad</dt>
              <dd className="font-semibold text-slate-950">
                {overview.quantity} {overview.uom}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Operador</dt>
              <dd className="font-semibold text-slate-950">{overview.operatorName}</dd>
            </div>
            <div className="col-span-2">
              <dt className="text-xs text-slate-500">Estacion operativa</dt>
              <dd className="font-semibold text-slate-950">
                {overview.workstationCode ? `${overview.workstationName} - ${overview.workstationCode}` : "No disponible"}
              </dd>
            </div>
          </dl>
        </DetailBlock>

        <DetailBlock title="Producto e inventario">
          <div className="space-y-2 text-sm text-slate-700">
            <div>
              <p className="font-semibold text-slate-950">{product.productName}</p>
              <p className="text-xs text-slate-500">
                {product.productCode} - {product.productKind} - {product.className}
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <span className="rounded-xl bg-slate-50 p-2">
                <span className="block text-xs text-slate-500">Antes</span>
                <span className="font-semibold">{product.stockBefore ?? "No disponible"}</span>
              </span>
              <span className="rounded-xl bg-slate-50 p-2">
                <span className="block text-xs text-slate-500">Despues</span>
                <span className="font-semibold">{product.stockAfter ?? "No disponible"}</span>
              </span>
              <span className="rounded-xl bg-slate-50 p-2">
                <span className="block text-xs text-slate-500">Actual</span>
                <span className="font-semibold">{product.currentStock ?? "No disponible"}</span>
              </span>
            </div>
          </div>
        </DetailBlock>

        <DetailBlock title="Motivo y evidencia">
          <div className="space-y-2 text-sm">
            <p className="font-semibold text-slate-950">{wasteDetail.reasonClassification.label}</p>
            <p className="text-slate-600">{wasteDetail.reasonClassification.description ?? "Sin descripcion adicional."}</p>
            <p className="rounded-xl bg-slate-50 p-2 text-slate-700">{overview.notes ?? "Sin notas registradas."}</p>
            {wasteDetail.evidence.evidenceItems.length === 0 ? (
              <p className="text-xs font-semibold text-slate-500">Esta merma no tiene evidencia adjunta.</p>
            ) : null}
          </div>
        </DetailBlock>

        <DetailBlock title="Lineas">
          <div className="space-y-2">
            {wasteDetail.lines.map((line) => (
              <div className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-sm" key={line.lineNumber}>
                <p className="font-semibold text-slate-950">{line.productName}</p>
                <p className="text-xs text-slate-500">
                  {line.quantity} {line.uom} - {line.productCode}
                </p>
              </div>
            ))}
          </div>
        </DetailBlock>

        <DetailBlock title="Impacto de inventario">
          {wasteDetail.inventoryImpact.movements.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">No hay movimiento de inventario vinculado.</p>
          ) : (
            <div className="space-y-2">
              {wasteDetail.inventoryImpact.movements.map((movement) => (
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-sm" key={movement.id}>
                  <p className="font-semibold text-slate-950">{movement.movementType}</p>
                  <p className="text-xs text-slate-500">
                    {movement.direction} - {movement.quantity} {movement.unitOfMeasure} - saldo {movement.balanceAfter ?? "N/D"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </DetailBlock>

        <DetailBlock title="Advertencias">
          {wasteDetail.warnings.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">No hay advertencias para esta merma.</p>
          ) : (
            <div className="space-y-2">
              {wasteDetail.warnings.map((warning) => (
                <p className={`rounded-xl border px-3 py-2 text-sm font-semibold ${toneClass(warning.severity)}`} key={warning.code}>
                  {warning.message}
                </p>
              ))}
            </div>
          )}
        </DetailBlock>

        <DetailBlock title="Documentos relacionados">
          {wasteDetail.relatedDocuments.length === 0 ? (
            <p className="text-sm font-semibold text-slate-500">Esta merma no tiene documentos relacionados.</p>
          ) : (
            <div className="space-y-2">
              {wasteDetail.relatedDocuments.map((document) => (
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-2 text-sm" key={`${document.documentType}-${document.documentId}`}>
                  <p className="font-semibold text-slate-950">{document.documentType}</p>
                  <p className="text-xs text-slate-500">
                    {document.folio} - {document.status}
                  </p>
                </div>
              ))}
            </div>
          )}
        </DetailBlock>

        <div className="grid gap-2">
          <button className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700" type="button" onClick={() => onOpenProduct(product.productId)}>
            Abrir producto
          </button>
          <button className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700" type="button" onClick={() => onOpenBranch(product.branchId)}>
            Abrir sucursal
          </button>
          <button className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700" type="button" onClick={() => onOpenInventory(product.productId, product.branchId)}>
            Ver inventario
          </button>
          <button className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700" type="button" onClick={() => onOpenCorrection(overview.id)}>
            Crear correccion
          </button>
        </div>
      </div>
    </aside>
  );
}
