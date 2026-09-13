import { AdminActionButton } from "../../components/AdminActionButton";
import type { ReactNode } from "react";

import type {
  AdminPurchaseDetail,
  AdminPurchaseListItem,
  AdminPurchaseStatus,
  AdminPurchaseType,
  AdminPurchaseWarning,
} from "../types";

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin registro";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatStatus(status: AdminPurchaseStatus): string {
  const labels: Record<AdminPurchaseStatus, string> = {
    CANCELLED: "Cancelada",
    DRAFT: "Borrador",
    ORDERED: "Pendiente de recepcion",
    PARTIALLY_RECEIVED: "Recibida parcialmente",
    RECEIVED: "Recibida",
  };
  return labels[status];
}

function formatType(type: AdminPurchaseType): string {
  return type === "DIRECT_ENTRY" ? "Entrada directa" : "Compra";
}

function formatMovementType(value: string): string {
  const labels: Record<string, string> = {
    PURCHASE_RECEIPT: "Recepcion de compra",
  };
  return labels[value] ?? value;
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="grid min-w-0 grid-cols-[7.75rem_minmax(0,1fr)] gap-2 text-xs">
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

function WarningItem({ warning }: { warning: AdminPurchaseWarning }) {
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

interface AdminPurchaseDetailPanelProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  onCancel: (purchase: AdminPurchaseDetail) => void;
  onConfirm: (purchase: AdminPurchaseDetail) => void;
  onOpenBranch: (branchId: string) => void;
  onOpenProduct: (productId: string) => void;
  onOpenSupplier: (supplierId: string) => void;
  onReceive: (purchase: AdminPurchaseDetail) => void;
  purchaseDetail?: AdminPurchaseDetail | null;
  purchasePreview?: AdminPurchaseListItem | null;
}

export function AdminPurchaseDetailPanel({
  errorMessage,
  isLoading = false,
  onCancel,
  onConfirm,
  onOpenBranch,
  onOpenProduct,
  onOpenSupplier,
  onReceive,
  purchaseDetail,
  purchasePreview,
}: AdminPurchaseDetailPanelProps) {
  if (!purchasePreview && !purchaseDetail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-3 py-2.5">
          <h3 className="truncate text-base font-semibold text-slate-950">Detalle de compra</h3>
        </div>
        <div className="flex min-h-0 flex-1 items-center p-3">
          <div className="rounded-[18px] border border-dashed border-[var(--ui-color-border)] bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            <p className="font-semibold text-slate-950">Sin compra seleccionada</p>
            <p>
              Selecciona una compra para revisar proveedor, productos, recepcion e impacto en
              inventario.
            </p>
          </div>
        </div>
      </aside>
    );
  }

  const folio = purchaseDetail?.overview.folio ?? purchasePreview?.folio ?? "";
  const status = purchaseDetail?.overview.status ?? purchasePreview?.status ?? "DRAFT";
  const type = purchaseDetail?.overview.documentType ?? purchasePreview?.documentType ?? "PURCHASE";
  const supplierName =
    purchaseDetail?.supplierContext.supplierName ?? purchasePreview?.supplierName ?? "";
  const branchName =
    purchaseDetail?.receivingBranch.branchName ?? purchasePreview?.branchName ?? "";

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-start justify-between gap-2 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate font-mono text-base font-semibold text-slate-950" title={folio}>
            {folio}
          </h3>
          <p className="truncate text-xs text-slate-500" title={`${supplierName} - ${branchName}`}>
            {supplierName} - {branchName}
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-600">
          {formatStatus(status)}
        </span>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2.5">
        {isLoading ? (
          <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 p-3 text-sm text-slate-600">
            Cargando detalle de compra.
          </div>
        ) : null}
        {errorMessage ? (
          <div className="rounded-[18px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-3 text-sm text-[var(--ui-color-danger)]">
            {errorMessage}
          </div>
        ) : null}

        <Section title="Resumen">
          <div className="grid gap-1.5">
            <InfoRow label="Tipo" value={formatType(type)} />
            <InfoRow label="Estado" value={formatStatus(status)} />
            <InfoRow
              label="Documento"
              value={purchaseDetail?.overview.externalDocumentNumber ?? "Sin externo"}
            />
            <InfoRow
              label="Fecha"
              value={formatDate(
                purchaseDetail?.overview.documentDate ?? purchasePreview?.documentDate,
              )}
            />
            <InfoRow
              label="Monto"
              value={purchaseDetail?.overview.totalAmount ?? purchasePreview?.totalAmount}
            />
            <InfoRow
              label="Operador"
              value={purchaseDetail?.overview.createdByUserName ?? purchasePreview?.operatorName}
            />
          </div>
        </Section>

        {purchaseDetail ? (
          <>
            <Section title="Proveedor">
              <div className="grid gap-1.5">
                <InfoRow label="Nombre" value={purchaseDetail.supplierContext.supplierName} />
                <InfoRow label="Comercial" value={purchaseDetail.supplierContext.commercialName} />
                <InfoRow label="Estado" value={purchaseDetail.supplierContext.status} />
                <InfoRow label="Contacto" value={purchaseDetail.supplierContext.primaryContact} />
                <InfoRow
                  label="Terminos"
                  value={purchaseDetail.supplierContext.paymentTermsSummary}
                />
                <InfoRow
                  label="Lead time"
                  value={`${purchaseDetail.supplierContext.leadTimeDays} dias`}
                />
              </div>
            </Section>

            <Section title="Sucursal receptora">
              <div className="grid gap-1.5">
                <InfoRow label="Sucursal" value={purchaseDetail.receivingBranch.branchName} />
                <InfoRow label="Codigo" value={purchaseDetail.receivingBranch.branchCode} />
                <InfoRow
                  label="Estado"
                  value={purchaseDetail.receivingBranch.branchIsActive ? "Activa" : "Inactiva"}
                />
                <InfoRow label="Zona horaria" value={purchaseDetail.receivingBranch.timezone} />
              </div>
            </Section>

            <Section title="Lineas de compra / recepcion">
              <div className="grid gap-1.5">
                {purchaseDetail.lines.map((line) => (
                  <div
                    className="grid min-w-0 gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs"
                    key={line.purchaseLineId}
                  >
                    <div className="flex min-w-0 items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p
                          className="truncate font-semibold text-slate-950"
                          title={line.productName}
                        >
                          {line.productName}
                        </p>
                        <p className="truncate font-mono text-slate-500" title={line.productCode}>
                          {line.productCode}
                        </p>
                      </div>
                      <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-0.5 font-semibold text-slate-600">
                        {line.lineStatus}
                      </span>
                    </div>
                    <div className="grid min-w-0 grid-cols-2 gap-1.5 md:grid-cols-4">
                      <InfoRow
                        label="Ordenado"
                        value={`${line.orderedQuantity} ${line.unitOfMeasure}`}
                      />
                      <InfoRow label="Recibido" value={line.receivedQuantity} />
                      <InfoRow label="Pendiente" value={line.pendingQuantity} />
                      <InfoRow label="Costo" value={line.unitCost} />
                    </div>
                    {line.discrepancyReason ? (
                      <p
                        className="truncate text-[var(--ui-color-danger)]"
                        title={line.discrepancyReason}
                      >
                        {line.discrepancyReason}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            </Section>

            <Section title="Recepcion / discrepancias">
              <div className="grid gap-1.5">
                <InfoRow label="Esperado" value={purchaseDetail.receipt.expectedQuantity} />
                <InfoRow label="Recibido" value={purchaseDetail.receipt.receivedQuantity} />
                <InfoRow label="Pendiente" value={purchaseDetail.receipt.pendingQuantity} />
                <InfoRow
                  label="Discrepancia"
                  value={
                    purchaseDetail.receipt.hasDiscrepancy ? "Con diferencias" : "Sin discrepancias"
                  }
                />
              </div>
            </Section>

            <Section title="Costo / valuacion">
              <div className="grid gap-1.5">
                <InfoRow label="Subtotal" value={purchaseDetail.costSummary.subtotal} />
                <InfoRow label="Recibido" value={purchaseDetail.costSummary.receivedTotal} />
                <InfoRow
                  label="Impuestos"
                  value={purchaseDetail.costSummary.taxes ?? "No conectado"}
                />
                <InfoRow
                  label="Total"
                  value={`${purchaseDetail.costSummary.total} ${purchaseDetail.costSummary.currency}`}
                />
              </div>
            </Section>

            <Section title="Impacto en inventario">
              {purchaseDetail.inventoryImpact.movements.length > 0 ? (
                <ul className="grid gap-1.5">
                  {purchaseDetail.inventoryImpact.movements.map((movement) => (
                    <li
                      className="grid min-w-0 gap-1 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs"
                      key={movement.id}
                    >
                      <div className="flex min-w-0 justify-between gap-2">
                        <span className="truncate font-semibold text-slate-950">
                          {formatMovementType(movement.movementType)}
                        </span>
                        <span className="shrink-0 font-semibold text-slate-950">
                          {movement.quantity} {movement.unitOfMeasure}
                        </span>
                      </div>
                      <p className="truncate text-slate-500" title={movement.locationCode}>
                        {movement.direction} - {movement.locationCode} - saldo{" "}
                        {movement.balanceAfter ?? "N/D"}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
                  {purchaseDetail.inventoryImpact.notes ??
                    "No hay movimientos de inventario vinculados."}
                </p>
              )}
            </Section>

            <Section title="Documentos relacionados">
              {purchaseDetail.relatedDocuments.length > 0 ? (
                <ul className="grid gap-1.5 text-xs">
                  {purchaseDetail.relatedDocuments.map((document) => (
                    <li
                      className="flex min-w-0 justify-between gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2"
                      key={`${document.documentType}-${document.documentId}`}
                    >
                      <span className="truncate font-semibold text-slate-950">
                        {document.documentType}
                      </span>
                      <span className="truncate text-slate-500">{document.folio}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs text-slate-600">
                  Esta compra no tiene documentos relacionados.
                </p>
              )}
            </Section>

            <Section title="Advertencias">
              {purchaseDetail.warnings.length > 0 ? (
                <ul className="grid gap-1.5">
                  {purchaseDetail.warnings.map((warning) => (
                    <WarningItem key={warning.code} warning={warning} />
                  ))}
                </ul>
              ) : (
                <p className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs text-slate-600">
                  Esta entrada no tiene discrepancias registradas.
                </p>
              )}
            </Section>
          </>
        ) : null}
      </div>

      {purchaseDetail ? (
        <div className="flex shrink-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] px-3 py-2 text-xs">
          {purchaseDetail.availableActions.canConfirm ? (
            <AdminActionButton
              capability="purchases.confirm"
              branchIds={[purchaseDetail.receivingBranch.branchId]}
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              type="button"
              onClick={() => onConfirm(purchaseDetail)}
            >
              Confirmar compra
            </AdminActionButton>
          ) : null}
          {purchaseDetail.availableActions.canReceive ? (
            <AdminActionButton
              capability="purchases.receive"
              branchIds={[purchaseDetail.receivingBranch.branchId]}
              className="rounded-full bg-[var(--ui-color-info)] px-3 py-1 font-semibold text-white transition hover:brightness-95 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              type="button"
              onClick={() => onReceive(purchaseDetail)}
            >
              Recibir
            </AdminActionButton>
          ) : null}
          {purchaseDetail.availableActions.canCancel ? (
            <AdminActionButton
              capability="purchases.cancel"
              branchIds={[purchaseDetail.receivingBranch.branchId]}
              className="rounded-full border border-rose-200 bg-white px-3 py-1 font-semibold text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              type="button"
              onClick={() => onCancel(purchaseDetail)}
            >
              Cancelar
            </AdminActionButton>
          ) : null}
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={() => onOpenSupplier(purchaseDetail.supplierContext.supplierId)}
          >
            Abrir proveedor
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={() => onOpenBranch(purchaseDetail.receivingBranch.branchId)}
          >
            Abrir sucursal
          </button>
          {purchaseDetail.lines[0] ? (
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              type="button"
              onClick={() => onOpenProduct(purchaseDetail.lines[0].productId)}
            >
              Abrir producto
            </button>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}
