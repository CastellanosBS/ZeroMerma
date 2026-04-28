import type { ReactNode } from "react";

import type { AuditSummaryView } from "../lib/api-contracts";
import type { PosBlockerMessage, PosConfirmationCopy } from "../lib/pos-messages";
import { useStatusMessageStore } from "../features/status-messages/store";
import { cn } from "../lib/utils";
import type { PosButtonVariant, PosStatusBadgeVariant } from "../features/pos-theme/theme";
import { formatRecordReference } from "../lib/formatters";
import {
  CopyFolioAction,
  DocumentActionsMenu,
  ExportPdfAction,
  PrintAction,
} from "./document-actions";
import {
  copyDocumentReferenceToClipboard,
  getDocumentActionAvailability,
  type PrintableDocumentKind,
} from "../lib/document-actions";
import { PosBlockerPanel, PosConfirmationDialog } from "./pos-feedback";
import { PosAuditSummary } from "./pos-audit-summary";
import { PosButton, PosCard, PosPanel, PosSectionTitle, PosStatusBadge } from "./pos-foundations";
import { PosSummaryPanel } from "./pos-module-layout";
import { type PosRecordAction, PosRecordList } from "./pos-records";
import {
  CheckCircleIcon,
  ClockIcon,
  ClipboardIcon,
  OperatorIcon,
  PrinterIcon,
  RotateCcwIcon,
  StationIcon,
  StoreIcon,
} from "./pos-icons";

export type OperationDocumentKind =
  | "branchReceipt"
  | "branchShipment"
  | "correction"
  | "counterTransfer"
  | "return"
  | "waste";

type OperationMetricTone = "danger" | "default" | "financial" | "success" | "warning";

export interface OperationDocumentAction {
  availabilityNote?: string;
  disabled?: boolean;
  kind?: "copyFolio" | "custom" | "exportPdf" | "print";
  key: string;
  label: string;
  leadingIcon?: ReactNode;
  onSelect: () => void;
  placement?: "inline" | "menu";
  referenceValue?: string | null;
  variant?: PosButtonVariant;
}

export interface OperationDocumentContext {
  branchName?: string | null;
  userName?: string | null;
  workstationName?: string | null;
}

export interface OperationDocumentMetric {
  key: string;
  label: string;
  tone?: OperationMetricTone;
  value: string;
}

export interface OperationDocumentTimestamps {
  committedAtLabel?: string;
  committedAtValue?: string | null;
  createdAtLabel?: string;
  createdAtValue?: string | null;
}

export interface OperationLineSummaryItem {
  amountText?: string;
  key: string;
  quantityText?: string;
  secondaryText?: string;
  statusLabel?: string;
  statusTone?: PosStatusBadgeVariant;
  trailingNote?: string;
  title: string;
}

export interface OperationHistoryRecord {
  documentTypeLabel?: string;
  folio: string;
  id: string;
  locationLabel?: string;
  metrics?: OperationDocumentMetric[];
  primaryTimestampLabel?: string;
  primaryTimestampValue?: string;
  secondaryTimestampLabel?: string;
  secondaryTimestampValue?: string;
  statusLabel?: string;
  statusTone?: PosStatusBadgeVariant;
  subtitle?: string;
  title: string;
  userLabel?: string;
}

function getOperationDocumentKindLabel(kind: OperationDocumentKind): string {
  switch (kind) {
    case "counterTransfer":
      return "Pasar a mostrador";
    case "branchShipment":
      return "Envio a sucursal";
    case "branchReceipt":
      return "Recepcion";
    case "waste":
      return "Merma";
    case "correction":
      return "Correccion";
    case "return":
      return "Devolucion";
    default:
      return "Documento";
  }
}

function getOperationDocumentResultTitle(kind: OperationDocumentKind): string {
  switch (kind) {
    case "counterTransfer":
      return "Traspaso registrado";
    case "branchShipment":
      return "Envio registrado";
    case "branchReceipt":
      return "Recepcion confirmada";
    case "waste":
      return "Merma registrada";
    case "correction":
      return "Correccion registrada";
    case "return":
      return "Devolucion registrada";
    default:
      return "Documento registrado";
  }
}

