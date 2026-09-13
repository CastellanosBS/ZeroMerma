import { AdminActionButton } from "../../components/AdminActionButton";
import type { ReactNode } from "react";

import type {
  AdminTransferDetail,
  AdminTransferInventoryMovement,
  AdminTransferListItem,
  AdminTransferStatus,
  AdminTransferWarning,
} from "../types";

function formatStatus(status: AdminTransferStatus): string {
  const labels: Record<AdminTransferStatus, string> = {
    CANCELLED: "Cancelada",
    DRAFT: "Borrador",
    IN_TRANSIT: "En transito",
    RECEIVED: "Recibida",
    RECEIVED_WITH_VARIANCE: "Recibida con diferencia",
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

function WarningItem({ warning }: { warning: AdminTransferWarning }) {
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

function MovementRow({ movement }: { movement: AdminTransferInventoryMovement }) {
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
        <span
          className={`shrink-0 rounded-full border px-2 py-0.5 font-semibold ${directionClass}`}
        >
          {movement.direction}
        </span>
      </div>
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_5rem] gap-2">
        <span
          className="truncate text-slate-500"
          title={`${movement.locationCode} - ${movement.sourceDocumentType ?? ""}`}
        >
          {movement.locationCode}
        </span>
        <span
          className="truncate text-right font-semibold text-slate-900"
          title={movement.quantity}
        >
          {movement.quantity}
        </span>
      </div>
      <p className="truncate text-slate-500" title={movement.sourceDocumentId ?? "Sin documento"}>
        {movement.sourceDocumentType ?? "Sin documento"}
      </p>
    </li>
  );
}

interface AdminTransferDetailPanelProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  isSubmitting?: boolean;
  onCancel: (detail: AdminTransferDetail) => void;
  onDispatch: (detail: AdminTransferDetail) => void;
  onEdit: (detail: AdminTransferDetail) => void;
  onOpenBranch: (branchId: string) => void;
  onOpenInventory: (productId: string, branchId: string) => void;
  onReceive: (detail: AdminTransferDetail) => void;
  transferDetail?: AdminTransferDetail | null;
  transferPreview?: AdminTransferListItem | null;
}

