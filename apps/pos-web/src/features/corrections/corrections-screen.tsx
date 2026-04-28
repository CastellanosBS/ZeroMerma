import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import {
  OperationConfirmationDialog,
  OperationDocumentResult,
  OperationDocumentSummaryPanel,
  OperationHistoryList,
  type OperationDocumentAction,
  type OperationDocumentMetric,
  type OperationHistoryRecord,
  type OperationLineSummaryItem,
} from "../../components/operation-documents";
import {
  CentralWorkspaceSheet,
  FlowGuide,
  InlineNotice,
  ListDetailColumn,
  ModuleStateChip,
  CompactPageHeader,
  ResponsivePaneLayout,
  ScrollPane,
  SearchField,
} from "../../components/pos-module-primitives";
import { OperationalStatus } from "../../components/operational-status";
import { PosContextBanner, PosSummaryPanel } from "../../components/pos-module-layout";
import { PosFilterBar, PosHistoryView, PosRecordDetailPanel, PosRecordList } from "../../components/pos-records";
import { Button } from "../../components/ui/button";
import { appEnv } from "../../env";
import type {
  CorrectionDocumentView,
  CorrectionHistoryListItemView,
  CorrectionProductOptionView,
  CorrectionSearchDocumentView,
  CorrectionTargetDetailResponse,
  OperationDocumentLineView,
  TransferDestinationBranchView,
} from "../../lib/api-contracts";
import { getDocumentActionAvailability } from "../../lib/document-actions";
import { formatLocalDateTime } from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import { isEditableTarget } from "../../lib/keyboard-shortcuts";
import { cn } from "../../lib/utils";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import { formatQuantityFromMilliUnits } from "../pos-terminal/model";
import {
  posInputClass,
  posOutlineButtonClass,
  posPrimaryButtonClass,
} from "../pos-theme/theme";
import { useStatusMessageStore } from "../status-messages/store";
import { commitCorrection, getCorrectionTargetDetail } from "./corrections-api";
import {
  buildCorrectionCommitLines,
  createInitialCorrectionDraftState,
  getCorrectionDraftBlockingMessages,
  getCorrectionDraftBlockedReason,
  getCorrectionDraftLineDirection,
  getCorrectionDraftLineMagnitudeText,
  getCorrectionDraftNetQuantityMilliUnits,
  getCorrectionDraftTotalAdjustedQuantityMilliUnits,
  hasCorrectionDraftInvalidQuantity,
  hasCorrectionDraftMissingReason,
  parseSignedQuantityToMilliUnits,
  removeCorrectionDraftLine,
  upsertAddedProductDraftAdjustment,
  upsertTargetLineDraftAdjustment,
  type CorrectionDirection,
  type CorrectionDraftLine,
} from "./model";
import {
  correctionTargetDetailQueryKey,
  correctionsBootstrapQueryKey,
  useCorrectionDocumentDetailQuery,
  useCorrectionProductsQuery,
  useCorrectionTargetDetailQuery,
  useCorrectionTargetsQuery,
  useCorrectionsBootstrapQuery,
  useCorrectionsHistoryQuery,
} from "./queries";

const DOCUMENT_TYPE_FILTERS = [
  { code: "", label: "Todos" },
  { code: "COUNTER_TRANSFER", label: "Paso a mostrador" },
  { code: "WASTE_RECORD", label: "Merma" },
  { code: "BRANCH_TRANSFER_SHIPMENT", label: "Envio a sucursal" },
] as const;

const CORRECTION_PROCESS_STEPS = [
  { key: "documents", label: "Documento" },
  { key: "history", label: "Historial" },
] as const;

const WRONG_DESTINATION_REASON_CODE = "WRONG_DESTINATION";

type CorrectionsCenterSection = "documents" | "history";
type CorrectionUiState =
  | "NO_DOC_SELECTED"
  | "DOC_SELECTED"
  | "DRAFT_EMPTY"
  | "DRAFT_BUILDING"
  | "BLOCKED_MISSING_REASON"
  | "BLOCKED_INVALID_SIGN"
  | "READY_TO_CONFIRM"
  | "CONFIRMING"
  | "CONFIRMED"
  | "ERROR";

function createRequestId(scope: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${scope}-${crypto.randomUUID()}`;
  }

  return `${scope}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function useDebouncedValue(value: string, delayMs: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeout);
  }, [delayMs, value]);

  return debouncedValue;
}

function formatQuantity(quantity: number | string): string {
  return new Intl.NumberFormat("es-MX", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(quantity));
}

function formatSignedHistoryQuantity(quantity: number | string): string {
  const numericValue = Number(quantity);
  if (numericValue === 0) {
    return "0";
  }

  const prefix = numericValue > 0 ? "+" : "-";
  return `${prefix}${formatQuantity(Math.abs(numericValue))}`;
}

function getLocalDayKey(dateTime: string, timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone,
    year: "numeric",
  }).format(new Date(dateTime));
}

function isTodayInTimeZone(dateTime: string | null, timeZone: string): boolean {
  if (!dateTime) {
    return false;
  }

  return getLocalDayKey(dateTime, timeZone) === getLocalDayKey(new Date().toISOString(), timeZone);
}

function formatCorrectionFolio(correctionId: string): string {
  return `COR-${correctionId.split("-", 1)[0].toUpperCase()}`;
}

function getCorrectionReference(correction: { folio?: string | null; id: string }): string {
  return correction.folio ?? formatCorrectionFolio(correction.id);
}

function getDocumentTypeLabel(documentType: string): string {
  switch (documentType) {
    case "COUNTER_TRANSFER":
      return "Paso a mostrador";
    case "WASTE_RECORD":
      return "Registro de merma";
    case "BRANCH_TRANSFER_SHIPMENT":
      return "Envio a sucursal";
    default:
      return documentType;
  }
}

function getCorrectionReasonLabel(reasonCode: string, fallbackName?: string): string {
  switch (reasonCode) {
    case "WRONG_QUANTITY":
      return "Cantidad incorrecta";
    case "WRONG_PRODUCT":
      return "Producto incorrecto";
    case "DUPLICATE_CAPTURE":
      return "Captura duplicada";
    case "DAMAGED_DURING_HANDLING":
      return "Danio durante manejo";
    case "COUNT_MISMATCH":
      return "Descuadre de conteo";
    case "WRONG_DESTINATION":
      return "Destino incorrecto";
    case "OTHER":
      return "Otro motivo";
    default:
      return fallbackName ?? reasonCode;
  }
}

function getSignedEffectLabel(value: number): string {
  if (value === 0) {
    return "Sin efecto neto";
  }

  const prefix = value > 0 ? "+" : "-";
  return `${prefix}${formatQuantityFromMilliUnits(Math.abs(value))} unidades`;
}

function getCorrectionHighImpactLabel(thresholdText: string): string {
  return `Ajuste alto impacto a partir de ${thresholdText} unidades ajustadas.`;
}

function buildDraftLineSummaryItems({
  draftLines,
  targetLines,
}: {
  draftLines: CorrectionDraftLine[];
  targetLines: OperationDocumentLineView[];
}): OperationLineSummaryItem[] {
  const targetLineById = new Map(targetLines.map((line) => [line.id, line]));

  return draftLines.map((line) => {
    const deltaMilliUnits = parseSignedQuantityToMilliUnits(line.deltaQuantityText) ?? 0;
    const originalLine = line.targetLineId ? targetLineById.get(line.targetLineId) ?? null : null;
    const originalMilliUnits = originalLine ? Number(originalLine.quantity) * 1000 : 0;
    const resultMilliUnits = originalMilliUnits + deltaMilliUnits;

    return {
      key: line.key,
      quantityText:
        deltaMilliUnits === 0 ? "Pendiente" : getSignedEffectLabel(deltaMilliUnits),
      secondaryText:
        line.targetLineId !== null
          ? `Original ${formatQuantityFromMilliUnits(originalMilliUnits)} -> Resultado ${formatQuantityFromMilliUnits(
              resultMilliUnits,
            )}`
          : `Nuevo producto -> Resultado ${formatQuantityFromMilliUnits(resultMilliUnits)}`,
      statusLabel: line.targetLineId ? "Linea original" : "Producto agregado",
      statusTone: line.targetLineId ? "warning" : "ready",
      title: line.productName,
      trailingNote: line.notes.trim().length > 0 ? line.notes.trim() : undefined,
    };
  });
}

function buildCorrectionsHistoryRecords(
  records: CorrectionHistoryListItemView[],
  timeZone: string,
): OperationHistoryRecord[] {
  return records.map((correction) => ({
    documentTypeLabel: getDocumentTypeLabel(correction.target_document_type),
    folio: correction.folio,
    id: correction.id,
    locationLabel: `${correction.source_branch_name} / ${correction.workstation_name}`,
    metrics: [
      {
        key: `${correction.id}:lines`,
        label: "Lineas",
        value: String(correction.line_count),
      },
      {
        key: `${correction.id}:effect`,
        label: "Efecto",
        value: getSignedEffectLabel(Number(correction.net_effect_quantity) * 1000),
      },
    ],
    primaryTimestampLabel: "Confirmado",
    primaryTimestampValue: correction.committed_at_utc
      ? formatLocalDateTime(correction.committed_at_utc, timeZone)
      : "Sin confirmar",
    secondaryTimestampLabel: "Creado",
    secondaryTimestampValue: formatLocalDateTime(correction.created_at_utc, timeZone),
    statusLabel: correction.status === "COMMITTED" ? "Registrada" : correction.status,
    statusTone: correction.status === "COMMITTED" ? "confirmed" : "draft",
    subtitle: `Documento ${correction.target_document_folio} · ${getCorrectionReasonLabel(
      correction.reason_code,
      correction.reason_name,
    )}`,
    title: getCorrectionReasonLabel(correction.reason_code, correction.reason_name),
    userLabel: correction.created_by_user_full_name,
  }));
}

function buildCorrectionLineSummaryItems(
  correction: CorrectionDocumentView | null,
): OperationLineSummaryItem[] {
  if (!correction) {
    return [];
  }

  return correction.lines.map((line) => ({
    key: `${correction.id}:${line.line_number}:${line.product_code_snapshot}`,
    quantityText: formatSignedHistoryQuantity(line.delta_quantity),
    secondaryText: line.product_code_snapshot,
    title: line.product_name_snapshot,
    trailingNote: `Linea ${line.line_number}`,
  }));
}

function buildCorrectionMetrics(
  correction: CorrectionDocumentView | null,
): OperationDocumentMetric[] {
  if (!correction) {
    return [];
  }

  const netEffectMilliUnits = correction.lines.reduce(
    (sum, line) => sum + Number(line.delta_quantity) * 1000,
    0,
  );

  const metrics: OperationDocumentMetric[] = [
    {
      key: "line-count",
      label: "Lineas",
      value: String(correction.lines.length),
    },
    {
      key: "net-effect",
      label: "Efecto neto",
      tone: netEffectMilliUnits === 0 ? "warning" : "financial",
      value: getSignedEffectLabel(netEffectMilliUnits),
    },
  ];

  if (correction.corrected_destination_branch_name) {
    metrics.push({
      key: "destination",
      label: "Destino corregido",
      value: correction.corrected_destination_branch_name,
    });
  }

  return metrics;
}