function getMetricToneClasses(tone: OperationMetricTone): string {
  switch (tone) {
    case "financial":
      return "border-[rgba(187,122,22,0.18)] bg-[var(--ui-color-warning-soft)]";
    case "success":
      return "border-[rgba(18,122,90,0.18)] bg-[var(--ui-color-success-soft)]";
    case "warning":
      return "border-[rgba(187,122,22,0.18)] bg-[var(--ui-color-warning-soft)]";
    case "danger":
      return "border-[rgba(180,35,24,0.18)] bg-[var(--ui-color-danger-soft)]";
    default:
      return "border-[var(--pos-shell-border)] bg-white";
  }
}

function getActionVariant(action: OperationDocumentAction, index: number): PosButtonVariant {
  if (action.variant) {
    return action.variant;
  }

  return index === 0 ? "primary" : "neutral";
}

function getActionIcon(action: OperationDocumentAction): ReactNode {
  if (action.leadingIcon) {
    return action.leadingIcon;
  }

  if (action.kind === "print") {
    return <PrinterIcon className="h-4 w-4" />;
  }

  if (action.kind === "copyFolio") {
    return <ClipboardIcon className="h-4 w-4" />;
  }

  const normalized = action.label.toLowerCase();

  if (normalized.includes("imprimir")) {
    return <PrinterIcon className="h-4 w-4" />;
  }

  if (normalized.includes("historial")) {
    return <RotateCcwIcon className="h-4 w-4" />;
  }

  if (normalized.includes("nuevo")) {
    return <ClipboardIcon className="h-4 w-4" />;
  }

  return null;
}

function mapDocumentKindToPrintableKind(kind: OperationDocumentKind): PrintableDocumentKind {
  switch (kind) {
    case "counterTransfer":
      return "counterTransferReceipt";
    case "branchShipment":
      return "branchShipmentDocument";
    case "branchReceipt":
      return "branchReceiptDocument";
    case "waste":
      return "wasteDocument";
    case "correction":
      return "correctionDocument";
    case "return":
      return "returnReceipt";
    default:
      return "counterTransferReceipt";
  }
}

function hasActionKind(actions: OperationDocumentAction[], kind: OperationDocumentAction["kind"]): boolean {
  return actions.some((action) => action.kind === kind);
}

function renderInlineAction(action: OperationDocumentAction, index: number) {
  if (action.kind === "copyFolio") {
    return (
      <CopyFolioAction
        disabled={action.disabled}
        key={action.key}
        label={action.label}
        referenceValue={action.referenceValue}
        title={action.availabilityNote}
        variant={getActionVariant(action, index)}
      />
    );
  }

  if (action.kind === "print") {
    return (
      <PrintAction
        availabilityNote={action.availabilityNote}
        disabled={action.disabled}
        key={action.key}
        label={action.label}
        onPrint={action.onSelect}
        title={action.availabilityNote}
        variant={getActionVariant(action, index)}
      />
    );
  }

  if (action.kind === "exportPdf") {
    return (
      <ExportPdfAction
        availabilityNote={action.availabilityNote}
        disabled={action.disabled}
        key={action.key}
        label={action.label}
        onExport={action.onSelect}
        title={action.availabilityNote}
        variant={getActionVariant(action, index)}
      />
    );
  }

  return (
    <PosButton
      disabled={action.disabled}
      key={action.key}
      leadingIcon={getActionIcon(action)}
      onClick={action.onSelect}
      variant={getActionVariant(action, index)}
    >
      {action.label}
    </PosButton>
  );
}

