import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentPropsWithoutRef,
  type ReactNode,
  type Ref,
} from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import { CatalogSelectionCard } from "../../components/catalog-selection-card";
import { CatalogVisual } from "../../components/catalog-visual";
import {
  OperationConfirmationDialog,
  OperationDocumentResult,
  OperationDocumentSummaryPanel,
  OperationHistoryList,
  OperationLineSummary,
  type OperationDocumentAction,
  type OperationHistoryRecord,
  type OperationLineSummaryItem,
} from "../../components/operation-documents";
import { OperationalStatus } from "../../components/operational-status";
import { PosContextBanner, PosModuleLayout, PosSummaryPanel } from "../../components/pos-module-layout";
import { PosBlockerPanel, PosInlineValidationMessage } from "../../components/pos-feedback";
import {
  PosButton,
  PosCard,
  PosFieldLabel,
  PosPanel,
  PosSectionTitle,
  PosStatusBadge,
} from "../../components/pos-foundations";
import {
  CentralWorkspaceSheet,
  FlowGuide,
  InlineNotice,
  ModuleStateChip,
  CompactPageHeader,
  SearchField,
} from "../../components/pos-module-primitives";
import { PosScannerInput } from "../../components/pos-scanner-input";
import { PosFilterBar, PosHistoryView, PosRecordTable, type PosRecordColumn } from "../../components/pos-records";
import {
  ArrowLeftIcon,
  ClipboardIcon,
  HashIcon,
  MinusIcon,
  PackageIcon,
  PlusIcon,
  PrinterIcon,
  RotateCcwIcon,
  StoreIcon,
  TrashIcon,
  XIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import { appEnv } from "../../env";
import type {
  CashCloseReconciliationProductView,
  CounterTransferCommitRequest,
  OperationHistoryFilterOptionView,
  OperationHistoryResponse,
  OperationHistoryScopeView,
  OperationDocumentView,
  WasteCommitRequest,
  WasteReasonView,
} from "../../lib/api-contracts";
import { getDocumentActionAvailability } from "../../lib/document-actions";
import { formatCompactLocalDateTime } from "../../lib/formatters";
import {
  getFocusableElements,
  getSelectionShortcutIndex,
  getSelectionShortcutLabel,
  isEditableTarget,
} from "../../lib/keyboard-shortcuts";
import { matchesScannerValue, parseProductScannerValue } from "../../lib/scanner";
import { toOperationalErrorMessage } from "../../lib/http";
import { cn } from "../../lib/utils";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import {
  cashCloseReconciliationQueryKey,
  useCashCloseReconciliationQuery,
} from "../cash-close/queries";
import { usePosAuthStore } from "../auth/auth-store";
import { useRovingFocusGrid } from "../pos-shell/keyboard";
import { useStatusMessageStore } from "../status-messages/store";
import {
  addPendingSelectionLine,
  buildOperationCommitLines,
  CONTROL_STATE_CLASS_SELECTION,
  CONTROL_STATE_PRODUCT_SELECTION,
  CONTROL_STATE_QUANTITY_CAPTURE,
  type OperationControlState,
  createInitialOperationDraftState,
  decrementPendingOperationQuantity,
  getWasteDocumentBlockedReason,
  getWasteDocumentBlockingMessages,
  getWasteDocumentUiState,
  getOperationDocumentState,
  getOperationLineCount,
  getOperationPendingCaptureTargetKey,
  getOperationTotalUnitsMilli,
  hasOperationInvalidLineQuantity,
  goBackFromOperationalState,
  incrementPendingOperationQuantity,
  removeOperationLine,
  selectClassForOperation,
  selectProductForOperation,
  setPendingQuantityText,
  sortOperationalClasses,
  sortOperationalProducts,
  updateOperationLineQuantity,
} from "./model";
import { commitCounterTransfer, commitWasteRecord } from "./operations-api";
import {
  operationDocumentQueryKey,
  operationHistoryQueryKey,
  useOperationsBootstrapQuery,
  useOperationsCatalogQuery,
  useOperationsClassProductsQuery,
  useOperationDocumentQuery,
  useOperationHistoryQuery,
} from "./queries";
import {
  formatQuantityFromMilliUnits,
  hasCapturedQuantity,
  parseQuantityToMilliUnits,
  sanitizeQuantityInput,
} from "../pos-terminal/model";
import { posInputClass, posOutlineButtonClass, posPrimaryButtonClass } from "../pos-theme/theme";

const WASTE_SOURCE_BUCKET_OPTIONS = [
  { label: "Mostrador", value: "COUNTER" },
  { label: "Fondo", value: "BACKROOM" },
] as const;

type OperationModuleVariant = "counterTransfer" | "waste";

interface OperationModuleConfig {
  commitButtonLabel: string;
  emptyMessage: string;
  moduleKey: string;
  summaryTitle: string;
  title: string;
}

const operationModuleConfig: Record<OperationModuleVariant, OperationModuleConfig> = {
  counterTransfer: {
    commitButtonLabel: "Transferir",
    emptyMessage: "Agrega productos exactos para preparar el documento de paso a mostrador.",
    moduleKey: "COUNTER_TRANSFER",
    summaryTitle: "Pasar a mostrador",
    title: "Pasar a mostrador",
  },
  waste: {
    commitButtonLabel: "Registrar merma",
    emptyMessage: "Agrega productos exactos para preparar el documento de merma.",
    moduleKey: "WASTE_RECORD",
    summaryTitle: "Registrar merma",
    title: "Registrar merma",
  },
};

const COUNTER_TRANSFER_HISTORY_SCOPE_LABELS: Record<string, string> = {
  CURRENT_SHIFT: "Turno actual",
  RECENT: "Recientes",
  TODAY: "Hoy",
};

type CounterTransferShiftFilter = "ALL" | "AFTERNOON" | "MORNING" | "NIGHT";

const WASTE_TRACEABILITY_OVERLAY_MESSAGE = "Selecciona origen y motivo para comenzar.";
const WASTE_TRACEABILITY_BLOCK_MESSAGE = "Selecciona origen y motivo para continuar.";

function getCounterTransferHistoryScopeLabel(scope: string): string {
  return COUNTER_TRANSFER_HISTORY_SCOPE_LABELS[scope] ?? "Historial";
}

function getCounterTransferShiftLabel(shift: CounterTransferShiftFilter): string {
  switch (shift) {
    case "MORNING":
      return "Manana";
    case "AFTERNOON":
      return "Tarde";
    case "NIGHT":
      return "Noche";
    default:
      return "Todo el dia";
  }
}

function getLocalHourInTimeZone(dateTime: string, timeZone: string): number {
  return Number(
    new Intl.DateTimeFormat("en-US", {
      hour: "2-digit",
      hourCycle: "h23",
      timeZone,
    }).format(new Date(dateTime)),
  );
}

function getCounterTransferShiftForRecord(
  record: OperationHistoryResponse["records"][number],
  timeZone: string,
): Exclude<CounterTransferShiftFilter, "ALL"> {
  const baseDateTime = record.committed_at_utc ?? record.created_at_utc;
  const hour = getLocalHourInTimeZone(baseDateTime, timeZone);

  if (hour >= 5 && hour < 12) {
    return "MORNING";
  }

  if (hour >= 12 && hour < 19) {
    return "AFTERNOON";
  }

  return "NIGHT";
}

function getCounterTransferBucketLabel(bucketCode?: string | null): string {
  switch (bucketCode) {
    case "BACKROOM":
      return "Empaque";
    case "COUNTER":
      return "Mostrador";
    default:
      return bucketCode ?? "Mostrador";
  }
}

function getOperationDocumentStatusLabel(status: string): string {
  switch (status) {
    case "COMMITTED":
      return "Confirmado";
    case "IN_TRANSIT":
      return "En transito";
    case "RECEIVED":
      return "Recibido";
    case "RECEIVED_WITH_VARIANCE":
      return "Recibido con diferencia";
    case "CANCELLED":
      return "Cancelado";
    default:
      return status;
  }
}

function getOperationDocumentStatusTone(status: string) {
  switch (status) {
    case "COMMITTED":
      return "confirmed" as const;
    case "RECEIVED":
      return "success" as const;
    case "RECEIVED_WITH_VARIANCE":
      return "warning" as const;
    case "CANCELLED":
      return "error" as const;
    default:
      return "draft" as const;
  }
}

function buildOperationDocumentSummaryLines(
  lines: OperationDocumentView["lines"],
): OperationLineSummaryItem[] {
  return lines.map((line) => ({
    key: line.id,
    quantityText: formatQuantityFromMilliUnits(Number(line.quantity) * 1000),
    secondaryText: line.product_class_name_snapshot,
    title: line.product_name_snapshot,
  }));
}

function buildWasteHistoryRecords(
  history: OperationHistoryResponse | undefined,
  timeZone: string,
): OperationHistoryRecord[] {
  return (history?.records ?? []).map((record: OperationHistoryResponse["records"][number]) => ({
    documentTypeLabel: "Merma",
    folio: record.folio,
    id: record.id,
    locationLabel: `${record.source_branch_name} / ${record.workstation_name}`,
    metrics: [
      {
        key: "line-count",
        label: "Lineas",
        value: String(record.line_count),
      },
      {
        key: "total-quantity",
        label: "Unidades",
        value: formatQuantityFromMilliUnits(Number(record.total_quantity) * 1000),
      },
    ],
    primaryTimestampLabel: "Confirmado",
    primaryTimestampValue: record.committed_at_utc
      ? formatCompactLocalDateTime(record.committed_at_utc, timeZone)
      : undefined,
    secondaryTimestampLabel: "Creado",
    secondaryTimestampValue: formatCompactLocalDateTime(record.created_at_utc, timeZone),
    statusLabel: getOperationDocumentStatusLabel(record.status),
    statusTone: getOperationDocumentStatusTone(record.status),
    subtitle: `${record.reason_name ?? "Sin motivo"} · ${record.source_bucket_code ?? "Origen"}`,
    title: record.reason_name ?? "Merma registrada",
    userLabel: record.created_by_user_full_name,
  }));
}

function getOperationStateLabel(
  state: ReturnType<typeof getOperationDocumentState>,
): string {
  switch (state) {
    case "NO_LINES_YET":
      return "Sin lineas";
    case "DOCUMENT_BUILDING":
      return "En captura";
    case "READY_TO_COMMIT":
      return "Listo para registrar";
    case "COMMITTING":
      return "Registrando";
    case "COMMITTED_SUCCESS":
      return "Registrado";
    default:
      return "Sin lineas";
  }
}

function getOperationStateTone(
  state: ReturnType<typeof getOperationDocumentState>,
): "muted" | "primary" | "success" {
  switch (state) {
    case "READY_TO_COMMIT":
    case "DOCUMENT_BUILDING":
    case "COMMITTING":
      return "primary";
    case "COMMITTED_SUCCESS":
      return "success";
    default:
      return "muted";
  }
}

function getOperationStateBadgeTone(
  state: ReturnType<typeof getOperationDocumentState>,
): "draft" | "pending" | "success" {
  switch (state) {
    case "READY_TO_COMMIT":
    case "DOCUMENT_BUILDING":
    case "COMMITTING":
      return "pending";
    case "COMMITTED_SUCCESS":
      return "success";
    default:
      return "draft";
  }
}

function getCounterTransferPanelTitle(
  state: ReturnType<typeof getOperationDocumentState>,
): string {
  switch (state) {
    case "NO_LINES_YET":
      return "Nuevo traspaso";
    case "DOCUMENT_BUILDING":
    case "READY_TO_COMMIT":
      return "Borrador de traspaso";
    case "COMMITTING":
      return "Registrando traspaso";
    case "COMMITTED_SUCCESS":
      return "Traspaso registrado";
    default:
      return "Borrador de traspaso";
  }
}

function getWasteReasonLabel(reason: WasteReasonView): string {
  switch (reason.code) {
    case "OLD_COUNTER":
      return "Producto rezagado";
    case "DAMAGED":
      return "Danado";
    case "CONTAMINATED":
      return "Contaminado";
    case "EXPIRED":
      return "Caducado";
    case "OTHER":
      return "Otro";
    default:
      return reason.name;
  }
}

function getWasteSourceBucketLabel(code: string): string {
  return (
    WASTE_SOURCE_BUCKET_OPTIONS.find((option) => option.value === code)?.label ??
    "Pendiente"
  );
}

function getWasteUiStateLabel(
  state: ReturnType<typeof getWasteDocumentUiState>,
): string {
  switch (state) {
    case "TRACEABILITY_INCOMPLETE":
    case "BLOCKED_MISSING_ORIGIN":
    case "BLOCKED_MISSING_REASON":
      return "Incompleto";
    case "READY_TO_CAPTURE":
    case "DOCUMENT_BUILDING":
    case "BLOCKED_NO_LINES":
      return "Pendiente";
    case "READY_TO_REGISTER":
      return "Listo";
    case "REGISTERING":
      return "Registrando...";
    case "REGISTERED_SUCCESS":
      return "Registrado";
    case "ERROR":
      return "Error";
    default:
      return "Incompleto";
  }
}

function getWasteUiStateTone(
  state: ReturnType<typeof getWasteDocumentUiState>,
): "muted" | "primary" | "success" | "warning" | "danger" {
  switch (state) {
    case "READY_TO_REGISTER":
      return "success";
    case "REGISTERING":
      return "primary";
    case "REGISTERED_SUCCESS":
      return "success";
    case "ERROR":
      return "danger";
    case "TRACEABILITY_INCOMPLETE":
    case "BLOCKED_MISSING_ORIGIN":
    case "BLOCKED_MISSING_REASON":
      return "warning";
    default:
      return "muted";
  }
}

function getWastePanelTitle(
  state: ReturnType<typeof getWasteDocumentUiState>,
): string {
  switch (state) {
    case "TRACEABILITY_INCOMPLETE":
    case "BLOCKED_MISSING_ORIGIN":
    case "BLOCKED_MISSING_REASON":
      return "Traceabilidad pendiente";
    case "READY_TO_CAPTURE":
    case "DOCUMENT_BUILDING":
    case "BLOCKED_NO_LINES":
      return "Merma en construccion";
    case "READY_TO_REGISTER":
      return "Merma lista para registrar";
    case "REGISTERING":
      return "Registrando merma";
    case "REGISTERED_SUCCESS":
      return "Merma registrada";
    case "ERROR":
      return "Error al registrar";
    default:
      return "Merma en construccion";
  }
}

function getWasteReasonName(
  wasteReasons: WasteReasonView[],
  reasonCode: string,
): string {
  const reason = wasteReasons.find((item) => item.code === reasonCode);
  return reason ? getWasteReasonLabel(reason) : "Pendiente";
}

function useDebouncedValue(value: string, delayMs: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    if (debouncedValue === value) {
      return;
    }

    const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeout);
  }, [debouncedValue, delayMs, value]);

  return debouncedValue;
}

function formatOperationQuantity(quantity: number | string): string {
  return new Intl.NumberFormat("es-MX", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(quantity));
}

function getCounterAvailableQuantity(
  product: CashCloseReconciliationProductView,
): number {
  const resolvedQuantity =
    product.final_expected_quantity ?? product.expected_quantity_before_deferred_attr;
  return Number(resolvedQuantity);
}

function buildCounterAvailabilityByProductId(
  products: CashCloseReconciliationProductView[],
): Map<string, number> {
  return new Map(
    products.map((product) => [product.product_id, getCounterAvailableQuantity(product)]),
  );
}

function SelectionCard({
  buttonRef,
  code,
  isActive = false,
  isDisabled = false,
  onCardFocus,
  onCardKeyDown,
  onSelect,
  shortcutLabel,
  tabIndex = -1,
  title,
}: {
  buttonRef?: Ref<HTMLButtonElement>;
  code: string;
  isActive?: boolean;
  isDisabled?: boolean;
  onCardFocus?: ComponentPropsWithoutRef<"button">["onFocus"];
  onCardKeyDown?: ComponentPropsWithoutRef<"button">["onKeyDown"];
  onSelect: () => void;
  shortcutLabel: string | null;
  tabIndex?: number;
  title: string;
}) {
  return (
    <CatalogSelectionCard
      buttonRef={buttonRef}
      code={code}
      isActive={isActive}
      isDisabled={isDisabled}
      name={title}
      onCardFocus={onCardFocus}
      onCardKeyDown={onCardKeyDown}
      onSelect={onSelect}
      shortcutLabel={shortcutLabel}
      tabIndex={tabIndex}
      variant="pos"
    />
  );
}

