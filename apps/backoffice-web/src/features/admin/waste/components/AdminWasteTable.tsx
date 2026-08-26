import type { AdminWasteBackendContract, AdminWasteListItem } from "../types";

interface AdminWasteTableProps {
  backendContract: AdminWasteBackendContract;
  errorMessage?: string | null;
  isLoading: boolean;
  isSubmitting: boolean;
  page: number;
  pageSize: number;
  selectedWasteId?: string | null;
  total: number;
  wasteRecords: AdminWasteListItem[];
  onOpenInventory: (productId: string, branchId: string) => void;
  onOpenProduct: (productId: string) => void;
  onPageChange: (page: number) => void;
  onSelectWaste: (item: AdminWasteListItem) => void;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatEstimatedValue(value?: string | null) {
  if (!value) {
    return "N/D";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "N/D";
  }
  return new Intl.NumberFormat("es-MX", {
    currency: "MXN",
    maximumFractionDigits: 2,
    style: "currency",
  }).format(numericValue);
}

function impactClass(impact: string) {
  return impact === "high"
    ? "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]"
    : "border-slate-200 bg-slate-50 text-slate-700";
}

function statusLabel(status: string) {
  if (status === "COMMITTED") {
    return "Confirmada";
  }
  if (status === "CANCELLED") {
    return "Cancelada";
  }
  return status;
}

function warningLabel(item: AdminWasteListItem) {
  if (!item.warningState) {
    return "Sin advertencias";
  }
  if (item.warningState === "critical") {
    return "Critico";
  }
  if (item.warningState === "warning") {
    return "Advertencia";
  }
  return "Info";
}

export function AdminWasteTable({
  backendContract,
  errorMessage,
  isLoading,
  isSubmitting,
  page,
  pageSize,
  selectedWasteId,
  total,
  wasteRecords,
  onOpenInventory,
  onOpenProduct,
  onPageChange,
  onSelectWaste,
}: AdminWasteTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex items-center justify-between border-b border-[var(--ui-color-border)] px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-950">Registros de merma</h2>
          <p className="text-xs text-slate-500">{backendContract.listEndpoint}</p>
        </div>
        <span className="rounded-full bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">{total} registros</span>
      </div>

      {errorMessage ? (
        <p className="m-3 rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-4 py-3 text-sm font-semibold text-[var(--ui-color-danger)]">
          {errorMessage}
        </p>
      ) : null}

      <div className="min-h-0 flex-1 overflow-auto">
        <table className="min-w-[96rem] w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-slate-50 text-left text-xs uppercase tracking-[0.08em] text-slate-500">
            <tr>
              <th className="px-4 py-3 font-semibold">Folio</th>
              <th className="px-4 py-3 font-semibold">Fecha / hora</th>
              <th className="px-4 py-3 font-semibold">Sucursal</th>
              <th className="px-4 py-3 font-semibold">Ubicacion / origen</th>
              <th className="px-4 py-3 font-semibold">Producto</th>
              <th className="px-4 py-3 font-semibold">Tipo</th>
              <th className="px-4 py-3 font-semibold">Motivo</th>
              <th className="px-4 py-3 font-semibold">Cantidad</th>
              <th className="px-4 py-3 font-semibold">Unidad</th>
              <th className="px-4 py-3 font-semibold">Valor estimado</th>
              <th className="px-4 py-3 font-semibold">Operador</th>
              <th className="px-4 py-3 font-semibold">Estado</th>
              <th className="px-4 py-3 font-semibold">Impacto</th>
              <th className="px-4 py-3 font-semibold">Evidencia</th>
              <th className="px-4 py-3 font-semibold">Advertencias</th>
              <th className="px-4 py-3 font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td className="px-4 py-8 text-center text-sm font-semibold text-slate-500" colSpan={16}>
                  Cargando mermas registradas.
                </td>
              </tr>
            ) : wasteRecords.length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-sm font-semibold text-slate-500" colSpan={16}>
                  No hay mermas registradas para los filtros seleccionados.
                </td>
              </tr>
            ) : (
              wasteRecords.map((item) => (
                <tr
                  className={`cursor-pointer hover:bg-slate-50 ${
                    selectedWasteId === item.id ? "bg-[var(--ui-color-primary-soft)]" : "bg-white"
                  }`}
                  key={item.id}
                  onClick={() => onSelectWaste(item)}
                >
                  <td className="px-4 py-3 font-semibold text-slate-950">{item.folio}</td>
                  <td className="px-4 py-3 text-slate-600">{formatDate(item.createdAt)}</td>
                  <td className="px-4 py-3 text-slate-700">{item.branchName}</td>
                  <td className="px-4 py-3 text-slate-700">{item.locationName}</td>
                  <td className="px-4 py-3">
                    <div className="font-semibold text-slate-900">{item.productName}</div>
                    <div className="text-xs text-slate-500">{item.productCode}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{item.productKind}</td>
                  <td className="px-4 py-3 text-slate-700">{item.reasonLabel}</td>
                  <td className="px-4 py-3 font-semibold text-slate-950">{item.quantity}</td>
                  <td className="px-4 py-3 text-slate-700">{item.uom}</td>
                  <td className="px-4 py-3 text-slate-700">{formatEstimatedValue(item.estimatedValue)}</td>
                  <td className="px-4 py-3 text-slate-700">{item.operatorName}</td>
                  <td className="px-4 py-3 text-slate-700">{statusLabel(item.status)}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${impactClass(item.impactLevel)}`}>
                      {item.impactLevel === "high" ? "Alto impacto" : "Normal"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{item.hasEvidence ? "Con evidencia" : "Sin evidencia"}</td>
                  <td className="px-4 py-3 text-slate-600">{warningLabel(item)}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1.5">
                      <button
                        className="rounded-full border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-[var(--ui-color-primary)]"
                        disabled={isSubmitting}
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          onSelectWaste(item);
                        }}
                      >
                        Ver
                      </button>
                      <button
                        className="rounded-full border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-[var(--ui-color-primary)]"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          void navigator.clipboard?.writeText(item.folio);
                        }}
                      >
                        Copiar
                      </button>
                      <button
                        className="rounded-full border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-[var(--ui-color-primary)]"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          onOpenProduct(item.productId);
                        }}
                      >
                        Producto
                      </button>
                      <button
                        className="rounded-full border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-[var(--ui-color-primary)]"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          onOpenInventory(item.productId, item.branchId);
                        }}
                      >
                        Inventario
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-[var(--ui-color-border)] px-4 py-3 text-xs text-slate-600">
        <span>
          Pagina {page} de {totalPages}
        </span>
        <div className="flex gap-2">
          <button
            className="rounded-full border border-slate-200 px-3 py-1.5 font-semibold disabled:opacity-50"
            disabled={page <= 1}
            type="button"
            onClick={() => onPageChange(page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-slate-200 px-3 py-1.5 font-semibold disabled:opacity-50"
            disabled={page >= totalPages}
            type="button"
            onClick={() => onPageChange(page + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>
    </section>
  );
}