function OperationActionRow({
  actions,
  className,
}: {
  actions: OperationDocumentAction[];
  className?: string;
}) {
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);

  if (actions.length === 0) {
    return null;
  }

  const inlineActions = actions.filter(
    (action) =>
      action.placement !== "menu" &&
      action.kind !== "copyFolio" &&
      action.kind !== "exportPdf",
  );
  const overflowActions = actions.filter(
    (action) =>
      action.placement === "menu" ||
      action.kind === "copyFolio" ||
      action.kind === "exportPdf",
  );

  if (inlineActions.length === 0 && overflowActions.length === 1) {
    return (
      <div className={cn("flex flex-wrap items-center gap-2", className)}>
        {renderInlineAction(overflowActions[0], 0)}
      </div>
    );
  }

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {inlineActions.map((action, index) => renderInlineAction(action, index))}
      {overflowActions.length > 0 ? (
        <DocumentActionsMenu
          actions={overflowActions.map((action) => {
            if (action.kind === "copyFolio") {
              return {
                disabled: action.disabled,
                disabledReason: action.availabilityNote,
                key: action.key,
                label: action.label,
                leadingIcon: getActionIcon(action),
                onSelect: () => {
                  if (!action.referenceValue) {
                    showError("No se pudo copiar el folio.");
                    return;
                  }

                  void copyDocumentReferenceToClipboard(action.referenceValue)
                    .then(() => showSuccess("Folio copiado."))
                    .catch(() => showError("No se pudo copiar el folio."));
                },
              };
            }

            return {
              disabled: action.disabled,
              disabledReason: action.availabilityNote,
              key: action.key,
              label: action.label,
              leadingIcon: getActionIcon(action),
              onSelect: action.onSelect,
            };
          })}
        />
      ) : null}
    </div>
  );
}

function OperationContextGrid({
  context,
  timestamps,
}: {
  context?: OperationDocumentContext;
  timestamps?: OperationDocumentTimestamps;
}) {
  const contextRows = [
    {
      icon: <StoreIcon className="h-4 w-4" />,
      key: "branch",
      label: "Sucursal",
      value: context?.branchName ?? null,
    },
    {
      icon: <StationIcon className="h-4 w-4" />,
      key: "workstation",
      label: "Estacion",
      value: context?.workstationName ?? null,
    },
    {
      icon: <OperatorIcon className="h-4 w-4" />,
      key: "user",
      label: "Operador",
      value: context?.userName ?? null,
    },
    {
      icon: <ClockIcon className="h-4 w-4" />,
      key: "created-at",
      label: timestamps?.createdAtLabel ?? "Creado",
      value: timestamps?.createdAtValue ?? null,
    },
    {
      icon: <CheckCircleIcon className="h-4 w-4" />,
      key: "committed-at",
      label: timestamps?.committedAtLabel ?? "Confirmado",
      value: timestamps?.committedAtValue ?? null,
    },
  ].filter((row) => row.value);

  if (contextRows.length === 0) {
    return null;
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {contextRows.map((row) => (
        <PosCard className="px-3 py-2.5" key={row.key}>
          <div className="flex items-start gap-2">
            <span aria-hidden="true" className="mt-0.5 text-slate-500">
              {row.icon}
            </span>
            <div className="min-w-0">
              <p className="pos-label-text">{row.label}</p>
              <p className="mt-1 truncate text-sm font-semibold text-slate-950" title={row.value ?? undefined}>
                {row.value}
              </p>
            </div>
          </div>
        </PosCard>
      ))}
    </div>
  );
}

function OperationMetricGrid({
  metrics,
}: {
  metrics: OperationDocumentMetric[];
}) {
  if (metrics.length === 0) {
    return null;
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {metrics.map((metric) => (
        <div
          className={cn(
            "rounded-[var(--pos-radius-control)] border px-3 py-2.5",
            getMetricToneClasses(metric.tone ?? "default"),
          )}
          key={metric.key}
        >
          <p className="pos-label-text">{metric.label}</p>
          <p className="mt-1 text-base font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
            {metric.value}
          </p>
        </div>
      ))}
    </div>
  );
}