function OperationLineRow({
  editingQuantityText,
  inputRef,
  isEditing,
  isSelected,
  name,
  onBeginEdit,
  onCancelEdit,
  onCommitEdit,
  onDecrement,
  onEditingQuantityChange,
  onIncrement,
  onRemove,
  onSelect,
  quantity,
}: {
  editingQuantityText: string;
  inputRef: Ref<HTMLInputElement>;
  isEditing: boolean;
  isSelected: boolean;
  name: string;
  onBeginEdit: () => void;
  onCancelEdit: () => void;
  onCommitEdit: () => void;
  onDecrement: () => void;
  onEditingQuantityChange: (value: string) => void;
  onIncrement: () => void;
  onRemove: () => void;
  onSelect: () => void;
  quantity: string;
}) {
  return (
    <div
      aria-selected={isSelected}
      className={cn(
        "grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-1.5 border-t border-[var(--pos-shell-border)] px-2 py-1.5 first:border-t-0",
        isSelected && "bg-[var(--pos-primary-soft)]/70",
      )}
      onClick={onSelect}
      onFocusCapture={onSelect}
      role="row"
      tabIndex={0}
    >
      <div className="min-w-0">
        <p className="truncate text-[13px] font-medium leading-5 text-slate-950">{name}</p>
      </div>

      <div className="flex items-center gap-0 rounded-md border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-0.5 py-0.5">
        <button
          className="flex h-7 w-7 items-center justify-center rounded-sm text-slate-900 transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
          onClick={(event) => {
            event.stopPropagation();
            onDecrement();
          }}
          type="button"
        >
          <MinusIcon className="h-3 w-3" />
        </button>
        <div className="w-[3.1rem]">
          {isEditing ? (
            <input
              aria-label={`Cantidad de ${name}`}
              className={cn(
                "h-7 w-full rounded-sm px-1 text-center text-[13px] font-semibold text-slate-950 [font-variant-numeric:tabular-nums]",
                posInputClass,
              )}
              inputMode="decimal"
              onBlur={onCommitEdit}
              onChange={(event) => onEditingQuantityChange(event.target.value)}
              onClick={(event) => event.stopPropagation()}
              onKeyDown={(event) => {
                event.stopPropagation();
                if (event.key === "Enter" || event.key === "NumpadEnter") {
                  event.preventDefault();
                  onCommitEdit();
                  return;
                }

                if (event.key === "Escape") {
                  event.preventDefault();
                  onCancelEdit();
                }
              }}
              ref={inputRef}
              value={editingQuantityText}
            />
          ) : (
            <button
              aria-label={`Editar cantidad de ${name}`}
              className="h-7 w-full rounded-sm px-1 text-center text-[13px] font-semibold text-slate-950 transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] [font-variant-numeric:tabular-nums]"
              onClick={(event) => {
                event.stopPropagation();
                onBeginEdit();
              }}
              type="button"
            >
              {quantity}
            </button>
          )}
        </div>
        <button
          className="flex h-7 w-7 items-center justify-center rounded-sm text-slate-900 transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
          onClick={(event) => {
            event.stopPropagation();
            onIncrement();
          }}
          type="button"
        >
          <PlusIcon className="h-3 w-3" />
        </button>
      </div>

      <button
        aria-label={`Eliminar ${name}`}
        className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
        onClick={(event) => {
          event.stopPropagation();
          onRemove();
        }}
        type="button"
      >
        <TrashIcon className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function CounterMovementSummaryCard({
  destinationLabel = "Mostrador",
  sourceLabel = "Empaque",
}: {
  destinationLabel?: string;
  sourceLabel?: string;
}) {
  return (
    <div className="h-fit self-start rounded-xl border border-[rgba(24,94,168,0.24)] bg-[rgba(24,94,168,0.08)] px-3 py-2 shadow-sm">
      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--pos-primary)]">
        Movimiento
      </p>
      <div className="mt-1 flex items-center justify-between gap-3 text-base font-semibold">
        <span className="truncate text-slate-950">{sourceLabel}</span>
        <span className="text-xl text-[var(--pos-primary)]">-&gt;</span>
        <span className="truncate text-[var(--pos-primary)]">{destinationLabel}</span>
      </div>
    </div>
  );
}