function getCorrectionUiState({
  centerSection,
  commitError,
  hasDraftWork,
  hasCommitted,
  hasInvalidQuantity,
  hasSelectedTarget,
  isCommitPending,
  isReasonMissing,
}: {
  centerSection: CorrectionsCenterSection;
  commitError: string | null;
  hasDraftWork: boolean;
  hasCommitted: boolean;
  hasInvalidQuantity: boolean;
  hasSelectedTarget: boolean;
  isCommitPending: boolean;
  isReasonMissing: boolean;
}): CorrectionUiState {
  if (commitError !== null) {
    return "ERROR";
  }

  if (hasCommitted) {
    return "CONFIRMED";
  }

  if (isCommitPending) {
    return "CONFIRMING";
  }

  if (!hasSelectedTarget) {
    return "NO_DOC_SELECTED";
  }

  if (centerSection !== "history") {
    return hasDraftWork ? "DRAFT_BUILDING" : "DOC_SELECTED";
  }

  if (!hasDraftWork) {
    return "DOC_SELECTED";
  }

  if (hasInvalidQuantity) {
    return "BLOCKED_INVALID_SIGN";
  }

  if (isReasonMissing) {
    return "BLOCKED_MISSING_REASON";
  }

  return "READY_TO_CONFIRM";
}

function getCorrectionUiStateLabel(state: CorrectionUiState): string {
  switch (state) {
    case "NO_DOC_SELECTED":
      return "Sin documento";
    case "DOC_SELECTED":
      return "En revision";
    case "DRAFT_EMPTY":
      return "Borrador vacio";
    case "DRAFT_BUILDING":
      return "Borrador en captura";
    case "BLOCKED_MISSING_REASON":
      return "Falta motivo";
    case "BLOCKED_INVALID_SIGN":
      return "Revisa cantidades";
    case "READY_TO_CONFIRM":
      return "Lista para confirmar";
    case "CONFIRMING":
      return "Registrando...";
    case "CONFIRMED":
      return "Confirmada";
    case "ERROR":
      return "Error";
  }
}

function getCorrectionUiStateTone(state: CorrectionUiState) {
  switch (state) {
    case "READY_TO_CONFIRM":
    case "CONFIRMED":
      return "success";
    case "BLOCKED_INVALID_SIGN":
    case "BLOCKED_MISSING_REASON":
    case "ERROR":
      return "danger";
    case "CONFIRMING":
    case "DRAFT_BUILDING":
      return "warning";
    default:
      return "muted";
  }
}

function getCorrectionSummaryStateTone(state: CorrectionUiState) {
  switch (state) {
    case "READY_TO_CONFIRM":
    case "CONFIRMED":
      return "success" as const;
    case "BLOCKED_INVALID_SIGN":
    case "BLOCKED_MISSING_REASON":
    case "ERROR":
      return "blocked" as const;
    case "CONFIRMING":
    case "DRAFT_BUILDING":
      return "warning" as const;
    default:
      return "draft" as const;
  }
}

function getOriginalDocumentLabel(documentTitle: string | null): string {
  return documentTitle ?? "Sin documento seleccionado";
}