export function OperationLineSummary({
  className,
  emptyMessage = "Sin lineas registradas.",
  lines,
  title = "Lineas",
}: {
  className?: string;
  emptyMessage?: string;
  lines: OperationLineSummaryItem[];
  title?: string;
}) {
  return (
    <div className={cn("grid gap-2", className)} data-operation-line-summary="true">
      <PosSectionTitle title={title} />
      {lines.length === 0 ? (
        <PosCard className="px-3 py-3">
          <p className="text-sm text-slate-600">{emptyMessage}</p>
        </PosCard>
      ) : (
        <div className="overflow-hidden rounded-[var(--pos-radius-panel)] border border-[var(--pos-shell-border)] bg-white">
          {lines.map((line) => (
            <div
              className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 border-t border-[var(--pos-shell-border)] px-3 py-2.5 first:border-t-0"
              key={line.key}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="truncate text-sm font-semibold text-slate-950" title={line.title}>
                    {line.title}
                  </p>
                  {line.statusLabel ? (
                    <PosStatusBadge status={line.statusTone ?? "draft"}>
                      {line.statusLabel}
                    </PosStatusBadge>
                  ) : null}
                </div>
                {line.secondaryText ? (
                  <p className="mt-1 truncate text-xs text-slate-500" title={line.secondaryText}>
                    {line.secondaryText}
                  </p>
                ) : null}
              </div>

              <div className="flex flex-col items-end gap-1 text-right text-sm">
                {line.quantityText ? (
                  <span className="font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                    {line.quantityText}
                  </span>
                ) : null}
                {line.amountText ? (
                  <span className="text-slate-700 [font-variant-numeric:tabular-nums]">
                    {line.amountText}
                  </span>
                ) : null}
                {line.trailingNote ? (
                  <span className="text-xs text-slate-500">{line.trailingNote}</span>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function OperationConfirmationDialog({
  actionsTitle = "Resumen del documento",
  cancelLabel = "Cancelar",
  confirmLabel = "Confirmar",
  confirmationTone = "warning",
  context,
  detailsContent,
  description,
  isOpen,
  isPending = false,
  kind,
  lines = [],
  metrics = [],
  onCancel,
  onConfirm,
  referenceLabel = "Folio",
  referenceValue,
  timestamps,
  title,
}: {
  actionsTitle?: string;
  cancelLabel?: string;
  confirmLabel?: string;
  confirmationTone?: PosConfirmationCopy["tone"];
  context?: OperationDocumentContext;
  detailsContent?: ReactNode;
  description?: string;
  isOpen: boolean;
  isPending?: boolean;
  kind: OperationDocumentKind;
  lines?: OperationLineSummaryItem[];
  metrics?: OperationDocumentMetric[];
  onCancel: () => void;
  onConfirm: () => void;
  referenceLabel?: string;
  referenceValue?: string | null;
  timestamps?: OperationDocumentTimestamps;
  title?: string;
}) {
  const confirmation: PosConfirmationCopy = {
    cancelLabel,
    confirmLabel,
    description:
      description ??
      `Vas a confirmar ${getOperationDocumentKindLabel(kind).toLowerCase()}. Revisa el resumen antes de continuar.`,
    eyebrow: "Revision final",
    title: title ?? `Confirmar ${getOperationDocumentKindLabel(kind).toLowerCase()}`,
    tone: confirmationTone,
  };

  return (
    <div data-operation-confirmation-dialog="true">
      <PosConfirmationDialog
        confirmation={confirmation}
        details={
          detailsContent ?? (
            <div className="grid gap-3">
              {referenceValue ? (
                <PosCard className="px-3 py-2.5">
                  <p className="pos-label-text">{referenceLabel}</p>
                  <p className="mt-1 text-base font-semibold text-slate-950">
                    {formatRecordReference(referenceValue, "Sin folio")}
                  </p>
                </PosCard>
              ) : null}
              <OperationContextGrid context={context} timestamps={timestamps} />
              <OperationMetricGrid metrics={metrics} />
              <OperationLineSummary
                emptyMessage="Sin lineas para revisar."
                lines={lines}
                title={actionsTitle}
              />
            </div>
          )
        }
        isOpen={isOpen}
        isPending={isPending}
        onCancel={onCancel}
        onConfirm={onConfirm}
      />
    </div>
  );
}

export function OperationDocumentResult({
  actions = [],
  auditSummary,
  className,
  context,
  description,
  kind,
  metrics = [],
  referenceLabel = "Folio",
  referenceValue,
  timeZone,
  timestamps,
  title,
}: {
  actions?: OperationDocumentAction[];
  auditSummary?: AuditSummaryView | null;
  className?: string;
  context?: OperationDocumentContext;
  description?: ReactNode;
  kind: OperationDocumentKind;
  metrics?: OperationDocumentMetric[];
  referenceLabel?: string;
  referenceValue?: string | null;
  timeZone?: string;
  timestamps?: OperationDocumentTimestamps;
  title?: string;
}) {
  const printableKind = mapDocumentKindToPrintableKind(kind);
  const availability = getDocumentActionAvailability(printableKind);
  const shouldAppendCopyAction = referenceValue && !hasActionKind(actions, "copyFolio");
  const shouldAppendExportAction = referenceValue && !hasActionKind(actions, "exportPdf");
  const resolvedActions = referenceValue
    ? [
        ...actions,
        ...(shouldAppendCopyAction
          ? [
              {
                key: `${printableKind}-copy-folio`,
                kind: "copyFolio" as const,
                label: availability.copyFolio.label,
                onSelect: () => undefined,
                placement: "menu" as const,
                referenceValue,
                variant: "neutral" as const,
              },
            ]
          : []),
        ...(shouldAppendExportAction
          ? [
              {
                availabilityNote: availability.exportPdf.unavailableReason,
                disabled: !availability.exportPdf.isAvailable,
                key: `${printableKind}-export-pdf`,
                kind: "exportPdf" as const,
                label: availability.exportPdf.label,
                onSelect: () => undefined,
                placement: "menu" as const,
                variant: "ghost" as const,
              },
            ]
          : []),
      ]
    : actions;

  return (
    <PosPanel
      className={cn("grid gap-4 px-4 py-4", className)}
      data-operation-document-result="true"
      tone="success"
    >
      <PosSectionTitle
        action={<PosStatusBadge icon={<CheckCircleIcon className="h-4 w-4" />} status="success">Operacion lista</PosStatusBadge>}
        description={description}
        eyebrow="Resultado"
        title={title ?? getOperationDocumentResultTitle(kind)}
      />

      {referenceValue ? (
        <PosCard className="px-3 py-2.5">
          <p className="pos-label-text">{referenceLabel}</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">
            {formatRecordReference(referenceValue, "Sin folio")}
          </p>
        </PosCard>
      ) : null}

      <OperationContextGrid context={context} timestamps={timestamps} />
      <OperationMetricGrid metrics={metrics} />
      {auditSummary && timeZone ? (
        <PosAuditSummary auditSummary={auditSummary} timeZone={timeZone} />
      ) : null}
      <OperationActionRow actions={resolvedActions} />
    </PosPanel>
  );
}

function OperationHistoryRecordCard({
  isSelected,
  record,
}: {
  isSelected: boolean;
  record: OperationHistoryRecord;
}) {
  const metadataRows = [
    { key: "type", label: "Tipo", value: record.documentTypeLabel },
    { key: "user", label: "Usuario", value: record.userLabel },
    { key: "location", label: "Sucursal / estacion", value: record.locationLabel },
  ].filter((row): row is { key: string; label: string; value: string } => Boolean(row.value));

  return (
    <div className="grid gap-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-950" title={record.title}>
            {record.title}
          </p>
          <p className="mt-0.5 text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
            {formatRecordReference(record.folio)}
          </p>
        </div>
        {record.statusLabel ? (
          <PosStatusBadge status={record.statusTone ?? "draft"}>
            {record.statusLabel}
          </PosStatusBadge>
        ) : null}
      </div>

      {record.subtitle ? (
        <p className="text-sm text-slate-700">{record.subtitle}</p>
      ) : null}

      {metadataRows.length > 0 ? (
        <div className="grid gap-1 text-xs text-slate-500">
          {metadataRows.map((row) => (
            <p key={row.key}>
              <span className="font-medium text-slate-700">{row.label}:</span> {row.value}
            </p>
          ))}
        </div>
      ) : null}

      <div className="grid gap-1 text-xs text-slate-500">
        {record.primaryTimestampValue ? (
          <p>
            <span className="font-medium text-slate-700">
              {record.primaryTimestampLabel ?? "Confirmado"}:
            </span>{" "}
            {record.primaryTimestampValue}
          </p>
        ) : null}
        {record.secondaryTimestampValue ? (
          <p>
            <span className="font-medium text-slate-700">
              {record.secondaryTimestampLabel ?? "Creado"}:
            </span>{" "}
            {record.secondaryTimestampValue}
          </p>
        ) : null}
      </div>

      {record.metrics && record.metrics.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {record.metrics.map((metric) => (
            <span
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs font-medium [font-variant-numeric:tabular-nums]",
                isSelected
                  ? "border-[var(--pos-primary)]/20 bg-white text-slate-700"
                  : "border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] text-slate-600",
              )}
              key={metric.key}
            >
              {metric.label}: {metric.value}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function OperationHistoryList({
  emptyDescription = "No hay documentos historicos para este filtro.",
  emptyTitle = "Sin historial",
  getRecordActions,
  loading = false,
  loadingTitle = "Consultando historial",
  onSelect,
  records,
  selectedRecordId,
}: {
  emptyDescription?: string;
  emptyTitle?: string;
  getRecordActions?: (record: OperationHistoryRecord) => PosRecordAction[];
  loading?: boolean;
  loadingTitle?: string;
  onSelect: (record: OperationHistoryRecord) => void;
  records: OperationHistoryRecord[];
  selectedRecordId?: string | null;
}) {
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);

  return (
    <div data-operation-history-list="true">
      <PosRecordList
        emptyDescription={emptyDescription}
        emptyTitle={emptyTitle}
        getKey={(record) => record.id}
        getRowActions={(record) => [
          {
            key: `${record.id}-copy-folio`,
            label: "Copiar folio",
            onSelect: () => {
              void copyDocumentReferenceToClipboard(record.folio)
                .then(() => showSuccess("Folio copiado."))
                .catch(() => showError("No se pudo copiar el folio."));
            },
          },
          ...(getRecordActions?.(record) ?? []),
        ]}
        loading={loading}
        loadingTitle={loadingTitle}
        onSelect={onSelect}
        records={records}
        renderContent={(record, state) => (
          <OperationHistoryRecordCard isSelected={state.isSelected} record={record} />
        )}
        selectedKey={selectedRecordId}
      />
    </div>
  );
}

export function OperationDocumentSummaryPanel({
  actions = [],
  auditSummary,
  blockers = [],
  className,
  context,
  description,
  kind,
  lines = [],
  metrics = [],
  notices,
  referenceLabel = "Folio",
  referenceValue,
  stateLabel,
  stateTone = "draft",
  timeZone,
  timestamps,
  title,
}: {
  actions?: OperationDocumentAction[];
  auditSummary?: AuditSummaryView | null;
  blockers?: PosBlockerMessage[];
  className?: string;
  context?: OperationDocumentContext;
  description?: ReactNode;
  kind: OperationDocumentKind;
  lines?: OperationLineSummaryItem[];
  metrics?: OperationDocumentMetric[];
  notices?: ReactNode;
  referenceLabel?: string;
  referenceValue?: string | null;
  stateLabel: string;
  stateTone?: PosStatusBadgeVariant;
  timeZone?: string;
  timestamps?: OperationDocumentTimestamps;
  title?: string;
}) {
  const printableKind = mapDocumentKindToPrintableKind(kind);
  const availability = getDocumentActionAvailability(printableKind);
  const shouldAppendCopyAction = referenceValue && !hasActionKind(actions, "copyFolio");
  const resolvedActions = referenceValue
    ? [
        ...actions,
        ...(shouldAppendCopyAction
          ? [
              {
                key: `${printableKind}-summary-copy-folio`,
                kind: "copyFolio" as const,
                label: availability.copyFolio.label,
                onSelect: () => undefined,
                placement: "menu" as const,
                referenceValue,
                variant: "neutral" as const,
              },
            ]
          : []),
      ]
    : actions;

  return (
    <PosSummaryPanel
      className={cn("grid", className)}
      data-operation-document-summary-panel="true"
      description={
        <div className="grid gap-1">
          <span className="pos-label-text">{getOperationDocumentKindLabel(kind)}</span>
          {description}
        </div>
      }
      stateLabel={stateLabel}
      stateTone={stateTone}
      title={title ?? "Documento operativo"}
    >
      {referenceValue ? (
        <PosCard className="px-3 py-2.5">
          <p className="pos-label-text">{referenceLabel}</p>
          <p className="mt-1 text-base font-semibold text-slate-950">
            {formatRecordReference(referenceValue, "Sin folio")}
          </p>
        </PosCard>
      ) : null}

      {notices}
      <OperationContextGrid context={context} timestamps={timestamps} />
      <OperationMetricGrid metrics={metrics} />
      {auditSummary && timeZone ? (
        <PosAuditSummary auditSummary={auditSummary} timeZone={timeZone} />
      ) : null}
      <OperationLineSummary lines={lines} />
      <PosBlockerPanel blockers={blockers} title="Bloqueos del documento" />
      <OperationActionRow actions={resolvedActions} />
    </PosSummaryPanel>
  );
}
