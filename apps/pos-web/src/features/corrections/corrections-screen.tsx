import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import {
  OperationHistoryList,
  type OperationHistoryRecord,
} from "../../components/operation-documents";
import {
  CentralWorkspaceSheet,
  InlineNotice,
  KeyValueRow,
  ModuleStateChip,
  CompactPageHeader,
  ScrollPane,
} from "../../components/pos-module-primitives";
import { OperationalStatus } from "../../components/operational-status";
import { PosSummaryPanel } from "../../components/pos-module-layout";
import {
  PosFilterBar,
  PosHistoryView,
  PosRecordTable,
  type PosRecordColumn,
} from "../../components/pos-records";
import { Button } from "../../components/ui/button";
import { appEnv } from "../../env";
import type {
  CorrectionDocumentView,
  CorrectionHistoryListItemView,
  CorrectionSearchDocumentView,
  CorrectionTargetDetailResponse,
  OperationDocumentLineView,
  TransferDestinationBranchView,
} from "../../lib/api-contracts";
import { formatCompactLocalDateTime, formatLocalDateTime } from "../../lib/formatters";
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
  getCorrectionDraftNetQuantityMilliUnits,
  getCorrectionDraftTotalAdjustedQuantityMilliUnits,
  hasCorrectionDraftInvalidQuantity,
  hasCorrectionDraftMissingReason,
  parseSignedQuantityToMilliUnits,
  removeCorrectionDraftLine,
  upsertTargetLineDraftAdjustment,
  type CorrectionDirection,
  type CorrectionDraftLine,
} from "./model";
import {
  correctionTargetDetailQueryKey,
  correctionsBootstrapQueryKey,
  useCorrectionDocumentDetailQuery,
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

function getCorrectionTargetTotalQuantityText(target: CorrectionTargetDetailResponse | null): string {
  if (!target) {
    return "-";
  }

  const totalMilliUnits = target.target_document.lines.reduce(
    (total, line) => total + (parseSignedQuantityToMilliUnits(String(line.quantity)) ?? 0),
    0,
  );
  return formatQuantityFromMilliUnits(totalMilliUnits);
}

function getCorrectionHighImpactLabel(thresholdText: string): string {
  return `Ajuste alto impacto a partir de ${thresholdText} unidades ajustadas.`;
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
    subtitle: `Movimiento ${correction.target_document_folio} · ${getCorrectionReasonLabel(
      correction.reason_code,
      correction.reason_name,
    )}`,
    title: getCorrectionReasonLabel(correction.reason_code, correction.reason_name),
    userLabel: correction.created_by_user_full_name,
  }));
}

function getCorrectionNetEffectMilliUnits(correction: CorrectionDocumentView): number {
  return correction.lines.reduce(
    (sum, line) => sum + Number(line.delta_quantity) * 1000,
    0,
  );
}