function SelectionPreview({
  correctedDestinationBranchId,
  correctionReasons,
  destinationBranches,
  draftLines,
  isCommitPending,
  isProductSearchPending,
  onCommitTargetLineAdjustment,
  onCorrectedDestinationBranchChange,
  onOpenHistory,
  onProductSearchTextChange,
  onSelectExactProduct,
  onRemoveDraftLine,
  onReasonChange,
  productSearchError,
  productSearchResults,
  productSearchText,
  reasonCode,
  selectedDocument,
  selectedTarget,
  selectedTargetError,
  selectedTargetPending,
  timeZone,
}: {
  correctedDestinationBranchId: string | null;
  correctionReasons: Array<{ code: string; name: string }>;
  destinationBranches: TransferDestinationBranchView[];
  draftLines: CorrectionDraftLine[];
  isCommitPending: boolean;
  isProductSearchPending: boolean;
  onCommitTargetLineAdjustment: (
    line: OperationDocumentLineView,
    direction: CorrectionDirection,
    magnitudeText: string,
  ) => void;
  onCorrectedDestinationBranchChange: (destinationBranchId: string | null) => void;
  onOpenHistory: () => void;
  onProductSearchTextChange: (value: string) => void;
  onSelectExactProduct: (product: CorrectionProductOptionView, magnitudeText: string) => void;
  onRemoveDraftLine: (draftLineKey: string) => void;
  onReasonChange: (reasonCode: string) => void;
  productSearchError: string | null;
  productSearchResults: CorrectionProductOptionView[];
  productSearchText: string;
  reasonCode: string;
  selectedDocument: CorrectionSearchDocumentView | null;
  selectedTarget: CorrectionTargetDetailResponse | null;
  selectedTargetError: string | null;
  selectedTargetPending: boolean;
  timeZone: string;
}) {
  const [editingLineIds, setEditingLineIds] = useState<string[]>([]);
  const [pendingEdits, setPendingEdits] = useState<Record<string, PendingTargetLineEdit>>({});
  const [isAddingProduct, setIsAddingProduct] = useState(false);
  const [selectedProductToAdd, setSelectedProductToAdd] = useState<CorrectionProductOptionView | null>(null);
  const [newProductQuantityText, setNewProductQuantityText] = useState("1");

  useEffect(() => {
    setEditingLineIds([]);
    setPendingEdits({});
    setIsAddingProduct(false);
    setSelectedProductToAdd(null);
    setNewProductQuantityText("1");
  }, [selectedTarget?.target_document.id]);

  const supportsDestinationCorrection =
    selectedTarget?.target_document.document_type === "BRANCH_TRANSFER_SHIPMENT";
  const availableReasonOptions = correctionReasons.filter(
    (reason) =>
      supportsDestinationCorrection || reason.code !== WRONG_DESTINATION_REASON_CODE,
  );
  const availableDestinationBranches = destinationBranches.filter(
    (branch) => branch.id !== selectedTarget?.target_document.destination_branch_id,
  );
  const isWrongDestinationReason = reasonCode === WRONG_DESTINATION_REASON_CODE;
  const isEditingDisabled = isCommitPending || !selectedTarget?.is_correctable;
  const addedDraftLines = draftLines.filter((line) => line.sourceKind === "ADDED_PRODUCT");
  const parsedNewProductQuantity = parseSignedQuantityToMilliUnits(newProductQuantityText);
  const newProductQuantityError =
    selectedProductToAdd !== null && parsedNewProductQuantity === null
      ? "Captura una cantidad mayor que cero."
      : null;

  useEffect(() => {
    if (!isAddingProduct) {
      return;
    }
    if (isWrongDestinationReason || isEditingDisabled) {
      setIsAddingProduct(false);
      setSelectedProductToAdd(null);
      setNewProductQuantityText("1");
      onProductSearchTextChange("");
    }
  }, [isAddingProduct, isEditingDisabled, isWrongDestinationReason, onProductSearchTextChange]);

  if (selectedDocument === null) {
    return (
      <ListDetailColumn
        description="Selecciona un documento para revisar su detalle sin alterar el original."
        title="Sin seleccion"
        tone="muted"
      >
        <div className="grid h-full min-h-0 place-items-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white px-5 py-10 text-center">
          <div className="grid max-w-sm gap-2">
            <p className="text-base font-semibold text-slate-950">Selecciona un documento original.</p>
            <p className="text-sm leading-6 text-slate-600">
              El ajuste crea un documento nuevo y auditable. Aqui solo eliges el caso correcto.
            </p>
          </div>
        </div>
      </ListDetailColumn>
    );
  }

  return (
    <ListDetailColumn
      action={
        <Button
          className={cn("h-10 px-4", posOutlineButtonClass)}
          disabled={selectedTarget === null || selectedTargetPending}
          onClick={onOpenHistory}
          type="button"
          variant="outline"
        >
            Historial de ajustes
        </Button>
      }
      description="Selecciona el documento correcto y agrega ajustes sin abrir una pantalla separada de detalle."
      title="Documento seleccionado"
      tone="muted"
    >
      {selectedTargetPending ? (
        <OperationalStatus
          description="Consultando elegibilidad y lineas originales."
          title="Cargando documento"
        />
      ) : selectedTargetError ? (
        <OperationalStatus
          description={selectedTargetError}
          title="No fue posible revisar el documento"
        />
      ) : selectedTarget ? (
        <div className="flex h-full min-h-0 flex-col gap-3">
          <div className="rounded-xl border border-[var(--pos-shell-border)] bg-white px-4 py-3.5">
            <div className="flex min-w-0 items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="break-words text-sm font-semibold text-slate-950">
                  {selectedTarget.document_title}
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-600">
                  <span className="min-w-0 break-words">
                    {selectedTarget.target_document.source_branch_name}
                  </span>
                  <span aria-hidden="true" className="text-slate-400">
                    |
                  </span>
                  <span className="min-w-0 break-words">
                    {selectedTarget.target_document.workstation_name}
                  </span>
                </div>
              </div>
              <span className="inline-flex min-h-9 shrink-0 items-center rounded-full border border-sky-200 bg-sky-50 px-3 py-1.5 text-sm font-medium text-sky-700">
                Solo lectura. El original no se altera.
              </span>
            </div>

            <div className="mt-3 grid gap-2 text-sm text-slate-600 md:grid-cols-2 xl:grid-cols-4">
              <div className="min-w-0">
                <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Documento
                </span>
                <p className="mt-1 break-words">{getDocumentTypeLabel(selectedTarget.target_document.document_type)}</p>
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Fecha
                </span>
                <p className="mt-1 break-words">
                  {selectedTarget.target_document.committed_at_utc
                    ? formatLocalDateTime(selectedTarget.target_document.committed_at_utc, timeZone)
                    : "Sin hora"}
                </p>
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Ajustes registrados
                </span>
                <p className="mt-1 break-words">
                  {selectedTarget.applied_corrections.length} registradas
                </p>
              </div>
              <div className="min-w-0">
                <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Estado
                </span>
                <p className="mt-1 break-words">
                  {selectedTarget.is_correctable ? "Corregible" : "No corregible"}
                </p>
              </div>
            </div>

            {selectedTarget.target_document.destination_branch_name ? (
              <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-600">
                <span className="font-medium text-slate-700">Destino:</span>
                <span className="min-w-0 break-words">
                  {selectedTarget.target_document.destination_branch_name}
                </span>
              </div>
            ) : null}

            {selectedTarget.blocking_reason ? (
              <div className="mt-3">
                <InlineNotice tone="error">{selectedTarget.blocking_reason}</InlineNotice>
              </div>
            ) : null}
          </div>

          <div className="grid min-h-0 gap-3">
            <div className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-3">
              <div
                className={cn(
                  "grid items-center gap-3",
                  isWrongDestinationReason
                    ? "xl:grid-cols-[auto_minmax(14rem,18rem)_auto_minmax(16rem,1fr)]"
                    : "xl:grid-cols-[auto_minmax(16rem,22rem)]",
                )}
              >
                <span className="text-[13px] font-semibold text-slate-700">Motivo</span>
                <label className="min-w-0">
                  <select
                    className={cn(
                      "h-10 w-full rounded-lg px-3 text-sm shadow-sm",
                      posInputClass,
                      reasonCode.trim().length === 0 &&
                        "border-[var(--ui-color-danger)] text-[var(--ui-color-danger)]",
                    )}
                    disabled={isEditingDisabled}
                    onChange={(event) => onReasonChange(event.target.value)}
                    value={reasonCode}
                  >
                    <option value="">Selecciona un motivo</option>
                    {availableReasonOptions.map((reason) => (
                      <option key={reason.code} value={reason.code}>
                        {getCorrectionReasonLabel(reason.code, reason.name)}
                      </option>
                    ))}
                  </select>
                </label>

                {isWrongDestinationReason ? (
                  <>
                    <span className="text-[13px] font-semibold text-slate-700">
                      Sucursal destino corregida
                    </span>
                    <label className="min-w-0">
                    <select
                      className={cn(
                        "h-10 w-full rounded-lg px-3 text-sm shadow-sm",
                        posInputClass,
                        correctedDestinationBranchId === null &&
                          "border-[var(--ui-color-danger)] text-[var(--ui-color-danger)]",
                      )}
                      disabled={isEditingDisabled}
                      onChange={(event) =>
                        onCorrectedDestinationBranchChange(
                          event.target.value.length > 0 ? event.target.value : null,
                        )
                      }
                      value={correctedDestinationBranchId ?? ""}
                    >
                      <option value="">Selecciona una sucursal</option>
                      {availableDestinationBranches.map((branch) => (
                        <option key={branch.id} value={branch.id}>
                          {branch.name}
                        </option>
                        ))}
                      </select>
                    </label>
                  </>
                ) : null}
              </div>
            </div>

            <div className="rounded-xl border border-[var(--pos-shell-border)] bg-white">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--pos-shell-border)] px-4 py-3">
                <div>
                  <p className="text-sm font-semibold text-slate-950">Lineas originales</p>
                  <p className="mt-1 text-sm text-slate-600">
                    Ajusta cantidades aqui mismo. El borrador se actualiza sin salir de esta vista.
                  </p>
                </div>

                <Button
                  className={cn("h-9 px-3", posOutlineButtonClass)}
                  disabled={isEditingDisabled || isWrongDestinationReason}
                  onClick={() => {
                    setIsAddingProduct((current) => !current);
                    setSelectedProductToAdd(null);
                    setNewProductQuantityText("1");
                    onProductSearchTextChange("");
                  }}
                  type="button"
                  variant="outline"
                >
                  Agregar producto
                </Button>
              </div>

              <div className="min-h-0 overflow-hidden">
                {isAddingProduct ? (
                  <div className="grid gap-3 border-b border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-3">
                    <SearchField
                      ariaLabel="Buscar producto para agregar"
                      className="w-full"
                      disabled={isEditingDisabled}
                      inputClassName={cn("h-10 rounded-lg text-sm shadow-sm", posInputClass)}
                      onChange={onProductSearchTextChange}
                      placeholder="Buscar por nombre o codigo"
                      value={productSearchText}
                    />

                    {selectedProductToAdd ? (
                      <div className="grid gap-3 rounded-xl border border-[var(--pos-shell-border)] bg-white px-4 py-3 sm:grid-cols-[minmax(0,1fr)_8rem_auto] sm:items-end">
                        <div className="min-w-0">
                          <p className="break-words text-sm font-semibold text-slate-950">
                            {selectedProductToAdd.name}
                          </p>
                          <p className="mt-1 break-words text-sm text-slate-600">
                            {selectedProductToAdd.product_class_name} | {selectedProductToAdd.code}
                          </p>
                        </div>

                        <label className="grid gap-1">
                          <span className="text-xs font-semibold text-slate-700">Cantidad</span>
                          <input
                            className={cn(
                              "h-10 rounded-lg px-3 text-sm shadow-sm",
                              posInputClass,
                              newProductQuantityError &&
                                "border-[var(--ui-color-danger)] text-[var(--ui-color-danger)]",
                            )}
                            disabled={isEditingDisabled}
                            inputMode="decimal"
                            onChange={(event) => setNewProductQuantityText(event.target.value)}
                            placeholder="1"
                            value={newProductQuantityText}
                          />
                        </label>

                        <div className="flex flex-wrap items-center gap-2">
                          <Button
                            className={cn("h-10 px-3", posOutlineButtonClass)}
                            disabled={isEditingDisabled}
                            onClick={() => {
                              setSelectedProductToAdd(null);
                              setNewProductQuantityText("1");
                            }}
                            type="button"
                            variant="outline"
                          >
                            Cambiar
                          </Button>
                          <Button
                            className={cn("h-10 px-3", posPrimaryButtonClass)}
                            disabled={isEditingDisabled || newProductQuantityError !== null}
                            onClick={() => {
                              if (!selectedProductToAdd || newProductQuantityError !== null) {
                                return;
                              }
                              onSelectExactProduct(selectedProductToAdd, newProductQuantityText);
                              setIsAddingProduct(false);
                              setSelectedProductToAdd(null);
                              setNewProductQuantityText("1");
                            }}
                            type="button"
                          >
                            Agregar
                          </Button>
                        </div>

                        {newProductQuantityError ? (
                          <p className="sm:col-span-3 text-xs leading-5 text-[var(--ui-color-danger)]">
                            {newProductQuantityError}
                          </p>
                        ) : null}
                      </div>
                    ) : productSearchText.trim().length === 0 ? (
                      <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white px-4 py-5 text-sm text-slate-600">
                        Busca el producto y luego captura la cantidad a agregar.
                      </div>
                    ) : isProductSearchPending ? (
                      <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white px-4 py-5 text-sm text-slate-600">
                        Buscando productos...
                      </div>
                    ) : productSearchError ? (
                      <InlineNotice tone="error">{productSearchError}</InlineNotice>
                    ) : productSearchResults.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white px-4 py-5 text-sm text-slate-600">
                        No hay productos que coincidan con la busqueda.
                      </div>
                    ) : (
                      <ScrollPane className="max-h-56">
                        <div className="grid gap-2">
                          {productSearchResults.map((product) => (
                            <button
                              className="grid gap-1 rounded-xl border border-[var(--pos-shell-border)] bg-white px-4 py-3 text-left transition hover:border-[var(--pos-primary)]/35 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
                              key={product.id}
                              onClick={() => setSelectedProductToAdd(product)}
                              type="button"
                            >
                              <span className="break-words text-sm font-semibold text-slate-950">
                                {product.name}
                              </span>
                              <span className="break-words text-sm text-slate-600">
                                {product.product_class_name} | {product.code}
                              </span>
                            </button>
                          ))}
                        </div>
                      </ScrollPane>
                    )}
                  </div>
                ) : null}

                <ScrollPane className="min-h-0">
                  <table className="w-full border-separate border-spacing-0">
                    <thead className="bg-slate-50">
                      <tr className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                        <th className="px-3 py-2 text-left">Linea</th>
                        <th className="px-3 py-2 text-left">Articulo</th>
                        <th className="px-3 py-2 text-right">Original</th>
                        <th className="px-3 py-2 text-left">Ajuste</th>
                        <th className="px-3 py-2 text-left">Efecto</th>
                        <th className="px-3 py-2 text-right">Accion</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--pos-shell-border)]">
                      {selectedTarget.target_document.lines.map((line) => {
                        const draftLine =
                          draftLines.find((candidate) => candidate.targetLineId === line.id) ?? null;
                        const isEditing = editingLineIds.includes(line.id);
                        const editState =
                          pendingEdits[line.id] ??
                          (isEditing ? createPendingTargetLineEdit(draftLine) : null);

                        return (
                          <OriginalLineTableRow
                            disabled={!selectedTarget.is_correctable || isCommitPending}
                            draftLine={draftLine}
                            editState={editState}
                            isEditing={isEditing}
                            key={line.id}
                            line={line}
                            onCancel={() => {
                              setEditingLineIds((current) =>
                                current.filter((lineId) => lineId !== line.id),
                              );
                              setPendingEdits((current) => {
                                const nextState = { ...current };
                                delete nextState[line.id];
                                return nextState;
                              });
                            }}
                            onConfirm={() => {
                              if (!editState) {
                                return;
                              }

                              onCommitTargetLineAdjustment(
                                line,
                                editState.direction,
                                editState.magnitudeText,
                              );
                              setEditingLineIds((current) =>
                                current.filter((lineId) => lineId !== line.id),
                              );
                              setPendingEdits((current) => {
                                const nextState = { ...current };
                                delete nextState[line.id];
                                return nextState;
                              });
                            }}
                            onEditChange={(nextState) =>
                              setPendingEdits((current) => ({
                                ...current,
                                [line.id]: nextState,
                              }))
                            }
                            onRemove={() => {
                              if (draftLine) {
                                onRemoveDraftLine(draftLine.key);
                              }
                            }}
                            onStartEditing={() => {
                              setEditingLineIds((current) =>
                                current.includes(line.id) ? current : [...current, line.id],
                              );
                              setPendingEdits((current) =>
                                current[line.id]
                                  ? current
                                  : {
                                      ...current,
                                      [line.id]: createPendingTargetLineEdit(draftLine),
                                    },
                              );
                            }}
                          />
                        );
                      })}
                      {addedDraftLines.map((draftLine) => {
                        const parsedQuantity =
                          parseSignedQuantityToMilliUnits(draftLine.deltaQuantityText);
                        const effectLabel =
                          parsedQuantity === null
                            ? "Pendiente"
                            : getSignedEffectLabel(parsedQuantity);

                        return (
                          <tr className="align-top transition hover:bg-slate-50/80" key={draftLine.key}>
                            <td className="px-3 py-3 text-sm text-slate-600">Nuevo</td>
                            <td className="min-w-0 px-3 py-3">
                              <div className="min-w-0">
                                <p className="break-words text-sm font-semibold text-slate-950">
                                  {draftLine.productName}
                                </p>
                                <p className="mt-1 break-words text-xs leading-5 text-slate-500">
                                  {draftLine.productClassName} | {draftLine.productCode}
                                </p>
                              </div>
                            </td>
                            <td className="px-3 py-3 text-right text-sm font-semibold text-slate-400">
                              --
                            </td>
                            <td className="px-3 py-3">
                              <span className="inline-flex min-h-9 items-center rounded-full bg-slate-100 px-3 text-sm font-medium text-slate-700">
                                Suma {getCorrectionDraftLineMagnitudeText(draftLine)}
                              </span>
                            </td>
                            <td className="px-3 py-3">
                              <span className="inline-flex min-h-9 items-center rounded-full bg-emerald-50 px-3 text-sm font-semibold text-emerald-700">
                                {effectLabel}
                              </span>
                            </td>
                            <td className="px-3 py-3 text-right">
                              <Button
                                className={cn("h-9 px-3", posOutlineButtonClass)}
                                disabled={isEditingDisabled}
                                onClick={() => onRemoveDraftLine(draftLine.key)}
                                type="button"
                                variant="outline"
                              >
                                Quitar
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </ScrollPane>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </ListDetailColumn>
  );
}

function TargetDocumentRecordContent({
  document,
  eligibility,
  timeZone,
}: {
  document: CorrectionSearchDocumentView;
  eligibility:
    | {
        blockingReason: string | null;
        isCorrectable: boolean;
        isPending: boolean;
      }
    | undefined;
  timeZone: string;
}) {
  return (
    <div className="grid gap-1.5 px-1 py-0.5">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="break-words text-sm font-semibold leading-5 text-slate-950">
            {document.display_title}
          </p>
          <span className="pos-chip" data-tone="muted">
            {getDocumentTypeLabel(document.document_type)}
          </span>
          <span className="pos-chip" data-tone="primary">
            {document.folio}
          </span>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs leading-5 text-slate-500">
          <span>
            {document.committed_at_utc
              ? formatLocalDateTime(document.committed_at_utc, timeZone)
              : "Sin hora de confirmacion"}
          </span>
          <span aria-hidden="true" className="text-slate-400">
            |
          </span>
          <span>{document.workstation_name}</span>
          <span aria-hidden="true" className="text-slate-400">
            |
          </span>
          <span>{document.correction_count} ajustes</span>
          {eligibility && !eligibility.isPending ? (
            <>
              <span aria-hidden="true" className="text-slate-400">
                |
              </span>
              <span
                className={cn(
                  "font-medium",
                  eligibility.isCorrectable ? "text-emerald-700" : "text-rose-600",
                )}
                title={eligibility.blockingReason ?? undefined}
              >
                {eligibility.isCorrectable ? "Lista" : "Bloqueado"}
              </span>
            </>
          ) : null}
        </div>
      </div>

      <div className="grid gap-1 text-xs leading-5 text-slate-500">
        <div className="min-w-0 break-words" title={document.source_branch_name}>
          {document.source_branch_name}
          {document.destination_branch_name ? ` -> ${document.destination_branch_name}` : ""}
        </div>
      </div>
    </div>
  );
}

type PendingTargetLineEdit = {
  direction: CorrectionDirection;
  magnitudeText: string;
};

function createPendingTargetLineEdit(
  draftLine: CorrectionDraftLine | null,
): PendingTargetLineEdit {
  return {
    direction: draftLine ? getCorrectionDraftLineDirection(draftLine) : "DECREASE",
    magnitudeText: draftLine ? getCorrectionDraftLineMagnitudeText(draftLine) : "1",
  };
}

function parsePendingTargetLineEdit(edit: PendingTargetLineEdit): number | null {
  const trimmedMagnitude = edit.magnitudeText.trim();
  if (trimmedMagnitude.length === 0) {
    return null;
  }

  return parseSignedQuantityToMilliUnits(
    edit.direction === "DECREASE" ? `-${trimmedMagnitude}` : trimmedMagnitude,
  );
}

function getPendingTargetLineSummary(edit: PendingTargetLineEdit | null): string {
  if (edit === null) {
    return "Sin ajuste";
  }

  const parsedQuantity = parsePendingTargetLineEdit(edit);
  if (parsedQuantity === null) {
    return "Pendiente";
  }

  return `${edit.direction === "DECREASE" ? "Resta" : "Suma"} ${formatQuantityFromMilliUnits(
    Math.abs(parsedQuantity),
  )}`;
}

function OriginalLineTableRow({
  disabled,
  draftLine,
  editState,
  isEditing,
  line,
  onCancel,
  onConfirm,
  onEditChange,
  onRemove,
  onStartEditing,
}: {
  disabled: boolean;
  draftLine: CorrectionDraftLine | null;
  editState: PendingTargetLineEdit | null;
  isEditing: boolean;
  line: OperationDocumentLineView;
  onCancel: () => void;
  onConfirm: () => void;
  onEditChange: (nextState: PendingTargetLineEdit) => void;
  onRemove: () => void;
  onStartEditing: () => void;
}) {
  const parsedEditQuantity = editState ? parsePendingTargetLineEdit(editState) : null;
  const parsedDraftQuantity = draftLine
    ? parseSignedQuantityToMilliUnits(draftLine.deltaQuantityText)
    : null;
  const validationMessage =
    isEditing && parsedEditQuantity === null ? "Captura una cantidad mayor que cero." : null;
  const effectLabel =
    draftLine && !isEditing
      ? parsedDraftQuantity === null
        ? "Pendiente"
        : getSignedEffectLabel(parsedDraftQuantity)
      : parsedEditQuantity === null
        ? "Pendiente"
        : getSignedEffectLabel(parsedEditQuantity);
  const hasEffect = parsedDraftQuantity !== null || parsedEditQuantity !== null;

  return (
    <tr
      className="align-top transition hover:bg-slate-50/80"
      data-correction-line-row={line.id}
    >
      <td className="px-3 py-3 text-sm text-slate-600">{line.line_number}</td>
      <td className="min-w-0 px-3 py-3">
        <div className="min-w-0">
          <p className="break-words text-sm font-semibold text-slate-950">
            {line.product_name_snapshot}
          </p>
          <p className="mt-1 break-words text-xs leading-5 text-slate-500">
            {line.product_class_name_snapshot} | {line.product_code_snapshot}
          </p>
        </div>
      </td>
      <td className="px-3 py-3 text-right text-sm font-semibold text-slate-950">
        {formatQuantity(line.quantity)}
      </td>
      <td className="px-3 py-3">
        {isEditing && editState ? (
          <div className="grid gap-2 sm:grid-cols-[7.5rem_minmax(6rem,7rem)]">
            <select
              className={cn("h-9 w-full rounded-lg px-3 text-sm shadow-sm", posInputClass)}
              disabled={disabled}
              onChange={(event) =>
                onEditChange({
                  ...editState,
                  direction: event.target.value as CorrectionDirection,
                })
              }
              value={editState.direction}
            >
              <option value="DECREASE">Restar</option>
              <option value="INCREASE">Sumar</option>
            </select>
            <input
              className={cn(
                "h-9 w-full rounded-lg px-3 text-sm shadow-sm",
                posInputClass,
                validationMessage &&
                  "border-[var(--ui-color-danger)] text-[var(--ui-color-danger)]",
              )}
              disabled={disabled}
              inputMode="decimal"
              onChange={(event) =>
                onEditChange({
                  ...editState,
                  magnitudeText: event.target.value,
                })
              }
              placeholder="1"
              value={editState.magnitudeText}
            />
          </div>
        ) : (
          <span
            className={cn(
              "inline-flex min-h-9 items-center rounded-full px-3 text-sm font-medium",
              draftLine === null ? "bg-slate-100 text-slate-500" : "bg-slate-100 text-slate-700",
            )}
          >
            {draftLine
              ? getPendingTargetLineSummary(createPendingTargetLineEdit(draftLine))
              : "Sin ajuste"}
          </span>
        )}
        {validationMessage ? (
          <p className="mt-1 text-xs leading-5 text-[var(--ui-color-danger)]">
            {validationMessage}
          </p>
        ) : null}
      </td>
      <td className="px-3 py-3">
        <span
          className={cn(
            "inline-flex min-h-9 items-center rounded-full px-3 text-sm font-semibold",
            !hasEffect
              ? "bg-slate-100 text-slate-500"
              : effectLabel.startsWith("+")
                ? "bg-emerald-50 text-emerald-700"
                : effectLabel.startsWith("-")
                  ? "bg-amber-50 text-amber-700"
                  : "bg-slate-100 text-slate-700",
          )}
        >
          {effectLabel}
        </span>
      </td>
      <td className="px-3 py-3">
        <div className="flex flex-wrap items-center justify-end gap-2">
          {isEditing ? (
            <>
              <Button
                className={cn("h-9 px-3", posOutlineButtonClass)}
                disabled={disabled}
                onClick={onCancel}
                type="button"
                variant="outline"
              >
                Cancelar
              </Button>
              <Button
                className={cn("h-9 px-3", posPrimaryButtonClass)}
                disabled={disabled || validationMessage !== null}
                onClick={onConfirm}
                type="button"
              >
                Confirmar
              </Button>
            </>
          ) : (
            <>
              <Button
                className={cn("h-9 px-3", posOutlineButtonClass)}
                disabled={disabled}
                onClick={onStartEditing}
                type="button"
                variant="outline"
              >
                Ajustar
              </Button>
              {draftLine ? (
                <Button
                  className={cn("h-9 px-3", posOutlineButtonClass)}
                  disabled={disabled}
                  onClick={onRemove}
                  type="button"
                  variant="outline"
                >
                  Quitar
                </Button>
              ) : null}
            </>
          )}
        </div>
      </td>
    </tr>
  );
}

function CorrectionConfirmationDialog({
  affectedDocumentLabel,
  branchName,
  documentReference,
  documentTitle,
  isOpen,
  isHighImpact,
  isPending,
  lineSummaryItems,
  lineCount,
  netEffectLabel,
  onCancel,
  onConfirm,
  reasonLabel,
  userName,
  workstationName,
}: {
  affectedDocumentLabel?: string | null;
  branchName?: string;
  documentReference: string;
  documentTitle: string;
  isOpen: boolean;
  isHighImpact: boolean;
  isPending: boolean;
  lineSummaryItems: OperationLineSummaryItem[];
  lineCount: number;
  netEffectLabel: string;
  onCancel: () => void;
  onConfirm: () => void;
  reasonLabel: string;
  userName?: string;
  workstationName?: string;
}) {
  return (
    <OperationConfirmationDialog
      confirmLabel={isPending ? "Registrando..." : "Confirmar ajuste"}
      confirmationTone={isHighImpact ? "danger" : "warning"}
      context={{
        branchName,
        userName,
        workstationName,
      }}
      description={
        isHighImpact
          ? "Este ajuste supera el umbral de alto impacto y dejara una alerta para backoffice."
          : "Se registrara un ajuste nuevo y auditable sin alterar el documento original."
      }
      isOpen={isOpen}
      isPending={isPending}
      kind="correction"
      lines={lineSummaryItems}
      metrics={[
        {
          key: "document-title",
          label: "Documento",
          value: documentTitle,
        },
        {
          key: "line-count",
          label: "Lineas",
          value: String(lineCount),
        },
        {
          key: "reason",
          label: "Motivo",
          value: reasonLabel,
        },
        {
          key: "net-effect",
          label: "Efecto neto",
          tone: "financial",
          value: netEffectLabel,
        },
        ...(affectedDocumentLabel
          ? [
              {
                key: "affected-document-type",
                label: "Documento afectado",
                value: affectedDocumentLabel,
              } satisfies OperationDocumentMetric,
            ]
          : []),
      ]}
      onCancel={onCancel}
      onConfirm={onConfirm}
      referenceLabel="Folio documento"
      referenceValue={documentReference}
      title="Confirmar ajuste auditado"
    />
  );
}

function CorrectionsSummaryPanel({
  blockedMessages,
  branchName,
  commitError,
  correctedDestinationLabel,
  documentReference,
  documentTitle,
  draftSummaryLines,
  draftReasonLabel,
  isHighImpactAcknowledged,
  isHighImpactAdjustment,
  lastHighImpactAlertRequested,
  lastCommittedCorrection,
  netEffectMilliUnits,
  onAcknowledgeHighImpact,
  onCommit,
  onResultAction,
  originalDateText,
  selectedTarget,
  timeZone,
  totalAdjustedQuantityMilliUnits,
  uiState,
  userName,
  workstationName,
}: {
  blockedMessages: string[];
  branchName: string;
  commitError: string | null;
  correctedDestinationLabel: string | null;
  documentReference: string | null;
  documentTitle: string | null;
  draftSummaryLines: OperationLineSummaryItem[];
  draftReasonLabel: string | null;
  isHighImpactAcknowledged: boolean;
  isHighImpactAdjustment: boolean;
  lastHighImpactAlertRequested: boolean;
  lastCommittedCorrection: CorrectionDocumentView | null;
  netEffectMilliUnits: number;
  onAcknowledgeHighImpact: (checked: boolean) => void;
  onCommit: () => void;
  onResultAction: OperationDocumentAction[];
  originalDateText: string;
  selectedTarget: CorrectionTargetDetailResponse | null;
  timeZone: string;
  totalAdjustedQuantityMilliUnits: number;
  uiState: CorrectionUiState;
  userName: string;
  workstationName: string;
}) {
  if (lastCommittedCorrection) {
    return (
      <OperationDocumentResult
        actions={onResultAction}
        auditSummary={lastCommittedCorrection.audit_summary}
        context={{
          branchName,
          userName,
          workstationName,
        }}
        description={
          lastHighImpactAlertRequested
            ? "El ajuste ya quedo auditado y se preparo una alerta para backoffice."
            : "El ajuste quedo registrado y auditado."
        }
        kind="correction"
        metrics={[
          {
            key: "reason",
            label: "Motivo",
            value: getCorrectionReasonLabel(
              lastCommittedCorrection.reason_code,
              lastCommittedCorrection.reason_name,
            ),
          },
          {
            key: "line-count",
            label: "Lineas",
            value: String(lastCommittedCorrection.lines.length),
          },
          ...(lastHighImpactAlertRequested
            ? [
                {
                  key: "alert",
                  label: "Alerta",
                  tone: "warning",
                  value: "Backoffice",
                } satisfies OperationDocumentMetric,
              ]
            : []),
        ]}
        referenceValue={getCorrectionReference(lastCommittedCorrection)}
        timeZone={timeZone}
        timestamps={{
          committedAtValue: lastCommittedCorrection.committed_at_utc
            ? formatLocalDateTime(lastCommittedCorrection.committed_at_utc, timeZone)
            : null,
          createdAtValue: formatLocalDateTime(lastCommittedCorrection.created_at_utc, timeZone),
        }}
        title="Ajuste auditado registrado"
      />
    );
  }

  const notices = (
    <div className="grid gap-2">
      {commitError ? <InlineNotice tone="error">{commitError}</InlineNotice> : null}
      {isHighImpactAdjustment ? (
        <div className="rounded-xl border border-[rgba(187,122,22,0.2)] bg-[var(--ui-color-warning-soft)] px-3 py-3">
          <p className="text-sm font-semibold text-slate-950">
            {getCorrectionHighImpactLabel(
              formatQuantityFromMilliUnits(totalAdjustedQuantityMilliUnits),
            )}
          </p>
          <p className="mt-1 text-sm text-slate-700">
            El ajuste puede registrarse con este cajero, pero debe quedar reconocido y enviara una alerta a backoffice.
          </p>
          <label className="mt-3 flex items-start gap-2 text-sm text-slate-700">
            <input
              checked={isHighImpactAcknowledged}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-[var(--pos-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--pos-focus-ring)]"
              onChange={(event) => onAcknowledgeHighImpact(event.target.checked)}
              type="checkbox"
            />
            <span>Confirmo que este ajuste de alto impacto fue verificado antes de registrarlo.</span>
          </label>
        </div>
      ) : null}
    </div>
  );

  return (
    <OperationDocumentSummaryPanel
      actions={[
        {
          disabled: blockedMessages.length > 0 || uiState === "CONFIRMING",
          key: "confirm-correction",
          label: uiState === "CONFIRMING" ? "Registrando ajuste..." : "Confirmar ajuste",
          onSelect: onCommit,
          variant: "primary",
        },
      ]}
      blockers={[
        ...(selectedTarget?.blocking_reason
          ? [{ key: "target-blocking-reason", message: selectedTarget.blocking_reason }]
          : []),
        ...blockedMessages.map((message, index) => ({
          key: `draft-blocker-${index}`,
          message,
        })),
      ]}
      auditSummary={selectedTarget?.target_document.audit_summary}
      context={{
        branchName,
        userName,
        workstationName,
      }}
      description={
        <span>
          Documento original: {getOriginalDocumentLabel(documentTitle)}
          {originalDateText ? ` · ${originalDateText}` : ""}
        </span>
      }
      kind="correction"
      lines={draftSummaryLines}
      metrics={[
        {
          key: "document-reference",
          label: "Documento",
          value: documentReference ?? "Pendiente",
        },
        {
          key: "reason",
          label: "Motivo",
          value: draftReasonLabel ?? "Pendiente",
        },
        ...(correctedDestinationLabel
          ? [
              {
                key: "destination",
                label: "Destino corregido",
                value: correctedDestinationLabel,
              } satisfies OperationDocumentMetric,
            ]
          : []),
        {
          key: "line-count",
          label: "Lineas",
          value: String(draftSummaryLines.length),
        },
        {
          key: "net-effect",
          label: "Efecto neto",
          tone: "financial",
          value: getSignedEffectLabel(netEffectMilliUnits),
        },
      ]}
      notices={notices}
      referenceLabel="Folio documento"
      referenceValue={documentReference}
      stateLabel={getCorrectionUiStateLabel(uiState)}
      stateTone={getCorrectionSummaryStateTone(uiState)}
      timeZone={timeZone}
      title="Resumen del ajuste"
    />
  );
}

export function CorrectionsScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const queryClient = useQueryClient();
  const correctionsBootstrapQuery = useCorrectionsBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const [selectedDocumentType, setSelectedDocumentType] = useState("");
  const [selectedDayScope, setSelectedDayScope] = useState<"all" | "today">("all");
  const [searchText, setSearchText] = useState("");
  const [historyScope, setHistoryScope] = useState("CURRENT_SHIFT");
  const [historySearchText, setHistorySearchText] = useState("");
  const [selectedHistoryCreatedByUserId, setSelectedHistoryCreatedByUserId] = useState("");
  const [selectedHistoryTargetDocumentType, setSelectedHistoryTargetDocumentType] = useState("");
  const [selectedHistoryReasonCode, setSelectedHistoryReasonCode] = useState("");
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);
  const [centerSection, setCenterSection] = useState<CorrectionsCenterSection>("documents");
  const [draftState, setDraftState] = useState(createInitialCorrectionDraftState);
  const [lastCommittedCorrection, setLastCommittedCorrection] =
    useState<CorrectionDocumentView | null>(null);
  const [lastHighImpactAlertRequested, setLastHighImpactAlertRequested] = useState(false);
  const [isHighImpactAcknowledged, setIsHighImpactAcknowledged] = useState(false);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [selectedHistoryCorrectionId, setSelectedHistoryCorrectionId] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const debouncedSearchText = useDebouncedValue(searchText, 220);
  const historySearchInputRef = useRef<HTMLInputElement | null>(null);
  const debouncedHistorySearchText = useDebouncedValue(historySearchText, 220);
  const debouncedProductSearchText = useDebouncedValue(draftState.productSearchText, 220);
  const correctionTargetsQuery = useCorrectionTargetsQuery(
    selectedDocumentType,
    debouncedSearchText,
  );
  const correctionsHistoryQuery = useCorrectionsHistoryQuery(
    historyScope,
    debouncedHistorySearchText,
    selectedHistoryCreatedByUserId,
    selectedHistoryTargetDocumentType,
    selectedHistoryReasonCode,
  );
  const correctionHistoryDetailQuery = useCorrectionDocumentDetailQuery(selectedHistoryCorrectionId);
  const correctionTargetDetailQuery = useCorrectionTargetDetailQuery(selectedTargetId);
  const correctionProductsQuery = useCorrectionProductsQuery(debouncedProductSearchText);
  const allDocuments = useMemo(
    () => correctionTargetsQuery.data?.documents ?? [],
    [correctionTargetsQuery.data?.documents],
  );
  const timeZone = correctionsBootstrapQuery.data?.branch.timezone ?? "UTC";
  const documents = useMemo(
    () =>
      selectedDayScope === "today"
        ? allDocuments.filter((document) => isTodayInTimeZone(document.committed_at_utc, timeZone))
        : allDocuments,
    [allDocuments, selectedDayScope, timeZone],
  );
  const selectedSearchDocument = useMemo(
    () => documents.find((document) => document.id === selectedTargetId) ?? null,
    [documents, selectedTargetId],
  );

  const eligibilityQueries = useQueries({
    queries: documents.map((document) => ({
      queryKey: correctionTargetDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, document.id),
      queryFn: () =>
        getCorrectionTargetDetail({
          accessToken: accessToken!,
          targetDocumentId: document.id,
          workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        }),
      enabled: accessToken !== null && document.id !== selectedTargetId,
      staleTime: 60_000,
    })),
  });

  useEffect(() => {
    if (selectedTargetId !== null && !documents.some((document) => document.id === selectedTargetId)) {
      setSelectedTargetId(null);
      setCenterSection("documents");
    }
  }, [documents, selectedTargetId]);

  const eligibilityByDocumentId = useMemo(() => {
    const map = new Map<
      string,
      {
        blockingReason: string | null;
        isCorrectable: boolean;
        isPending: boolean;
      }
    >();

    documents.forEach((document, index) => {
      if (document.id === selectedTargetId) {
        if (correctionTargetDetailQuery.data) {
          map.set(document.id, {
            blockingReason: correctionTargetDetailQuery.data.blocking_reason,
            isCorrectable: correctionTargetDetailQuery.data.is_correctable,
            isPending: false,
          });
          return;
        }

        map.set(document.id, {
          blockingReason: null,
          isCorrectable: false,
          isPending: correctionTargetDetailQuery.isPending,
        });
        return;
      }

      const query = eligibilityQueries[index];
      if (query?.data) {
        map.set(document.id, {
          blockingReason: query.data.blocking_reason,
          isCorrectable: query.data.is_correctable,
          isPending: false,
        });
        return;
      }

      map.set(document.id, {
        blockingReason: null,
        isCorrectable: false,
        isPending: Boolean(query?.isPending || query?.isFetching),
      });
    });

    return map;
  }, [
    correctionTargetDetailQuery.data,
    correctionTargetDetailQuery.isPending,
    documents,
    eligibilityQueries,
    selectedTargetId,
  ]);
  const selectedTarget = correctionTargetDetailQuery.data ?? null;
  const isWrongDestinationReason = draftState.reasonCode === WRONG_DESTINATION_REASON_CODE;
  const hasDestinationCorrection =
    isWrongDestinationReason && draftState.correctedDestinationBranchId !== null;
  const hasDraftWork = draftState.lines.length > 0 || hasDestinationCorrection;
  const hasInvalidQuantity = hasCorrectionDraftInvalidQuantity(draftState.lines);
  const totalAdjustedQuantityMilliUnits = getCorrectionDraftTotalAdjustedQuantityMilliUnits(
    draftState.lines,
  );
  const correctionHighImpactThresholdMilliUnits =
    parseSignedQuantityToMilliUnits(
      String(
        correctionsBootstrapQuery.data?.correction_controls.high_impact_quantity_threshold ?? "0",
      ),
    ) ?? 0;
  const isHighImpactAdjustment =
    correctionHighImpactThresholdMilliUnits > 0 &&
    totalAdjustedQuantityMilliUnits >= correctionHighImpactThresholdMilliUnits;
  const isReasonMissing =
    hasDraftWork && hasCorrectionDraftMissingReason(draftState.reasonCode);
  const blockedReason = getCorrectionDraftBlockedReason({
    hasHighImpactAcknowledgement: isHighImpactAcknowledged,
    correctedDestinationBranchId: draftState.correctedDestinationBranchId,
    hasSelectedTarget: selectedTarget !== null,
    highImpactAcknowledgementRequired: isHighImpactAdjustment,
    isCorrectable: selectedTarget?.is_correctable ?? false,
    lines: draftState.lines,
    reasonAllowsDestinationCorrection: isWrongDestinationReason,
    reasonCode: draftState.reasonCode,
  });

  useEffect(() => {
    if (selectedTargetId === null) {
      return;
    }

    if (!documents.some((document) => document.id === selectedTargetId)) {
      setSelectedTargetId(null);
      setCenterSection("documents");
    }
  }, [documents, selectedTargetId]);

  useEffect(() => {
    setDraftState(createInitialCorrectionDraftState());
    setCommitError(null);
    setLastCommittedCorrection(null);
    setLastHighImpactAlertRequested(false);
    setIsHighImpactAcknowledged(false);
    setIsConfirmDialogOpen(false);
    setSelectedHistoryCorrectionId(null);
  }, [selectedTargetId]);

  useEffect(() => {
    if (selectedTargetId === null) {
      setCenterSection("documents");
    }
  }, [selectedTargetId]);

  useEffect(() => {
    if (!isHighImpactAdjustment && isHighImpactAcknowledged) {
      setIsHighImpactAcknowledged(false);
    }
  }, [isHighImpactAcknowledged, isHighImpactAdjustment]);

  useEffect(() => {
    if (selectedTargetId === null && centerSection === "documents") {
      searchInputRef.current?.focus();
    }
  }, [centerSection, selectedTargetId]);

  useEffect(() => {
    if (centerSection !== "history") {
      return;
    }

    const historyRecords = correctionsHistoryQuery.data?.records ?? [];
    if (historyRecords.length === 0) {
      setSelectedHistoryCorrectionId(null);
      return;
    }

    if (
      selectedHistoryCorrectionId &&
      historyRecords.some((record) => record.id === selectedHistoryCorrectionId)
    ) {
      return;
    }

    if (lastCommittedCorrection) {
      const committedRecord = historyRecords.find((record) => record.id === lastCommittedCorrection.id);
      if (committedRecord) {
        setSelectedHistoryCorrectionId(committedRecord.id);
        return;
      }
    }

    setSelectedHistoryCorrectionId(historyRecords[0]?.id ?? null);
  }, [
    centerSection,
    correctionsHistoryQuery.data?.records,
    lastCommittedCorrection,
    selectedHistoryCorrectionId,
  ]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) {
        return;
      }

      const isInteractiveTrigger =
        event.target instanceof HTMLElement &&
        event.target.closest("button, a, [role=\"button\"], summary") !== null;

      if (event.key === "Enter" && !isConfirmDialogOpen) {
        if (isInteractiveTrigger) {
          return;
        }

        if (centerSection === "documents" && selectedTarget?.is_correctable) {
          event.preventDefault();
          setCenterSection("history");
          return;
        }

        return;
      }

      if (event.key !== "Escape") {
        return;
      }

      if (isConfirmDialogOpen) {
        event.preventDefault();
        setIsConfirmDialogOpen(false);
        return;
      }

      if (centerSection === "history") {
        event.preventDefault();
        setCenterSection("documents");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [blockedReason, centerSection, isConfirmDialogOpen, selectedTarget]);

  const updateDraftState = (
    updater: (
      current: ReturnType<typeof createInitialCorrectionDraftState>,
    ) => ReturnType<typeof createInitialCorrectionDraftState>,
  ) => {
    setLastCommittedCorrection(null);
    setCommitError(null);
    setDraftState(updater);
  };

  const commitMutation = useMutation({
    mutationFn: async () => {
      if (!accessToken || !selectedTargetId) {
        throw new Error("Selecciona un documento antes de confirmar el ajuste.");
      }

      return commitCorrection({
        accessToken,
        payload: {
          high_impact_acknowledged: isHighImpactAcknowledged,
          workstation_code: appEnv.VITE_POS_WORKSTATION_CODE,
          target_document_id: selectedTargetId,
          reason_code: draftState.reasonCode,
          corrected_destination_branch_id:
            draftState.reasonCode === WRONG_DESTINATION_REASON_CODE
              ? draftState.correctedDestinationBranchId ?? undefined
              : undefined,
          notes: draftState.notes.trim().length > 0 ? draftState.notes.trim() : undefined,
          lines:
            draftState.reasonCode === WRONG_DESTINATION_REASON_CODE
              ? []
              : buildCorrectionCommitLines(draftState.lines),
        },
        requestId: createRequestId("correction"),
      });
    },
    onSuccess: async (result) => {
      const correctionAlertRequested =
        isHighImpactAdjustment && result.lines.length > 0;
      setLastCommittedCorrection(result);
      setLastHighImpactAlertRequested(correctionAlertRequested);
      setSelectedHistoryCorrectionId(result.id);
      setDraftState(createInitialCorrectionDraftState());
      setCommitError(null);
      setIsHighImpactAcknowledged(false);
      setIsConfirmDialogOpen(false);
      setCenterSection("documents");
      showSuccess(
        correctionAlertRequested
          ? `Ajuste ${getCorrectionReference(result)} registrado. Se preparo alerta para backoffice.`
          : `Ajuste ${getCorrectionReference(result)} registrado correctamente.`,
      );
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: correctionsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: ["corrections", "search", appEnv.VITE_POS_WORKSTATION_CODE],
        }),
        queryClient.invalidateQueries({
          queryKey: ["corrections", "history", appEnv.VITE_POS_WORKSTATION_CODE],
        }),
        selectedTargetId
          ? queryClient.invalidateQueries({
              queryKey: correctionTargetDetailQueryKey(
                appEnv.VITE_POS_WORKSTATION_CODE,
                selectedTargetId,
              ),
            })
          : Promise.resolve(),
        queryClient.invalidateQueries({
          queryKey: ["corrections", "history-detail", appEnv.VITE_POS_WORKSTATION_CODE, result.id],
        }),
      ]);
    },
    onError: (error) => {
      const message = toOperationalErrorMessage(
        error,
        "No fue posible registrar el ajuste.",
      );
      setCommitError(message);
      setIsConfirmDialogOpen(false);
      showError(message);
    },
  });

  const selectedReasonLabel =
    draftState.reasonCode.trim().length > 0
      ? getCorrectionReasonLabel(draftState.reasonCode)
      : null;
  const correctedDestinationLabel =
    draftState.correctedDestinationBranchId !== null
      ? correctionsBootstrapQuery.data?.destination_branches.find(
          (branch) => branch.id === draftState.correctedDestinationBranchId,
        )?.name ?? null
      : null;
  const netEffectMilliUnits = getCorrectionDraftNetQuantityMilliUnits(draftState.lines);
  const uiState = getCorrectionUiState({
    centerSection,
    commitError,
    hasDraftWork,
    hasCommitted: lastCommittedCorrection !== null,
    hasInvalidQuantity,
    hasSelectedTarget: selectedTarget !== null,
    isCommitPending: commitMutation.isPending,
    isReasonMissing,
  });
  const originalDateText =
    selectedTarget?.target_document.committed_at_utc
      ? formatLocalDateTime(
          selectedTarget.target_document.committed_at_utc,
          correctionsBootstrapQuery.data?.branch.timezone ?? "UTC",
        )
      : "Sin hora";
  const draftBlockingMessages = getCorrectionDraftBlockingMessages({
    hasHighImpactAcknowledgement: isHighImpactAcknowledged,
    correctedDestinationBranchId: draftState.correctedDestinationBranchId,
    hasSelectedTarget: selectedTarget !== null,
    highImpactAcknowledgementRequired: isHighImpactAdjustment,
    isCorrectable: selectedTarget?.is_correctable ?? false,
    lines: draftState.lines,
    reasonAllowsDestinationCorrection: isWrongDestinationReason,
    reasonCode: draftState.reasonCode,
  });
  const draftSummaryLines = buildDraftLineSummaryItems({
    draftLines: draftState.lines,
    targetLines: selectedTarget?.target_document.lines ?? [],
  });
  const historyScopeOptions = correctionsHistoryQuery.data?.available_scopes ?? [
    { code: "CURRENT_SHIFT", label: "Turno actual" },
    { code: "TODAY", label: "Hoy" },
    { code: "RECENT", label: "Recientes" },
  ];
  const historyUserOptions = correctionsHistoryQuery.data?.available_users ?? [];
  const historyDocumentTypeOptions = correctionsHistoryQuery.data?.available_document_types ?? [];
  const historyReasonOptions = correctionsHistoryQuery.data?.available_reasons ?? [];
  const historyRecords = useMemo(
    () => buildCorrectionsHistoryRecords(correctionsHistoryQuery.data?.records ?? [], timeZone),
    [correctionsHistoryQuery.data?.records, timeZone],
  );
  const selectedHistoryRecord =
    correctionsHistoryQuery.data?.records.find(
      (correction) => correction.id === selectedHistoryCorrectionId,
    ) ?? null;
  const selectedHistoryCorrection = correctionHistoryDetailQuery.data ?? null;
  const correctionResultActions: OperationDocumentAction[] = useMemo(
    () => {
      const correctionDocumentAvailability = getDocumentActionAvailability("correctionDocument");

      return [
        {
          availabilityNote: correctionDocumentAvailability.print.unavailableReason,
          disabled: !correctionDocumentAvailability.print.isAvailable,
          kind: "print",
          key: "print-correction",
          label: correctionDocumentAvailability.print.label,
          variant: "neutral",
          onSelect: () => undefined,
        },
        {
          key: "open-history",
          label: "Ver historial",
          variant: "neutral",
          onSelect: () => {
            setCenterSection("history");
            if (lastCommittedCorrection) {
              setSelectedHistoryCorrectionId(lastCommittedCorrection.id);
            }
          },
        },
        {
          key: "new-correction",
          label: "Nuevo ajuste",
          variant: "primary",
          onSelect: () => {
            setLastCommittedCorrection(null);
            setLastHighImpactAlertRequested(false);
            setCommitError(null);
            setDraftState(createInitialCorrectionDraftState());
            setIsHighImpactAcknowledged(false);
            setCenterSection("documents");
            setIsConfirmDialogOpen(false);
          },
        },
      ];
    },
    [lastCommittedCorrection],
  );

  const draftSummaryPanel = useMemo(
    () => (
      <CorrectionsSummaryPanel
        blockedMessages={draftBlockingMessages}
        branchName={correctionsBootstrapQuery.data?.branch.name ?? "Sucursal"}
        commitError={commitError}
        correctedDestinationLabel={correctedDestinationLabel}
        documentReference={selectedSearchDocument?.folio ?? null}
        documentTitle={selectedTarget?.document_title ?? null}
        draftSummaryLines={draftSummaryLines}
        draftReasonLabel={selectedReasonLabel}
        isHighImpactAcknowledged={isHighImpactAcknowledged}
        isHighImpactAdjustment={isHighImpactAdjustment}
        lastHighImpactAlertRequested={lastHighImpactAlertRequested}
        lastCommittedCorrection={lastCommittedCorrection}
        netEffectMilliUnits={netEffectMilliUnits}
        onAcknowledgeHighImpact={setIsHighImpactAcknowledged}
        onCommit={() => {
          if (blockedReason === null) {
            setIsConfirmDialogOpen(true);
          }
        }}
        onResultAction={correctionResultActions}
        originalDateText={originalDateText}
        selectedTarget={selectedTarget}
        timeZone={timeZone}
        totalAdjustedQuantityMilliUnits={totalAdjustedQuantityMilliUnits}
        uiState={uiState}
        userName={correctionsBootstrapQuery.data?.user.full_name ?? "Cajero"}
        workstationName={correctionsBootstrapQuery.data?.workstation.name ?? "Estacion"}
      />
    ),
    [
      blockedReason,
      correctionResultActions,
      correctionsBootstrapQuery.data?.branch.name,
      correctionsBootstrapQuery.data?.user.full_name,
      correctionsBootstrapQuery.data?.workstation.name,
      commitError,
      correctedDestinationLabel,
      draftBlockingMessages,
      draftSummaryLines,
      isHighImpactAcknowledged,
      isHighImpactAdjustment,
      lastHighImpactAlertRequested,
      lastCommittedCorrection,
      netEffectMilliUnits,
      originalDateText,
      selectedReasonLabel,
      selectedSearchDocument?.folio,
      selectedTarget,
      timeZone,
      totalAdjustedQuantityMilliUnits,
      uiState,
    ],
  );

  const summaryPanel = useMemo(
    () =>
      centerSection === "history" ? (
        selectedHistoryCorrection ? (
          <OperationDocumentSummaryPanel
            actions={[
              {
                availabilityNote:
                  getDocumentActionAvailability("correctionDocument").print.unavailableReason,
                disabled: !getDocumentActionAvailability("correctionDocument").print.isAvailable,
                kind: "print",
                key: "history-print-correction",
                label: getDocumentActionAvailability("correctionDocument").print.label,
                onSelect: () => undefined,
                variant: "neutral",
              },
              {
                key: "history-review-target",
                label: "Revisar documento",
                onSelect: () => {
                  setSelectedTargetId(selectedHistoryCorrection.target_document_id);
                  setCenterSection("documents");
                },
                variant: "neutral",
              },
            ]}
            auditSummary={selectedHistoryCorrection.audit_summary}
            blockers={[]}
            context={{
              branchName: selectedHistoryCorrection.source_branch_name,
              userName: selectedHistoryCorrection.created_by_user_full_name,
              workstationName: selectedHistoryCorrection.workstation_name,
            }}
            description={
              selectedHistoryRecord
                ? `Documento ${selectedHistoryRecord.target_document_folio}`
                : getCorrectionReasonLabel(
                    selectedHistoryCorrection.reason_code,
                    selectedHistoryCorrection.reason_name,
                  )
            }
            kind="correction"
            lines={buildCorrectionLineSummaryItems(selectedHistoryCorrection)}
            metrics={buildCorrectionMetrics(selectedHistoryCorrection)}
            notices={
              selectedHistoryCorrection.corrected_destination_branch_name ? (
                <InlineNotice tone="info">
                  Destino corregido a {selectedHistoryCorrection.corrected_destination_branch_name}.
                </InlineNotice>
              ) : undefined
            }
            referenceValue={selectedHistoryCorrection.folio}
            stateLabel={
              selectedHistoryCorrection.status === "COMMITTED"
                ? "Registrada"
                : selectedHistoryCorrection.status
            }
            stateTone="confirmed"
            timeZone={timeZone}
            timestamps={{
              committedAtValue: selectedHistoryCorrection.committed_at_utc
                ? formatLocalDateTime(selectedHistoryCorrection.committed_at_utc, timeZone)
                : null,
              createdAtValue: formatLocalDateTime(
                selectedHistoryCorrection.created_at_utc,
                timeZone,
              ),
            }}
            title="Detalle del ajuste"
          />
        ) : (
          <PosSummaryPanel
            description="Selecciona un ajuste para revisar su trazabilidad."
            stateLabel="Sin seleccion"
            stateTone="draft"
            title="Detalle del ajuste"
          >
            <InlineNotice tone="info">
              El historial es global para la sucursal actual y no expone metadatos internos.
            </InlineNotice>
          </PosSummaryPanel>
        )
      ) : (
        draftSummaryPanel
      ),
    [
      centerSection,
      draftSummaryPanel,
      selectedHistoryCorrection,
      selectedHistoryRecord,
      timeZone,
    ],
  );

  useAppShellRightPanel(summaryPanel);

  const isPending = correctionsBootstrapQuery.isPending || currentCashSessionQuery.isPending;

  if (isPending) {
    return (
      <OperationalStatus
        description="Consultando la caja activa y la configuracion operativa de Ajustes."
        title="Cargando ajustes auditados"
      />
    );
  }

  if (correctionsBootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => correctionsBootstrapQuery.refetch()}>Reintentar</Button>}
        description={toOperationalErrorMessage(
          correctionsBootstrapQuery.error,
          "Confirma la configuracion de la estacion y el contexto operativo.",
        )}
        title="No fue posible cargar Ajustes"
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

  if (currentCashSessionQuery.data.user_id !== correctionsBootstrapQuery.data.user.id) {
    return (
      <OperationalStatus
        description="La caja abierta de esta estacion pertenece a otro cajero. Inicia sesion con el operador correcto o espera el relevo."
        title="La caja activa no coincide con este cajero"
      />
    );
  }

  const processStepKey = centerSection === "history" ? "history" : "documents";
  const selectedTargetErrorMessage = correctionTargetDetailQuery.error
    ? toOperationalErrorMessage(
        correctionTargetDetailQuery.error,
        "No fue posible revisar el documento seleccionado.",
      )
    : null;
  const documentsListPane = (
    <PosHistoryView
      description="Busca por folio, documento o producto y selecciona el original que vas a ajustar."
      title="Documentos originales"
      toolbar={
        <PosFilterBar
          chipFilters={[
            ...DOCUMENT_TYPE_FILTERS.map((filter) => ({
              isActive: selectedDocumentType === filter.code,
              key: filter.code || "all-types",
              label: filter.label,
              onSelect: () => {
                setSelectedDayScope("all");
                setSelectedDocumentType(filter.code);
              },
            })),
            {
              isActive: selectedDayScope === "today",
              key: "today",
              label: "Hoy",
              onSelect: () =>
                setSelectedDayScope((current) => (current === "today" ? "all" : "today")),
            },
          ]}
          countLabel={<ModuleStateChip tone="muted">{documents.length} visibles</ModuleStateChip>}
          searchInput={{
            ariaLabel: "Buscar documento",
            className: "min-w-[16rem] max-w-md",
            hotkeyLabel: "Buscar documento en ajustes",
            inputRef: searchInputRef,
            onChange: setSearchText,
            placeholder: "Buscar folio, documento o producto",
            value: searchText,
          }}
          title="Consulta"
        />
      }
    >
      {correctionTargetsQuery.error ? (
        <OperationalStatus
          action={<Button onClick={() => correctionTargetsQuery.refetch()}>Reintentar</Button>}
          description={toOperationalErrorMessage(
            correctionTargetsQuery.error,
            "No fue posible consultar los documentos operativos.",
          )}
          title="La busqueda no esta disponible"
        />
      ) : (
        <PosRecordList
          emptyDescription="No hay documentos auditables para este filtro. Usa Devoluciones para ventas confirmadas y Merma para bajas definitivas."
          emptyTitle="Sin documentos elegibles"
          getKey={(record) => record.id}
          loading={correctionTargetsQuery.isFetching && documents.length === 0}
          loadingTitle="Buscando documentos"
          onSelect={(record) => setSelectedTargetId(record.id)}
          records={documents}
          renderContent={(document) => (
            <TargetDocumentRecordContent
              document={document}
              eligibility={eligibilityByDocumentId.get(document.id)}
              timeZone={timeZone}
            />
          )}
          selectedKey={selectedTargetId}
        />
      )}
    </PosHistoryView>
  );
  const correctionDetailPane =
    centerSection === "documents" ? (
      <div className="grid h-full min-h-0 gap-3">
        <PosContextBanner
          description="Usa ajustes auditados para corregir documentos operativos confirmados. Usa Devoluciones para ventas confirmadas y Merma para bajas definitivas."
          title="Ajustes auditados"
        />
        <SelectionPreview
          correctedDestinationBranchId={draftState.correctedDestinationBranchId}
          correctionReasons={correctionsBootstrapQuery.data.correction_reasons}
          destinationBranches={correctionsBootstrapQuery.data.destination_branches}
          draftLines={draftState.lines}
          isCommitPending={commitMutation.isPending}
          isProductSearchPending={correctionProductsQuery.isPending}
          onCommitTargetLineAdjustment={(line, direction, magnitudeText) => {
            updateDraftState((current) => ({
              ...current,
              lines: upsertTargetLineDraftAdjustment(
                current.lines,
                line,
                direction,
                magnitudeText,
              ),
            }));
            window.setTimeout(() => {
              const row = document.querySelector<HTMLElement>(
                `[data-correction-line-row="${line.id}"]`,
              );
              if (row && typeof row.scrollIntoView === "function") {
                row.scrollIntoView({ block: "start", behavior: "instant" });
              }
            }, 0);
          }}
          onCorrectedDestinationBranchChange={(destinationBranchId) =>
            updateDraftState((current) => ({
              ...current,
              correctedDestinationBranchId: destinationBranchId,
            }))
          }
          onOpenHistory={() => {
            setCenterSection("history");
            if (lastCommittedCorrection) {
              setSelectedHistoryCorrectionId(lastCommittedCorrection.id);
            }
          }}
          onProductSearchTextChange={(value) =>
            updateDraftState((current) => ({
              ...current,
              productSearchText: value,
            }))
          }
          onSelectExactProduct={(product, magnitudeText) =>
            updateDraftState((current) => ({
              ...current,
              lines: upsertAddedProductDraftAdjustment(current.lines, product, magnitudeText),
              productSearchText: "",
            }))
          }
          onRemoveDraftLine={(draftLineKey) =>
            updateDraftState((current) => ({
              ...current,
              lines: removeCorrectionDraftLine(current.lines, draftLineKey),
            }))
          }
          onReasonChange={(reasonCode) =>
            updateDraftState((current) => ({
              ...current,
              correctedDestinationBranchId:
                reasonCode === WRONG_DESTINATION_REASON_CODE
                  ? current.correctedDestinationBranchId
                  : null,
              reasonCode,
            }))
          }
          productSearchError={
            correctionProductsQuery.error
              ? toOperationalErrorMessage(
                  correctionProductsQuery.error,
                  "No fue posible buscar productos para este ajuste.",
                )
              : null
          }
          productSearchResults={correctionProductsQuery.data?.products ?? []}
          productSearchText={draftState.productSearchText}
          reasonCode={draftState.reasonCode}
          selectedDocument={selectedSearchDocument}
          selectedTarget={selectedTarget}
          selectedTargetError={selectedTargetErrorMessage}
          selectedTargetPending={correctionTargetDetailQuery.isPending}
          timeZone={timeZone}
        />
      </div>
    ) : (
      <PosHistoryView
        action={
          <Button
            className={cn("h-10 px-4", posOutlineButtonClass)}
            onClick={() => setCenterSection("documents")}
            type="button"
            variant="outline"
          >
            Revisar documento
          </Button>
        }
        description="Consulta los ajustes auditados de la sucursal actual sin exponer payloads internos."
        title="Historial de ajustes"
        toolbar={
          <PosFilterBar
            chipFilters={historyScopeOptions.map((scope) => ({
              isActive: historyScope === scope.code,
              key: scope.code,
              label: scope.label,
              onSelect: () => setHistoryScope(scope.code),
            }))}
            countLabel={
              <ModuleStateChip tone="muted">
                {historyRecords.length} {historyRecords.length === 1 ? "ajuste" : "ajustes"}
              </ModuleStateChip>
            }
            searchInput={{
              ariaLabel: "Buscar ajuste",
              className: "min-w-[16rem] max-w-md",
              hotkeyLabel: "Buscar ajuste en historial",
              inputRef: historySearchInputRef,
              onChange: setHistorySearchText,
              placeholder: "Buscar folio, documento o motivo",
              value: historySearchText,
            }}
            selectFilters={[
              {
                ariaLabel: "Filtrar historial por usuario",
                key: "history-user",
                onChange: setSelectedHistoryCreatedByUserId,
                options: [
                  { label: "Todos los usuarios", value: "" },
                  ...historyUserOptions.map((option) => ({
                    label: option.label,
                    value: option.value,
                  })),
                ],
                value: selectedHistoryCreatedByUserId,
              },
              {
                ariaLabel: "Filtrar historial por tipo de documento",
                key: "history-document-type",
                onChange: setSelectedHistoryTargetDocumentType,
                options: [
                  { label: "Todos los tipos", value: "" },
                  ...historyDocumentTypeOptions.map((option) => ({
                    label: option.label,
                    value: option.value,
                  })),
                ],
                value: selectedHistoryTargetDocumentType,
              },
              {
                ariaLabel: "Filtrar historial por motivo",
                key: "history-reason",
                onChange: setSelectedHistoryReasonCode,
                options: [
                  { label: "Todos los motivos", value: "" },
                  ...historyReasonOptions.map((option) => ({
                    label: option.label,
                    value: option.value,
                  })),
                ],
                value: selectedHistoryReasonCode,
              },
            ]}
            title="Consulta"
          />
        }
      >
        {correctionsHistoryQuery.error ? (
          <OperationalStatus
            action={<Button onClick={() => correctionsHistoryQuery.refetch()}>Reintentar</Button>}
            description={toOperationalErrorMessage(
              correctionsHistoryQuery.error,
              "No fue posible consultar el historial de ajustes.",
            )}
            title="Historial no disponible"
          />
        ) : (
          <div className="grid h-full min-h-0 gap-3 xl:grid-cols-[minmax(18rem,22rem)_minmax(0,1fr)]">
            <OperationHistoryList
              emptyDescription="No hay ajustes auditados para este filtro."
              loading={correctionsHistoryQuery.isPending}
              loadingTitle="Consultando ajustes"
              onSelect={(record) => setSelectedHistoryCorrectionId(record.id)}
              records={historyRecords}
              selectedRecordId={selectedHistoryCorrectionId}
            />
            <PosRecordDetailPanel
              badge={
                selectedHistoryCorrection ? (
                  <ModuleStateChip tone="success">
                    {selectedHistoryCorrection.status === "COMMITTED"
                      ? "Registrada"
                      : selectedHistoryCorrection.status}
                  </ModuleStateChip>
                ) : undefined
              }
              description={
                selectedHistoryRecord
                  ? `Documento ${selectedHistoryRecord.target_document_folio}`
                  : "Selecciona un ajuste para revisar su efecto."
              }
              title={
                selectedHistoryCorrection
                  ? getCorrectionReference(selectedHistoryCorrection)
                  : "Sin ajuste seleccionado"
              }
            >
              {correctionHistoryDetailQuery.isPending ? (
                <OperationalStatus
                  description="Cargando el ajuste seleccionado."
                  title="Cargando detalle"
                />
              ) : correctionHistoryDetailQuery.error ? (
                <OperationalStatus
                  action={<Button onClick={() => correctionHistoryDetailQuery.refetch()}>Reintentar</Button>}
                  description={toOperationalErrorMessage(
                    correctionHistoryDetailQuery.error,
                    "No fue posible cargar el ajuste seleccionado.",
                  )}
                  title="Detalle no disponible"
                />
              ) : selectedHistoryCorrection ? (
                <OperationDocumentSummaryPanel
                  blockers={[]}
                  auditSummary={selectedHistoryCorrection.audit_summary}
                  context={{
                    branchName: selectedHistoryCorrection.source_branch_name,
                    userName: selectedHistoryCorrection.created_by_user_full_name,
                    workstationName: selectedHistoryCorrection.workstation_name,
                  }}
                  description={getCorrectionReasonLabel(
                    selectedHistoryCorrection.reason_code,
                    selectedHistoryCorrection.reason_name,
                  )}
                  kind="correction"
                  lines={buildCorrectionLineSummaryItems(selectedHistoryCorrection)}
                  metrics={buildCorrectionMetrics(selectedHistoryCorrection)}
                  notices={
                    selectedHistoryCorrection.corrected_destination_branch_name ? (
                      <InlineNotice tone="info">
                        Destino corregido a {selectedHistoryCorrection.corrected_destination_branch_name}.
                      </InlineNotice>
                    ) : undefined
                  }
                  referenceValue={getCorrectionReference(selectedHistoryCorrection)}
                  stateLabel={
                    selectedHistoryCorrection.status === "COMMITTED"
                      ? "Registrada"
                      : selectedHistoryCorrection.status
                  }
                  stateTone="confirmed"
                  timeZone={timeZone}
                  timestamps={{
                    committedAtValue: selectedHistoryCorrection.committed_at_utc
                      ? formatLocalDateTime(selectedHistoryCorrection.committed_at_utc, timeZone)
                      : null,
                    createdAtValue: formatLocalDateTime(
                      selectedHistoryCorrection.created_at_utc,
                      timeZone,
                    ),
                  }}
                  title="Detalle del ajuste"
                />
              ) : (
                <div className="grid h-full place-items-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white px-4 py-8 text-center text-sm text-slate-600">
                  Selecciona un ajuste registrado para revisar su efecto.
                </div>
              )}
            </PosRecordDetailPanel>
          </div>
        )}
      </PosHistoryView>
    );
  return (
    <>
      <CorrectionConfirmationDialog
        affectedDocumentLabel={
          selectedSearchDocument
            ? getDocumentTypeLabel(selectedSearchDocument.document_type)
            : null
        }
        branchName={correctionsBootstrapQuery.data.branch.name}
        documentReference={selectedSearchDocument?.folio ?? "Pendiente"}
        documentTitle={selectedTarget?.document_title ?? "Sin documento"}
        isOpen={isConfirmDialogOpen}
        isHighImpact={isHighImpactAdjustment}
        isPending={commitMutation.isPending}
        lineSummaryItems={draftSummaryLines}
        lineCount={draftState.lines.length}
        netEffectLabel={getSignedEffectLabel(netEffectMilliUnits)}
        onCancel={() => setIsConfirmDialogOpen(false)}
        onConfirm={() => {
          void commitMutation.mutateAsync();
        }}
        reasonLabel={selectedReasonLabel ?? "Pendiente"}
        userName={correctionsBootstrapQuery.data.user.full_name}
        workstationName={correctionsBootstrapQuery.data.workstation.name}
      />

      <CentralWorkspaceSheet
        className="lg:h-full"
        contentClassName="min-h-0 overflow-hidden px-3 pb-3 pt-2"
        header={
          <CompactPageHeader
            secondaryChips={
              selectedTarget ? (
                <ModuleStateChip tone="primary">
                  {selectedTarget.document_title}
                </ModuleStateChip>
              ) : null
            }
            stateChip={
              <ModuleStateChip tone={getCorrectionUiStateTone(uiState)}>
                {getCorrectionUiStateLabel(uiState)}
              </ModuleStateChip>
            }
            title="Ajustes auditados"
          >
            <FlowGuide activeStepKey={processStepKey} steps={[...CORRECTION_PROCESS_STEPS]} variant="process" />
          </CompactPageHeader>
        }
      >
        <ResponsivePaneLayout
          className="h-full gap-2.5"
          detail={correctionDetailPane}
          detailClassName="min-h-0"
          list={documentsListPane}
          listClassName="min-h-0"
          splitVariant="narrow-list"
        />
      </CentralWorkspaceSheet>
    </>
  );
}