export function AdminTransferDetailPanel({
  errorMessage,
  isLoading = false,
  isSubmitting = false,
  onCancel,
  onDispatch,
  onEdit,
  onOpenBranch,
  onOpenInventory,
  onReceive,
  transferDetail,
  transferPreview,
}: AdminTransferDetailPanelProps) {
  if (!transferPreview && !transferDetail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-3 py-2.5">
          <h3 className="truncate text-base font-semibold text-slate-950">
            Detalle de transferencia
          </h3>
        </div>
        <div className="flex min-h-0 flex-1 items-center p-3">
          <div className="rounded-[18px] border border-dashed border-[var(--ui-color-border)] bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            <p className="font-semibold text-slate-950">Sin transferencia seleccionada</p>
            <p>
              Selecciona una transferencia para revisar origen, destino, lineas, recepcion e impacto
              en inventario.
            </p>
          </div>
        </div>
      </aside>
    );
  }

  const folio = transferDetail?.overview.folio ?? transferPreview?.folio ?? "";
  const status = transferDetail?.overview.status ?? transferPreview?.status ?? "DRAFT";
  const warnings = transferDetail?.warnings ?? transferPreview?.warnings ?? [];
  const originBranchId = transferDetail?.origin.branchId ?? transferPreview?.originBranchId ?? "";
  const destinationBranchId =
    transferDetail?.destination.branchId ?? transferPreview?.destinationBranchId ?? "";

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
        {(transferDetail?.overview.hasDiscrepancy ?? transferPreview?.hasDiscrepancy) ? (
          <span className="shrink-0 rounded-full border border-rose-200 bg-[var(--ui-color-danger-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--ui-color-danger)]">
            Discrepancia
          </span>
        ) : (
          <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-600">
            Sin diferencia
          </span>
        )}
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2.5">
        {isLoading ? (
          <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 p-3 text-sm text-slate-600">
            Cargando detalle de transferencia.
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
            <InfoRow
              label="Creada"
              value={formatDate(transferDetail?.overview.createdAt ?? transferPreview?.createdAt)}
            />
            <InfoRow
              label="Enviada"
              value={formatDate(
                transferDetail?.overview.dispatchedAt ?? transferPreview?.dispatchedAt,
              )}
            />
            <InfoRow
              label="Recibida"
              value={formatDate(transferDetail?.overview.receivedAt ?? transferPreview?.receivedAt)}
            />
            <InfoRow
              label="Lineas"
              value={transferDetail?.overview.lineCount ?? transferPreview?.lineCount}
            />
            <InfoRow
              label="Unidades"
              value={`${transferDetail?.overview.sentUnitCount ?? transferPreview?.sentUnitCount ?? "0"} enviadas`}
            />
          </div>
        </Section>

        <Section title="Origen / destino">
          <div className="grid gap-1.5">
            <InfoRow
              label="Origen"
              value={
                transferDetail
                  ? `${transferDetail.origin.branchName} (${transferDetail.origin.branchCode})`
                  : `${transferPreview?.originBranchName} (${transferPreview?.originBranchCode})`
              }
            />
            <InfoRow
              label="Destino"
              value={
                transferDetail
                  ? `${transferDetail.destination.branchName} (${transferDetail.destination.branchCode})`
                  : `${transferPreview?.destinationBranchName} (${transferPreview?.destinationBranchCode})`
              }
            />
            {transferDetail ? (
              <>
                <InfoRow
                  label="Origen activo"
                  value={transferDetail.origin.branchIsActive ? "Si" : "No"}
                />
                <InfoRow
                  label="Destino activo"
                  value={transferDetail.destination.branchIsActive ? "Si" : "No"}
                />
                <InfoRow label="Zona origen" value={transferDetail.origin.timezone} />
              </>
            ) : null}
          </div>
        </Section>

        {transferDetail ? (
          <>
            <Section title="Lineas">
              {transferDetail.lines.length > 0 ? (
                <ul className="grid gap-1.5">
                  {transferDetail.lines.map((line) => (
                    <li
                      className="grid min-w-0 gap-1.5 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs"
                      key={line.shipmentLineId}
                    >
                      <div className="flex min-w-0 items-center justify-between gap-2">
                        <span
                          className="truncate font-semibold text-slate-950"
                          title={line.productName}
                        >
                          {line.productName}
                        </span>
                        <span className="shrink-0 font-mono text-slate-500">
                          {line.productCode}
                        </span>
                      </div>
                      <div className="grid min-w-0 grid-cols-3 gap-2 text-slate-600">
                        <span className="truncate" title={`Solicitado ${line.requestedQuantity}`}>
                          Sol. {line.requestedQuantity}
                        </span>
                        <span className="truncate" title={`Enviado ${line.sentQuantity}`}>
                          Env. {line.sentQuantity}
                        </span>
                        <span
                          className="truncate"
                          title={`Recibido ${line.receivedQuantity ?? "Pendiente"}`}
                        >
                          Rec. {line.receivedQuantity ?? "Pend."}
                        </span>
                      </div>
                      {line.difference && line.difference !== "0.000" ? (
                        <p className="rounded-[12px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-2 py-1 font-semibold text-[var(--ui-color-danger)]">
                          Diferencia {line.difference}.{" "}
                          {line.varianceReason ?? "Sin razon registrada"}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm leading-6 text-slate-600">
                  Esta transferencia no tiene lineas registradas.
                </p>
              )}
            </Section>

            <Section title="Recepcion / discrepancias">
              <div className="grid gap-1.5">
                <InfoRow label="Estado" value={transferDetail.receipt.state} />
                <InfoRow label="Esperado" value={transferDetail.receipt.expectedTotalQuantity} />
                <InfoRow
                  label="Recibido"
                  value={transferDetail.receipt.receivedTotalQuantity ?? "Pendiente"}
                />
                <InfoRow
                  label="Diferencia"
                  value={transferDetail.receipt.difference ?? "Pendiente"}
                />
              </div>
              {!transferDetail.receipt.hasDiscrepancy ? (
                <p className="mt-2 rounded-[14px] border border-emerald-200 bg-[var(--ui-color-success-soft)] px-3 py-2 text-xs font-semibold text-[var(--ui-color-success)]">
                  Esta transferencia no tiene discrepancias registradas.
                </p>
              ) : null}
            </Section>

            <Section title="Impacto en inventario">
              {transferDetail.inventoryImpact.integrationAvailable ? (
                transferDetail.inventoryImpact.movements.length > 0 ? (
                  <ul className="grid gap-1.5">
                    {transferDetail.inventoryImpact.movements.map((movement) => (
                      <MovementRow key={movement.id} movement={movement} />
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm leading-6 text-slate-600">
                    El backend integra inventario; aun no hay movimientos para este documento.
                  </p>
                )
              ) : (
                <p className="text-sm leading-6 text-slate-600">
                  {transferDetail.inventoryImpact.notes ?? "Contrato de movimientos pendiente."}
                </p>
              )}
            </Section>

            <Section title="Documentos relacionados">
              {transferDetail.relatedDocuments.length > 0 ? (
                <ul className="grid gap-1.5">
                  {transferDetail.relatedDocuments.map((document) => (
                    <li
                      className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs"
                      key={`${document.documentType}-${document.documentId}`}
                    >
                      <span
                        className="block truncate font-semibold text-slate-950"
                        title={document.folio}
                      >
                        {document.folio}
                      </span>
                      <span
                        className="block truncate text-slate-500"
                        title={`${document.documentType} - ${document.status}`}
                      >
                        {document.documentType} - {document.status}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm leading-6 text-slate-600">
                  Esta transferencia no tiene documentos relacionados.
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
              No hay advertencias para esta transferencia.
            </p>
          )}
        </Section>
      </div>

      <div className="flex shrink-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] p-3 text-xs">
        {transferDetail?.availableActions.canDispatch ? (
          <AdminActionButton
            capability="transfers.execute"
            branchIds={[originBranchId, destinationBranchId]}
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={isSubmitting}
            type="button"
            onClick={() => onDispatch(transferDetail)}
          >
            Enviar transferencia
          </AdminActionButton>
        ) : null}
        {transferDetail?.availableActions.canEdit ? (
          <AdminActionButton
            capability="transfers.manage"
            branchIds={[originBranchId, destinationBranchId]}
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={isSubmitting}
            type="button"
            onClick={() => onEdit(transferDetail)}
          >
            Editar
          </AdminActionButton>
        ) : null}
        {transferDetail?.availableActions.canReceive ? (
          <AdminActionButton
            capability="transfers.execute"
            branchIds={[originBranchId, destinationBranchId]}
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={isSubmitting}
            type="button"
            onClick={() => onReceive(transferDetail)}
          >
            Recibir
          </AdminActionButton>
        ) : null}
        {transferDetail?.availableActions.canCancel ? (
          <AdminActionButton
            capability="transfers.cancel"
            branchIds={[originBranchId, destinationBranchId]}
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={isSubmitting}
            type="button"
            onClick={() => onCancel(transferDetail)}
          >
            Cancelar
          </AdminActionButton>
        ) : null}
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onOpenBranch(originBranchId)}
        >
          Abrir origen
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onOpenBranch(destinationBranchId)}
        >
          Abrir destino
        </button>
        {transferDetail?.lines[0] ? (
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={() => onOpenInventory(transferDetail.lines[0].productId, originBranchId)}
          >
            Ver inventario
          </button>
        ) : null}
      </div>
    </aside>
  );
}