function CompactOperationLineSection({
  badgeLabel,
  emptyMessage,
  lines,
  title,
}: {
  badgeLabel?: string;
  emptyMessage: string;
  lines: OperationLineSummaryItem[];
  title: string;
}) {
  return (
    <div className="grid gap-1">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
        {badgeLabel ? (
          <span className="pos-chip" data-tone="muted">
            {badgeLabel}
          </span>
        ) : null}
      </div>
      {lines.length === 0 ? (
        <PosCard className="px-3 py-2.5">
          <p className="text-sm text-slate-600">{emptyMessage}</p>
        </PosCard>
      ) : (
        <div className="overflow-hidden rounded-[var(--pos-radius-panel)] border border-[var(--pos-shell-border)] bg-white">
          {lines.map((line) => (
            <div
              className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 border-t border-[var(--pos-shell-border)] px-3 py-2 first:border-t-0"
              key={line.key}
            >
              <p className="truncate text-sm font-semibold text-slate-950" title={line.title}>
                {line.title}
              </p>
              {line.quantityText ? (
                <span className="font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                  {line.quantityText}
                </span>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CounterAvailabilitySection({
  branchName,
  containerRef,
  onRetry,
  products,
  queryErrorMessage,
  queryPending,
}: {
  branchName: string;
  containerRef?: Ref<HTMLDivElement>;
  onRetry: () => void;
  products: CashCloseReconciliationProductView[];
  queryErrorMessage: string | null;
  queryPending: boolean;
}) {
  const columns = useMemo<PosRecordColumn<CashCloseReconciliationProductView>[]>(
    () => [
      {
        header: "Producto",
        key: "product",
        renderCell: (product) => (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-950">{product.product_name}</p>
            <p className="mt-1 truncate text-xs font-medium text-slate-500">
              {product.product_class_name}
            </p>
          </div>
        ),
      },
      {
        header: "Codigo",
        key: "code",
        renderCell: (product) => (
          <span className="font-medium text-slate-700">{product.product_code}</span>
        ),
        width: "8rem",
      },
      {
        align: "right",
        header: "Disponible",
        key: "quantity",
        renderCell: (product) => (
          <span className="font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
            {formatOperationQuantity(getCounterAvailableQuantity(product))}
          </span>
        ),
        width: "7rem",
      },
    ],
    [],
  );

  return (
    <div className="grid gap-3" ref={containerRef} tabIndex={-1}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-slate-950">
            Productos en mostrador
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Vista operativa del saldo actual esperado en mostrador para {branchName}. Refleja el
            estado confirmado del mostrador, incluyendo traspasos, mermas y otros ajustes ya
            registrados.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ModuleStateChip tone="info">Vista de consulta</ModuleStateChip>
          <span className="pos-chip" data-tone="muted">
            {products.length} productos
          </span>
        </div>
      </div>

      {queryPending ? (
        <OperationalStatus
          description="Consultando el saldo actual esperado en mostrador."
          title="Cargando disponibilidad"
        />
      ) : null}

      {!queryPending && queryErrorMessage ? (
        <OperationalStatus
          action={<Button onClick={onRetry}>Reintentar</Button>}
          description={queryErrorMessage}
          title="No fue posible consultar mostrador"
        />
      ) : null}

      {!queryPending && !queryErrorMessage ? (
        <PosRecordTable
          columns={columns}
          emptyDescription="Aun no hay productos disponibles en mostrador para esta sucursal."
          emptyTitle="Mostrador sin productos"
          getKey={(product) => product.product_id}
          onSelect={() => undefined}
          records={products}
          tableAriaLabel="Productos actualmente en mostrador"
        />
      ) : null}
    </div>
  );
}

function WasteTraceabilitySection({
  controlState,
  getOriginItemProps,
  getReasonItemProps,
  isCommitPending,
  isSearchDisabled,
  originActiveIndex,
  onGoBack,
  onReasonChange,
  onSourceBucketChange,
  reasonActiveIndex,
  reasonCode,
  searchField,
  sourceBucketCode,
  wasteReasons,
}: {
  controlState: OperationControlState;
  getOriginItemProps: (index: number) => {
    onFocus: () => void;
    onKeyDown: ComponentPropsWithoutRef<"button">["onKeyDown"];
    ref: Ref<HTMLButtonElement>;
    tabIndex: number;
  };
  getReasonItemProps: (index: number) => {
    onFocus: () => void;
    onKeyDown: ComponentPropsWithoutRef<"button">["onKeyDown"];
    ref: Ref<HTMLButtonElement>;
    tabIndex: number;
  };
  isCommitPending: boolean;
  isSearchDisabled: boolean;
  originActiveIndex: number;
  onGoBack: () => void;
  onReasonChange: (value: string) => void;
  onSourceBucketChange: (value: string) => void;
  reasonActiveIndex: number;
  reasonCode: string;
  searchField?: ReactNode;
  sourceBucketCode: string;
  wasteReasons: WasteReasonView[];
}) {
  const isTraceabilityReady = sourceBucketCode.trim().length > 0 && reasonCode.trim().length > 0;

  return (
    <PosPanel className="grid gap-4 px-4 py-4">
      <PosSectionTitle
        description="Selecciona origen y motivo antes de habilitar la captura de productos."
        eyebrow="1. Trazabilidad"
        title="Define el contexto de la merma"
      />

      <div className="grid gap-3 xl:grid-cols-[minmax(0,16rem)_minmax(0,1fr)]">
        <PosCard className="px-3.5 py-3">
          <PosFieldLabel helper="Usa flechas y Enter para seleccionar." required>
            Origen
          </PosFieldLabel>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {WASTE_SOURCE_BUCKET_OPTIONS.map((option, index) => {
              const isActive = sourceBucketCode === option.value;
              const itemProps = getOriginItemProps(index);

              return (
                <PosButton
                  className={cn(originActiveIndex === index && "ring-2 ring-[var(--pos-ring)]")}
                  disabled={isCommitPending}
                  key={option.value}
                  onClick={() => onSourceBucketChange(option.value)}
                  onFocus={itemProps.onFocus}
                  onKeyDown={itemProps.onKeyDown}
                  ref={itemProps.ref}
                  tabIndex={itemProps.tabIndex}
                  variant={isActive ? "secondary" : "neutral"}
                >
                  {option.label}
                </PosButton>
              );
            })}
          </div>
        </PosCard>

        <PosCard className="px-3.5 py-3">
          <PosFieldLabel helper="Usa flechas y Enter para seleccionar." required>
            Motivo
          </PosFieldLabel>
          <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {wasteReasons.map((reason, index) => {
              const isActive = reasonCode === reason.code;
              const itemProps = getReasonItemProps(index);

              return (
                <PosButton
                  className={cn(reasonActiveIndex === index && "ring-2 ring-[var(--pos-ring)]")}
                  disabled={isCommitPending}
                  key={reason.code}
                  onClick={() => onReasonChange(reason.code)}
                  onFocus={itemProps.onFocus}
                  onKeyDown={itemProps.onKeyDown}
                  ref={itemProps.ref}
                  tabIndex={itemProps.tabIndex}
                  title={getWasteReasonLabel(reason)}
                  variant={isActive ? "secondary" : "neutral"}
                >
                  {getWasteReasonLabel(reason)}
                </PosButton>
              );
            })}
          </div>
        </PosCard>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <PosStatusBadge status={isTraceabilityReady ? "ready" : "blocked"}>
            {isTraceabilityReady ? "Captura habilitada" : "Faltan origen y motivo"}
          </PosStatusBadge>
          {!isTraceabilityReady ? (
            <span className="text-sm text-slate-600">
              Selecciona origen y motivo para habilitar productos.
            </span>
          ) : null}
        </div>

        {searchField ? (
          <div className="flex w-full flex-wrap items-center justify-end gap-2 lg:max-w-xl">
            {controlState === CONTROL_STATE_PRODUCT_SELECTION ? (
              <Button
                aria-label="Regresar"
                className={cn("h-10 px-3", posOutlineButtonClass)}
                disabled={isCommitPending}
                onClick={onGoBack}
                title="Regresar"
                type="button"
              >
                <ArrowLeftIcon className="h-4 w-4" />
              </Button>
            ) : null}
            <div className="w-full min-w-0 lg:max-w-sm">{searchField}</div>
          </div>
        ) : null}
      </div>

      {isSearchDisabled ? (
        <InlineNotice tone="warning">{WASTE_TRACEABILITY_BLOCK_MESSAGE}</InlineNotice>
      ) : null}
    </PosPanel>
  );
}

export function OperationModuleScreen({ variant }: { variant: OperationModuleVariant }) {
  const config = operationModuleConfig[variant];
  const queryClient = useQueryClient();
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const showWarning = useStatusMessageStore((state) => state.showWarning);
  const quantityInputRef = useRef<HTMLInputElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const scannerInputRef = useRef<HTMLInputElement>(null);
  const counterTransferAvailabilityRef = useRef<HTMLDivElement>(null);
  const quantityFocusTargetRef = useRef<string | null>(null);
  const [draftState, setDraftState] = useState(createInitialOperationDraftState());
  const [selectionErrorMessage, setSelectionErrorMessage] = useState<string | null>(null);
  const [commitErrorMessage, setCommitErrorMessage] = useState<string | null>(null);
  const [lastCommittedDocument, setLastCommittedDocument] = useState<OperationDocumentView | null>(
    null,
  );
  const [sourceBucketCode, setSourceBucketCode] = useState("");
  const [reasonCode, setReasonCode] = useState("");
  const [notes, setNotes] = useState("");
  const [isWasteHighImpactAcknowledged, setIsWasteHighImpactAcknowledged] = useState(false);
  const [lastWasteHighImpactAlertRequested, setLastWasteHighImpactAlertRequested] =
    useState(false);
  const [scannerText, setScannerText] = useState("");
  const [pendingScannerCode, setPendingScannerCode] = useState<string | null>(null);
  const [isWasteConfirmDialogOpen, setIsWasteConfirmDialogOpen] = useState(false);
  const [wasteCenterView, setWasteCenterView] = useState<"capture" | "history">("capture");
  const [counterTransferCenterView, setCounterTransferCenterView] = useState<
    "capture" | "counterAvailability" | "history"
  >("capture");
  const [isCounterTransferConfirmDialogOpen, setIsCounterTransferConfirmDialogOpen] =
    useState(false);
  const [selectedCounterTransferDraftLineKey, setSelectedCounterTransferDraftLineKey] = useState<
    string | null
  >(null);
  const [editingCounterTransferDraftLineKey, setEditingCounterTransferDraftLineKey] = useState<
    string | null
  >(null);
  const [editingCounterTransferQuantityText, setEditingCounterTransferQuantityText] = useState("");
  const [selectedHistoryDocumentId, setSelectedHistoryDocumentId] = useState<string | null>(null);
  const [counterTransferHistoryScope, setCounterTransferHistoryScope] = useState("TODAY");
  const [counterTransferHistoryUserId, setCounterTransferHistoryUserId] = useState<string>("ALL");
  const [counterTransferHistoryShiftFilter, setCounterTransferHistoryShiftFilter] =
    useState<CounterTransferShiftFilter>("ALL");
  const [wasteHistoryScope, setWasteHistoryScope] = useState("CURRENT_SHIFT");
  const [wasteHistoryUserId, setWasteHistoryUserId] = useState<string>("ALL");
  const [wasteHistoryReasonCode, setWasteHistoryReasonCode] = useState<string>("ALL");
  const [wasteHistoryProductId, setWasteHistoryProductId] = useState<string>("ALL");
  const [wasteHistorySearchText, setWasteHistorySearchText] = useState("");
  const lastGridFocusKeyRef = useRef<string | null>(null);
  const counterTransferDraftQuantityInputRef = useRef<HTMLInputElement | null>(null);
  const operationsBootstrapQuery = useOperationsBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const wasteStockValidatedSourceBuckets = useMemo(
    () => operationsBootstrapQuery.data?.waste_controls.stock_validated_source_bucket_codes ?? [],
    [operationsBootstrapQuery.data?.waste_controls.stock_validated_source_bucket_codes],
  );
  const shouldLoadCounterAvailability =
    (variant === "counterTransfer" && counterTransferCenterView === "counterAvailability") ||
    (variant === "counterTransfer" && counterTransferCenterView === "history") ||
    (variant === "waste" &&
      wasteCenterView === "capture" &&
      wasteStockValidatedSourceBuckets.includes(sourceBucketCode));
  const counterAvailabilityQuery = useCashCloseReconciliationQuery(
    shouldLoadCounterAvailability,
  );
  const debouncedSearchText = useDebouncedValue(draftState.searchText, 180);
  const catalogQuery = useOperationsCatalogQuery(
    config.moduleKey,
    draftState.controlState === CONTROL_STATE_CLASS_SELECTION ? debouncedSearchText : "",
  );
  const classProductsQuery = useOperationsClassProductsQuery(
    config.moduleKey,
    draftState.pendingSelection?.productClass.id ?? null,
    draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ? debouncedSearchText : "",
  );
  const counterTransferHistoryQuery = useOperationHistoryQuery(
    "COUNTER_TRANSFER",
    {
      createdByUserId:
        counterTransferHistoryUserId !== "ALL" ? counterTransferHistoryUserId : undefined,
      scope: counterTransferHistoryScope,
    },
    variant === "counterTransfer" && counterTransferCenterView === "history",
  );
  const wasteHistoryQuery = useOperationHistoryQuery(
    "WASTE_RECORD",
    {
      createdByUserId: wasteHistoryUserId !== "ALL" ? wasteHistoryUserId : undefined,
      productId: wasteHistoryProductId !== "ALL" ? wasteHistoryProductId : undefined,
      reasonCode: wasteHistoryReasonCode !== "ALL" ? wasteHistoryReasonCode : undefined,
      scope: wasteHistoryScope,
    },
    variant === "waste" && wasteCenterView === "history",
  );
  const selectedHistoryDocumentQuery = useOperationDocumentQuery(
    (variant === "counterTransfer" && counterTransferCenterView === "history") ||
      (variant === "waste" && wasteCenterView === "history")
      ? selectedHistoryDocumentId
      : null,
  );

  useEffect(() => {
    setSelectionErrorMessage(null);
  }, [draftState.controlState, draftState.pendingSelection]);

  useEffect(() => {
    if (
      variant !== "counterTransfer" ||
      (draftState.controlState !== CONTROL_STATE_CLASS_SELECTION &&
        draftState.controlState !== CONTROL_STATE_PRODUCT_SELECTION)
    ) {
      setPendingScannerCode(null);
    }
  }, [draftState.controlState, variant]);

  useEffect(() => {
    setCommitErrorMessage(null);
  }, [draftState.lines, notes, reasonCode, sourceBucketCode]);

  useEffect(() => {
    if (variant !== "counterTransfer") {
      setCounterTransferCenterView("capture");
    }
  }, [variant]);

  useEffect(() => {
    if (variant !== "counterTransfer") {
      setSelectedCounterTransferDraftLineKey(null);
      return;
    }

    if (draftState.lines.length === 0) {
      setSelectedCounterTransferDraftLineKey(null);
      return;
    }

    setSelectedCounterTransferDraftLineKey((current) =>
      current !== null && draftState.lines.some((line) => line.key === current)
        ? current
        : draftState.lines[0]?.key ?? null,
    );
  }, [draftState.lines, variant]);

  useEffect(() => {
    if (variant !== "waste") {
      setWasteCenterView("capture");
    }
  }, [variant]);

  useEffect(() => {
    if (variant !== "counterTransfer" || counterTransferCenterView !== "counterAvailability") {
      return;
    }

    const firstRow = counterTransferAvailabilityRef.current?.querySelector(
      "tbody tr",
    ) as HTMLElement | null;

    if (firstRow) {
      firstRow.focus();
      return;
    }

    counterTransferAvailabilityRef.current?.focus();
  }, [counterAvailabilityQuery.data?.relevant_products?.length, counterTransferCenterView, variant]);

  useEffect(() => {
    const quantityCaptureTarget =
      draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE
        ? getOperationPendingCaptureTargetKey(draftState.pendingSelection)
        : null;

    if (!quantityCaptureTarget) {
      quantityFocusTargetRef.current = null;
      return;
    }

    const canFocusWasteQuantity =
      variant !== "waste" ||
      (sourceBucketCode.trim().length > 0 && reasonCode.trim().length > 0);

    if (!canFocusWasteQuantity) {
      quantityFocusTargetRef.current = null;
      return;
    }

    if (quantityFocusTargetRef.current === quantityCaptureTarget) {
      return;
    }

    quantityFocusTargetRef.current = quantityCaptureTarget;
    quantityInputRef.current?.focus();
    quantityInputRef.current?.select();
  }, [
    draftState.controlState,
    draftState.pendingSelection,
    reasonCode,
    sourceBucketCode,
    variant,
  ]);

  const sortedClasses = useMemo(
    () => sortOperationalClasses(catalogQuery.data?.classes ?? []),
    [catalogQuery.data?.classes],
  );
  const sortedProducts = useMemo(
    () => sortOperationalProducts(classProductsQuery.data?.products ?? []),
    [classProductsQuery.data?.products],
  );
  const isSelectionLoading =
    (draftState.controlState === CONTROL_STATE_CLASS_SELECTION && catalogQuery.isPending) ||
    (draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION && classProductsQuery.isPending);
  const selectionError =
    draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
      ? classProductsQuery.error
      : catalogQuery.error;

  useEffect(() => {
    if (
      variant !== "counterTransfer" ||
      pendingScannerCode === null ||
      isSelectionLoading ||
      selectionError !== null
    ) {
      return;
    }

    if (draftState.controlState === CONTROL_STATE_CLASS_SELECTION) {
      const exactClassMatch = sortedClasses.find((productClass) =>
        matchesScannerValue(productClass.code, pendingScannerCode),
      );

      if (exactClassMatch) {
        setPendingScannerCode(null);
        setLastCommittedDocument(null);
        setDraftState((state) => selectClassForOperation(state, exactClassMatch));
        return;
      }

      if (sortedClasses.length === 1) {
        setPendingScannerCode(null);
        setLastCommittedDocument(null);
        setDraftState((state) => selectClassForOperation(state, sortedClasses[0]!));
      }
      return;
    }

    if (draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION) {
      const exactProductMatch = sortedProducts.find((product) =>
        matchesScannerValue(product.code, pendingScannerCode),
      );

      if (exactProductMatch) {
        setPendingScannerCode(null);
        setLastCommittedDocument(null);
        setDraftState((state) => selectProductForOperation(state, exactProductMatch));
        return;
      }

      if (sortedProducts.length === 1) {
        setPendingScannerCode(null);
        setLastCommittedDocument(null);
        setDraftState((state) => selectProductForOperation(state, sortedProducts[0]!));
      }
    }
  }, [
    draftState.controlState,
    isSelectionLoading,
    pendingScannerCode,
    selectionError,
    sortedClasses,
    sortedProducts,
    variant,
  ]);

  const classGridFocus = useRovingFocusGrid({
    itemCount: sortedClasses.length,
    onActivate: (index) => {
      const productClass = sortedClasses[index];
      if (
        productClass &&
        !(variant === "waste" && !(sourceBucketCode.trim().length > 0 && reasonCode.trim().length > 0))
      ) {
        setLastCommittedDocument(null);
        setDraftState((state) => selectClassForOperation(state, productClass));
      }
    },
  });
  const productGridFocus = useRovingFocusGrid({
    itemCount: sortedProducts.length,
    onActivate: (index) => {
      const product = sortedProducts[index];
      if (
        product &&
        !(variant === "waste" && !(sourceBucketCode.trim().length > 0 && reasonCode.trim().length > 0))
      ) {
        setLastCommittedDocument(null);
        setDraftState((state) => selectProductForOperation(state, product));
      }
    },
  });
  const wasteOriginGridFocus = useRovingFocusGrid({
    columnCount: 2,
    itemCount: WASTE_SOURCE_BUCKET_OPTIONS.length,
    onActivate: (index) => {
      const option = WASTE_SOURCE_BUCKET_OPTIONS[index];
      if (!option) {
        return;
      }

      setLastCommittedDocument(null);
      setSourceBucketCode(option.value);
    },
  });
  const wasteReasonGridFocus = useRovingFocusGrid({
    columnCount: Math.min(3, Math.max(1, operationsBootstrapQuery.data?.waste_reasons.length ?? 1)),
    itemCount: operationsBootstrapQuery.data?.waste_reasons.length ?? 0,
    onActivate: (index) => {
      const reason = operationsBootstrapQuery.data?.waste_reasons[index];
      if (!reason) {
        return;
      }

      setLastCommittedDocument(null);
      setReasonCode(reason.code);
    },
  });
  const {
    activeIndex: classActiveIndex,
    focusIndex: focusClassIndex,
    getItemProps: getClassItemProps,
  } = classGridFocus;
  const {
    activeIndex: productActiveIndex,
    focusIndex: focusProductIndex,
    getItemProps: getProductItemProps,
  } = productGridFocus;
  const {
    activeIndex: wasteOriginActiveIndex,
    getItemProps: getWasteOriginItemProps,
  } = wasteOriginGridFocus;
  const {
    activeIndex: wasteReasonActiveIndex,
    getItemProps: getWasteReasonItemProps,
  } = wasteReasonGridFocus;
  const totalUnitsText = formatQuantityFromMilliUnits(
    getOperationTotalUnitsMilli(draftState.lines),
  );
  const hasWasteOrigin = sourceBucketCode.trim().length > 0;
  const hasWasteReason = reasonCode.trim().length > 0;
  const hasWasteNotes = notes.trim().length > 0;
  const hasInvalidLineQuantity = hasOperationInvalidLineQuantity(draftState.lines);
  const wasteTotalUnitsMilli = getOperationTotalUnitsMilli(draftState.lines);
  const wasteControls = operationsBootstrapQuery.data?.waste_controls;
  const selectedWasteReason =
    operationsBootstrapQuery.data?.waste_reasons.find((item) => item.code === reasonCode) ?? null;
  const wasteHighImpactThresholdMilli =
    parseQuantityToMilliUnits(String(wasteControls?.high_impact_quantity_threshold ?? "0")) ?? 0;
  const isWasteHighImpact =
    wasteHighImpactThresholdMilli > 0 && wasteTotalUnitsMilli > wasteHighImpactThresholdMilli;
  const wasteRequiresEvidenceNote =
    (selectedWasteReason?.requires_note ?? false) ||
    ((wasteControls?.high_impact_requires_note ?? false) && isWasteHighImpact);
  const wasteRequiresHighImpactAcknowledgement =
    (wasteControls?.high_impact_requires_acknowledgement ?? false) && isWasteHighImpact;
  const counterAvailabilityByProductId = useMemo(
    () =>
      buildCounterAvailabilityByProductId(
        counterAvailabilityQuery.data?.relevant_products ?? [],
      ),
    [counterAvailabilityQuery.data?.relevant_products],
  );
  const wasteStockBlockingMessages = useMemo(() => {
    if (
      variant !== "waste" ||
      !hasWasteOrigin ||
      !wasteStockValidatedSourceBuckets.includes(sourceBucketCode)
    ) {
      return [];
    }

    if (counterAvailabilityQuery.isPending) {
      return ["Consultando saldo esperado de mostrador."];
    }

    if (counterAvailabilityQuery.error || counterAvailabilityQuery.data === undefined) {
      return [];
    }

    return draftState.lines.flatMap((line) => {
      const availableQuantity = counterAvailabilityByProductId.get(line.productId) ?? 0;
      const capturedQuantity = line.quantityMilliUnits / 1000;
      if (capturedQuantity <= availableQuantity) {
        return [];
      }

      return [
        `La merma de ${line.productName} excede el saldo esperado en mostrador (${formatOperationQuantity(
          availableQuantity,
        )} disponible).`,
      ];
    });
  }, [
    counterAvailabilityByProductId,
    counterAvailabilityQuery.data,
    counterAvailabilityQuery.error,
    counterAvailabilityQuery.isPending,
    draftState.lines,
    hasWasteOrigin,
    sourceBucketCode,
    variant,
    wasteStockValidatedSourceBuckets,
  ]);
  const wasteStockWarningMessage = useMemo(() => {
    if (
      variant !== "waste" ||
      !hasWasteOrigin ||
      wasteStockValidatedSourceBuckets.includes(sourceBucketCode)
    ) {
      return null;
    }

    return `La disponibilidad de ${getWasteSourceBucketLabel(sourceBucketCode)} no tiene contrato de stock actual. Confirma fisicamente antes de registrar.`;
  }, [hasWasteOrigin, sourceBucketCode, variant, wasteStockValidatedSourceBuckets]);
  const wasteCounterAvailabilityWarningMessage = useMemo(() => {
    if (
      variant !== "waste" ||
      !hasWasteOrigin ||
      !wasteStockValidatedSourceBuckets.includes(sourceBucketCode)
    ) {
      return null;
    }

    if (counterAvailabilityQuery.error) {
      return "No fue posible validar el saldo esperado de mostrador. Confirma fisicamente antes de registrar.";
    }

    if (!counterAvailabilityQuery.isPending && counterAvailabilityQuery.data !== undefined) {
      return null;
    }

    return null;
  }, [
    counterAvailabilityQuery.data,
    counterAvailabilityQuery.error,
    counterAvailabilityQuery.isPending,
    hasWasteOrigin,
    sourceBucketCode,
    variant,
    wasteStockValidatedSourceBuckets,
  ]);
  const wasteBlockedMessages = useMemo(
    () =>
      variant === "waste"
        ? getWasteDocumentBlockingMessages({
            additionalBlockingMessages: wasteStockBlockingMessages,
            evidenceNoteRequired: wasteRequiresEvidenceNote,
            hasEvidenceNote: hasWasteNotes,
            hasHighImpactAcknowledgement: isWasteHighImpactAcknowledged,
            hasInvalidQuantity: hasInvalidLineQuantity,
            highImpactAcknowledgementRequired: wasteRequiresHighImpactAcknowledgement,
            hasOrigin: hasWasteOrigin,
            hasReason: hasWasteReason,
            lineCount: draftState.lines.length,
            totalUnitsMilli: wasteTotalUnitsMilli,
          })
        : [],
    [
      draftState.lines.length,
      hasWasteNotes,
      hasInvalidLineQuantity,
      isWasteHighImpactAcknowledged,
      hasWasteOrigin,
      hasWasteReason,
      wasteRequiresEvidenceNote,
      wasteRequiresHighImpactAcknowledgement,
      wasteStockBlockingMessages,
      variant,
      wasteTotalUnitsMilli,
    ],
  );
  const wasteBlockedReason = useMemo(
    () =>
      variant === "waste"
        ? getWasteDocumentBlockedReason({
            additionalBlockingMessages: wasteStockBlockingMessages,
            evidenceNoteRequired: wasteRequiresEvidenceNote,
            hasEvidenceNote: hasWasteNotes,
            hasHighImpactAcknowledgement: isWasteHighImpactAcknowledged,
            hasInvalidQuantity: hasInvalidLineQuantity,
            highImpactAcknowledgementRequired: wasteRequiresHighImpactAcknowledgement,
            hasOrigin: hasWasteOrigin,
            hasReason: hasWasteReason,
            lineCount: draftState.lines.length,
            totalUnitsMilli: wasteTotalUnitsMilli,
          })
        : null,
    [
      draftState.lines.length,
      hasWasteNotes,
      hasInvalidLineQuantity,
      isWasteHighImpactAcknowledged,
      hasWasteOrigin,
      hasWasteReason,
      wasteRequiresEvidenceNote,
      wasteRequiresHighImpactAcknowledgement,
      wasteStockBlockingMessages,
      variant,
      wasteTotalUnitsMilli,
    ],
  );
  const isWasteTraceabilityReady = variant !== "waste" || (hasWasteOrigin && hasWasteReason);
  const showWasteCaptureOverlay =
    variant === "waste" &&
    !isWasteTraceabilityReady &&
    draftState.controlState !== CONTROL_STATE_QUANTITY_CAPTURE;
  const isCounterTransferAvailabilityView =
    variant === "counterTransfer" && counterTransferCenterView === "counterAvailability";
  const activeGridKey = useMemo(() => {
    if (isCounterTransferAvailabilityView) {
      return null;
    }

    if (draftState.controlState === CONTROL_STATE_CLASS_SELECTION) {
      return "classes";
    }

    if (
      draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION &&
      draftState.pendingSelection !== null
    ) {
      return `products:${draftState.pendingSelection.productClass.id}`;
    }

    return null;
  }, [
    draftState.controlState,
    draftState.pendingSelection,
    isCounterTransferAvailabilityView,
  ]);
  const availableCounterProducts = useMemo(
    () =>
      (counterAvailabilityQuery.data?.relevant_products ?? []).filter(
        (product) => getCounterAvailableQuantity(product) > 0,
      ),
    [counterAvailabilityQuery.data?.relevant_products],
  );
  const counterAvailabilityErrorMessage = counterAvailabilityQuery.error
    ? toOperationalErrorMessage(
        counterAvailabilityQuery.error,
        "No fue posible consultar los productos disponibles en mostrador.",
      )
    : null;
  const counterTransferHistoryAllDayRows = useMemo(
    () => (variant === "counterTransfer" ? counterTransferHistoryQuery.data?.records ?? [] : []),
    [counterTransferHistoryQuery.data?.records, variant],
  );
  const counterTransferHistoryShiftCounts = useMemo(() => {
    const counts: Record<CounterTransferShiftFilter, number> = {
      ALL: counterTransferHistoryAllDayRows.length,
      AFTERNOON: 0,
      MORNING: 0,
      NIGHT: 0,
    };
    const timeZone = operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo";

    for (const record of counterTransferHistoryAllDayRows) {
      counts[getCounterTransferShiftForRecord(record, timeZone)] += 1;
    }

    return counts;
  }, [counterTransferHistoryAllDayRows, operationsBootstrapQuery.data?.branch.timezone]);
  const counterTransferHistoryRows = useMemo(() => {
    if (counterTransferHistoryShiftFilter === "ALL") {
      return counterTransferHistoryAllDayRows;
    }

    const timeZone = operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo";
    return counterTransferHistoryAllDayRows.filter(
      (record) =>
        getCounterTransferShiftForRecord(record, timeZone) === counterTransferHistoryShiftFilter,
    );
  }, [
    counterTransferHistoryAllDayRows,
    counterTransferHistoryShiftFilter,
    operationsBootstrapQuery.data?.branch.timezone,
  ]);
  const wasteHistoryRecords = useMemo(() => {
    const records = buildWasteHistoryRecords(
      wasteHistoryQuery.data,
      operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
    );
    const normalizedSearch = wasteHistorySearchText.trim().toLowerCase();

    if (normalizedSearch.length === 0) {
      return records;
    }

    return records.filter((record) =>
      [record.folio, record.title, record.subtitle]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLowerCase().includes(normalizedSearch)),
    );
  }, [
    operationsBootstrapQuery.data?.branch.timezone,
    wasteHistoryQuery.data,
    wasteHistorySearchText,
  ]);

  useEffect(() => {
    if (
      variant === "waste" &&
      isWasteTraceabilityReady &&
      selectionErrorMessage === WASTE_TRACEABILITY_BLOCK_MESSAGE
    ) {
      setSelectionErrorMessage(null);
    }
  }, [isWasteTraceabilityReady, selectionErrorMessage, variant]);

  useEffect(() => {
    if (variant === "waste" && !isWasteHighImpact && isWasteHighImpactAcknowledged) {
      setIsWasteHighImpactAcknowledged(false);
    }
  }, [isWasteHighImpact, isWasteHighImpactAcknowledged, variant]);

  useEffect(() => {
    if (activeGridKey === null) {
      lastGridFocusKeyRef.current = null;
      return;
    }

    if (lastGridFocusKeyRef.current === activeGridKey) {
      return;
    }

    if (draftState.controlState === CONTROL_STATE_CLASS_SELECTION && sortedClasses.length > 0) {
      lastGridFocusKeyRef.current = activeGridKey;
      focusClassIndex(0);
      return;
    }

    if (
      draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION &&
      sortedProducts.length > 0
    ) {
      lastGridFocusKeyRef.current = activeGridKey;
      focusProductIndex(0);
    }
  }, [
    activeGridKey,
    draftState.controlState,
    focusClassIndex,
    focusProductIndex,
    sortedClasses.length,
    sortedProducts.length,
  ]);

  useEffect(() => {
    if (variant !== "counterTransfer" || counterTransferCenterView !== "history") {
      return;
    }

    if (counterTransferHistoryRows.length === 0) {
      if (selectedHistoryDocumentId !== null) {
        setSelectedHistoryDocumentId(null);
      }
      return;
    }

    const selectedRecordIsVisible = counterTransferHistoryRows.some(
      (record) => record.id === selectedHistoryDocumentId,
    );
    if (!selectedRecordIsVisible) {
      setSelectedHistoryDocumentId(counterTransferHistoryRows[0]?.id ?? null);
    }
  }, [
    counterTransferCenterView,
    counterTransferHistoryRows,
    selectedHistoryDocumentId,
    variant,
  ]);

  useEffect(() => {
    if (variant !== "waste" || wasteCenterView !== "history") {
      return;
    }

    if (selectedHistoryDocumentId !== null) {
      return;
    }

    const firstRecord = wasteHistoryQuery.data?.records[0];
    if (firstRecord) {
      setSelectedHistoryDocumentId(firstRecord.id);
    }
  }, [
    selectedHistoryDocumentId,
    variant,
    wasteCenterView,
    wasteHistoryQuery.data?.records,
  ]);

  const commitMutation = useMutation({
    mutationFn: async () => {
      if (accessToken === null || operationsBootstrapQuery.data === undefined) {
        throw new Error("Se requiere autenticacion y contexto de estacion.");
      }

      const lines = buildOperationCommitLines(draftState.lines);
      if (variant === "counterTransfer") {
        const payload: CounterTransferCommitRequest = {
          workstation_code: operationsBootstrapQuery.data.workstation.code,
          lines,
          notes: null,
        };
        return commitCounterTransfer(accessToken, payload);
      }

      const payload: WasteCommitRequest = {
        high_impact_acknowledged: wasteRequiresHighImpactAcknowledgement
          ? isWasteHighImpactAcknowledged
          : false,
        workstation_code: operationsBootstrapQuery.data.workstation.code,
        source_bucket_code: sourceBucketCode,
        reason_code: reasonCode,
        lines,
        notes: notes.trim().length > 0 ? notes.trim() : null,
      };
      return commitWasteRecord(accessToken, payload);
    },
    onSuccess: (document) => {
      const wasteAlertRequested = variant === "waste" && isWasteHighImpact;
      setLastCommittedDocument(variant === "waste" ? document : null);
      setLastWasteHighImpactAlertRequested(wasteAlertRequested);
      setSelectionErrorMessage(null);
      setCommitErrorMessage(null);
      setDraftState(createInitialOperationDraftState());
      setIsWasteHighImpactAcknowledged(false);
      setIsWasteConfirmDialogOpen(false);
      setIsCounterTransferConfirmDialogOpen(false);
      if (variant === "counterTransfer") {
        setCounterTransferCenterView("counterAvailability");
        setSelectedHistoryDocumentId(document.id);
        void queryClient.invalidateQueries({
          queryKey: ["operation-history", appEnv.VITE_POS_WORKSTATION_CODE, "COUNTER_TRANSFER"],
        });
        void queryClient.invalidateQueries({
          queryKey: operationDocumentQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, document.id),
        });
        void queryClient.invalidateQueries({
          queryKey: cashCloseReconciliationQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        });
        void counterAvailabilityQuery.refetch();
      }
      if (variant === "counterTransfer") {
        showSuccess(`Traspaso registrado. Folio ${document.folio}.`);
      } else {
        showSuccess(
          wasteAlertRequested
            ? `Merma registrada. Folio ${document.folio}. Se preparo alerta para backoffice.`
            : `Merma registrada. Folio ${document.folio}.`,
        );
      }
      if (variant === "waste") {
        setSourceBucketCode("");
        setReasonCode("");
        setNotes("");
        setWasteCenterView("capture");
        setSelectedHistoryDocumentId(document.id);
        setWasteHistorySearchText("");
        void queryClient.invalidateQueries({
          queryKey: operationHistoryQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, "WASTE_RECORD", {
            createdByUserId: wasteHistoryUserId !== "ALL" ? wasteHistoryUserId : undefined,
            productId: wasteHistoryProductId !== "ALL" ? wasteHistoryProductId : undefined,
            reasonCode: wasteHistoryReasonCode !== "ALL" ? wasteHistoryReasonCode : undefined,
            scope: wasteHistoryScope,
          }),
        });
        void queryClient.invalidateQueries({
          queryKey: operationDocumentQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, document.id),
        });
        void queryClient.invalidateQueries({
          queryKey: cashCloseReconciliationQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        });
      }
    },
    onError: (error) => {
      const message = toOperationalErrorMessage(
        error,
        variant === "waste"
          ? "No fue posible registrar la merma."
          : "No fue posible registrar el traspaso.",
      );
      setCommitErrorMessage(message);
      setIsWasteConfirmDialogOpen(false);
      setIsCounterTransferConfirmDialogOpen(false);
      showError(message);
    },
  });
  const documentState = getOperationDocumentState({
    hasCommittedDocument: lastCommittedDocument !== null,
    isCaptureInProgress: draftState.controlState !== CONTROL_STATE_CLASS_SELECTION,
    isCommitPending: commitMutation.isPending,
    lineCount: draftState.lines.length,
  });
  const wasteDocumentState =
    variant === "waste"
      ? getWasteDocumentUiState({
          hasCommittedDocument: lastCommittedDocument !== null,
          hasCommitError: commitErrorMessage !== null,
          hasInvalidQuantity: hasInvalidLineQuantity,
          hasOrigin: hasWasteOrigin,
          hasReason: hasWasteReason,
          isCaptureInProgress: draftState.controlState !== CONTROL_STATE_CLASS_SELECTION,
          isCommitPending: commitMutation.isPending,
          lineCount: draftState.lines.length,
          totalUnitsMilli: wasteTotalUnitsMilli,
        })
      : "READY_TO_CAPTURE";
  const counterTransferDraftLines = useMemo<OperationLineSummaryItem[]>(
    () =>
      draftState.lines.map((line) => ({
        key: line.key,
        quantityText: line.quantityText,
        title: line.productName,
      })),
    [draftState.lines],
  );
  const selectedCounterTransferHistoryDocument =
    variant === "counterTransfer" && counterTransferCenterView === "history"
      ? selectedHistoryDocumentQuery.data ?? null
      : null;
  const selectedWasteHistoryDocument =
    variant === "waste" && wasteCenterView === "history"
      ? selectedHistoryDocumentQuery.data ?? null
      : null;
  const counterTransferHistoryColumns = useMemo<
    PosRecordColumn<OperationHistoryResponse["records"][number]>[]
  >(
    () => [
      {
        header: "Folio",
        key: "folio",
        renderCell: (record) => (
          <span className="font-semibold text-slate-950">{record.folio}</span>
        ),
        width: "8rem",
      },
      {
        header: "Confirmado",
        key: "committed-at",
        renderCell: (record) => (
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-900">
              {record.committed_at_utc
                ? formatCompactLocalDateTime(
                    record.committed_at_utc,
                    operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
                  )
                : formatCompactLocalDateTime(
                    record.created_at_utc,
                    operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
                  )}
            </p>
            <p className="mt-1 text-xs font-medium text-slate-500">{record.workstation_name}</p>
          </div>
        ),
        width: "13rem",
      },
      {
        header: "Turno",
        key: "shift",
        renderCell: (record) => (
          <span className="pos-chip" data-tone="muted">
            {getCounterTransferShiftLabel(
              getCounterTransferShiftForRecord(
                record,
                operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
              ),
            )}
          </span>
        ),
        width: "8rem",
      },
      {
        header: "Operador",
        key: "operator",
        renderCell: (record) => (
          <div className="min-w-0">
            <p className="truncate font-medium text-slate-900">{record.created_by_user_full_name}</p>
            <p className="mt-1 truncate text-xs font-medium text-slate-500">{record.workstation_name}</p>
          </div>
        ),
        width: "14rem",
      },
    ],
    [operationsBootstrapQuery.data?.branch.timezone],
  );
  const counterTransferCurrentCounterLines = useMemo<OperationLineSummaryItem[]>(
    () =>
      availableCounterProducts.map((product) => ({
        key: product.product_id,
        quantityText: formatOperationQuantity(getCounterAvailableQuantity(product)),
        title: product.product_name,
      })),
    [availableCounterProducts],
  );

  useEffect(() => {
    if (editingCounterTransferDraftLineKey === null) {
      return;
    }

    const target = counterTransferDraftQuantityInputRef.current;
    target?.focus();
    target?.select();
  }, [editingCounterTransferDraftLineKey]);

  useEffect(() => {
    if (
      editingCounterTransferDraftLineKey !== null &&
      !draftState.lines.some((line) => line.key === editingCounterTransferDraftLineKey)
    ) {
      setEditingCounterTransferDraftLineKey(null);
      setEditingCounterTransferQuantityText("");
    }
  }, [draftState.lines, editingCounterTransferDraftLineKey]);

  const beginCounterTransferInlineEdit = useCallback((lineKey: string, quantityText: string) => {
    setSelectedCounterTransferDraftLineKey(lineKey);
    setEditingCounterTransferDraftLineKey(lineKey);
    setEditingCounterTransferQuantityText(quantityText);
  }, []);

  const cancelCounterTransferInlineEdit = useCallback(() => {
    setEditingCounterTransferDraftLineKey(null);
    setEditingCounterTransferQuantityText("");
  }, []);

  const commitCounterTransferInlineEdit = useCallback(() => {
    if (editingCounterTransferDraftLineKey === null) {
      return;
    }

    const normalizedQuantityText = sanitizeQuantityInput(editingCounterTransferQuantityText);
    const quantityMilliUnits = parseQuantityToMilliUnits(normalizedQuantityText);
    if (quantityMilliUnits === null || quantityMilliUnits <= 0) {
      showWarning("Captura una cantidad valida antes de guardar.");
      return;
    }

    setLastCommittedDocument(null);
    setDraftState((state) => ({
      ...state,
      lines: state.lines.map((currentLine) =>
        currentLine.key === editingCounterTransferDraftLineKey
          ? updateOperationLineQuantity(currentLine, quantityMilliUnits)
          : currentLine,
      ),
    }));
    setEditingCounterTransferDraftLineKey(null);
    setEditingCounterTransferQuantityText("");
  }, [editingCounterTransferDraftLineKey, editingCounterTransferQuantityText, showWarning]);

  function handleAddLine() {
    if (variant === "waste" && !isWasteTraceabilityReady) {
      setSelectionErrorMessage(WASTE_TRACEABILITY_BLOCK_MESSAGE);
      return;
    }

    try {
      setDraftState((state) => addPendingSelectionLine(state));
      setSelectionErrorMessage(null);
      setLastCommittedDocument(null);
    } catch (error) {
      setSelectionErrorMessage(
        toOperationalErrorMessage(
          error,
          "Confirma el producto exacto y la cantidad antes de agregar la linea.",
        ),
      );
    }
  }

  function handleCounterTransferScannerSubmit() {
    const scannedCode = parseProductScannerValue(scannerText);
    if (scannedCode === null) {
      setSelectionErrorMessage("No se pudo interpretar el codigo escaneado.");
      return;
    }

    setSelectionErrorMessage(null);
    setScannerText("");
    setPendingScannerCode(scannedCode);
    setDraftState((state) => ({
      ...state,
      searchText: scannedCode,
    }));
  }

  const runCommit = useCallback(() => {
    commitMutation.reset();
    setCommitErrorMessage(null);
    void commitMutation.mutateAsync().catch(() => undefined);
  }, [commitMutation]);

  useEffect(() => {
    function handleKeyboard(event: KeyboardEvent) {
      if (
        variant === "counterTransfer" &&
        isCounterTransferConfirmDialogOpen &&
        event.ctrlKey &&
        event.key === "Enter" &&
        !commitMutation.isPending
      ) {
        event.preventDefault();
        runCommit();
        return;
      }

      if (
        variant === "counterTransfer" &&
        !isCounterTransferConfirmDialogOpen &&
        event.ctrlKey &&
        event.key.toLowerCase() === "h"
      ) {
        event.preventDefault();
        setCounterTransferHistoryScope("TODAY");
        setCounterTransferHistoryUserId("ALL");
        setCounterTransferHistoryShiftFilter("ALL");
        setSelectedHistoryDocumentId(null);
        setCounterTransferCenterView("history");
        void counterAvailabilityQuery.refetch();
        return;
      }

      if (!isEditableTarget(event.target)) {
        if ((event.ctrlKey && event.key.toLowerCase() === "f") || event.key === "/") {
          if (
            draftState.controlState !== CONTROL_STATE_QUANTITY_CAPTURE &&
            !(variant === "waste" && !isWasteTraceabilityReady)
          ) {
            event.preventDefault();
            searchInputRef.current?.focus();
            searchInputRef.current?.select();
          }
          return;
        }
      }

      if (event.key === "Escape") {
        if (variant === "counterTransfer" && isCounterTransferConfirmDialogOpen) {
          event.preventDefault();
          setIsCounterTransferConfirmDialogOpen(false);
          return;
        }

        if (
          variant === "counterTransfer" &&
          (counterTransferCenterView === "counterAvailability" ||
            counterTransferCenterView === "history")
        ) {
          event.preventDefault();
          setCounterTransferCenterView("capture");
          return;
        }

        if (variant === "waste" && wasteCenterView === "history") {
          event.preventDefault();
          setWasteCenterView("capture");
          return;
        }

        if (
          draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ||
          draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE
        ) {
          event.preventDefault();
          setDraftState((state) => goBackFromOperationalState(state));
          return;
        }

        if (draftState.searchText.trim().length > 0) {
          event.preventDefault();
          setDraftState((state) => ({
            ...state,
            searchText: "",
          }));
        }

        return;
      }

      if (isEditableTarget(event.target)) {
        return;
      }

      const shortcutIndex = getSelectionShortcutIndex(event.key);
      if (shortcutIndex === null) {
        return;
      }

      if (draftState.controlState === CONTROL_STATE_CLASS_SELECTION) {
        if (variant === "waste" && !isWasteTraceabilityReady) {
          return;
        }
        const productClass = sortedClasses[shortcutIndex];
        if (productClass) {
          event.preventDefault();
          setLastCommittedDocument(null);
          setDraftState((state) => selectClassForOperation(state, productClass));
        }
        return;
      }

      if (draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION) {
        if (variant === "waste" && !isWasteTraceabilityReady) {
          return;
        }
        const product = sortedProducts[shortcutIndex];
        if (product) {
          event.preventDefault();
          setLastCommittedDocument(null);
          setDraftState((state) => selectProductForOperation(state, product));
        }
      }
    }

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [
    commitMutation.isPending,
    counterAvailabilityQuery,
    draftState.controlState,
    draftState.searchText,
    counterTransferCenterView,
    isCounterTransferConfirmDialogOpen,
    isWasteTraceabilityReady,
    runCommit,
    sortedClasses,
    sortedProducts,
    variant,
    wasteCenterView,
  ]);

  const handleOpenCounterTransferHistory = useCallback(() => {
    setCounterTransferHistoryScope("TODAY");
    setCounterTransferHistoryUserId("ALL");
    setCounterTransferHistoryShiftFilter("ALL");
    setCounterTransferCenterView((current) => {
      const nextView = current === "history" ? "capture" : "history";
      if (nextView === "history") {
        setSelectedHistoryDocumentId(null);
        void counterAvailabilityQuery.refetch();
      }
      return nextView;
    });
  }, [counterAvailabilityQuery]);
  const handleCloseCounterTransferHistory = useCallback(() => {
    setCounterTransferCenterView("capture");
    setSelectedHistoryDocumentId(null);
  }, []);
  const handleCommit = useCallback(() => {
    if (variant === "waste") {
      if (wasteBlockedReason === null) {
        setIsWasteConfirmDialogOpen(true);
      }
      return;
    }

    if (draftState.lines.length === 0) {
      showWarning("Agrega al menos una linea para registrar el traspaso.");
      return;
    }

    setIsCounterTransferConfirmDialogOpen(true);
  }, [draftState.lines.length, showWarning, variant, wasteBlockedReason]);

  useEffect(() => {
    if (
      variant !== "counterTransfer" ||
      counterTransferCenterView !== "capture" ||
      isCounterTransferConfirmDialogOpen
    ) {
      return;
    }

    function handleScopedTab(event: KeyboardEvent) {
      if (event.key !== "Tab") {
        return;
      }

      const centerRegion = document.querySelector('[data-pos-shell-region="center"]');
      const rightRegion = document.querySelector('[data-pos-shell-region="right"]');
      const focusableItems = [
        ...getFocusableElements(centerRegion),
        ...getFocusableElements(rightRegion),
      ];

      if (focusableItems.length === 0) {
        return;
      }

      const activeElement = document.activeElement as HTMLElement | null;
      const currentIndex = activeElement ? focusableItems.indexOf(activeElement) : -1;
      if (currentIndex === -1) {
        return;
      }

      const isBackward = event.shiftKey;
      const isAtBoundary =
        (isBackward && currentIndex === 0) ||
        (!isBackward && currentIndex === focusableItems.length - 1);

      if (!isAtBoundary) {
        return;
      }

      event.preventDefault();
      if (isBackward) {
        focusableItems[focusableItems.length - 1]?.focus();
        return;
      }

      focusableItems[0]?.focus();
    }

    window.addEventListener("keydown", handleScopedTab, true);
    return () => window.removeEventListener("keydown", handleScopedTab, true);
  }, [counterTransferCenterView, isCounterTransferConfirmDialogOpen, variant]);

  const summaryPanel = useMemo(() => {
    const clearDraft = () => {
      if (
        draftState.lines.length > 0 &&
        !window.confirm(
          variant === "counterTransfer"
            ? "Vaciar el borrador actual del traspaso?"
            : "Vaciar el documento actual?",
        )
      ) {
        return;
      }

      setDraftState(createInitialOperationDraftState());
      setSelectionErrorMessage(null);
      setCommitErrorMessage(null);
      setLastCommittedDocument(null);
      setLastWasteHighImpactAlertRequested(false);
      setSelectedHistoryDocumentId(null);
      if (variant === "counterTransfer") {
        setCounterTransferCenterView("capture");
      }
      if (variant === "waste") {
        setIsWasteHighImpactAcknowledged(false);
        setSourceBucketCode("");
        setReasonCode("");
        setNotes("");
        setWasteCenterView("capture");
        setWasteHistorySearchText("");
      }
    };
    const counterTransferDocumentAvailability =
      getDocumentActionAvailability("counterTransferReceipt");
    const wasteDocumentAvailability = getDocumentActionAvailability("wasteDocument");

    if (variant === "counterTransfer") {
      if (lastCommittedDocument !== null) {
        const resultActions: OperationDocumentAction[] = [
          {
            availabilityNote: counterTransferDocumentAvailability.print.unavailableReason,
            disabled: !counterTransferDocumentAvailability.print.isAvailable,
            kind: "print",
            key: "print",
            label: counterTransferDocumentAvailability.print.label,
            leadingIcon: <PrinterIcon className="h-4 w-4" />,
            onSelect: () => undefined,
            variant: "neutral",
          },
          {
            key: "history",
            label: "Ver historial",
            leadingIcon: <RotateCcwIcon className="h-4 w-4" />,
            onSelect: () => {
              setSelectedHistoryDocumentId(lastCommittedDocument.id);
              setCounterTransferCenterView("history");
            },
            variant: "neutral",
          },
          {
            key: "new-transfer",
            label: "Nuevo traspaso",
            leadingIcon: <ClipboardIcon className="h-4 w-4" />,
            onSelect: () => {
              setLastCommittedDocument(null);
              setSelectedHistoryDocumentId(null);
              setCounterTransferCenterView("capture");
            },
            variant: "primary",
          },
        ];

        return (
          <OperationDocumentResult
            actions={resultActions}
            auditSummary={lastCommittedDocument.audit_summary}
            context={{
              branchName: lastCommittedDocument.source_branch_name,
              userName: lastCommittedDocument.created_by_user_full_name,
              workstationName: lastCommittedDocument.workstation_name,
            }}
            description="El traspaso ya quedo confirmado. Puedes continuar con una nueva captura o revisar el historial."
            kind="counterTransfer"
            metrics={[
              {
                key: "line-count",
                label: "Lineas",
                value: String(lastCommittedDocument.lines.length),
              },
              {
                key: "total-units",
                label: "Unidades",
                tone: "financial",
                value: formatQuantityFromMilliUnits(
                  lastCommittedDocument.lines.reduce(
                    (total, line) => total + Number(line.quantity) * 1000,
                    0,
                  ),
                ),
              },
            ]}
            referenceValue={lastCommittedDocument.folio}
            timeZone={operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo"}
            timestamps={{
              committedAtValue: lastCommittedDocument.committed_at_utc
                ? formatCompactLocalDateTime(
                    lastCommittedDocument.committed_at_utc,
                    operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
                  )
                : null,
              createdAtValue: formatCompactLocalDateTime(
                lastCommittedDocument.created_at_utc,
                operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
              ),
            }}
          />
        );
      }

      if (counterTransferCenterView === "history") {
        if (selectedHistoryDocumentQuery.error) {
          return (
            <PosSummaryPanel
              description="No fue posible consultar el traspaso seleccionado."
              stateLabel="Error"
              stateTone="error"
              title="Historial de traspasos"
            >
              <div className="grid h-full place-items-center px-3 text-center">
                <p className="text-sm leading-6 text-slate-600">
                  Reintenta desde el listado para recuperar el detalle operativo.
                </p>
              </div>
            </PosSummaryPanel>
          );
        }

        if (selectedCounterTransferHistoryDocument !== null) {
          return (
            <PosSummaryPanel
              title={`Traspaso ${selectedCounterTransferHistoryDocument.folio}`}
              footer={
                <Button
                  className={cn(
                    "h-10 w-full bg-[var(--pos-primary-soft)] text-[var(--pos-primary)] hover:bg-[var(--pos-primary-soft)]/80",
                    posOutlineButtonClass,
                  )}
                  onClick={handleCloseCounterTransferHistory}
                  type="button"
                  variant="outline"
                >
                  Regresar
                </Button>
              }
            >
              <div className="grid h-full min-h-0 auto-rows-max content-start gap-1.5">
                <CounterMovementSummaryCard
                  destinationLabel={
                    getCounterTransferBucketLabel(
                      selectedCounterTransferHistoryDocument.destination_bucket_code,
                    )
                  }
                  sourceLabel={
                    getCounterTransferBucketLabel(
                      selectedCounterTransferHistoryDocument.source_bucket_code,
                    )
                  }
                />
                <CompactOperationLineSection
                  badgeLabel="Aprox. hasta cierre"
                  emptyMessage="Aun no hay productos confirmados en mostrador."
                  lines={counterTransferCurrentCounterLines}
                  title="Mostrador actual"
                />
              </div>
            </PosSummaryPanel>
          );
        }

        return (
          <PosSummaryPanel
            title="Historial de traspasos"
            footer={
              <Button
                className={cn(
                  "h-10 w-full bg-[var(--pos-primary-soft)] text-[var(--pos-primary)] hover:bg-[var(--pos-primary-soft)]/80",
                  posOutlineButtonClass,
                )}
                onClick={handleCloseCounterTransferHistory}
                type="button"
                variant="outline"
              >
                Regresar
              </Button>
            }
          >
            <div className="grid h-full min-h-0 auto-rows-max content-start gap-1.5">
              <CounterMovementSummaryCard />
              <CompactOperationLineSection
                badgeLabel="Aprox. hasta cierre"
                emptyMessage="Aun no hay productos confirmados en mostrador."
                lines={counterTransferCurrentCounterLines}
                title="Mostrador actual"
              />
            </div>
          </PosSummaryPanel>
        );
      }

      return (
        <PosSummaryPanel
          action={
            <PosStatusBadge
              className="translate-y-3 scale-[0.8]"
              status={getOperationStateBadgeTone(documentState)}
            >
              {getOperationStateLabel(documentState)}
            </PosStatusBadge>
          }
          footer={
            <div className="grid gap-2">
              <Button
                className={cn("h-10", posOutlineButtonClass)}
                onClick={handleOpenCounterTransferHistory}
                type="button"
                variant="outline"
              >
                Ver historial
              </Button>
              <Button
                className={cn("h-11", posPrimaryButtonClass)}
                disabled={commitMutation.isPending}
                onClick={handleCommit}
                type="button"
              >
                {commitMutation.isPending ? "Registrando..." : config.commitButtonLabel}
              </Button>
            </div>
          }
          title={
            <span className="text-[1.35rem] font-semibold leading-tight text-slate-950">
              {getCounterTransferPanelTitle(documentState)}
            </span>
          }
        >
          <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3 pt-2">
            <CounterMovementSummaryCard />

            <div className="grid min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-2">
              <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white">
                {draftState.lines.length === 0 ? (
                  <div className="flex h-full min-h-[8.5rem] items-center justify-center px-4 py-4 text-center text-sm leading-6 text-slate-600">
                    Aun no hay lineas. Agrega productos para surtir mostrador.
                  </div>
                ) : (
                  <div className="h-full overflow-y-auto">
                    {draftState.lines.map((line) => (
                      <OperationLineRow
                        editingQuantityText={
                          editingCounterTransferDraftLineKey === line.key
                            ? editingCounterTransferQuantityText
                            : line.quantityText
                        }
                        inputRef={
                          editingCounterTransferDraftLineKey === line.key
                            ? counterTransferDraftQuantityInputRef
                            : null
                        }
                        isEditing={editingCounterTransferDraftLineKey === line.key}
                        key={line.key}
                        isSelected={selectedCounterTransferDraftLineKey === line.key}
                        name={line.productName}
                        onBeginEdit={() =>
                          beginCounterTransferInlineEdit(line.key, line.quantityText)
                        }
                        onCancelEdit={cancelCounterTransferInlineEdit}
                        onCommitEdit={commitCounterTransferInlineEdit}
                        onDecrement={() => {
                          if (editingCounterTransferDraftLineKey === line.key) {
                            setEditingCounterTransferDraftLineKey(null);
                            setEditingCounterTransferQuantityText("");
                          }
                          setLastCommittedDocument(null);
                          setDraftState((state) => ({
                            ...state,
                            lines: state.lines.map((currentLine) =>
                              currentLine.key === line.key
                                ? updateOperationLineQuantity(
                                    currentLine,
                                    Math.max(currentLine.quantityMilliUnits - 1000, 1000),
                                  )
                                : currentLine,
                            ),
                          }));
                        }}
                        onEditingQuantityChange={(value) =>
                          setEditingCounterTransferQuantityText(sanitizeQuantityInput(value))
                        }
                        onIncrement={() => {
                          if (editingCounterTransferDraftLineKey === line.key) {
                            setEditingCounterTransferDraftLineKey(null);
                            setEditingCounterTransferQuantityText("");
                          }
                          setLastCommittedDocument(null);
                          setDraftState((state) => ({
                            ...state,
                            lines: state.lines.map((currentLine) =>
                              currentLine.key === line.key
                                ? updateOperationLineQuantity(
                                    currentLine,
                                    currentLine.quantityMilliUnits + 1000,
                                  )
                                : currentLine,
                            ),
                          }));
                        }}
                        onRemove={() => {
                          if (editingCounterTransferDraftLineKey === line.key) {
                            setEditingCounterTransferDraftLineKey(null);
                            setEditingCounterTransferQuantityText("");
                          }
                          setLastCommittedDocument(null);
                          setDraftState((state) => ({
                            ...state,
                            lines: removeOperationLine(state.lines, line.key),
                          }));
                        }}
                        onSelect={() => setSelectedCounterTransferDraftLineKey(line.key)}
                        quantity={line.quantityText}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </PosSummaryPanel>
      );
    }

    if (lastCommittedDocument !== null) {
      const resultActions: OperationDocumentAction[] = [
        {
          availabilityNote: wasteDocumentAvailability.print.unavailableReason,
          disabled: !wasteDocumentAvailability.print.isAvailable,
          kind: "print",
          key: "print-waste",
          label: wasteDocumentAvailability.print.label,
          leadingIcon: <PrinterIcon className="h-4 w-4" />,
          onSelect: () => undefined,
          variant: "neutral",
        },
        {
          key: "waste-history",
          label: "Ver historial",
          leadingIcon: <RotateCcwIcon className="h-4 w-4" />,
          onSelect: () => {
            setSelectedHistoryDocumentId(lastCommittedDocument.id);
            setWasteCenterView("history");
          },
          variant: "neutral",
        },
          {
            key: "new-waste",
            label: "Nueva merma",
            leadingIcon: <ClipboardIcon className="h-4 w-4" />,
            onSelect: () => {
              setLastCommittedDocument(null);
              setLastWasteHighImpactAlertRequested(false);
              setSelectedHistoryDocumentId(null);
              setWasteCenterView("capture");
            },
            variant: "primary",
          },
      ];

      return (
        <OperationDocumentResult
          actions={resultActions}
          auditSummary={lastCommittedDocument.audit_summary}
          context={{
            branchName: lastCommittedDocument.source_branch_name,
            userName: lastCommittedDocument.created_by_user_full_name,
            workstationName: lastCommittedDocument.workstation_name,
          }}
          description={
            lastWasteHighImpactAlertRequested
              ? "La merma quedo registrada y se preparo una alerta para backoffice por alto impacto."
              : "La merma ya quedo registrada. Puedes revisar el historial o preparar un nuevo documento."
          }
          kind="waste"
          metrics={[
            {
              key: "line-count",
              label: "Lineas",
              value: String(lastCommittedDocument.lines.length),
            },
            {
              key: "total-units",
              label: "Unidades",
              tone: "financial",
              value: formatQuantityFromMilliUnits(
                lastCommittedDocument.lines.reduce(
                  (total, line) => total + Number(line.quantity) * 1000,
                  0,
                ),
              ),
            },
            {
              key: "origin",
              label: "Origen",
              value: getWasteSourceBucketLabel(lastCommittedDocument.source_bucket_code ?? ""),
            },
            {
              key: "reason",
              label: "Motivo",
              value: lastCommittedDocument.reason_name ?? "Pendiente",
            },
            ...(lastWasteHighImpactAlertRequested
              ? [
                  {
                    key: "high-impact-alert",
                    label: "Alerta",
                    tone: "warning" as const,
                    value: "Backoffice",
                  },
                ]
              : []),
          ]}
          referenceValue={lastCommittedDocument.folio}
          timeZone={operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo"}
          timestamps={{
            committedAtValue: lastCommittedDocument.committed_at_utc
              ? formatCompactLocalDateTime(
                  lastCommittedDocument.committed_at_utc,
                  operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
                )
              : null,
            createdAtValue: formatCompactLocalDateTime(
              lastCommittedDocument.created_at_utc,
              operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
            ),
          }}
        />
      );
    }

    if (wasteCenterView === "history") {
      if (selectedHistoryDocumentQuery.error) {
        return (
          <PosSummaryPanel
            description="No fue posible consultar la merma seleccionada."
            stateLabel="Error"
            stateTone="error"
            title="Historial de merma"
          >
            <div className="grid h-full place-items-center px-3 text-center">
              <p className="text-sm leading-6 text-slate-600">
                Reintenta desde el listado para recuperar el detalle operativo.
              </p>
            </div>
          </PosSummaryPanel>
        );
      }

      if (selectedWasteHistoryDocument !== null) {
        return (
          <OperationDocumentSummaryPanel
            actions={[
              {
                key: "back-to-waste",
                label: "Registrar merma",
                leadingIcon: <RotateCcwIcon className="h-4 w-4" />,
                onSelect: () => setWasteCenterView("capture"),
                variant: "primary",
              },
              {
                availabilityNote: wasteDocumentAvailability.print.unavailableReason,
                disabled: !wasteDocumentAvailability.print.isAvailable,
                kind: "print",
                key: "print-waste-history",
                label: wasteDocumentAvailability.print.label,
                leadingIcon: <PrinterIcon className="h-4 w-4" />,
                onSelect: () => undefined,
                variant: "neutral",
                },
              ]}
            auditSummary={selectedWasteHistoryDocument.audit_summary}
            context={{
              branchName: selectedWasteHistoryDocument.source_branch_name,
              userName: selectedWasteHistoryDocument.created_by_user_full_name,
              workstationName: selectedWasteHistoryDocument.workstation_name,
            }}
            description="Detalle de la merma seleccionada."
            kind="waste"
            lines={buildOperationDocumentSummaryLines(selectedWasteHistoryDocument.lines)}
            metrics={[
              {
                key: "origin",
                label: "Origen",
                value: getWasteSourceBucketLabel(selectedWasteHistoryDocument.source_bucket_code ?? ""),
              },
              {
                key: "reason",
                label: "Motivo",
                value: selectedWasteHistoryDocument.reason_name ?? "Pendiente",
              },
              {
                key: "line-count",
                label: "Lineas",
                value: String(selectedWasteHistoryDocument.lines.length),
              },
              {
                key: "total-units",
                label: "Unidades",
                tone: "financial",
                value: formatQuantityFromMilliUnits(
                  selectedWasteHistoryDocument.lines.reduce(
                    (total, line) => total + Number(line.quantity) * 1000,
                    0,
                  ),
                ),
              },
            ]}
            referenceValue={selectedWasteHistoryDocument.folio}
            stateLabel={getOperationDocumentStatusLabel(selectedWasteHistoryDocument.status)}
            stateTone={getOperationDocumentStatusTone(selectedWasteHistoryDocument.status)}
            timeZone={operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo"}
            timestamps={{
              committedAtValue: selectedWasteHistoryDocument.committed_at_utc
                ? formatCompactLocalDateTime(
                    selectedWasteHistoryDocument.committed_at_utc,
                    operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
                  )
                : null,
              createdAtValue: formatCompactLocalDateTime(
                selectedWasteHistoryDocument.created_at_utc,
                operationsBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
              ),
            }}
            title="Merma seleccionada"
          />
        );
      }

      return (
        <PosSummaryPanel
          description="Selecciona una merma del historial para revisar su detalle."
          stateLabel={
            wasteHistoryQuery.isPending || selectedHistoryDocumentQuery.isPending
              ? "Consultando"
              : "Sin seleccion"
          }
          stateTone={
            wasteHistoryQuery.isPending || selectedHistoryDocumentQuery.isPending
              ? "pending"
              : "draft"
          }
          title="Historial de merma"
        >
          <div className="flex h-full items-center justify-center px-3 text-center">
            <p className="text-sm leading-6 text-slate-600">
              Elige un registro del historial para ver folio, motivo y lineas confirmadas.
            </p>
          </div>
        </PosSummaryPanel>
      );
    }

    return (
      <PosSummaryPanel
        description="Resumen operativo de la merma en construccion."
        stateLabel={getWasteUiStateLabel(wasteDocumentState)}
        stateTone={
          wasteDocumentState === "REGISTERED_SUCCESS"
            ? "success"
            : wasteDocumentState === "READY_TO_REGISTER"
              ? "pending"
              : wasteBlockedMessages.length > 0
                ? "blocked"
                : "draft"
        }
        title={getWastePanelTitle(wasteDocumentState)}
      >
        <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3">
          <div className="grid gap-3">
            {commitErrorMessage ? <InlineNotice tone="error">{commitErrorMessage}</InlineNotice> : null}
            <div className="grid gap-2 sm:grid-cols-2">
              <PosCard className="px-3 py-2.5">
                <p className="pos-label-text">Origen</p>
                <p className="mt-1 text-sm font-semibold text-slate-950">
                  {hasWasteOrigin ? getWasteSourceBucketLabel(sourceBucketCode) : "Pendiente"}
                </p>
              </PosCard>
              <PosCard className="px-3 py-2.5">
                <p className="pos-label-text">Motivo</p>
                <p className="mt-1 text-sm font-semibold text-slate-950">
                  {hasWasteReason
                    ? getWasteReasonName(operationsBootstrapQuery.data?.waste_reasons ?? [], reasonCode)
                    : "Pendiente"}
                </p>
              </PosCard>
              <PosCard className="px-3 py-2.5">
                <p className="pos-label-text">Lineas</p>
                <p className="mt-1 text-base font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                  {getOperationLineCount(draftState.lines)}
                </p>
              </PosCard>
              <PosCard className="px-3 py-2.5" tone="warning">
                <p className="pos-label-text">Unidades</p>
                <p className="mt-1 text-base font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                  {totalUnitsText}
                </p>
              </PosCard>
              {isWasteHighImpact ? (
                <PosCard
                  className="px-3 py-2.5"
                  tone={isWasteHighImpactAcknowledged ? "warning" : "danger"}
                >
                  <p className="pos-label-text">Control</p>
                  <p className="mt-1 text-sm font-semibold text-slate-950">
                    {isWasteHighImpactAcknowledged
                      ? "Alto impacto confirmado"
                      : "Falta confirmar alto impacto"}
                  </p>
                </PosCard>
              ) : null}
            </div>
            <PosCard className="px-3 py-2.5">
              <p className="pos-label-text">Notas y evidencia</p>
              <p className="mt-1 text-sm text-slate-700">
                {notes.trim().length > 0 ? notes.trim() : "Sin notas operativas registradas."}
              </p>
            </PosCard>
          </div>

          <div className="grid min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3">
            <PosBlockerPanel
              blockers={wasteBlockedMessages.map((message) => ({
                key: message,
                message,
                tone: "warning" as const,
              }))}
            />
            <OperationLineSummary
              emptyMessage="Agrega productos para construir el documento."
              lines={draftState.lines.map((line) => ({
                key: line.key,
                quantityText: line.quantityText,
                secondaryText: line.productClassCode,
                title: line.productName,
              }))}
              title="Lineas del documento"
            />
          </div>
        </div>
        <div className="grid gap-2">
          <div className="grid grid-cols-2 gap-2">
            <PosButton onClick={() => setWasteCenterView("history")} variant="neutral">
              Ver historial
            </PosButton>
            <PosButton
              disabled={draftState.lines.length === 0 || commitMutation.isPending}
              onClick={clearDraft}
              variant="neutral"
            >
              Vaciar documento
            </PosButton>
          </div>
          <PosButton
            disabled={wasteBlockedReason !== null || commitMutation.isPending}
            onClick={handleCommit}
            variant="primary"
          >
            {commitMutation.isPending ? "Registrando..." : config.commitButtonLabel}
          </PosButton>
        </div>
      </PosSummaryPanel>
    );
  }, [
    commitErrorMessage,
    commitMutation.isPending,
    config.commitButtonLabel,
    counterTransferCenterView,
    counterTransferCurrentCounterLines,
    beginCounterTransferInlineEdit,
    cancelCounterTransferInlineEdit,
    commitCounterTransferInlineEdit,
    documentState,
    draftState.lines,
    editingCounterTransferDraftLineKey,
    editingCounterTransferQuantityText,
    handleCommit,
    handleCloseCounterTransferHistory,
    handleOpenCounterTransferHistory,
    hasWasteOrigin,
    hasWasteReason,
    isWasteHighImpact,
    isWasteHighImpactAcknowledged,
    lastCommittedDocument,
    lastWasteHighImpactAlertRequested,
    notes,
    operationsBootstrapQuery.data?.branch.timezone,
    operationsBootstrapQuery.data?.waste_reasons,
    reasonCode,
    selectedCounterTransferDraftLineKey,
    selectedCounterTransferHistoryDocument,
    selectedWasteHistoryDocument,
    selectedHistoryDocumentQuery.error,
    selectedHistoryDocumentQuery.isPending,
    sourceBucketCode,
    totalUnitsText,
    variant,
    wasteCenterView,
    wasteBlockedMessages,
    wasteBlockedReason,
    wasteDocumentState,
    wasteHistoryQuery.isPending,
  ]);
  useAppShellRightPanel(summaryPanel);

  if (operationsBootstrapQuery.isPending || currentCashSessionQuery.isPending) {
    return (
      <OperationalStatus
        description="Consultando el contexto operativo de la estacion."
        title={`Cargando ${config.title}`}
      />
    );
  }

  if (operationsBootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => operationsBootstrapQuery.refetch()}>Reintentar</Button>}
        description={toOperationalErrorMessage(
          operationsBootstrapQuery.error,
          "Confirma la configuracion de la estacion y los datos operativos iniciales.",
        )}
        title={`${config.title} no esta disponible`}
      />
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => currentCashSessionQuery.refetch()}>Reintentar</Button>}
        description={toOperationalErrorMessage(
          currentCashSessionQuery.error,
          "Confirma la conexion con la API y el estado actual de la caja.",
        )}
        title="No fue posible consultar la caja"
      />
    );
  }

  if (!currentCashSessionQuery.data) {
    return <Navigate to="/cash-session/open" />;
  }

  const flowActiveStepKey =
    isCounterTransferAvailabilityView
      ? "summary"
      : variant === "counterTransfer" && counterTransferCenterView === "history"
        ? "summary"
      : variant === "waste" && wasteCenterView === "history"
        ? "summary"
      : variant === "waste" && !isWasteTraceabilityReady
      ? "traceability"
      : draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
        ? "product"
        : draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE
          ? "quantity"
          : draftState.lines.length > 0
            ? "summary"
            : "class";
  const showSearch =
    !isCounterTransferAvailabilityView &&
    !(variant === "counterTransfer" && counterTransferCenterView === "history") &&
    !(variant === "waste" && wasteCenterView === "history") &&
    draftState.controlState !== CONTROL_STATE_QUANTITY_CAPTURE;
  const showStageBackAction =
    variant === "counterTransfer" &&
    (draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ||
      draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE);
  const isWasteSearchDisabled = variant === "waste" && !isWasteTraceabilityReady;
  const quantitySelection =
    draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE &&
    draftState.pendingSelection !== null
      ? draftState.pendingSelection
      : null;
  const quantityProduct = quantitySelection?.product ?? null;
  const isQuantityReady =
    quantitySelection !== null && hasCapturedQuantity(quantitySelection.quantityText);
  const isWasteQuantityBlocked = variant === "waste" && !isWasteTraceabilityReady;
  const quantityPresets = ["1", "2", "3", "6", "12"];
  const quantityShortcuts = [
    { label: "Enter", value: "Agrega" },
    { label: "Esc", value: "Regresa" },
  ];
  const counterTransferLineSummary =
    variant === "counterTransfer" && draftState.lines.length > 0
      ? `${draftState.lines.length} ${draftState.lines.length === 1 ? "linea" : "lineas"} en documento`
      : null;
  const wasteOriginLabel = getWasteSourceBucketLabel(sourceBucketCode);
  const wasteReasonLabel = getWasteReasonName(
    operationsBootstrapQuery.data?.waste_reasons ?? [],
    reasonCode,
  );
  const selectedCounterTransferClass =
    variant === "counterTransfer" ? draftState.pendingSelection?.productClass ?? null : null;
  const pageHeader =
    variant === "counterTransfer" ? (
      counterTransferCenterView === "capture" && !isCounterTransferAvailabilityView ? (
        <CompactPageHeader
          secondaryChips={
            <>
              <ModuleStateChip tone="info">Empaque -&gt; Mostrador</ModuleStateChip>
              {counterTransferLineSummary ? (
                <ModuleStateChip tone="muted">{counterTransferLineSummary}</ModuleStateChip>
              ) : null}
            </>
          }
          stateChip={
            <ModuleStateChip tone={draftState.lines.length > 0 ? "primary" : "muted"}>
              {draftState.lines.length > 0 ? "En construccion" : "Documento vacio"}
            </ModuleStateChip>
          }
          title="Pasar a mostrador"
        >
          <FlowGuide
            activeStepKey={flowActiveStepKey}
            steps={[
              {
                icon: <StoreIcon className="h-3.5 w-3.5" />,
                key: "class",
                label: "Clase",
              },
              {
                icon: <PackageIcon className="h-3.5 w-3.5" />,
                key: "product",
                label: "Producto",
              },
              {
                icon: <HashIcon className="h-3.5 w-3.5" />,
                key: "quantity",
                label: "Cantidad",
              },
              {
                icon: <ClipboardIcon className="h-3.5 w-3.5" />,
                key: "summary",
                label: "Traspaso",
              },
            ]}
            variant="process"
          />
        </CompactPageHeader>
      ) : (
        <CompactPageHeader
          secondaryChips={
            <ModuleStateChip
              tone={
                counterTransferCenterView === "history"
                  ? "info"
                  : isCounterTransferAvailabilityView
                    ? "info"
                    : "primary"
              }
            >
              {counterTransferCenterView === "history"
                ? "Historial de traspasos"
                  : isCounterTransferAvailabilityView
                    ? "Mostrador actual"
                    : "Empaque -&gt; Mostrador"}
            </ModuleStateChip>
          }
          stateChip={
            counterTransferCenterView === "history" ? (
              <ModuleStateChip tone="muted">Todo el dia</ModuleStateChip>
            ) : (
              <ModuleStateChip tone={getOperationStateTone(documentState)}>
                {getOperationStateLabel(documentState)}
              </ModuleStateChip>
            )
          }
          title={counterTransferCenterView === "history" ? "Historial del mostrador" : "Pasar a mostrador"}
        />
      )
    ) : (
      <CompactPageHeader
        secondaryChips={
          <ModuleStateChip
            tone={wasteCenterView === "history" ? "info" : isWasteTraceabilityReady ? "primary" : "muted"}
          >
            {wasteCenterView === "history"
              ? "Historial de merma"
              : `${wasteOriginLabel} - ${wasteReasonLabel}`}
          </ModuleStateChip>
        }
        stateChip={
          <ModuleStateChip tone={getWasteUiStateTone(wasteDocumentState)}>
            {getWasteUiStateLabel(wasteDocumentState)}
          </ModuleStateChip>
        }
        title="Registrar merma"
      >
        <FlowGuide
          activeStepKey={flowActiveStepKey}
          steps={[
            {
              icon: <ClipboardIcon className="h-3.5 w-3.5" />,
              key: "traceability",
              label: "Trazabilidad",
            },
            {
              icon: <StoreIcon className="h-3.5 w-3.5" />,
              key: "class",
              label: "Clase",
            },
            {
              icon: <PackageIcon className="h-3.5 w-3.5" />,
              key: "product",
              label: "Producto",
            },
            {
              icon: <HashIcon className="h-3.5 w-3.5" />,
              key: "quantity",
              label: "Cantidad",
            },
            {
              icon: <PackageIcon className="h-3.5 w-3.5" />,
              key: "summary",
              label: "Resumen",
            },
          ]}
          variant="process"
        />
      </CompactPageHeader>
    );
  const stageToolbar =
    variant === "counterTransfer" ? (
      !isCounterTransferAvailabilityView && counterTransferCenterView !== "history" ? (
        <div className="grid w-full gap-3">
          <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              {showStageBackAction ? (
                <Button
                  aria-label="Regresar"
                  className={cn("h-10 px-3", posOutlineButtonClass)}
                  onClick={() => setDraftState((state) => goBackFromOperationalState(state))}
                  title="Regresar"
                  type="button"
                >
                  <ArrowLeftIcon className="h-4 w-4" />
                </Button>
              ) : null}
            </div>

            {showSearch ? (
              <div className="flex min-w-0 flex-1 justify-end">
                <SearchField
                  ariaLabel="Buscar en la etapa actual"
                  className="w-full max-w-sm"
                  inputClassName={cn("h-9 rounded-lg text-sm shadow-sm", posInputClass)}
                  inputRef={searchInputRef}
                  onChange={(value) => {
                    setPendingScannerCode(null);
                    setSelectionErrorMessage(null);
                    setDraftState((state) => ({
                      ...state,
                      searchText: value,
                    }));
                  }}
                  placeholder={
                    draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
                      ? "Filtrar producto"
                      : "Filtrar clase"
                  }
                  value={draftState.searchText}
                />
              </div>
            ) : null}
          </div>

          {showSearch ? (
            <PosScannerInput
              ariaLabel={
                draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
                  ? "Escanear codigo de producto"
                  : "Escanear codigo de producto o clase"
              }
              description="El escaner funciona como teclado y no interfiere con cantidad."
              inputRef={scannerInputRef}
              modeLabel="Escaneo de producto"
              onChange={setScannerText}
              onSubmit={handleCounterTransferScannerSubmit}
              placeholder={
                draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
                  ? "Escanear producto"
                  : "Escanear producto o clase"
              }
              submitLabel="Aplicar codigo"
              value={scannerText}
            />
          ) : null}
        </div>
      ) : undefined
    ) : undefined;

  return (
    <>
      {variant === "waste" ? (
        <OperationConfirmationDialog
          actionsTitle="Lineas a registrar"
          confirmLabel="Confirmar merma"
          context={{
            branchName: operationsBootstrapQuery.data.branch.name,
            userName: operationsBootstrapQuery.data.user.full_name,
            workstationName: operationsBootstrapQuery.data.workstation.name,
          }}
          description={
            isWasteHighImpact
              ? "Revisa origen, motivo, cantidades y evidencia antes de confirmar. Esta merma supera el umbral operativo y generara una alerta para backoffice."
              : "Revisa origen, motivo y cantidades antes de confirmar la merma. Esta accion reducira inventario disponible."
          }
          isOpen={isWasteConfirmDialogOpen}
          isPending={commitMutation.isPending}
          kind="waste"
          lines={draftState.lines.map((line) => ({
            key: line.key,
            quantityText: line.quantityText,
            secondaryText: line.productClassName,
            title: line.productName,
          }))}
          metrics={[
            {
              key: "origin",
              label: "Origen",
              value: wasteOriginLabel,
            },
            {
              key: "reason",
              label: "Motivo",
              value: wasteReasonLabel,
            },
            {
              key: "line-count",
              label: "Lineas",
              value: String(getOperationLineCount(draftState.lines)),
            },
            {
              key: "total-units",
              label: "Unidades",
              tone: "financial",
              value: totalUnitsText,
            },
            ...(isWasteHighImpact
              ? [
                  {
                    key: "high-impact",
                    label: "Control",
                    tone: "warning" as const,
                    value: "Alto impacto",
                  },
                ]
              : []),
            ...(notes.trim().length > 0
              ? [
                  {
                    key: "notes",
                    label: "Notas",
                    value: notes.trim(),
                  },
                ]
              : []),
          ]}
          onCancel={() => setIsWasteConfirmDialogOpen(false)}
          onConfirm={runCommit}
          title="Confirmar merma"
        />
      ) : null}

      {variant === "counterTransfer" ? (
        <OperationConfirmationDialog
          actionsTitle="Lineas a transferir"
          confirmLabel="Confirmar traspaso"
          context={{
            branchName: operationsBootstrapQuery.data.branch.name,
            userName: operationsBootstrapQuery.data.user.full_name,
            workstationName: operationsBootstrapQuery.data.workstation.name,
          }}
          description=""
          detailsContent={
            <div className="grid gap-3">
              <div className="flex flex-wrap items-start gap-x-5 gap-y-2">
                <div className="min-w-0">
                  <p className="pos-label-text">Sucursal</p>
                  <p
                    className="truncate text-sm font-semibold text-slate-950"
                    title={operationsBootstrapQuery.data.branch.name}
                  >
                    {operationsBootstrapQuery.data.branch.name}
                  </p>
                </div>
                <div className="min-w-0">
                  <p className="pos-label-text">Estacion</p>
                  <p
                    className="truncate text-sm font-semibold text-slate-950"
                    title={operationsBootstrapQuery.data.workstation.name}
                  >
                    {operationsBootstrapQuery.data.workstation.name}
                  </p>
                </div>
                <div className="min-w-0">
                  <p className="pos-label-text">Operador</p>
                  <p
                    className="truncate text-sm font-semibold text-slate-950"
                    title={operationsBootstrapQuery.data.user.full_name}
                  >
                    {operationsBootstrapQuery.data.user.full_name}
                  </p>
                </div>
                <ModuleStateChip tone="info">Empaque -&gt; Mostrador</ModuleStateChip>
              </div>
              <OperationLineSummary
                emptyMessage="Sin lineas para revisar."
                lines={counterTransferDraftLines}
                title="Lineas a transferir"
              />
            </div>
          }
          isOpen={isCounterTransferConfirmDialogOpen}
          isPending={commitMutation.isPending}
          kind="counterTransfer"
          lines={counterTransferDraftLines}
          metrics={[]}
          onCancel={() => setIsCounterTransferConfirmDialogOpen(false)}
          onConfirm={runCommit}
          title="Confirmar traspaso a mostrador"
        />
      ) : null}

      <PosModuleLayout
        mobileSummary={
          <section className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-surface)] px-4 py-3 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-900">{config.summaryTitle}</p>
                <p className="text-sm text-slate-600">
                  {draftState.lines.length === 0
                    ? config.emptyMessage
                    : `${totalUnitsText} unidades listas para registrar.`}
                </p>
              </div>
              <span className="pos-chip" data-tone="primary">
                {getOperationLineCount(draftState.lines)} lineas
              </span>
            </div>
          </section>
        }
      >
        <CentralWorkspaceSheet
          className="lg:h-full"
          contentClassName="min-h-0 overflow-y-auto px-3 pb-3 pt-2"
          header={pageHeader}
          toolbar={stageToolbar}
          toolbarClassName="py-2"
        >
          {variant === "waste" ? (
            <div className="grid gap-3 border-b border-[var(--pos-shell-border)] pb-3">
              <WasteTraceabilitySection
                controlState={draftState.controlState}
                getOriginItemProps={getWasteOriginItemProps}
                getReasonItemProps={getWasteReasonItemProps}
                isCommitPending={commitMutation.isPending}
                isSearchDisabled={isWasteSearchDisabled}
                originActiveIndex={wasteOriginActiveIndex}
                onGoBack={() => setDraftState((state) => goBackFromOperationalState(state))}
                onReasonChange={(value) => {
                  setLastCommittedDocument(null);
                  setReasonCode(value);
                }}
                onSourceBucketChange={(value) => {
                  setLastCommittedDocument(null);
                  setSourceBucketCode(value);
                }}
                reasonActiveIndex={wasteReasonActiveIndex}
                reasonCode={reasonCode}
                searchField={
                  showSearch ? (
                    <SearchField
                      ariaLabel="Buscar catalogo operativo"
                      className="w-full"
                      disabled={isWasteSearchDisabled}
                      inputClassName={cn("h-9 rounded-lg text-sm shadow-sm", posInputClass)}
                      inputRef={searchInputRef}
                      onChange={(value) =>
                        setDraftState((state) => ({
                          ...state,
                          searchText: value,
                        }))
                      }
                      placeholder={
                        draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
                          ? "Filtrar producto"
                          : "Filtrar clase"
                      }
                      value={draftState.searchText}
                    />
                  ) : undefined
                }
                sourceBucketCode={sourceBucketCode}
                wasteReasons={operationsBootstrapQuery.data?.waste_reasons ?? []}
              />
            </div>
          ) : null}

          {variant === "counterTransfer" && counterTransferCenterView === "history" ? (
            <PosHistoryView
              description="Consulta los traspasos confirmados del dia por operador o turno."
              title="Historial de traspasos"
              toolbar={
                <PosFilterBar
                  chipFilters={[
                    {
                      count: counterTransferHistoryShiftCounts.ALL,
                      isActive: counterTransferHistoryShiftFilter === "ALL",
                      key: "all-day",
                      label: getCounterTransferShiftLabel("ALL"),
                      onSelect: () => setCounterTransferHistoryShiftFilter("ALL"),
                    },
                    {
                      count: counterTransferHistoryShiftCounts.MORNING,
                      isActive: counterTransferHistoryShiftFilter === "MORNING",
                      key: "morning",
                      label: getCounterTransferShiftLabel("MORNING"),
                      onSelect: () => setCounterTransferHistoryShiftFilter("MORNING"),
                    },
                    {
                      count: counterTransferHistoryShiftCounts.AFTERNOON,
                      isActive: counterTransferHistoryShiftFilter === "AFTERNOON",
                      key: "afternoon",
                      label: getCounterTransferShiftLabel("AFTERNOON"),
                      onSelect: () => setCounterTransferHistoryShiftFilter("AFTERNOON"),
                    },
                    {
                      count: counterTransferHistoryShiftCounts.NIGHT,
                      isActive: counterTransferHistoryShiftFilter === "NIGHT",
                      key: "night",
                      label: getCounterTransferShiftLabel("NIGHT"),
                      onSelect: () => setCounterTransferHistoryShiftFilter("NIGHT"),
                    },
                  ]}
                  countLabel={
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <ModuleStateChip tone="info">Hoy completo</ModuleStateChip>
                      <span className="pos-chip" data-tone="muted">
                        {counterTransferHistoryRows.length} visibles
                      </span>
                      <span className="pos-chip" data-tone="muted">
                        {counterTransferHistoryUserId === "ALL"
                          ? "Todos los operadores"
                          : (counterTransferHistoryQuery.data?.available_users.find(
                              (option) => option.value === counterTransferHistoryUserId,
                            )?.label ?? "Operador")}
                      </span>
                    </div>
                  }
                  selectFilters={[
                    {
                      ariaLabel: "Filtrar historial por operador",
                      key: "history-user",
                      onChange: setCounterTransferHistoryUserId,
                      options: [
                        { label: "Todos los operadores", value: "ALL" },
                        ...(counterTransferHistoryQuery.data?.available_users ?? []).map(
                          (option: OperationHistoryFilterOptionView) => ({
                            label: option.label,
                            value: option.value,
                          }),
                        ),
                      ],
                      value: counterTransferHistoryUserId,
                    },
                  ]}                  
                  title="Movimientos del mostrador"
                />
              }
            >
              {counterTransferHistoryQuery.error ? (
                <OperationalStatus
                  action={
                    <Button
                      className={posPrimaryButtonClass}
                      onClick={() => void counterTransferHistoryQuery.refetch()}
                    >
                      Reintentar
                    </Button>
                  }
                  description={toOperationalErrorMessage(
                    counterTransferHistoryQuery.error,
                    "No fue posible consultar el historial operativo.",
                  )}
                  title="El historial no esta disponible"
                />
              ) : (
                <PosRecordTable
                  columns={counterTransferHistoryColumns}
                  emptyDescription="Aun no hay traspasos confirmados para los filtros seleccionados."
                  emptyTitle="Sin movimientos"
                  getKey={(record) => record.id}
                  loading={counterTransferHistoryQuery.isPending}
                  onSelect={(record) => setSelectedHistoryDocumentId(record.id)}
                  records={counterTransferHistoryRows}
                  selectedKey={selectedHistoryDocumentId}
                  tableAriaLabel="Historial de traspasos a mostrador"
                />
              )}
            </PosHistoryView>
          ) : variant === "waste" && wasteCenterView === "history" ? (
            <PosHistoryView
              action={
                <Button
                  className={cn("h-10 px-3", posOutlineButtonClass)}
                  onClick={() => setWasteCenterView("capture")}
                  type="button"
                  variant="outline"
                >
                  <ArrowLeftIcon className="h-4 w-4" />
                  Registrar merma
                </Button>
              }
              description="Consulta mermas confirmadas por turno, operador, motivo o producto."
              title="Historial de merma"
              toolbar={
                <PosFilterBar
                  chipFilters={(
                    wasteHistoryQuery.data?.available_scopes ?? [
                      { code: "CURRENT_SHIFT", label: "Turno actual" },
                      { code: "TODAY", label: "Hoy" },
                      { code: "RECENT", label: "Recientes" },
                    ]
                  ).map((scope: OperationHistoryScopeView) => ({
                    isActive: wasteHistoryScope === scope.code,
                    key: scope.code,
                    label: getCounterTransferHistoryScopeLabel(scope.code),
                    onSelect: () => setWasteHistoryScope(scope.code),
                  }))}
                  countLabel={
                    <span className="pos-chip" data-tone="muted">
                      {wasteHistoryRecords.length} registros
                    </span>
                  }
                  searchInput={{
                    ariaLabel: "Buscar merma por folio o motivo",
                    onChange: setWasteHistorySearchText,
                    placeholder: "Buscar folio o motivo",
                    value: wasteHistorySearchText,
                  }}
                  selectFilters={[
                    {
                      ariaLabel: "Filtrar merma por operador",
                      key: "waste-history-user",
                      onChange: setWasteHistoryUserId,
                      options: [
                        { label: "Todos los operadores", value: "ALL" },
                        ...(wasteHistoryQuery.data?.available_users ?? []).map(
                          (option: OperationHistoryFilterOptionView) => ({
                            label: option.label,
                            value: option.value,
                          }),
                        ),
                      ],
                      value: wasteHistoryUserId,
                    },
                    {
                      ariaLabel: "Filtrar merma por motivo",
                      key: "waste-history-reason",
                      onChange: setWasteHistoryReasonCode,
                      options: [
                        { label: "Todos los motivos", value: "ALL" },
                        ...(wasteHistoryQuery.data?.available_reasons ?? []).map(
                          (option: OperationHistoryFilterOptionView) => ({
                            label: option.label,
                            value: option.value,
                          }),
                        ),
                      ],
                      value: wasteHistoryReasonCode,
                    },
                    {
                      ariaLabel: "Filtrar merma por producto",
                      key: "waste-history-product",
                      onChange: setWasteHistoryProductId,
                      options: [
                        { label: "Todos los productos", value: "ALL" },
                        ...(wasteHistoryQuery.data?.available_products ?? []).map(
                          (option: OperationHistoryFilterOptionView) => ({
                            label: option.label,
                            value: option.value,
                          }),
                        ),
                      ],
                      value: wasteHistoryProductId,
                    },
                  ]}
                  title="Historial disponible"
                />
              }
            >
              {wasteHistoryQuery.error ? (
                <OperationalStatus
                  action={
                    <Button
                      className={posPrimaryButtonClass}
                      onClick={() => void wasteHistoryQuery.refetch()}
                    >
                      Reintentar
                    </Button>
                  }
                  description={toOperationalErrorMessage(
                    wasteHistoryQuery.error,
                    "No fue posible consultar el historial de merma.",
                  )}
                  title="El historial no esta disponible"
                />
              ) : (
                <OperationHistoryList
                  emptyDescription="Aun no hay mermas confirmadas para los filtros seleccionados."
                  loading={wasteHistoryQuery.isPending}
                  onSelect={(record) => setSelectedHistoryDocumentId(record.id)}
                  records={wasteHistoryRecords}
                  selectedRecordId={selectedHistoryDocumentId}
                />
              )}
            </PosHistoryView>
          ) : isCounterTransferAvailabilityView ? (
            <CounterAvailabilitySection
              branchName={operationsBootstrapQuery.data.branch.name}
              containerRef={counterTransferAvailabilityRef}
              onRetry={() => void counterAvailabilityQuery.refetch()}
              products={availableCounterProducts}
              queryErrorMessage={counterAvailabilityErrorMessage}
              queryPending={counterAvailabilityQuery.isPending}
            />
          ) : variant === "counterTransfer" ? (
            <>
              {isSelectionLoading ? (
                <OperationalStatus
                  description="Cargando el catalogo operativo actual."
                  title="Cargando seleccion"
                />
              ) : null}

              {!isSelectionLoading && selectionError ? (
                <OperationalStatus
                  action={
                    <Button
                      className={posPrimaryButtonClass}
                      onClick={() =>
                        draftState.controlState === CONTROL_STATE_CLASS_SELECTION
                          ? catalogQuery.refetch()
                          : classProductsQuery.refetch()
                      }
                    >
                      Reintentar
                    </Button>
                  }
                  description={toOperationalErrorMessage(
                    selectionError,
                    "Confirma el contexto de la estacion y la disponibilidad del catalogo operativo.",
                  )}
                  title="La seleccion no esta disponible"
                />
              ) : null}

              {selectionErrorMessage && draftState.controlState !== CONTROL_STATE_QUANTITY_CAPTURE ? (
                <div className="mb-2 flex items-start justify-between gap-3 rounded-lg border border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm text-[var(--ui-color-danger)]">
                  <p className="leading-6">{selectionErrorMessage}</p>
                  <button
                    aria-label="Cerrar error"
                    className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)]"
                    onClick={() => setSelectionErrorMessage(null)}
                    type="button"
                  >
                    <XIcon className="h-4 w-4" />
                  </button>
                </div>
              ) : null}

              {!isSelectionLoading && !selectionError ? (
                <>
                  {draftState.controlState === CONTROL_STATE_CLASS_SELECTION ? (
                    sortedClasses.length > 0 ? (
                      <div className="grid gap-2.5">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                            <span className="pos-chip" data-tone="muted">
                              Captura por clase
                            </span>
                            <span className="pos-chip" data-tone="primary">
                              Producto directo
                            </span>
                          </div>
                        </div>
                        <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                          {sortedClasses.map((productClass, index) => {
                            const itemProps = getClassItemProps(index);

                            return (
                              <CatalogSelectionCard
                                buttonRef={itemProps.ref}
                                code={productClass.code}
                                isActive={classActiveIndex === index}
                                isDisabled={commitMutation.isPending}
                                key={productClass.id}
                                name={productClass.name}
                                onCardFocus={itemProps.onFocus}
                                onCardKeyDown={itemProps.onKeyDown}
                                onSelect={() => {
                                  setLastCommittedDocument(null);
                                  setDraftState((state) =>
                                    selectClassForOperation(state, productClass),
                                  );
                                }}
                                shortcutLabel={getSelectionShortcutLabel(index)}
                                tabIndex={itemProps.tabIndex}
                                variant="pos"
                              />
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-center text-sm text-slate-600">
                        No hay clases para la busqueda actual.
                      </div>
                    )
                  ) : null}

                  {draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ? (
                    sortedProducts.length > 0 ? (
                      <div className="grid gap-2.5">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                            <span className="font-medium text-slate-700">
                              {selectedCounterTransferClass?.name}
                            </span>
                            <span className="pos-chip" data-tone="primary">
                              Producto exacto
                            </span>
                          </div>
                        </div>
                        <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                          {sortedProducts.map((product, index) => {
                            const itemProps = getProductItemProps(index);

                            return (
                              <CatalogSelectionCard
                                buttonRef={itemProps.ref}
                                code={product.code}
                                isActive={productActiveIndex === index}
                                isDisabled={commitMutation.isPending}
                                key={product.id}
                                name={product.name}
                                onCardFocus={itemProps.onFocus}
                                onCardKeyDown={itemProps.onKeyDown}
                                onSelect={() => {
                                  setLastCommittedDocument(null);
                                  setDraftState((state) =>
                                    selectProductForOperation(state, product),
                                  );
                                }}
                                priceText={product.unit_price}
                                shortcutLabel={getSelectionShortcutLabel(index)}
                                tabIndex={itemProps.tabIndex}
                                variant="pos"
                              />
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-center text-sm text-slate-600">
                        No hay productos para esta busqueda.
                      </div>
                    )
                  ) : null}

                  {quantitySelection !== null && quantityProduct !== null ? (
                    <div className="w-full max-w-5xl justify-self-center rounded-xl border border-[var(--pos-shell-border)] bg-white p-3 shadow-sm">
                      <div className="grid gap-3 lg:grid-cols-[12rem_minmax(0,1fr)]">
                        <CatalogVisual
                          className="min-h-[11.5rem]"
                          code={quantityProduct.code}
                          name={quantityProduct.name}
                        />

                        <div className="grid gap-2.5">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="text-base font-semibold text-slate-950">
                                  {quantityProduct.name}
                                </p>
                                <span className="pos-chip" data-tone="primary">
                                  Producto exacto
                                </span>
                              </div>
                              <p className="mt-1 text-sm text-slate-600">
                                {quantitySelection.productClass.name}
                              </p>
                            </div>
                          </div>

                          <div className="grid gap-2">
                            <input
                              aria-label="Cantidad"
                              className={cn(
                                "h-16 rounded-xl px-4 text-[2.25rem] font-semibold tracking-tight shadow-sm",
                                posInputClass,
                              )}
                              inputMode="decimal"
                              onChange={(event) =>
                                setDraftState((state) =>
                                  setPendingQuantityText(state, event.target.value),
                                )
                              }
                              onKeyDown={(event) => {
                                if (event.key === "Enter" || event.key === "NumpadEnter") {
                                  event.preventDefault();
                                  handleAddLine();
                                }

                                if (event.key === "Escape") {
                                  event.preventDefault();
                                  event.stopPropagation();
                                  setDraftState((state) => goBackFromOperationalState(state));
                                }

                                if (event.key === "Delete") {
                                  event.preventDefault();
                                  setDraftState((state) => setPendingQuantityText(state, ""));
                                  setSelectionErrorMessage(null);
                                }
                              }}
                              placeholder="0"
                              ref={quantityInputRef}
                              value={quantitySelection.quantityText}
                            />
                            <div className="flex flex-wrap items-center gap-2">
                              <div className="flex items-center gap-2">
                                <Button
                                  className={cn("h-10 px-3", posOutlineButtonClass)}
                                  onClick={() =>
                                    setDraftState((state) =>
                                      decrementPendingOperationQuantity(state),
                                    )
                                  }
                                  type="button"
                                >
                                  -1
                                </Button>
                                <Button
                                  className={cn("h-10 px-3", posOutlineButtonClass)}
                                  onClick={() =>
                                    setDraftState((state) =>
                                      incrementPendingOperationQuantity(state),
                                    )
                                  }
                                  type="button"
                                >
                                  +1
                                </Button>
                              </div>

                              <div className="flex flex-wrap items-center gap-2">
                                {quantityPresets.map((preset) => (
                                  <Button
                                    className={cn("h-10 min-w-12 px-3", posOutlineButtonClass)}
                                    key={preset}
                                    onClick={() =>
                                      setDraftState((state) => setPendingQuantityText(state, preset))
                                    }
                                    type="button"
                                  >
                                    {preset}
                                  </Button>
                                ))}
                              </div>
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                              {quantityShortcuts.map((shortcut) => (
                                <span className="pos-chip" data-tone="muted" key={shortcut.label}>
                                  {shortcut.label} {shortcut.value}
                                </span>
                              ))}
                            </div>
                            <div className="flex flex-wrap items-center justify-end gap-3">
                              <Button
                                className={cn("h-10 px-4", posOutlineButtonClass)}
                                onClick={() =>
                                  setDraftState((state) => goBackFromOperationalState(state))
                                }
                                type="button"
                              >
                                Cancelar
                              </Button>
                              <Button
                                className={cn("h-10 px-5", posPrimaryButtonClass)}
                                disabled={!isQuantityReady}
                                onClick={handleAddLine}
                                type="button"
                              >
                                Agregar
                              </Button>
                            </div>
                            {selectionErrorMessage ? (
                              <div className="flex items-start justify-between gap-3 rounded-lg border border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm text-[var(--ui-color-danger)]">
                                <p className="leading-6">{selectionErrorMessage}</p>
                                <button
                                  aria-label="Cerrar error"
                                  className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)]"
                                  onClick={() => setSelectionErrorMessage(null)}
                                  type="button"
                                >
                                  <XIcon className="h-4 w-4" />
                                </button>
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </>
              ) : null}
            </>
          ) : (
            <>
              <PosContextBanner
                description="Documenta origen, motivo y productos exactos para registrar la merma con trazabilidad completa."
                title="Trazabilidad -> Merma"
              />

              {isSelectionLoading ? (
                <OperationalStatus
                  description="Cargando el catalogo operativo actual."
                  title="Cargando seleccion"
                />
              ) : null}

              {!isSelectionLoading && selectionError ? (
                <OperationalStatus
                  action={
                    <Button
                      className={posPrimaryButtonClass}
                      onClick={() =>
                        draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
                          ? classProductsQuery.refetch()
                          : catalogQuery.refetch()
                      }
                    >
                      Reintentar
                    </Button>
                  }
                  description={toOperationalErrorMessage(
                    selectionError,
                    "Confirma el contexto de la estacion y la disponibilidad del catalogo operativo.",
                  )}
                  title="La seleccion no esta disponible"
                />
              ) : null}

              {!isSelectionLoading &&
              !selectionError &&
              draftState.controlState === CONTROL_STATE_CLASS_SELECTION ? (
                <div className="grid gap-2.5">
                  <h2 className="text-sm font-semibold text-slate-950">Selecciona una clase</h2>
                  <div className="relative min-h-[14rem]">
                  <div
                    className={cn(
                      showWasteCaptureOverlay && "pointer-events-none select-none opacity-45",
                    )}
                  >
                    {sortedClasses.length > 0 ? (
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                        {sortedClasses.map((productClass, index) => {
                          const itemProps = getClassItemProps(index);

                          return (
                            <SelectionCard
                              buttonRef={itemProps.ref}
                              code={productClass.code}
                              isActive={classActiveIndex === index}
                              isDisabled={showWasteCaptureOverlay}
                              key={productClass.id}
                              onCardFocus={itemProps.onFocus}
                              onCardKeyDown={itemProps.onKeyDown}
                              onSelect={() => {
                                setLastCommittedDocument(null);
                                setDraftState((state) =>
                                  selectClassForOperation(state, productClass),
                                );
                              }}
                              shortcutLabel={getSelectionShortcutLabel(index)}
                              tabIndex={itemProps.tabIndex}
                              title={productClass.name}
                            />
                          );
                        })}
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-sm text-slate-600">
                        No hay clases para la busqueda actual.
                      </div>
                    )}
                  </div>
                  {showWasteCaptureOverlay ? (
                    <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white/90 px-4 text-center">
                      <div className="max-w-sm rounded-xl border border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)] px-4 py-3 text-sm font-medium text-[var(--ui-color-warning)]">
                        {WASTE_TRACEABILITY_OVERLAY_MESSAGE}
                      </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {!isSelectionLoading &&
              !selectionError &&
              draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ? (
                <div className="grid gap-2.5">
                  <h2 className="text-sm font-semibold text-slate-950">Selecciona un producto</h2>
                  <div className="relative min-h-[14rem]">
                  <div
                    className={cn(
                      showWasteCaptureOverlay && "pointer-events-none select-none opacity-45",
                    )}
                  >
                    {sortedProducts.length > 0 ? (
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        {sortedProducts.map((product, index) => {
                          const itemProps = getProductItemProps(index);

                          return (
                            <SelectionCard
                              buttonRef={itemProps.ref}
                              code={product.code}
                              isActive={productActiveIndex === index}
                              isDisabled={showWasteCaptureOverlay}
                              key={product.id}
                              onCardFocus={itemProps.onFocus}
                              onCardKeyDown={itemProps.onKeyDown}
                              onSelect={() => {
                                setLastCommittedDocument(null);
                                setDraftState((state) =>
                                  selectProductForOperation(state, product),
                                );
                              }}
                              shortcutLabel={getSelectionShortcutLabel(index)}
                              tabIndex={itemProps.tabIndex}
                              title={product.name}
                            />
                          );
                        })}
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-sm text-slate-600">
                        No hay productos para esta busqueda.
                      </div>
                    )}
                  </div>
                  {showWasteCaptureOverlay ? (
                    <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white/90 px-4 text-center">
                      <div className="max-w-sm rounded-xl border border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)] px-4 py-3 text-sm font-medium text-[var(--ui-color-warning)]">
                        {WASTE_TRACEABILITY_OVERLAY_MESSAGE}
                      </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {quantitySelection !== null && quantityProduct !== null ? (
            <div className="w-full max-w-5xl justify-self-center rounded-xl border border-[var(--pos-shell-border)] bg-white p-3 shadow-sm">
              <div className="grid gap-3 lg:grid-cols-[12rem_minmax(0,1fr)]">
                <CatalogVisual
                  className="min-h-[11.5rem]"
                  code={quantityProduct.code}
                  name={quantityProduct.name}
                />

                <div className="grid gap-2.5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-base font-semibold text-slate-950">{quantityProduct.name}</p>
                        {!isQuantityReady ? (
                          <span className="pos-chip" data-tone="warning">
                            Pendiente
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-1 text-sm text-slate-600">
                        {quantitySelection.productClass.name}
                      </p>
                    </div>

                    <Button
                      aria-label="Regresar"
                      className={cn("h-10 px-3", posOutlineButtonClass)}
                      onClick={() => setDraftState((state) => goBackFromOperationalState(state))}
                      title="Regresar"
                      type="button"
                    >
                      <ArrowLeftIcon className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="grid gap-2">
                    <input
                      aria-label="Cantidad"
                      className={cn(
                        "h-16 rounded-xl px-4 text-[2.25rem] font-semibold tracking-tight shadow-sm",
                        posInputClass,
                      )}
                      disabled={isWasteQuantityBlocked}
                      inputMode="decimal"
                      onChange={(event) =>
                        setDraftState((state) => setPendingQuantityText(state, event.target.value))
                      }
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          handleAddLine();
                        }

                        if (event.key === "Escape") {
                          event.preventDefault();
                          event.stopPropagation();
                          setDraftState((state) => goBackFromOperationalState(state));
                        }
                      }}
                      placeholder="0"
                      ref={quantityInputRef}
                      value={quantitySelection.quantityText}
                    />
                    {isWasteQuantityBlocked ? (
                      <InlineNotice tone="warning">
                        {WASTE_TRACEABILITY_BLOCK_MESSAGE}
                      </InlineNotice>
                    ) : null}
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="flex items-center gap-2">
                        <Button
                          className={cn("h-10 px-3", posOutlineButtonClass)}
                          disabled={isWasteQuantityBlocked}
                          onClick={() =>
                            setDraftState((state) => decrementPendingOperationQuantity(state))
                          }
                          type="button"
                        >
                          -1
                        </Button>
                        <Button
                          className={cn("h-10 px-3", posOutlineButtonClass)}
                          disabled={isWasteQuantityBlocked}
                          onClick={() =>
                            setDraftState((state) => incrementPendingOperationQuantity(state))
                          }
                          type="button"
                        >
                          +1
                        </Button>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {quantityShortcuts.map((shortcut) => (
                          <span className="pos-chip" data-tone="muted" key={shortcut.label}>
                            {shortcut.label} {shortcut.value}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-3">
                      <Button
                        className={cn("h-10 px-5", posPrimaryButtonClass)}
                        disabled={!isQuantityReady || isWasteQuantityBlocked}
                        onClick={handleAddLine}
                        type="button"
                      >
                        Agregar
                      </Button>
                    </div>
                    {selectionErrorMessage ? (
                      <div className="flex items-start justify-between gap-3 rounded-lg border border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm text-[var(--ui-color-danger)]">
                        <p className="leading-6">{selectionErrorMessage}</p>
                        <button
                          aria-label="Cerrar error"
                          className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)]"
                          onClick={() => setSelectionErrorMessage(null)}
                          type="button"
                        >
                          <XIcon className="h-4 w-4" />
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
              ) : null}

              {quantitySelection !== null && quantityProduct !== null ? (
            <div className="w-full max-w-5xl justify-self-center rounded-xl border border-[var(--pos-shell-border)] bg-white p-3 shadow-sm">
              <div className="grid gap-3 lg:grid-cols-[12rem_minmax(0,1fr)]">
                <CatalogVisual
                  className="min-h-[11.5rem]"
                  code={quantityProduct.code}
                  name={quantityProduct.name}
                />

                <div className="grid gap-2.5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-base font-semibold text-slate-950">{quantityProduct.name}</p>
                        {!isQuantityReady ? (
                          <span className="pos-chip" data-tone="warning">
                            Pendiente
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-1 text-sm text-slate-600">
                        {quantitySelection.productClass.name}
                      </p>
                    </div>

                    <Button
                      aria-label="Regresar"
                      className={cn("h-10 px-3", posOutlineButtonClass)}
                      onClick={() => setDraftState((state) => goBackFromOperationalState(state))}
                      title="Regresar"
                      type="button"
                    >
                      <ArrowLeftIcon className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="grid gap-2">
                    <input
                      aria-label="Cantidad"
                      className={cn(
                        "h-16 rounded-xl px-4 text-[2.25rem] font-semibold tracking-tight shadow-sm",
                        posInputClass,
                      )}
                      disabled={isWasteQuantityBlocked}
                      inputMode="decimal"
                      onChange={(event) =>
                        setDraftState((state) => setPendingQuantityText(state, event.target.value))
                      }
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          handleAddLine();
                        }

                        if (event.key === "Escape") {
                          event.preventDefault();
                          setDraftState((state) => goBackFromOperationalState(state));
                        }
                      }}
                      placeholder="0"
                      ref={quantityInputRef}
                      value={quantitySelection.quantityText}
                    />
                    {isWasteQuantityBlocked ? (
                      <InlineNotice tone="warning">
                        {WASTE_TRACEABILITY_BLOCK_MESSAGE}
                      </InlineNotice>
                    ) : null}
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="flex items-center gap-2">
                        <Button
                          className={cn("h-10 px-3", posOutlineButtonClass)}
                          disabled={isWasteQuantityBlocked}
                          onClick={() =>
                            setDraftState((state) => decrementPendingOperationQuantity(state))
                          }
                          type="button"
                        >
                          -1
                        </Button>
                        <Button
                          className={cn("h-10 px-3", posOutlineButtonClass)}
                          disabled={isWasteQuantityBlocked}
                          onClick={() =>
                            setDraftState((state) => incrementPendingOperationQuantity(state))
                          }
                          type="button"
                        >
                          +1
                        </Button>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {quantityShortcuts.map((shortcut) => (
                          <span className="pos-chip" data-tone="muted" key={shortcut.label}>
                            {shortcut.label} {shortcut.value}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-3">
                      <Button
                        className={cn("h-10 px-5", posPrimaryButtonClass)}
                        disabled={!isQuantityReady || isWasteQuantityBlocked}
                        onClick={handleAddLine}
                        type="button"
                      >
                        Agregar
                      </Button>
                    </div>
                    {selectionErrorMessage ? (
                      <div className="flex items-start justify-between gap-3 rounded-lg border border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm text-[var(--ui-color-danger)]">
                        <p className="leading-6">{selectionErrorMessage}</p>
                        <button
                          aria-label="Cerrar error"
                          className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)]"
                          onClick={() => setSelectionErrorMessage(null)}
                          type="button"
                        >
                          <XIcon className="h-4 w-4" />
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
              ) : null}

              {variant === "waste" ? (
                <PosPanel className="mt-3 grid gap-3 px-4 py-4">
                  <PosSectionTitle
                    description="Registra notas operativas. Los archivos adjuntos quedan como dependencia futura."
                    eyebrow="3. Notas y evidencia"
                    title="Contexto adicional"
                  />
                  <div className="grid gap-2">
                    <PosFieldLabel
                      helper={
                        wasteRequiresEvidenceNote
                          ? "Requerida para este motivo o por alto impacto. La nota queda auditada."
                          : "Este campo es opcional y queda auditado con el documento."
                      }
                      required={wasteRequiresEvidenceNote}
                    >
                      Notas operativas
                    </PosFieldLabel>
                    <textarea
                      className={cn("min-h-24 rounded-lg px-3 py-2 text-sm shadow-sm", posInputClass)}
                      disabled={commitMutation.isPending}
                      onChange={(event) => {
                        setLastCommittedDocument(null);
                        setNotes(event.target.value);
                      }}
                      placeholder="Describe evidencia o contexto operativo"
                      value={notes}
                    />
                    {wasteRequiresEvidenceNote ? (
                      <PosInlineValidationMessage tone="warning">
                        Este motivo requiere evidencia en notas. Los archivos adjuntos aun no estan
                        disponibles en este flujo.
                      </PosInlineValidationMessage>
                    ) : null}
                    {wasteStockWarningMessage ? (
                      <PosInlineValidationMessage tone="warning">
                        {wasteStockWarningMessage}
                      </PosInlineValidationMessage>
                    ) : null}
                    {wasteCounterAvailabilityWarningMessage ? (
                      <PosInlineValidationMessage tone="warning">
                        {wasteCounterAvailabilityWarningMessage}
                      </PosInlineValidationMessage>
                    ) : null}
                    {isWasteHighImpact ? (
                      <div className="grid gap-2 rounded-[var(--pos-radius-control)] border border-[rgba(187,122,22,0.22)] bg-[var(--ui-color-warning-soft)] px-3 py-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <PosStatusBadge status="warning">Alto impacto</PosStatusBadge>
                          <span className="text-xs font-medium text-slate-700">
                            Umbral {formatQuantityFromMilliUnits(wasteHighImpactThresholdMilli)}
                          </span>
                        </div>
                        <p className="text-sm leading-6 text-slate-700">
                          Esta merma supera el umbral operativo y generara una alerta para backoffice
                          al confirmar.
                        </p>
                        <label className="flex items-start gap-3 text-sm text-slate-800">
                          <input
                            checked={isWasteHighImpactAcknowledged}
                            className="mt-1 h-4 w-4 rounded border-[var(--pos-shell-border)] text-[var(--pos-accent-strong)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2"
                            disabled={commitMutation.isPending}
                            onChange={(event) =>
                              setIsWasteHighImpactAcknowledged(event.target.checked)
                            }
                            type="checkbox"
                          />
                          <span>
                            Confirmo la merma de alto impacto y la notificacion operativa a
                            backoffice.
                          </span>
                        </label>
                      </div>
                    ) : null}
                  </div>
                </PosPanel>
              ) : null}
            </>
          )}
        </CentralWorkspaceSheet>
      </PosModuleLayout>
    </>
  );
}