function getCorrectionUiState({
  commitError,
  hasDraftWork,
  hasCommitted,
  hasInvalidQuantity,
  hasSelectedTarget,
  isCommitPending,
  isReasonMissing,
}: {
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
      return "Sin movimiento";
    case "DOC_SELECTED":
      return "Movimiento seleccionado";
    case "DRAFT_EMPTY":
      return "Borrador vacio";
    case "DRAFT_BUILDING":
      return "Editando";
    case "BLOCKED_MISSING_REASON":
      return "Falta motivo";
    case "BLOCKED_INVALID_SIGN":
      return "Revisa cantidades";
    case "READY_TO_CONFIRM":
      return "Lista para guardar";
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

function CorrectionsSummaryPanel({
  blockedMessages,
  commitError,
  correctedDestinationBranchId,
  correctedDestinationLabel,
  correctionReasons,
  destinationBranches,
  documentReference,
  draftLines,
  isHighImpactAcknowledged,
  isHighImpactAdjustment,
  netEffectMilliUnits,
  onAcknowledgeHighImpact,
  onCommit,
  onCommitTargetLineAdjustment,
  onCorrectedDestinationBranchChange,
  onReasonChange,
  onRemoveDraftLine,
  reasonCode,
  selectedTarget,
  selectedTargetError,
  selectedTargetPending,
  totalAdjustedQuantityMilliUnits,
  uiState,
}: {
  blockedMessages: string[];
  commitError: string | null;
  correctedDestinationBranchId: string | null;
  correctedDestinationLabel: string | null;
  correctionReasons: Array<{ code: string; name: string }>;
  destinationBranches: TransferDestinationBranchView[];
  documentReference: string | null;
  draftLines: CorrectionDraftLine[];
  isHighImpactAcknowledged: boolean;
  isHighImpactAdjustment: boolean;
  netEffectMilliUnits: number;
  onAcknowledgeHighImpact: (checked: boolean) => void;
  onCommit: () => void;
  onCommitTargetLineAdjustment: (
    line: OperationDocumentLineView,
    direction: CorrectionDirection,
    magnitudeText: string,
  ) => void;
  onCorrectedDestinationBranchChange: (destinationBranchId: string | null) => void;
  onReasonChange: (reasonCode: string) => void;
  onRemoveDraftLine: (draftLineKey: string) => void;
  reasonCode: string;
  selectedTarget: CorrectionTargetDetailResponse | null;
  selectedTargetError: string | null;
  selectedTargetPending: boolean;
  totalAdjustedQuantityMilliUnits: number;
  uiState: CorrectionUiState;
}) {
  const [editingLineId, setEditingLineId] = useState<string | null>(null);
  const [editingQuantityText, setEditingQuantityText] = useState("");
  const [editingError, setEditingError] = useState<string | null>(null);
  const quantityInputRef = useRef<HTMLInputElement | null>(null);
  const reasonSelectRef = useRef<HTMLSelectElement | null>(null);
  const previousDraftLineCountRef = useRef(draftLines.length);

  const hasDraftWork = draftLines.length > 0 || correctedDestinationLabel !== null;
  const originalQuantityMilliUnits =
    selectedTarget?.target_document.lines.reduce(
      (total, line) => total + (parseSignedQuantityToMilliUnits(String(line.quantity)) ?? 0),
      0,
    ) ?? 0;
  const adjustedQuantityMilliUnits = originalQuantityMilliUnits + netEffectMilliUnits;
  const visibleBlockingMessages = selectedTarget && hasDraftWork ? blockedMessages : [];
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
  const isEditingDisabled =
    uiState === "CONFIRMING" || !selectedTarget?.is_correctable || isWrongDestinationReason;

  useEffect(() => {
    setEditingLineId(null);
    setEditingQuantityText("");
    setEditingError(null);
  }, [selectedTarget?.target_document.id]);

  useEffect(() => {
    if (!editingLineId) {
      return;
    }

    window.setTimeout(() => quantityInputRef.current?.focus(), 0);
  }, [editingLineId]);

  useEffect(() => {
    const previousLineCount = previousDraftLineCountRef.current;
    previousDraftLineCountRef.current = draftLines.length;

    if (draftLines.length <= previousLineCount || reasonCode.trim().length > 0) {
      return;
    }

    window.setTimeout(() => reasonSelectRef.current?.focus(), 0);
  }, [draftLines.length, reasonCode]);

  const getDraftLineForTarget = (lineId: string) =>
    draftLines.find((candidate) => candidate.targetLineId === lineId) ?? null;

  const startLineEdit = (line: OperationDocumentLineView) => {
    if (isEditingDisabled) {
      return;
    }

    const draftLine = getDraftLineForTarget(line.id);
    const originalQuantityMilliUnits =
      parseSignedQuantityToMilliUnits(String(line.quantity)) ?? 0;
    const draftQuantityMilliUnits = draftLine
      ? parseSignedQuantityToMilliUnits(draftLine.deltaQuantityText) ?? 0
      : 0;

    setEditingLineId(line.id);
    setEditingQuantityText(
      formatQuantityFromMilliUnits(originalQuantityMilliUnits + draftQuantityMilliUnits),
    );
    setEditingError(null);
  };

  const cancelLineEdit = () => {
    setEditingLineId(null);
    setEditingQuantityText("");
    setEditingError(null);
  };

  const commitLineEdit = (line: OperationDocumentLineView) => {
    const correctedQuantityMilliUnits = parseSignedQuantityToMilliUnits(editingQuantityText);
    const originalQuantityMilliUnits = parseSignedQuantityToMilliUnits(String(line.quantity));

    if (
      correctedQuantityMilliUnits === null ||
      originalQuantityMilliUnits === null ||
      correctedQuantityMilliUnits < 0
    ) {
      setEditingError("Cantidad invalida.");
      return;
    }

    const draftLine = getDraftLineForTarget(line.id);
    const deltaQuantityMilliUnits = correctedQuantityMilliUnits - originalQuantityMilliUnits;

    if (deltaQuantityMilliUnits === 0) {
      if (draftLine) {
        onRemoveDraftLine(draftLine.key);
      }
      cancelLineEdit();
      return;
    }

    onCommitTargetLineAdjustment(
      line,
      deltaQuantityMilliUnits < 0 ? "DECREASE" : "INCREASE",
      formatQuantityFromMilliUnits(Math.abs(deltaQuantityMilliUnits)),
    );
    cancelLineEdit();
  };

  const getDeltaLabel = (deltaMilliUnits: number | null) => {
    if (deltaMilliUnits === null || deltaMilliUnits === 0) {
      return "0";
    }

    const prefix = deltaMilliUnits > 0 ? "+" : "-";
    return `${prefix}${formatQuantityFromMilliUnits(Math.abs(deltaMilliUnits))}`;
  };

  return (
    <PosSummaryPanel
      description={selectedTarget ? documentReference ?? undefined : undefined}
      footer={
        selectedTarget && hasDraftWork ? (
          <Button
            className={cn("h-11 w-full font-semibold shadow-sm", posPrimaryButtonClass)}
            disabled={visibleBlockingMessages.length > 0 || uiState === "CONFIRMING"}
            onClick={onCommit}
            type="button"
          >
            {uiState === "CONFIRMING" ? "Registrando..." : "Guardar ajuste"}
          </Button>
        ) : undefined
      }
      stateLabel={getCorrectionUiStateLabel(uiState)}
      stateTone={getCorrectionSummaryStateTone(uiState)}
      title="Ajuste"
    >
      {selectedTargetPending ? (
        <OperationalStatus
          description="Consultando lineas del movimiento."
          title="Cargando movimiento"
        />
      ) : selectedTargetError ? (
        <OperationalStatus
          description={selectedTargetError}
          title="No fue posible cargar el movimiento"
        />
      ) : !selectedTarget ? (
        <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-4 text-sm text-slate-600">
          Selecciona un movimiento para ajustar.
        </div>
      ) : (
        <div className="grid h-full min-h-0 gap-2.5 overflow-hidden">
          {commitError ? <InlineNotice tone="error">{commitError}</InlineNotice> : null}

          <div className="rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2">
            <div className="flex min-w-0 items-center justify-between gap-2">
              <span className="min-w-0 truncate text-sm font-semibold text-slate-950" title={documentReference ?? undefined}>
                {documentReference ?? "Movimiento"}
              </span>
              <ModuleStateChip tone={selectedTarget.is_correctable ? "success" : "warning"}>
                {selectedTarget.is_correctable ? "Listo" : "Bloqueado"}
              </ModuleStateChip>
            </div>
            <p className="mt-1 truncate text-xs text-slate-600">
              {getDocumentTypeLabel(selectedTarget.target_document.document_type)}
              {selectedTarget.target_document.destination_branch_name
                ? ` · ${selectedTarget.target_document.destination_branch_name}`
                : ""}
            </p>
            <div className="mt-2 grid grid-cols-3 gap-1 text-center text-xs">
              <div className="rounded-lg bg-slate-50 px-2 py-1">
                <span className="block font-semibold text-slate-950">
                  {formatQuantityFromMilliUnits(originalQuantityMilliUnits)}
                </span>
                <span className="text-slate-500">Original</span>
              </div>
              <div className="rounded-lg bg-slate-50 px-2 py-1">
                <span className="block font-semibold text-slate-950">
                  {formatQuantityFromMilliUnits(adjustedQuantityMilliUnits)}
                </span>
                <span className="text-slate-500">Nuevo</span>
              </div>
              <div className="rounded-lg bg-slate-50 px-2 py-1">
                <span className="block font-semibold text-slate-950">
                  {getDeltaLabel(netEffectMilliUnits)}
                </span>
                <span className="text-slate-500">Dif.</span>
              </div>
            </div>
            {selectedTarget.blocking_reason ? (
              <div className="mt-2">
                <InlineNotice tone="error">{selectedTarget.blocking_reason}</InlineNotice>
              </div>
            ) : null}
          </div>

          <div className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-2.5">
            <label className="grid gap-1">
              <span className="text-xs font-semibold text-slate-700">Motivo</span>
              <select
                ref={reasonSelectRef}
                className={cn(
                  "h-9 w-full rounded-lg px-2.5 text-sm shadow-sm",
                  posInputClass,
                  reasonCode.trim().length === 0 &&
                    hasDraftWork &&
                    "border-[var(--ui-color-danger)] text-[var(--ui-color-danger)]",
                )}
                disabled={uiState === "CONFIRMING" || !selectedTarget.is_correctable}
                onChange={(event) => onReasonChange(event.target.value)}
                value={reasonCode}
              >
                <option value="">Selecciona motivo</option>
                {availableReasonOptions.map((reason) => (
                  <option key={reason.code} value={reason.code}>
                    {getCorrectionReasonLabel(reason.code, reason.name)}
                  </option>
                ))}
              </select>
            </label>

            {isWrongDestinationReason ? (
              <label className="grid gap-1">
                <span className="text-xs font-semibold text-slate-700">Destino corregido</span>
                <select
                  className={cn(
                    "h-9 w-full rounded-lg px-2.5 text-sm shadow-sm",
                    posInputClass,
                    correctedDestinationBranchId === null &&
                      "border-[var(--ui-color-danger)] text-[var(--ui-color-danger)]",
                  )}
                  disabled={uiState === "CONFIRMING" || !selectedTarget.is_correctable}
                  onChange={(event) =>
                    onCorrectedDestinationBranchChange(
                      event.target.value.length > 0 ? event.target.value : null,
                    )
                  }
                  value={correctedDestinationBranchId ?? ""}
                >
                  <option value="">Selecciona sucursal</option>
                  {availableDestinationBranches.map((branch) => (
                    <option key={branch.id} value={branch.id}>
                      {branch.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>

          <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white">
            <div className="grid grid-cols-[minmax(0,1fr)_2.8rem_4.2rem_3.2rem] gap-2 border-b border-[var(--pos-shell-border)] bg-slate-50 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
              <span>Producto</span>
              <span className="text-right">Orig.</span>
              <span className="text-right">Nuevo</span>
              <span className="text-right">Dif.</span>
            </div>
            <ScrollPane className="max-h-[17rem] divide-y divide-[var(--pos-shell-border)]">
              {selectedTarget.target_document.lines.map((line) => {
                const draftLine = getDraftLineForTarget(line.id);
                const originalLineQuantityMilliUnits =
                  parseSignedQuantityToMilliUnits(String(line.quantity)) ?? 0;
                const draftLineDeltaMilliUnits = draftLine
                  ? parseSignedQuantityToMilliUnits(draftLine.deltaQuantityText) ?? 0
                  : 0;
                const isEditing = editingLineId === line.id;
                const shownDeltaMilliUnits =
                  isEditing
                    ? (() => {
                        const editedQuantity = parseSignedQuantityToMilliUnits(editingQuantityText);
                        return editedQuantity === null
                          ? null
                          : editedQuantity - originalLineQuantityMilliUnits;
                      })()
                    : draftLineDeltaMilliUnits;
                const correctedLineQuantityMilliUnits =
                  originalLineQuantityMilliUnits + draftLineDeltaMilliUnits;

                return (
                  <div
                    className="grid grid-cols-[minmax(0,1fr)_2.8rem_4.2rem_3.2rem] items-center gap-2 px-3 py-2 text-sm"
                    data-correction-line-row={line.id}
                    key={line.id}
                  >
                    <span className="min-w-0 truncate font-semibold text-slate-950" title={line.product_name_snapshot}>
                      {line.product_name_snapshot}
                    </span>
                    <span className="text-right font-semibold text-slate-600">
                      {formatQuantity(line.quantity)}
                    </span>
                    <span className="text-right">
                      {isEditing ? (
                        <input
                          ref={quantityInputRef}
                          className={cn(
                            "h-8 w-full rounded-lg px-2 text-right text-sm font-semibold shadow-sm",
                            posInputClass,
                            editingError &&
                              "border-[var(--ui-color-danger)] text-[var(--ui-color-danger)]",
                          )}
                          disabled={isEditingDisabled}
                          inputMode="decimal"
                          onBlur={() => commitLineEdit(line)}
                          onChange={(event) => {
                            setEditingQuantityText(event.target.value);
                            setEditingError(null);
                          }}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              event.preventDefault();
                              commitLineEdit(line);
                            }
                            if (event.key === "Escape") {
                              event.preventDefault();
                              cancelLineEdit();
                            }
                          }}
                          value={editingQuantityText}
                        />
                      ) : (
                        <button
                          aria-label={`Editar cantidad de ${line.product_name_snapshot}`}
                          className={cn(
                            "inline-flex h-8 min-w-10 items-center justify-end rounded-lg px-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]",
                            draftLine
                              ? "bg-sky-50 text-sky-700 hover:bg-sky-100"
                              : "bg-slate-100 text-slate-700 hover:bg-slate-200",
                            isEditingDisabled && "cursor-not-allowed opacity-70",
                          )}
                          data-correction-line-quantity-button={line.id}
                          disabled={isEditingDisabled}
                          onClick={() => startLineEdit(line)}
                          type="button"
                        >
                          {formatQuantityFromMilliUnits(correctedLineQuantityMilliUnits)}
                        </button>
                      )}
                    </span>
                    <span
                      className={cn(
                        "text-right text-xs font-semibold",
                        shownDeltaMilliUnits === null || shownDeltaMilliUnits === 0
                          ? "text-slate-400"
                          : shownDeltaMilliUnits > 0
                            ? "text-emerald-700"
                            : "text-amber-700",
                      )}
                    >
                      {getDeltaLabel(shownDeltaMilliUnits)}
                    </span>
                  </div>
                );
              })}
            </ScrollPane>
          </div>

          {editingError ? (
            <p className="text-xs leading-5 text-[var(--ui-color-danger)]">{editingError}</p>
          ) : null}

          {isHighImpactAdjustment ? (
            <div className="rounded-xl border border-[rgba(187,122,22,0.2)] bg-[var(--ui-color-warning-soft)] px-3 py-3">
              <p className="text-sm font-semibold text-slate-950">
                {getCorrectionHighImpactLabel(
                  formatQuantityFromMilliUnits(totalAdjustedQuantityMilliUnits),
                )}
              </p>
              <label className="mt-2 flex items-start gap-2 text-sm text-slate-700">
                <input
                  checked={isHighImpactAcknowledged}
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-[var(--pos-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--pos-focus-ring)]"
                  onChange={(event) => onAcknowledgeHighImpact(event.target.checked)}
                  type="checkbox"
                />
                <span>Confirmo que el ajuste fue verificado.</span>
              </label>
            </div>
          ) : null}

          {visibleBlockingMessages.map((message) => (
            <InlineNotice key={message} tone="warning">
              {message}
            </InlineNotice>
          ))}

          {!hasDraftWork ? (
            <InlineNotice tone="info">
              Da click en una cantidad nueva para editarla.
            </InlineNotice>
          ) : null}
        </div>
      )}
    </PosSummaryPanel>
  );
}

function CorrectionsHistorySummaryPanel({
  correction,
  onReviewTarget,
  selectedHistoryRecord,
  timeZone,
}: {
  correction: CorrectionDocumentView | null;
  onReviewTarget: () => void;
  selectedHistoryRecord: CorrectionHistoryListItemView | null;
  timeZone: string;
}) {
  if (!correction) {
    return (
      <PosSummaryPanel
        description="Selecciona un ajuste registrado."
        stateLabel="Historial"
        stateTone="draft"
        title="Detalle del ajuste"
      >
        <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-4 text-sm text-slate-600">
          Selecciona un ajuste del historial para ver su detalle.
        </div>
      </PosSummaryPanel>
    );
  }

  return (
    <PosSummaryPanel
      description={
        selectedHistoryRecord
          ? `Movimiento ${selectedHistoryRecord.target_document_folio}`
          : "Ajuste registrado"
      }
      footer={
        <Button
          className={cn("h-11 w-full font-semibold shadow-sm", posPrimaryButtonClass)}
          onClick={onReviewTarget}
          type="button"
        >
          Revisar movimiento
        </Button>
      }
      stateLabel={correction.status === "COMMITTED" ? "Registrada" : correction.status}
      stateTone="success"
      title="Detalle del ajuste"
    >
      <div className="grid h-full min-h-0 gap-3 overflow-hidden">
        <div className="grid gap-1 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <KeyValueRow label="Ajuste" title={correction.folio} value={correction.folio} />
          <KeyValueRow
            label="Motivo"
            value={getCorrectionReasonLabel(correction.reason_code, correction.reason_name)}
          />
          <KeyValueRow
            label="Fecha"
            value={
              correction.committed_at_utc
                ? formatCompactLocalDateTime(correction.committed_at_utc, timeZone)
                : formatCompactLocalDateTime(correction.created_at_utc, timeZone)
            }
          />
          <KeyValueRow
            label="Diferencia"
            value={getSignedEffectLabel(getCorrectionNetEffectMilliUnits(correction))}
          />
        </div>

        <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white">
          <div className="border-b border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-2 text-sm font-semibold text-slate-950">
            Lineas
          </div>
          <ScrollPane className="max-h-[14rem] divide-y divide-[var(--pos-shell-border)]">
            {correction.lines.map((line) => (
              <div
                className="grid grid-cols-[minmax(0,1fr)_5.5rem] items-center gap-2 px-3 py-2"
                key={line.id}
              >
                <span className="truncate text-sm font-semibold text-slate-950" title={line.product_name_snapshot}>
                  {line.product_name_snapshot}
                </span>
                <span className="text-right text-sm font-semibold text-slate-950">
                  {formatSignedHistoryQuantity(line.delta_quantity)}
                </span>
              </div>
            ))}
          </ScrollPane>
        </div>

        {correction.corrected_destination_branch_name ? (
          <InlineNotice tone="info">
            Destino corregido a {correction.corrected_destination_branch_name}.
          </InlineNotice>
        ) : null}
      </div>
    </PosSummaryPanel>
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
  const [isHighImpactAcknowledged, setIsHighImpactAcknowledged] = useState(false);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [selectedHistoryCorrectionId, setSelectedHistoryCorrectionId] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const debouncedSearchText = useDebouncedValue(searchText, 220);
  const historySearchInputRef = useRef<HTMLInputElement | null>(null);
  const debouncedHistorySearchText = useDebouncedValue(historySearchText, 220);
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
        totalQuantityText: string;
      }
    >();

    documents.forEach((document, index) => {
      if (document.id === selectedTargetId) {
        if (correctionTargetDetailQuery.data) {
          map.set(document.id, {
            blockingReason: correctionTargetDetailQuery.data.blocking_reason,
            isCorrectable: correctionTargetDetailQuery.data.is_correctable,
            isPending: false,
            totalQuantityText: getCorrectionTargetTotalQuantityText(correctionTargetDetailQuery.data),
          });
          return;
        }

        map.set(document.id, {
          blockingReason: null,
          isCorrectable: false,
          isPending: correctionTargetDetailQuery.isPending,
          totalQuantityText: "-",
        });
        return;
      }

      const query = eligibilityQueries[index];
      if (query?.data) {
          map.set(document.id, {
            blockingReason: query.data.blocking_reason,
            isCorrectable: query.data.is_correctable,
            isPending: false,
            totalQuantityText: getCorrectionTargetTotalQuantityText(query.data),
          });
        return;
      }

      map.set(document.id, {
        blockingReason: null,
        isCorrectable: false,
        isPending: Boolean(query?.isPending || query?.isFetching),
        totalQuantityText: "-",
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
    setIsHighImpactAcknowledged(false);
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

      if (event.key === "Enter") {
        if (isInteractiveTrigger) {
          return;
        }

        return;
      }

      if (event.key !== "Escape") {
        return;
      }

      if (centerSection === "history") {
        event.preventDefault();
        setCenterSection("documents");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [centerSection]);

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
        throw new Error("Selecciona un movimiento antes de guardar el ajuste.");
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
      setSelectedHistoryCorrectionId(result.id);
      setDraftState(createInitialCorrectionDraftState());
      setCommitError(null);
      setIsHighImpactAcknowledged(false);
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
      showError(message);
    },
  });

  const correctedDestinationLabel =
    draftState.correctedDestinationBranchId !== null
      ? correctionsBootstrapQuery.data?.destination_branches.find(
          (branch) => branch.id === draftState.correctedDestinationBranchId,
        )?.name ?? null
      : null;
  const netEffectMilliUnits = getCorrectionDraftNetQuantityMilliUnits(draftState.lines);
  const uiState = getCorrectionUiState({
    commitError,
    hasDraftWork,
    hasCommitted: lastCommittedCorrection !== null,
    hasInvalidQuantity,
    hasSelectedTarget: selectedTarget !== null,
    isCommitPending: commitMutation.isPending,
    isReasonMissing,
  });
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

  const draftSummaryPanel = useMemo(
    () => (
      <CorrectionsSummaryPanel
        blockedMessages={draftBlockingMessages}
        commitError={commitError}
        correctedDestinationBranchId={draftState.correctedDestinationBranchId}
        correctedDestinationLabel={correctedDestinationLabel}
        correctionReasons={correctionsBootstrapQuery.data?.correction_reasons ?? []}
        destinationBranches={correctionsBootstrapQuery.data?.destination_branches ?? []}
        documentReference={selectedSearchDocument?.folio ?? null}
        draftLines={draftState.lines}
        isHighImpactAcknowledged={isHighImpactAcknowledged}
        isHighImpactAdjustment={isHighImpactAdjustment}
        netEffectMilliUnits={netEffectMilliUnits}
        onAcknowledgeHighImpact={setIsHighImpactAcknowledged}
        onCommit={() => {
          if (blockedReason === null) {
            void commitMutation.mutateAsync();
          }
        }}
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
        }}
        onCorrectedDestinationBranchChange={(destinationBranchId) =>
          updateDraftState((current) => ({
            ...current,
            correctedDestinationBranchId: destinationBranchId,
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
        onRemoveDraftLine={(draftLineKey) =>
          updateDraftState((current) => ({
            ...current,
            lines: removeCorrectionDraftLine(current.lines, draftLineKey),
          }))
        }
        reasonCode={draftState.reasonCode}
        selectedTarget={selectedTarget}
        selectedTargetError={
          correctionTargetDetailQuery.error
            ? toOperationalErrorMessage(
                correctionTargetDetailQuery.error,
                "No fue posible revisar el movimiento seleccionado.",
              )
            : null
        }
        selectedTargetPending={correctionTargetDetailQuery.isPending}
        totalAdjustedQuantityMilliUnits={totalAdjustedQuantityMilliUnits}
        uiState={uiState}
      />
    ),
    [
      blockedReason,
      commitMutation,
      commitError,
      correctedDestinationLabel,
      correctionsBootstrapQuery.data?.correction_reasons,
      correctionsBootstrapQuery.data?.destination_branches,
      correctionTargetDetailQuery.error,
      correctionTargetDetailQuery.isPending,
      draftBlockingMessages,
      draftState.correctedDestinationBranchId,
      draftState.lines,
      draftState.reasonCode,
      isHighImpactAcknowledged,
      isHighImpactAdjustment,
      netEffectMilliUnits,
      selectedSearchDocument?.folio,
      selectedTarget,
      totalAdjustedQuantityMilliUnits,
      uiState,
    ],
  );

  const summaryPanel = useMemo(
    () =>
      centerSection === "history" ? (
        <CorrectionsHistorySummaryPanel
          correction={selectedHistoryCorrection}
          onReviewTarget={() => {
            if (!selectedHistoryCorrection) {
              return;
            }
            setSelectedTargetId(selectedHistoryCorrection.target_document_id);
            setCenterSection("documents");
          }}
          selectedHistoryRecord={selectedHistoryRecord}
          timeZone={timeZone}
        />
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
        title="Cargando ajustes"
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

  const documentColumns: PosRecordColumn<CorrectionSearchDocumentView>[] = [
    {
      header: "Folio",
      key: "folio",
      renderCell: (document) => (
        <span className="block truncate font-semibold text-slate-950" title={document.folio}>
          {document.folio}
        </span>
      ),
      width: "22%",
    },
    {
      header: "Tipo",
      key: "type",
      renderCell: (document) => (
        <span className="block truncate" title={getDocumentTypeLabel(document.document_type)}>
          {getDocumentTypeLabel(document.document_type)}
        </span>
      ),
      width: "24%",
    },
    {
      header: "Fecha/hora",
      key: "date",
      renderCell: (document) =>
        document.committed_at_utc
          ? formatCompactLocalDateTime(document.committed_at_utc, timeZone)
          : "Sin confirmar",
      width: "20%",
    },
    {
      align: "right",
      header: "Unidades",
      key: "units",
      renderCell: (document) =>
        eligibilityByDocumentId.get(document.id)?.totalQuantityText ?? "-",
      width: "14%",
    },
    {
      align: "right",
      header: "Estado",
      key: "status",
      renderCell: (document) => {
        const eligibility = eligibilityByDocumentId.get(document.id);

        if (!eligibility || eligibility.isPending) {
          return (
            <span className="pos-chip" data-tone="muted">
              Revisando
            </span>
          );
        }

        return (
          <span
            className="pos-chip"
            data-tone={eligibility.isCorrectable ? "success" : "danger"}
            title={eligibility.blockingReason ?? undefined}
          >
            {eligibility.isCorrectable ? "Listo" : "Bloqueado"}
          </span>
        );
      },
      width: "20%",
    },
  ];
  const documentsListPane = (
    <PosHistoryView
      title="Movimientos"
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
            ariaLabel: "Buscar movimiento",
            className: "min-w-[16rem] max-w-md",
            hotkeyLabel: "Buscar movimiento en ajustes",
            inputRef: searchInputRef,
            onChange: setSearchText,
            placeholder: "Buscar movimiento",
            value: searchText,
          }}
        />
      }
    >
      {correctionTargetsQuery.error ? (
        <OperationalStatus
          action={<Button onClick={() => correctionTargetsQuery.refetch()}>Reintentar</Button>}
          description={toOperationalErrorMessage(
            correctionTargetsQuery.error,
            "No fue posible consultar los movimientos operativos.",
          )}
          title="La busqueda no esta disponible"
        />
      ) : (
        <PosRecordTable
          columns={documentColumns}
          emptyDescription="No hay movimientos ajustables para este filtro."
          emptyTitle="Sin movimientos elegibles"
          getKey={(record) => record.id}
          loading={correctionTargetsQuery.isFetching && documents.length === 0}
          loadingTitle="Buscando movimientos"
          onSelect={(record) => setSelectedTargetId(record.id)}
          records={documents}
          selectedKey={selectedTargetId}
          tableAriaLabel="Movimientos ajustables"
        />
      )}
    </PosHistoryView>
  );
  const historyPane = (
      <PosHistoryView
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
              placeholder: "Buscar folio, movimiento o motivo",
              value: historySearchText,
            }}
            selectFilters={[
              {
                ariaLabel: "Filtrar historial por usuario",
                key: "history-user",
                onChange: setSelectedHistoryCreatedByUserId,
                options: [
                  { label: "Todos los cajeros", value: "" },
                  ...historyUserOptions.map((option) => ({
                    label: option.label,
                    value: option.value,
                  })),
                ],
                value: selectedHistoryCreatedByUserId,
              },
              {
                ariaLabel: "Filtrar historial por tipo de movimiento",
                key: "history-document-type",
                onChange: setSelectedHistoryTargetDocumentType,
                options: [
                  { label: "Todos los tipos", value: "" },
                  ...historyDocumentTypeOptions.map((option) => ({
                    label: getDocumentTypeLabel(option.value),
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
                    label: getCorrectionReasonLabel(option.value, option.label),
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
          <OperationHistoryList
            emptyDescription="No hay ajustes para este filtro."
            loading={correctionsHistoryQuery.isPending}
            loadingTitle="Consultando ajustes"
            onSelect={(record) => setSelectedHistoryCorrectionId(record.id)}
            records={historyRecords}
            selectedRecordId={selectedHistoryCorrectionId}
          />
        )}
      </PosHistoryView>
    );
  return (
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
          title="Ajustes"
        >
          <div className="flex flex-wrap items-center gap-2">
            <Button
              className={cn(
                "h-9 px-4 font-semibold shadow-sm",
                centerSection === "history" ? posPrimaryButtonClass : posOutlineButtonClass,
              )}
              onClick={() => {
                if (centerSection === "history") {
                  setCenterSection("documents");
                  return;
                }

                setCenterSection("history");
                if (lastCommittedCorrection) {
                  setSelectedHistoryCorrectionId(lastCommittedCorrection.id);
                }
              }}
              type="button"
              variant={centerSection === "history" ? undefined : "outline"}
            >
              {centerSection === "history" ? "Volver a ajustes" : "Historial de ajustes"}
            </Button>
          </div>
        </CompactPageHeader>
      }
    >
      {centerSection === "history" ? historyPane : documentsListPane}
    </CentralWorkspaceSheet>
  );
}


