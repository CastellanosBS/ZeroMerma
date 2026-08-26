import type { AdminCashFlowMovementDetail, AdminCashFlowMovementListItem } from "../types";

interface AdminCashFlowDetailPanelProps {
  detail: AdminCashFlowMovementDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyReference: (value: AdminCashFlowMovementListItem | string) => void;
  selectedMovement: AdminCashFlowMovementListItem | null;
}

function formatMoney(value: string | null | undefined) {
  if (!value) {
    return "N/A";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} MXN`;
  }
  return new Intl.NumberFormat("es-MX", { currency: "MXN", style: "currency" }).format(
    numericValue,
  );
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "N/A";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <span className="min-w-0 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2">
      <span className="block text-xs font-medium text-slate-500">{label}</span>
      <span className="block truncate text-sm font-semibold text-slate-950">{value ?? "N/A"}</span>
    </span>
  );
}

function ActionLink({ children, href }: { children: string; href: string | null | undefined }) {
  if (!href) {
    return null;
  }
  return (
    <a
      className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)]"
      href={href}
    >
      {children}
    </a>
  );
}

export function AdminCashFlowDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onCopyReference,
  selectedMovement,
}: AdminCashFlowDetailPanelProps) {
  if (!selectedMovement) {
    return (
      <aside className="flex min-h-0 flex-col rounded-[20px] border border-dashed border-[var(--ui-color-border)] bg-white p-4 text-sm text-slate-600">
        <h3 className="text-base font-semibold text-slate-950">Sin movimiento seleccionado</h3>
        <p className="mt-2">
          Selecciona un movimiento para revisar origen, impacto financiero y documentos
          relacionados.
        </p>
      </aside>
    );
  }

  if (isLoading) {
    return (
      <aside className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-4 text-sm text-slate-600">
        Cargando detalle del movimiento.
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

  if (!detail) {
    return (
      <aside className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-4 text-sm text-slate-600">
        No se cargo informacion de detalle.
      </aside>
    );
  }

  return (
    <aside className="flex min-h-0 min-w-0 flex-col gap-3 overflow-auto rounded-[20px] border border-[var(--ui-color-border)] bg-white p-4">
      <header className="min-w-0 border-b border-[var(--ui-color-border)] pb-3">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
          Detalle de movimiento
        </p>
        <div className="mt-1 flex min-w-0 items-center justify-between gap-3">
          <h3 className="truncate text-lg font-semibold text-slate-950">
            {detail.overview.sourceReference}
          </h3>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
            type="button"
            onClick={() => onCopyReference(detail.overview.sourceReference)}
          >
            Copiar
          </button>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          {detail.overview.branchName} - {detail.overview.workstationName}
        </p>
      </header>

      <section>
        <h4 className="text-sm font-semibold text-slate-950">Resumen</h4>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          <Field label="Fecha / hora" value={formatDate(detail.overview.occurredAt)} />
          <Field label="Direccion" value={detail.overview.direction} />
          <Field label="Monto" value={formatMoney(detail.overview.amount)} />
          <Field label="Metodo" value={detail.overview.paymentMethod} />
          <Field label="Categoria" value={detail.overview.category ?? "N/A"} />
          <Field label="Operador" value={detail.overview.operatorName} />
        </div>
      </section>

      <section>
        <h4 className="text-sm font-semibold text-slate-950">Documento origen</h4>
        <div className="mt-2 grid gap-2">
          <Field label="Origen" value={detail.sourceDocumentContext.sourceType} />
          <Field label="Folio" value={detail.sourceDocumentContext.sourceReference} />
          <Field label="Estado" value={detail.sourceDocumentContext.sourceStatus} />
          <Field label="Concepto" value={detail.sourceDocumentContext.concept} />
          <Field label="Ticket original" value={detail.sourceDocumentContext.originalTicketFolio} />
          <Field label="Corte asociado" value={detail.sourceDocumentContext.cashCutFolio} />
        </div>
        {detail.sourceDocumentContext.note ? (
          <p className="mt-2 rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-600">
            {detail.sourceDocumentContext.note}
          </p>
        ) : null}
        <div className="mt-2 flex flex-wrap gap-2">
          <ActionLink href={detail.sourceDocumentContext.sourceRouteHint}>Abrir origen</ActionLink>
          <ActionLink href={detail.sourceDocumentContext.cashCutRouteHint}>Abrir corte</ActionLink>
        </div>
      </section>

      <section>
        <h4 className="text-sm font-semibold text-slate-950">Clasificacion financiera</h4>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          <Field
            label="Impacto efectivo"
            value={formatMoney(detail.financialClassification.cashImpact)}
          />
          <Field
            label="Impacto tarjeta"
            value={formatMoney(detail.financialClassification.cardImpact)}
          />
          <Field
            label="Efecto neto"
            value={formatMoney(detail.financialClassification.netEffect)}
          />
          <Field
            label="Afecta caja"
            value={detail.financialClassification.affectsCashDrawer ? "Si" : "No"}
          />
        </div>
        {detail.financialClassification.note ? (
          <p className="mt-2 rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-600">
            {detail.financialClassification.note}
          </p>
        ) : null}
      </section>

      <section>
        <h4 className="text-sm font-semibold text-slate-950">Conciliacion</h4>
        <div className="mt-2 grid gap-2">
          <Field label="Estado" value={detail.reconciliation.status} />
          <Field label="Folio" value={detail.reconciliation.reconciliationFolio} />
          <Field
            label="Monto pendiente"
            value={formatMoney(detail.reconciliation.unresolvedAmount)}
          />
          <Field label="Motivo" value={detail.reconciliation.reasonLabel} />
        </div>
        <p className="mt-2 rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-600">
          {detail.reconciliation.message}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <ActionLink href={detail.reconciliation.routeHint}>Abrir conciliacion</ActionLink>
        </div>
      </section>

      <section>
        <h4 className="text-sm font-semibold text-slate-950">Documentos relacionados</h4>
        <div className="mt-2 grid gap-2">
          {detail.relatedDocuments.length > 0 ? (
            detail.relatedDocuments.map((document) => (
              <a
                className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm transition hover:border-[var(--ui-color-info)]"
                href={document.routeHint ?? undefined}
                key={`${document.documentType}-${document.id}`}
              >
                <span className="block font-semibold text-slate-950">{document.folio}</span>
                <span className="block text-xs text-slate-500">
                  {document.documentType} - {document.status}
                  {document.amount ? ` - ${formatMoney(document.amount)}` : ""}
                </span>
              </a>
            ))
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este movimiento no tiene documentos relacionados.
            </p>
          )}
        </div>
      </section>

      <section>
        <h4 className="text-sm font-semibold text-slate-950">Acciones disponibles</h4>
        <div className="mt-2 flex flex-wrap gap-2">
          {detail.availableActions.canOpenSource ? (
            <ActionLink href={detail.sourceDocumentContext.sourceRouteHint}>
              Abrir origen
            </ActionLink>
          ) : null}
          {detail.availableActions.canOpenCashCut ? (
            <ActionLink href={detail.sourceDocumentContext.cashCutRouteHint}>
              Abrir corte
            </ActionLink>
          ) : null}
          {detail.availableActions.canOpenReconciliation ? (
            <ActionLink href={detail.reconciliation.routeHint}>Abrir conciliacion</ActionLink>
          ) : null}
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-40"
            disabled={!detail.availableActions.canExport}
            type="button"
          >
            Exportar
          </button>
        </div>
        {detail.availableActions.note ? (
          <p className="mt-2 rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-600">
            {detail.availableActions.note}
          </p>
        ) : null}
      </section>
    </aside>
  );
}
