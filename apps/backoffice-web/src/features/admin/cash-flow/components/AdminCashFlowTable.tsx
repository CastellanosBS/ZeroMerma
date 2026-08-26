import type { AdminCashFlowMovementListItem } from "../types";

interface AdminCashFlowTableProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  movements: AdminCashFlowMovementListItem[];
  onCopyReference: (movement: AdminCashFlowMovementListItem) => void;
  onPageChange: (page: number) => void;
  onSelectMovement: (movement: AdminCashFlowMovementListItem) => void;
  page: number;
  pageSize: number;
  selectedMovementId?: string | null;
  total: number;
}

const directionLabels: Record<string, string> = {
  ADJUSTMENT: "Ajuste",
  INFLOW: "Entrada",
  OUTFLOW: "Salida",
};

const sourceLabels: Record<string, string> = {
  CASH_CUT_DIFFERENCE: "Diferencia de caja",
  OPERATIONAL_DISCOUNT: "Descuento operativo",
  OPERATIONAL_PAYMENT: "Pago operativo",
  RETURN_REFUND: "Devolucion",
  SALE: "Venta",
};

function formatMoney(value: string) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} MXN`;
  }
  return new Intl.NumberFormat("es-MX", { currency: "MXN", style: "currency" }).format(
    numericValue,
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function warningLabel(value: string) {
  if (value === "critical") return "Critico";
  if (value === "reconciliation") return "Conciliacion";
  if (value === "pending_cut") return "Pendiente corte";
  return "OK";
}

export function AdminCashFlowTable({
  errorMessage,
  isLoading = false,
  movements,
  onCopyReference,
  onPageChange,
  onSelectMovement,
  page,
  pageSize,
  selectedMovementId,
  total,
}: AdminCashFlowTableProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-4 py-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">Movimientos de flujo</h3>
          <p className="truncate text-xs text-slate-500">
            {total} movimientos derivados de documentos persistidos
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
          Pagina {page} / {pageCount}
        </span>
      </div>

      {errorMessage ? (
        <p className="m-3 rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {errorMessage}
        </p>
      ) : null}

      <div className="min-h-0 flex-1 overflow-auto">
        <table className="min-w-[70rem] text-left text-sm">
          <thead className="sticky top-0 z-10 bg-slate-50 text-xs uppercase tracking-[0.08em] text-slate-500">
            <tr>
              <th className="px-3 py-2">Fecha / hora</th>
              <th className="px-3 py-2">Sucursal</th>
              <th className="px-3 py-2">Caja / estacion</th>
              <th className="px-3 py-2">Direccion</th>
              <th className="px-3 py-2">Origen</th>
              <th className="px-3 py-2">Folio origen</th>
              <th className="px-3 py-2">Categoria</th>
              <th className="px-3 py-2">Metodo</th>
              <th className="px-3 py-2 text-right">Monto</th>
              <th className="px-3 py-2">Conciliacion</th>
              <th className="px-3 py-2">Operador</th>
              <th className="px-3 py-2">Advertencias</th>
              <th className="px-3 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td className="px-3 py-8 text-center text-sm text-slate-500" colSpan={13}>
                  Cargando movimientos de flujo de efectivo.
                </td>
              </tr>
            ) : movements.length === 0 ? (
              <tr>
                <td className="px-3 py-8 text-center text-sm text-slate-500" colSpan={13}>
                  No hay movimientos de flujo de efectivo para los filtros seleccionados.
                </td>
              </tr>
            ) : (
              movements.map((movement) => (
                <tr
                  className={`cursor-pointer border-b border-[var(--ui-color-border)] transition hover:bg-slate-50 ${
                    selectedMovementId === movement.id ? "bg-[var(--ui-color-primary-soft)]" : ""
                  }`}
                  key={movement.id}
                  onClick={() => onSelectMovement(movement)}
                >
                  <td className="whitespace-nowrap px-3 py-2 text-slate-700">
                    {formatDate(movement.occurredAt)}
                  </td>
                  <td className="px-3 py-2 font-medium text-slate-950">{movement.branchName}</td>
                  <td className="px-3 py-2 text-slate-700">{movement.workstationName}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${
                        movement.direction === "INFLOW"
                          ? "bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]"
                          : movement.direction === "OUTFLOW"
                            ? "bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]"
                            : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {directionLabels[movement.direction] ?? movement.direction}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-slate-700">
                    {sourceLabels[movement.sourceType] ?? movement.sourceType}
                  </td>
                  <td className="px-3 py-2 font-semibold text-slate-950">
                    {movement.sourceReference}
                  </td>
                  <td className="px-3 py-2 text-slate-600">{movement.category ?? "N/A"}</td>
                  <td className="px-3 py-2 text-slate-700">{movement.paymentMethod}</td>
                  <td className="px-3 py-2 text-right font-semibold text-slate-950">
                    {formatMoney(movement.amount)}
                  </td>
                  <td className="px-3 py-2 text-slate-700">{movement.reconciliationStatus}</td>
                  <td className="px-3 py-2 text-slate-700">{movement.operatorName}</td>
                  <td className="px-3 py-2 text-slate-700">
                    {warningLabel(movement.warningState)}
                  </td>
                  <td className="px-3 py-2">
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700"
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onCopyReference(movement);
                      }}
                    >
                      Copiar
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-end gap-2 border-t border-[var(--ui-color-border)] px-4 py-3">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-40"
          disabled={page <= 1}
          type="button"
          onClick={() => onPageChange(page - 1)}
        >
          Anterior
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-40"
          disabled={page >= pageCount}
          type="button"
          onClick={() => onPageChange(page + 1)}
        >
          Siguiente
        </button>
      </div>
    </section>
  );
}
