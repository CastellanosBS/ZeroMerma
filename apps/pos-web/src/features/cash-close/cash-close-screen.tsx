import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import { CatalogSelectionCard } from "../../components/catalog-selection-card";
import { CatalogVisual } from "../../components/catalog-visual";
import {
  CopyFolioAction,
  DocumentActionsMenu,
} from "../../components/document-actions";
import {
  PosBlockerPanel,
  PosConfirmationDialog,
  PosEmptyState,
  PosErrorState,
  PosInlineValidationMessage,
  PosLoadingState,
} from "../../components/pos-feedback";
import { PosButton, PosPanel, PosSectionTitle, PosStatusBadge } from "../../components/pos-foundations";
import {
  PosContextBanner,
  PosModuleLayout,
  PosSummaryPanel,
} from "../../components/pos-module-layout";
import {
  CentralWorkspaceSheet,
  FlowGuide,
  KeyValueGroup,
  KeyValueRow,
  MetricCard,
  ModuleStateChip,
  CompactPageHeader,
  ScrollPane,
  SummaryMetric,
  SearchField,
} from "../../components/pos-module-primitives";
import {
  ArrowLeftIcon,
  HashIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import { appEnv } from "../../env";
import type {
  CashCloseDetailResponse,
  CashCloseIssueView,
  CashClosePreviewResponse,
} from "../../lib/api-contracts";
import { getDocumentActionAvailability } from "../../lib/document-actions";
import { formatCurrency } from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import {
  getSelectionShortcutIndex,
  getSelectionShortcutLabel,
  isEditableTarget,
} from "../../lib/keyboard-shortcuts";
import { cn } from "../../lib/utils";
import { usePosAuthStore } from "../auth/auth-store";
import { sortOperationalClasses, sortOperationalProducts } from "../operations/model";
import {
  useOperationsCatalogQuery,
  useOperationsClassProductsQuery,
} from "../operations/queries";
import { usePosTerminalStore } from "../pos-terminal/store";
import {
  posInputClass,
  posOutlineButtonClass,
  posPrimaryButtonClass,
} from "../pos-theme/theme";
import { useStatusMessageStore } from "../status-messages/store";
import { commitCashClose, previewCashClose } from "./cash-close-api";
import {
  useCashCloseBootstrapQuery,
  useCashCloseReconciliationQuery,
  useCashCloseSummaryQuery,
} from "./queries";
import {
  CLOSE_SECTION_CONTEXT,
  CLOSE_SECTION_FINANCIAL,
  CLOSE_PHYSICAL_STATE_CLASS_SELECTION,
  CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION,
  CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE,
  CLOSE_SECTION_PHYSICAL,
  CLOSE_SECTION_RECONCILIATION,
  CLOSE_SECTION_REVIEW,
  addCashClosePendingCountLine,
  buildCashClosePreviewRequest,
  createInitialCashCloseDraftState,
  getCashCloseBlockingReason,
  getCashCloseCountValueState,
  getDraftCountedTotalCents,
  getCashCloseUiState,
  getCountedProductRowCount,
  getCountedProductTotalQuantityText,
  getDraftCountedCashCents,
  getDraftPaymentMethodRows,
  hasCashCloseExpectedPaymentCounts,
  hasCashClosePhysicalCounts,
  goBackFromCashClosePhysicalState,
  removeCashCloseCountedLine,
  sanitizeMoneyInput,
  selectClassForCashCloseCount,
  selectProductForCashCloseCount,
  setCashClosePendingQuantityText,
  setCashClosePhysicalSearchText,
  syncCashCloseDraftState,
  updateCashCloseCountedLineQuantity,
  type CashCloseFindingSeverity,
  type CashCloseDraftState,
  type CashCloseSection,
  type CashCloseUiState,
} from "./model";
import {
  canAttemptCashCloseSubmit,
  finalizeSuccessfulCashClose,
  submitCashCloseAttempt,
} from "./submit";
import {
  CountedLineRow,
  PaymentCountRow,
} from "./ui";

const CLOSE_COUNT_CATALOG_MODULE = "COUNTER_TRANSFER";

const CLOSE_WIZARD_STEP_VALIDATE = "VALIDATE";
const CLOSE_WIZARD_STEP_SUMMARY = "SUMMARY";
const CLOSE_WIZARD_STEP_CASH = "CASH";
const CLOSE_WIZARD_STEP_PAYMENTS = "PAYMENTS";
const CLOSE_WIZARD_STEP_PHYSICAL = "PHYSICAL";
const CLOSE_WIZARD_STEP_DIFFERENCES = "DIFFERENCES";
const CLOSE_WIZARD_STEP_SIGN_OFF = "SIGN_OFF";
const CLOSE_WIZARD_STEP_FINALIZE = "FINALIZE";

type CashCloseWizardStep =
  | typeof CLOSE_WIZARD_STEP_VALIDATE
  | typeof CLOSE_WIZARD_STEP_SUMMARY
  | typeof CLOSE_WIZARD_STEP_CASH
  | typeof CLOSE_WIZARD_STEP_PAYMENTS
  | typeof CLOSE_WIZARD_STEP_PHYSICAL
  | typeof CLOSE_WIZARD_STEP_DIFFERENCES
  | typeof CLOSE_WIZARD_STEP_SIGN_OFF
  | typeof CLOSE_WIZARD_STEP_FINALIZE;

const CLOSE_WIZARD_STEPS: Array<{
  description: string;
  key: CashCloseWizardStep;
  label: string;
}> = [
  {
    key: CLOSE_WIZARD_STEP_VALIDATE,
    label: "Validar sesion",
    description: "Confirma que exista una caja abierta y revisa los bloqueos del cierre.",
  },
  {
    key: CLOSE_WIZARD_STEP_SUMMARY,
    label: "Resumen",
    description: "Revisa totales, movimientos y el contexto real del turno.",
  },
  {
    key: CLOSE_WIZARD_STEP_CASH,
    label: "Efectivo",
    description: "Captura el total de efectivo contado. El desglose por denominacion sigue diferido.",
  },
  {
    key: CLOSE_WIZARD_STEP_PAYMENTS,
    label: "Tarjeta y otros",
    description: "Concuerda tarjeta y medios adicionales antes de pasar al mostrador.",
  },
  {
    key: CLOSE_WIZARD_STEP_PHYSICAL,
    label: "Mostrador y clase",
    description: "Cuenta el mostrador y deja lista la conciliacion por clase.",
  },
  {
    key: CLOSE_WIZARD_STEP_DIFFERENCES,
    label: "Diferencias",
    description: "Revisa ajustes preparados, advertencias y cualquier desvio del turno.",
  },
  {
    key: CLOSE_WIZARD_STEP_SIGN_OFF,
    label: "Validacion",
    description: "Registra la revision del cajero y deja visible lo pendiente para backoffice.",
  },
  {
    key: CLOSE_WIZARD_STEP_FINALIZE,
    label: "Cierre final",
    description: "Confirma el resultado final y conserva el reporte del cierre antes de salir.",
  },
];

function getWizardStepLabel(step: CashCloseWizardStep): string {
  return CLOSE_WIZARD_STEPS.find((wizardStep) => wizardStep.key === step)?.label ?? "Cerrar turno";
}

function mapWizardStepToSection(step: CashCloseWizardStep): CashCloseSection {
  switch (step) {
    case CLOSE_WIZARD_STEP_VALIDATE:
    case CLOSE_WIZARD_STEP_SUMMARY:
      return CLOSE_SECTION_CONTEXT;
    case CLOSE_WIZARD_STEP_CASH:
    case CLOSE_WIZARD_STEP_PAYMENTS:
      return CLOSE_SECTION_FINANCIAL;
    case CLOSE_WIZARD_STEP_PHYSICAL:
      return CLOSE_SECTION_PHYSICAL;
    case CLOSE_WIZARD_STEP_DIFFERENCES:
      return CLOSE_SECTION_RECONCILIATION;
    case CLOSE_WIZARD_STEP_SIGN_OFF:
    case CLOSE_WIZARD_STEP_FINALIZE:
      return CLOSE_SECTION_REVIEW;
    default:
      return CLOSE_SECTION_CONTEXT;
  }
}

function mapSectionToWizardStep(section: CashCloseSection): CashCloseWizardStep {
  switch (section) {
    case CLOSE_SECTION_CONTEXT:
      return CLOSE_WIZARD_STEP_VALIDATE;
    case CLOSE_SECTION_FINANCIAL:
      return CLOSE_WIZARD_STEP_CASH;
    case CLOSE_SECTION_PHYSICAL:
      return CLOSE_WIZARD_STEP_PHYSICAL;
    case CLOSE_SECTION_RECONCILIATION:
      return CLOSE_WIZARD_STEP_DIFFERENCES;
    case CLOSE_SECTION_REVIEW:
      return CLOSE_WIZARD_STEP_FINALIZE;
    default:
      return CLOSE_WIZARD_STEP_VALIDATE;
  }
}

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  CARD: "Tarjeta",
  CASH: "Efectivo",
  MIXED: "Mixto",
};

interface DetectedDifferenceItem {
  description: string;
  key: string;
  severity: CashCloseFindingSeverity;
  targetSection: CashCloseSection | null;
  targetSectionLabel: string | null;
  title: string;
}

function useDebouncedValue(value: string, delayMs: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeoutId);
  }, [delayMs, value]);

  return debouncedValue;
}

function getDifferenceTitle(code: string): string {
  switch (code) {
    case "MISSING_COUNTED_PAYMENT_TOTALS":
      return "Completa el efectivo contado";
    case "MISSING_COUNTED_CLOSING_STOCK":
      return "Completa el conteo del mostrador";
    case "UNRESOLVED_CLASS_CAPTURE_MISMATCH":
      return "Quedan ventas por clase sin conciliar";
    case "INVALID_MANUAL_RECONCILIATION_OVERRIDE":
      return "La conciliacion ya no es valida";
    case "INVALID_DISCREPANCY_RESOLUTION":
      return "Hay una diferencia que requiere revision";
    case "INTERNAL_INTEGRITY_MISMATCH":
      return "El cierre requiere una revision adicional";
    default:
      return "Revisa esta diferencia";
  }
}

function getWarningTitle(code: string): string {
  switch (code) {
    case "PENDING_INBOUND_TRANSFERS":
      return "Hay envios pendientes por recibir";
    case "OUTBOUND_TRANSFERS_IN_TRANSIT":
      return "Hay envios en transito";
    case "LARGE_CASH_VARIANCE":
      return "La diferencia de efectivo es alta";
    case "LONG_SESSION_DURATION":
      return "El turno lleva abierto mas tiempo de lo habitual";
    default:
      return "Atencion del cierre";
  }
}

function getSectionLabel(section: CashCloseSection): string {
  switch (section) {
    case CLOSE_SECTION_CONTEXT:
      return "Contexto";
    case CLOSE_SECTION_FINANCIAL:
      return "Conteo financiero";
    case CLOSE_SECTION_PHYSICAL:
      return "Conteo fisico";
    case CLOSE_SECTION_RECONCILIATION:
      return "Reconciliacion";
    case CLOSE_SECTION_REVIEW:
      return "Revision y cierre";
    default:
      return "Cerrar turno";
  }
}

function getPreviousWizardStep(step: CashCloseWizardStep): CashCloseWizardStep | null {
  const stepIndex = CLOSE_WIZARD_STEPS.findIndex((wizardStep) => wizardStep.key === step);
  if (stepIndex <= 0) {
    return null;
  }

  return CLOSE_WIZARD_STEPS[stepIndex - 1]?.key ?? null;
}

function getDifferenceTargetSection(code: string): CashCloseSection | null {
  switch (code) {
    case "MISSING_COUNTED_PAYMENT_TOTALS":
      return CLOSE_SECTION_FINANCIAL;
    case "MISSING_COUNTED_CLOSING_STOCK":
      return CLOSE_SECTION_PHYSICAL;
    case "UNRESOLVED_CLASS_CAPTURE_MISMATCH":
    case "INVALID_MANUAL_RECONCILIATION_OVERRIDE":
    case "INVALID_DISCREPANCY_RESOLUTION":
    case "INTERNAL_INTEGRITY_MISMATCH":
      return CLOSE_SECTION_RECONCILIATION;
    default:
      return null;
  }
}

function getWarningTargetSection(code: string): CashCloseSection | null {
  switch (code) {
    case "LARGE_CASH_VARIANCE":
      return CLOSE_SECTION_FINANCIAL;
    case "PENDING_INBOUND_TRANSFERS":
    case "OUTBOUND_TRANSFERS_IN_TRANSIT":
    case "LONG_SESSION_DURATION":
      return CLOSE_SECTION_CONTEXT;
    default:
      return null;
  }
}

function formatLocalDateTime(value: string | null | undefined): string {
  if (!value) {
    return "--";
  }

  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
  }).format(new Date(value));
}

function buildWarningItems(warnings: CashCloseIssueView[]): DetectedDifferenceItem[] {
  return warnings.map((issue) => ({
    description: issue.message,
    key: `warning-${issue.code}`,
    severity: "WARNING" as const,
    targetSection: getWarningTargetSection(issue.code),
    targetSectionLabel: getWarningTargetSection(issue.code)
      ? getSectionLabel(getWarningTargetSection(issue.code)!)
      : null,
    title: getWarningTitle(issue.code),
  }));
}

function buildBlockerItems(
  previewResult: CashClosePreviewResponse | null,
): DetectedDifferenceItem[] {
  if (!previewResult) {
    return [];
  }

  return previewResult.blockers.map((issue) => ({
    description: issue.message,
    key: `blocker-${issue.code}`,
    severity: "BLOCKER" as const,
    targetSection: getDifferenceTargetSection(issue.code),
    targetSectionLabel: getDifferenceTargetSection(issue.code)
      ? getSectionLabel(getDifferenceTargetSection(issue.code)!)
      : null,
    title: getDifferenceTitle(issue.code),
  }));
}

function buildInfoItems(
  previewResult: CashClosePreviewResponse | null,
): DetectedDifferenceItem[] {
  if (!previewResult) {
    return [];
  }

  return [
    ...previewResult.discrepancy_resolutions.map((resolution) => ({
      description: `Esperado ${resolution.expected_quantity}, contado ${resolution.counted_quantity}. El sistema preparara ${
        resolution.resolution_type === "CLOSE_WASTE_ADJUSTMENT"
          ? "un ajuste por merma"
          : "un ajuste de mostrador"
      }.`,
      key: `discrepancy-${resolution.product_id}`,
      severity: "INFO" as const,
      targetSection: CLOSE_SECTION_RECONCILIATION as CashCloseSection,
      targetSectionLabel: getSectionLabel(CLOSE_SECTION_RECONCILIATION),
      title: resolution.product_name,
    })),
    ...previewResult.class_reconciliations.map((reconciliation) => ({
      description:
        reconciliation.resolution_status === "AUTO_RESOLVED" ||
        reconciliation.resolution_status === "MANUAL_RESOLVED"
          ? `${reconciliation.product_class_name} quedo conciliada durante la revision.`
          : `Quedaron ${reconciliation.pending_quantity} pendientes en ${reconciliation.product_class_name}. El sistema seguira revisando esa clase con el conteo capturado.`,
      key: `class-${reconciliation.product_class_id}`,
      severity: "INFO" as const,
      targetSection: CLOSE_SECTION_RECONCILIATION as CashCloseSection,
      targetSectionLabel: getSectionLabel(CLOSE_SECTION_RECONCILIATION),
      title: reconciliation.product_class_name,
    })),
  ];
}

function getDifferenceBoxClass(severity: CashCloseFindingSeverity) {
  switch (severity) {
    case "BLOCKER":
      return "border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
    case "WARNING":
      return "border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
    default:
      return "border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] text-slate-700";
  }
}

function getCloseUiStateLabel(uiState: CashCloseUiState): string {
  switch (uiState) {
    case "HAS_HARD_BLOCKERS":
      return "Bloqueado";
    case "HAS_WARNINGS":
      return "Con advertencias";
    case "READY_TO_CLOSE":
      return "Listo para cerrar";
    case "CLOSING":
      return "Cerrando...";
    case "CLOSED":
      return "Cerrado";
    case "ERROR":
      return "Error";
    default:
      return "En revision";
  }
}

function getCloseUiStateTone(
  uiState: CashCloseUiState,
): "danger" | "info" | "success" | "warning" {
  switch (uiState) {
    case "HAS_HARD_BLOCKERS":
    case "ERROR":
      return "danger";
    case "HAS_WARNINGS":
      return "warning";
    case "READY_TO_CLOSE":
    case "CLOSED":
      return "success";
    default:
      return "info";
  }
}

function CloseFindingsGroup({
  emptyMessage,
  findings,
  onResolve,
  title,
}: {
  emptyMessage?: string;
  findings: DetectedDifferenceItem[];
  onResolve?: (section: CashCloseSection) => void;
  title: string;
}) {
  if (findings.length === 0) {
    return emptyMessage ? (
      <div className="rounded-2xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-4 text-sm leading-6 text-slate-600">
        {emptyMessage}
      </div>
    ) : null;
  }

  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-950">{title}</p>
        <span className="pos-chip" data-tone="muted">
          {findings.length}
        </span>
      </div>

      {findings.map((finding) => (
        <div
          className={cn(
            "rounded-2xl border px-4 py-4",
            getDifferenceBoxClass(finding.severity),
          )}
          key={finding.key}
        >
          <p className="text-sm font-semibold text-slate-950">{finding.title}</p>
          <p className="mt-1 text-sm leading-6 text-slate-700">{finding.description}</p>
          {finding.targetSection && finding.targetSectionLabel && onResolve ? (
            <div className="mt-3">
              <Button
                className={cn("h-9 px-3", posOutlineButtonClass)}
                onClick={() => onResolve(finding.targetSection!)}
                type="button"
                variant="outline"
              >
                Ir a {finding.targetSectionLabel}
              </Button>
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function CloseConfirmationDialog({
  countedCashText,
  countedLineCount,
  countedUnitsText,
  discrepancyText,
  expectedCashText,
  isOpen,
  isPending,
  onCancel,
  onConfirm,
  sessionLabel,
  warningMessages,
}: {
  countedCashText: string;
  countedLineCount: number;
  countedUnitsText: string;
  discrepancyText: string;
  expectedCashText: string;
  isOpen: boolean;
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  sessionLabel: string;
  warningMessages: string[];
}) {
  return (
    <PosConfirmationDialog
      confirmation={{
        cancelLabel: "Cancelar",
        confirmLabel: "Confirmar cierre",
        description:
          "Se registrara el cierre final con los conteos capturados y el sistema aplicara la conciliacion resultante.",
        eyebrow: "Confirma el cierre",
        title: "Confirmar cierre",
        tone: "warning",
      }}
      details={
        <>
          <div className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3 text-sm text-slate-700">
            <p>
              Turno: <span className="font-semibold text-slate-950">{sessionLabel}</span>
            </p>
            <p>
              Efectivo contado: <span className="font-semibold text-slate-950">{countedCashText}</span>
            </p>
            <p>
              Efectivo esperado: <span className="font-semibold text-slate-950">{expectedCashText}</span>
            </p>
            <p>
              Diferencia: <span className="font-semibold text-slate-950">{discrepancyText}</span>
            </p>
            <p>
              Lineas contadas: <span className="font-semibold text-slate-950">{countedLineCount}</span>
            </p>
            <p>
              Unidades contadas: <span className="font-semibold text-slate-950">{countedUnitsText}</span>
            </p>
          </div>

          {warningMessages.length > 0 ? (
            <div className="rounded-xl border border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)] px-3 py-3 text-sm text-slate-700">
              <p className="font-semibold text-slate-950">Advertencias</p>
              <ul className="mt-2 grid gap-1">
                {warningMessages.map((warning) => (
                  <li key={warning}>- {warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      }
      isOpen={isOpen}
      isPending={isPending}
      onCancel={onCancel}
      onConfirm={onConfirm}
    />
  );
}

export function CashCloseScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const clearSession = usePosAuthStore((state) => state.clearSession);
  const resetPosTerminal = usePosTerminalStore((state) => state.reset);
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const bootstrapQuery = useCashCloseBootstrapQuery();
  const [activeStep, setActiveStep] = useState<CashCloseWizardStep>(CLOSE_WIZARD_STEP_VALIDATE);
  const [draftState, setDraftState] = useState<CashCloseDraftState>(
    createInitialCashCloseDraftState(),
  );
  const [validationResult, setValidationResult] = useState<CashClosePreviewResponse | null>(null);
  const [isLivePreviewPending, setIsLivePreviewPending] = useState(false);
  const [livePreviewErrorMessage, setLivePreviewErrorMessage] = useState<string | null>(null);
  const [submitErrorMessage, setSubmitErrorMessage] = useState<string | null>(null);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [hasClosedSuccessfully, setHasClosedSuccessfully] = useState(false);
  const [completedCloseDetail, setCompletedCloseDetail] = useState<CashCloseDetailResponse | null>(
    null,
  );
  const [isCloseAcknowledged, setIsCloseAcknowledged] = useState(false);
  const quantityInputRef = useRef<HTMLInputElement>(null);
  const paymentInputRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const livePreviewRequestRef = useRef(0);
  const currentOpenCashSession = bootstrapQuery.data?.current_open_cash_session ?? null;
  const summaryQuery = useCashCloseSummaryQuery(currentOpenCashSession !== null);
  const reconciliationQuery = useCashCloseReconciliationQuery(currentOpenCashSession !== null);
  const debouncedSearchText = useDebouncedValue(draftState.physicalSearchText, 180);
  const catalogQuery = useOperationsCatalogQuery(
    CLOSE_COUNT_CATALOG_MODULE,
    draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION
      ? debouncedSearchText
      : "",
  );
  const classProductsQuery = useOperationsClassProductsQuery(
    CLOSE_COUNT_CATALOG_MODULE,
    draftState.physicalPendingSelection?.productClass.id ?? null,
    draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION
      ? debouncedSearchText
      : "",
  );

  const sortedClasses = useMemo(
    () => sortOperationalClasses(catalogQuery.data?.classes ?? []),
    [catalogQuery.data?.classes],
  );
  const sortedProducts = useMemo(
    () => sortOperationalProducts(classProductsQuery.data?.products ?? []),
    [classProductsQuery.data?.products],
  );
  const activeSection = mapWizardStepToSection(activeStep);
  const countedCashState = getCashCloseCountValueState(
    draftState.countedPaymentAmounts.CASH ?? "",
  );
  const countedCashText =
    countedCashState === "CAPTURED"
      ? formatCurrency(getDraftCountedCashCents(draftState.countedPaymentAmounts) / 100)
      : "Pendiente";
  const countedLineCount = getCountedProductRowCount(draftState);
  const countedUnitsText = getCountedProductTotalQuantityText(draftState);
  const { countedPaymentAmounts, countedProductDraftLines } = draftState;
  const previewPayload = useMemo(
    () =>
      buildCashClosePreviewRequest(appEnv.VITE_POS_WORKSTATION_CODE, {
        countedPaymentAmounts,
        countedProductDraftLines,
      }),
    [countedPaymentAmounts, countedProductDraftLines],
  );
  const blockerFindings = useMemo(() => buildBlockerItems(validationResult), [validationResult]);
  const warningItems = useMemo(
    () =>
      buildWarningItems(
        validationResult?.warnings ??
          summaryQuery.data?.warnings ??
          bootstrapQuery.data?.warnings ??
          [],
      ),
    [bootstrapQuery.data, summaryQuery.data, validationResult],
  );
  const infoFindings = useMemo(() => buildInfoItems(validationResult), [validationResult]);
  const paymentMethodDraftRows = useMemo(
    () =>
      bootstrapQuery.data
        ? getDraftPaymentMethodRows(
            bootstrapQuery.data.payment_method_catalog,
            draftState.countedPaymentAmounts,
          )
        : [],
    [bootstrapQuery.data, draftState.countedPaymentAmounts],
  );
  const missingExpectedMethodLabels = useMemo(
    () =>
      paymentMethodDraftRows
        .filter(
          (row) =>
            row.isExpectedSupported &&
            getCashCloseCountValueState(row.countedAmountText) === "PENDING",
        )
        .map((row) => PAYMENT_METHOD_LABELS[row.key] ?? row.key),
    [paymentMethodDraftRows],
  );
  const countedCardRow =
    paymentMethodDraftRows.find((row) => row.key === "CARD") ?? null;
  const countedCardText = countedCardRow
    ? getCashCloseCountValueState(countedCardRow.countedAmountText) === "CAPTURED"
      ? formatCurrency(countedCardRow.countedAmountCents / 100)
      : "Pendiente"
    : "--";
  const hasExpectedFinancialCounts = useMemo(
    () =>
      bootstrapQuery.data
        ? hasCashCloseExpectedPaymentCounts(
            bootstrapQuery.data.payment_method_catalog,
            draftState.countedPaymentAmounts,
          )
        : false,
    [bootstrapQuery.data, draftState.countedPaymentAmounts],
  );
  const hasPhysicalCounts = useMemo(() => hasCashClosePhysicalCounts(draftState), [draftState]);
  const totalExpectedCents = useMemo(() => {
    if (validationResult) {
      return validationResult.payment_method_rows.reduce((runningTotal, row) => {
        return runningTotal + Math.round(Number(row.expected_amount ?? 0) * 100);
      }, 0);
    }

    if (summaryQuery.data) {
      return Math.round(Number(summaryQuery.data.expected_cash_amount) * 100);
    }

    return 0;
  }, [summaryQuery.data, validationResult]);
  const totalVarianceText = hasExpectedFinancialCounts
    ? formatCurrency(
        (getDraftCountedTotalCents(draftState.countedPaymentAmounts) - totalExpectedCents) / 100,
      )
    : "Pendiente";
  const resolvedClassCount = useMemo(
    () =>
      validationResult?.class_reconciliations.filter(
        (reconciliation) =>
          reconciliation.resolution_status === "AUTO_RESOLVED" ||
          reconciliation.resolution_status === "MANUAL_RESOLVED",
      ).length ?? 0,
    [validationResult],
  );
  const unresolvedClassCount = useMemo(
    () =>
      validationResult?.class_reconciliations.filter(
        (reconciliation) =>
          reconciliation.resolution_status !== "AUTO_RESOLVED" &&
          reconciliation.resolution_status !== "MANUAL_RESOLVED",
      ).length ?? 0,
    [validationResult],
  );
  const generatedAdjustmentCount =
    validationResult?.generated_discrepancy_documents.length ??
    validationResult?.discrepancy_resolutions.length ??
    0;
  const sessionOpenedAtText = formatLocalDateTime(
    currentOpenCashSession?.opened_at ? String(currentOpenCashSession.opened_at) : null,
  );
  const flowActiveStepKey =
    draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION
      ? "product"
      : draftState.physicalControlState === CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE
        ? "quantity"
        : "class";
  const quantitySelection =
    draftState.physicalControlState === CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE
      ? draftState.physicalPendingSelection
      : null;
  const quantityProduct = quantitySelection?.product ?? null;
  const expectedCashText =
    validationResult?.expected_cash_amount !== undefined
      ? formatCurrency(Number(validationResult.expected_cash_amount))
      : summaryQuery.data
        ? formatCurrency(summaryQuery.data.expected_cash_amount)
        : "--";
  const cashVarianceText =
    validationResult?.cash_variance_amount !== undefined
      ? formatCurrency(Number(validationResult.cash_variance_amount))
      : totalVarianceText;
  const hasLargeVarianceWarning = warningItems.some(
    (warning) => warning.key === "warning-LARGE_CASH_VARIANCE",
  );
  const requiresCloseAcknowledgement =
    validationResult !== null &&
    (warningItems.length > 0 ||
      generatedAdjustmentCount > 0 ||
      Number(validationResult.cash_variance_amount ?? 0) !== 0);

  function updateDraftState(
    updater: (currentState: CashCloseDraftState) => CashCloseDraftState,
  ) {
    setDraftState((currentState) => updater(currentState));
    setHasClosedSuccessfully(false);
    setCompletedCloseDetail(null);
    setIsCloseAcknowledged(false);
    setSubmitErrorMessage(null);
    setLivePreviewErrorMessage(null);
  }

  useEffect(() => {
    if (!bootstrapQuery.data) {
      return;
    }

    setDraftState((currentState) =>
      syncCashCloseDraftState(currentState, {
        paymentMethodCatalog: bootstrapQuery.data.payment_method_catalog,
      }),
    );
  }, [bootstrapQuery.data]);

  useEffect(() => {
    if (draftState.physicalControlState !== CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE) {
      return;
    }

    quantityInputRef.current?.focus();
  }, [draftState.physicalControlState, draftState.physicalPendingSelection]);

  useEffect(() => {
    if (accessToken === null || currentOpenCashSession === null) {
      setIsLivePreviewPending(false);
      return;
    }

    const currentRequestId = livePreviewRequestRef.current + 1;
    livePreviewRequestRef.current = currentRequestId;
    setIsLivePreviewPending(true);

    const timeoutId = window.setTimeout(() => {
      void previewCashClose(accessToken, previewPayload)
        .then((previewResult) => {
          if (livePreviewRequestRef.current !== currentRequestId) {
            return;
          }

          setValidationResult(previewResult);
          setIsLivePreviewPending(false);
          setLivePreviewErrorMessage(null);
        })
        .catch((error) => {
          if (livePreviewRequestRef.current !== currentRequestId) {
            return;
          }

          setIsLivePreviewPending(false);
          setLivePreviewErrorMessage(
            toOperationalErrorMessage(
              error,
              "No pudimos actualizar la conciliacion del cierre.",
            ),
          );
        });
    }, 320);

    return () => window.clearTimeout(timeoutId);
  }, [accessToken, currentOpenCashSession, previewPayload]);

  useEffect(() => {
    function handleKeyboard(event: KeyboardEvent) {
      if (event.key === "Escape" && isConfirmDialogOpen) {
        event.preventDefault();
        setIsConfirmDialogOpen(false);
        return;
      }

      if (event.key === "Escape" && !isEditableTarget(event.target)) {
        if (
          activeStep === CLOSE_WIZARD_STEP_PHYSICAL &&
          draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION &&
          draftState.physicalSearchText.trim().length === 0
        ) {
          event.preventDefault();
          setActiveStep(CLOSE_WIZARD_STEP_PAYMENTS);
          return;
        }

        const previousStep = getPreviousWizardStep(activeStep);
        if (previousStep !== null) {
          event.preventDefault();
          setActiveStep(previousStep);
          return;
        }
      }

      if (activeStep !== CLOSE_WIZARD_STEP_PHYSICAL) {
        return;
      }

      if (event.key === "Escape") {
        if (
          draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION ||
          draftState.physicalControlState === CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE
        ) {
          event.preventDefault();
          updateDraftState((state) => goBackFromCashClosePhysicalState(state));
          return;
        }

        if (draftState.physicalSearchText.trim().length > 0) {
          event.preventDefault();
          updateDraftState((state) => setCashClosePhysicalSearchText(state, ""));
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

      if (draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION) {
        const productClass = sortedClasses[shortcutIndex];
        if (productClass) {
          event.preventDefault();
          updateDraftState((state) => selectClassForCashCloseCount(state, productClass));
        }
        return;
      }

      if (draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION) {
        const product = sortedProducts[shortcutIndex];
        if (product) {
          event.preventDefault();
          updateDraftState((state) => selectProductForCashCloseCount(state, product));
        }
      }
    }

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [
    activeStep,
    draftState.physicalControlState,
    draftState.physicalSearchText,
    isConfirmDialogOpen,
    sortedClasses,
    sortedProducts,
  ]);

  const closeMutation = useMutation({
    mutationFn: (payload: ReturnType<typeof buildCashClosePreviewRequest>) =>
      submitCashCloseAttempt({
        commit: (validatedPayload) => commitCashClose(accessToken!, validatedPayload),
        payload,
        preview: (validatedPayload) => previewCashClose(accessToken!, validatedPayload),
      }),
    onSuccess: async (result) => {
      setValidationResult(result.preview);
      setIsConfirmDialogOpen(false);

      if (!result.detail) {
        setHasClosedSuccessfully(false);
        setCompletedCloseDetail(null);
        setSubmitErrorMessage(
          "Se detectaron diferencias o datos faltantes. Revisa lo marcado en esta consola antes de volver a cerrar.",
        );
        setActiveStep(CLOSE_WIZARD_STEP_FINALIZE);
        return;
      }

      setHasClosedSuccessfully(true);
      setCompletedCloseDetail(result.detail);
      setSubmitErrorMessage(null);
      setActiveStep(CLOSE_WIZARD_STEP_FINALIZE);
      showSuccess(`Turno cerrado · ID ${result.detail.id}.`);
    },
    onError: (error) => {
      const nextMessage = toOperationalErrorMessage(
        error,
        "No fue posible validar o cerrar el turno.",
      );
      setHasClosedSuccessfully(false);
      setCompletedCloseDetail(null);
      setSubmitErrorMessage(nextMessage);
      showError(nextMessage);
      setActiveStep(CLOSE_WIZARD_STEP_FINALIZE);
    },
  });

  const canAttemptCommit = canAttemptCashCloseSubmit({
    accessToken,
    hasOpenCashSession: currentOpenCashSession !== null,
    isCommitPending: closeMutation.isPending,
  });
  const closeUiState = getCashCloseUiState({
    activeSection,
    draftState,
    hasClosedSuccessfully,
    hasOpenCashSession: currentOpenCashSession !== null,
    hasSubmitError: submitErrorMessage !== null,
    isClosing: closeMutation.isPending,
    isLoadingContext: bootstrapQuery.isPending,
    isPreviewPending: isLivePreviewPending,
    paymentMethodCatalog: bootstrapQuery.data?.payment_method_catalog ?? [],
    previewResult: validationResult,
  });

  const currentSectionLabel = getWizardStepLabel(activeStep);
  const openingAmountText = summaryQuery.data
    ? formatCurrency(summaryQuery.data.opening_amount)
    : "--";
  const sessionStateLabel =
    currentOpenCashSession === null
      ? "No hay una caja abierta."
      : `Caja abierta desde ${sessionOpenedAtText}`;
  const readinessTone = getCloseUiStateTone(closeUiState);
  const readinessLabel = getCloseUiStateLabel(closeUiState);
  const signOffIsReady =
    validationResult !== null &&
    validationResult.blockers.length === 0 &&
    (!requiresCloseAcknowledgement || isCloseAcknowledged);
  const isReviewReadyForClose =
    signOffIsReady &&
    canAttemptCommit &&
    hasExpectedFinancialCounts &&
    hasPhysicalCounts &&
    validationResult?.reconciliation_status === "READY";
  const baseBlockingReason = getCashCloseBlockingReason({
    draftState,
    hasOpenCashSession: currentOpenCashSession !== null,
    paymentMethodCatalog: bootstrapQuery.data?.payment_method_catalog ?? [],
    previewResult: validationResult,
  });
  const financialBlockingReason =
    missingExpectedMethodLabels.length === 0
      ? null
      : missingExpectedMethodLabels.length === 1 &&
          missingExpectedMethodLabels[0] === "Efectivo"
        ? "Falta capturar efectivo contado."
        : missingExpectedMethodLabels.length === 1 &&
            missingExpectedMethodLabels[0] === "Tarjeta"
          ? "Falta capturar tarjeta contada."
          : "Completa los montos contados del cierre.";
  const physicalBlockingReason = hasPhysicalCounts ? null : "Falta conteo fisico.";
  const differencesBlockingReason =
    isLivePreviewPending
      ? "Estamos conciliando el conteo actual."
      : validationResult === null
        ? "Aun no hay una vista previa del cierre."
        : null;
  const signOffBlockingReason =
    validationResult === null
      ? "Actualiza la vista previa antes de validar el cierre."
      : blockerFindings.length > 0
        ? "Resuelve los bloqueos antes de validar el cierre."
        : requiresCloseAcknowledgement && !isCloseAcknowledged
          ? "Confirma la revision del cajero para continuar."
          : null;

  const focusPaymentMethodInput = useCallback((paymentMethodCode: string | null) => {
    if (!paymentMethodCode) {
      return;
    }

    paymentInputRefs.current[paymentMethodCode]?.focus();
  }, []);

  const handlePaymentFieldKeyDown = useCallback(
    (paymentMethodCode: string) => (event: ReactKeyboardEvent<HTMLInputElement>) => {
      if (event.key !== "Enter" && event.key !== "NumpadEnter") {
        return;
      }

      event.preventDefault();

      const visibleRows =
        activeStep === CLOSE_WIZARD_STEP_CASH
          ? paymentMethodDraftRows.filter((row) => row.key === "CASH")
          : paymentMethodDraftRows.filter((row) => row.key !== "CASH");
      const currentIndex = visibleRows.findIndex((row) => row.key === paymentMethodCode);
      const nextRow = visibleRows[currentIndex + 1] ?? null;
      if (nextRow) {
        focusPaymentMethodInput(nextRow.key);
        return;
      }

      if (activeStep === CLOSE_WIZARD_STEP_CASH) {
        setActiveStep(CLOSE_WIZARD_STEP_PAYMENTS);
        window.setTimeout(() => {
          const firstNonCash =
            paymentMethodDraftRows.find((row) => row.key !== "CASH")?.key ?? null;
          if (firstNonCash) {
            focusPaymentMethodInput(firstNonCash);
          }
        }, 0);
        return;
      }

      setActiveStep(CLOSE_WIZARD_STEP_PHYSICAL);
    },
    [activeStep, focusPaymentMethodInput, paymentMethodDraftRows],
  );

  const handleProceedToNextSession = useCallback(async () => {
    resetPosTerminal();
    queryClient.clear();
    await navigate({ to: "/cash-session/open" });
  }, [navigate, queryClient, resetPosTerminal]);

  const handleExitAfterClose = useCallback(async () => {
    await finalizeSuccessfulCashClose({
      clearQueryCache: () => queryClient.clear(),
      clearSession,
      navigateToLogin: () => navigate({ to: "/login" }),
      resetPosTerminal,
    });
  }, [clearSession, navigate, queryClient, resetPosTerminal]);

  const handleCommitAttempt = useCallback(() => {
    if (!isReviewReadyForClose) {
      return;
    }

    setSubmitErrorMessage(null);
    setHasClosedSuccessfully(false);
    closeMutation.mutate(previewPayload);
  }, [closeMutation, isReviewReadyForClose, previewPayload]);

  const handleStepSelect = useCallback((step: CashCloseWizardStep) => {
    setActiveStep(step);
  }, []);

  const primaryActionLabel =
    completedCloseDetail
      ? "Abrir nuevo turno"
      : activeStep === CLOSE_WIZARD_STEP_VALIDATE
        ? currentOpenCashSession === null
          ? "Ir a apertura"
          : "Ver resumen del turno"
        : activeStep === CLOSE_WIZARD_STEP_SUMMARY
          ? "Capturar efectivo"
          : activeStep === CLOSE_WIZARD_STEP_CASH
            ? "Revisar tarjeta y otros"
            : activeStep === CLOSE_WIZARD_STEP_PAYMENTS
              ? "Contar mostrador"
              : activeStep === CLOSE_WIZARD_STEP_PHYSICAL
                ? "Revisar diferencias"
                : activeStep === CLOSE_WIZARD_STEP_DIFFERENCES
                  ? "Validar cierre"
                  : activeStep === CLOSE_WIZARD_STEP_SIGN_OFF
                    ? "Ir al cierre final"
                    : hasClosedSuccessfully
                      ? "Abrir nuevo turno"
                      : "Confirmar cierre";
  const primaryActionHandler = useCallback(() => {
    if (completedCloseDetail) {
      void handleProceedToNextSession();
      return;
    }

    if (activeStep === CLOSE_WIZARD_STEP_VALIDATE) {
      if (currentOpenCashSession === null) {
        void navigate({ to: "/cash-session/open" });
        return;
      }
      setActiveStep(CLOSE_WIZARD_STEP_SUMMARY);
      return;
    }

    if (activeStep === CLOSE_WIZARD_STEP_SUMMARY) {
      setActiveStep(CLOSE_WIZARD_STEP_CASH);
      return;
    }

    if (activeStep === CLOSE_WIZARD_STEP_CASH) {
      setActiveStep(CLOSE_WIZARD_STEP_PAYMENTS);
      return;
    }

    if (activeStep === CLOSE_WIZARD_STEP_PAYMENTS) {
      setActiveStep(CLOSE_WIZARD_STEP_PHYSICAL);
      return;
    }

    if (activeStep === CLOSE_WIZARD_STEP_PHYSICAL) {
      setActiveStep(CLOSE_WIZARD_STEP_DIFFERENCES);
      return;
    }

    if (activeStep === CLOSE_WIZARD_STEP_DIFFERENCES) {
      setActiveStep(CLOSE_WIZARD_STEP_SIGN_OFF);
      return;
    }

    if (activeStep === CLOSE_WIZARD_STEP_SIGN_OFF) {
      setActiveStep(CLOSE_WIZARD_STEP_FINALIZE);
      return;
    }

    if (isReviewReadyForClose) {
      setIsConfirmDialogOpen(true);
    }
  }, [
    activeStep,
    completedCloseDetail,
    currentOpenCashSession,
    handleProceedToNextSession,
    isReviewReadyForClose,
    navigate,
  ]);
  const primaryActionHelperText =
    completedCloseDetail
      ? "El cierre ya quedo registrado. Puedes iniciar el siguiente turno o salir."
      : activeStep === CLOSE_WIZARD_STEP_VALIDATE
        ? "Primero valida que la caja abierta corresponda al turno que vas a cerrar."
        : activeStep === CLOSE_WIZARD_STEP_SUMMARY
          ? "Revisa totales y movimientos antes de capturar conteos."
          : activeStep === CLOSE_WIZARD_STEP_CASH
            ? "Captura el total contado de efectivo. Enter avanza al siguiente paso."
            : activeStep === CLOSE_WIZARD_STEP_PAYMENTS
              ? hasExpectedFinancialCounts
                ? "Los medios de pago ya quedaron listos para pasar al conteo fisico."
                : "Captura tarjeta y otros medios reales del turno."
              : activeStep === CLOSE_WIZARD_STEP_PHYSICAL
                ? hasPhysicalCounts
                  ? "El conteo fisico ya puede revisarse contra la conciliacion."
                  : "Cuenta solo lo que quedo fisicamente en mostrador."
                : activeStep === CLOSE_WIZARD_STEP_DIFFERENCES
                  ? "Revisa bloqueos, advertencias y ajustes preparados por el backend."
                  : activeStep === CLOSE_WIZARD_STEP_SIGN_OFF
                    ? requiresCloseAcknowledgement
                      ? "Registra la revision del cajero antes del cierre final."
                      : "No hay diferencias criticas adicionales para validar."
                    : blockerFindings.length > 0
                      ? "Resuelve los bloqueos marcados antes de confirmar."
                      : warningItems.length > 0
                        ? "El cierre puede continuar con advertencias visibles."
                        : "La vista previa quedo lista para registrarse.";
  const primaryActionDisabledReason =
    closeMutation.isPending
      ? "Estamos cerrando el turno."
      : completedCloseDetail
        ? null
        : activeStep === CLOSE_WIZARD_STEP_VALIDATE
          ? null
          : activeStep === CLOSE_WIZARD_STEP_SUMMARY
            ? currentOpenCashSession === null
              ? "No hay una sesion abierta para cerrar."
              : null
            : activeStep === CLOSE_WIZARD_STEP_CASH
              ? currentOpenCashSession === null
                ? "No hay una sesion abierta para cerrar."
                : null
              : activeStep === CLOSE_WIZARD_STEP_PAYMENTS
                ? hasExpectedFinancialCounts
                  ? null
                  : financialBlockingReason ?? baseBlockingReason
                : activeStep === CLOSE_WIZARD_STEP_PHYSICAL
                  ? physicalBlockingReason
                  : activeStep === CLOSE_WIZARD_STEP_DIFFERENCES
                    ? differencesBlockingReason
                    : activeStep === CLOSE_WIZARD_STEP_SIGN_OFF
                      ? signOffBlockingReason
                      : isReviewReadyForClose
                        ? null
                        : baseBlockingReason;
  const primaryActionDisabled =
    closeMutation.isPending ||
    accessToken === null ||
    primaryActionDisabledReason !== null;

  useEffect(() => {
    function handlePrimaryEnter(event: KeyboardEvent) {
      if (
        event.key !== "Enter" ||
        isConfirmDialogOpen ||
        isEditableTarget(event.target) ||
        primaryActionDisabled
      ) {
        return;
      }

        event.preventDefault();
        primaryActionHandler();
    }

    window.addEventListener("keydown", handlePrimaryEnter);
    return () => window.removeEventListener("keydown", handlePrimaryEnter);
  }, [isConfirmDialogOpen, primaryActionDisabled, primaryActionHandler]);

  const panelBlockerMessages =
    activeStep === CLOSE_WIZARD_STEP_VALIDATE && currentOpenCashSession === null
      ? ["No hay una sesion abierta para cerrar."]
      : activeStep === CLOSE_WIZARD_STEP_FINALIZE || activeStep === CLOSE_WIZARD_STEP_DIFFERENCES
      ? blockerFindings.map((finding) => finding.title)
      : primaryActionDisabledReason !== null
        ? [primaryActionDisabledReason]
        : [];
  const panelWarningMessages =
    activeStep === CLOSE_WIZARD_STEP_CASH || activeStep === CLOSE_WIZARD_STEP_PAYMENTS
      ? warningItems
          .filter((warning) => warning.targetSection === CLOSE_SECTION_FINANCIAL)
          .map((warning) => warning.title)
      : activeStep === CLOSE_WIZARD_STEP_VALIDATE ||
          activeStep === CLOSE_WIZARD_STEP_SUMMARY ||
          activeStep === CLOSE_WIZARD_STEP_DIFFERENCES ||
          activeStep === CLOSE_WIZARD_STEP_SIGN_OFF ||
          activeStep === CLOSE_WIZARD_STEP_FINALIZE
        ? warningItems.map((warning) => warning.title)
        : [];
  const closeStageSections = CLOSE_WIZARD_STEPS.map((section) => {
    let status: "blocked" | "completed" | "current" | "upcoming" = "upcoming";
    const isBlocked =
      (section.key === CLOSE_WIZARD_STEP_SUMMARY ||
        section.key === CLOSE_WIZARD_STEP_CASH) &&
      currentOpenCashSession === null
        ? true
        : section.key === CLOSE_WIZARD_STEP_PAYMENTS
          ? countedCashState !== "CAPTURED"
          : section.key === CLOSE_WIZARD_STEP_PHYSICAL
            ? !hasExpectedFinancialCounts
            : section.key === CLOSE_WIZARD_STEP_DIFFERENCES
              ? !hasPhysicalCounts
              : section.key === CLOSE_WIZARD_STEP_SIGN_OFF
                ? validationResult === null || isLivePreviewPending
                : section.key === CLOSE_WIZARD_STEP_FINALIZE
                  ? validationResult === null || isLivePreviewPending || blockerFindings.length > 0
                  : false;

    if (section.key === activeStep) {
      status = "current";
    } else if (isBlocked) {
      status = "blocked";
    } else {
      const currentIndex = CLOSE_WIZARD_STEPS.findIndex((wizardStep) => wizardStep.key === activeStep);
      const sectionIndex = CLOSE_WIZARD_STEPS.findIndex(
        (wizardStep) => wizardStep.key === section.key,
      );
      status = sectionIndex < currentIndex ? "completed" : "upcoming";
    }

    return {
      ...section,
      isClickable: status !== "blocked" && !closeMutation.isPending,
      status,
    };
  });
  const sessionIdentityLabel =
    currentOpenCashSession === null || !bootstrapQuery.data
      ? "Turno actual"
      : `${bootstrapQuery.data.branch.name} / ${bootstrapQuery.data.workstation.name} / ${bootstrapQuery.data.user.full_name}`;
  const cashCloseReportAvailability = getDocumentActionAvailability("cashCloseReport");

  const summaryPanel = completedCloseDetail ? (
    <PosSummaryPanel
      description="El cierre ya fue confirmado con el detalle persistido por backend."
      footer={
        <div className="grid gap-2">
          <PosButton onClick={() => void handleProceedToNextSession()} variant="primary">
            Abrir nuevo turno
          </PosButton>
          <PosButton onClick={() => void handleExitAfterClose()} variant="neutral">
            Salir al acceso
          </PosButton>
          <div className="flex flex-wrap items-center gap-2">
            <CopyFolioAction
              label={cashCloseReportAvailability.copyFolio.label}
              referenceValue={completedCloseDetail.id}
              variant="neutral"
            />
            <DocumentActionsMenu
              actions={[
                {
                  disabled: !cashCloseReportAvailability.print.isAvailable,
                  disabledReason: cashCloseReportAvailability.print.unavailableReason,
                  key: "cash-close-print",
                  label: cashCloseReportAvailability.print.label,
                  onSelect: () => undefined,
                },
                {
                  disabled: !cashCloseReportAvailability.exportPdf.isAvailable,
                  disabledReason: cashCloseReportAvailability.exportPdf.unavailableReason,
                  key: "cash-close-export-pdf",
                  label: cashCloseReportAvailability.exportPdf.label,
                  onSelect: () => undefined,
                },
              ]}
            />
          </div>
        </div>
      }
      stateLabel="Cerrado"
      stateTone="confirmed"
      title="Resultado del cierre"
    >
      <ScrollPane className="grid gap-3 pr-1">
        <div className="grid gap-2 md:grid-cols-2">
          <SummaryMetric label="Referencia" value={completedCloseDetail.id} />
          <SummaryMetric
            label="Cerrado"
            tone="financial"
            value={formatLocalDateTime(String(completedCloseDetail.closed_at))}
          />
          <MetricCard helper="Efectivo esperado" tone="financial" value={formatCurrency(Number(completedCloseDetail.expected_cash_amount))} />
          <MetricCard helper="Efectivo contado" tone="financial" value={formatCurrency(Number(completedCloseDetail.counted_cash_amount))} />
          <MetricCard helper="Diferencia" tone={Number(completedCloseDetail.cash_variance_amount) === 0 ? undefined : "financial"} value={formatCurrency(Number(completedCloseDetail.cash_variance_amount))} />
          <MetricCard helper="Documentos generados" value={completedCloseDetail.generated_discrepancy_documents.length} />
        </div>
        {completedCloseDetail.warnings.length > 0 ? (
          <div className="grid gap-2">
            {completedCloseDetail.warnings.map((warning) => (
              <PosInlineValidationMessage key={warning.code} tone="warning">
                {warning.message}
              </PosInlineValidationMessage>
            ))}
          </div>
        ) : null}
      </ScrollPane>
    </PosSummaryPanel>
  ) : (
    <PosSummaryPanel
      description={
        <div className="grid gap-1">
          <span>{sessionStateLabel}</span>
          <span className="text-xs leading-5 text-slate-500">{primaryActionHelperText}</span>
        </div>
      }
      footer={
        <div className="grid gap-2">
          {submitErrorMessage ? (
            <PosInlineValidationMessage tone="error">{submitErrorMessage}</PosInlineValidationMessage>
          ) : null}
          <PosButton
            disabled={primaryActionDisabled}
            onClick={primaryActionHandler}
            variant={activeStep === CLOSE_WIZARD_STEP_FINALIZE ? "primary" : "secondary"}
          >
            {closeMutation.isPending ? "Procesando..." : primaryActionLabel}
          </PosButton>
          {primaryActionDisabledReason ? (
            <p className="text-sm leading-5 text-slate-600">{primaryActionDisabledReason}</p>
          ) : null}
        </div>
      }
      stateLabel={readinessLabel}
      stateTone={readinessTone === "danger" ? "blocked" : readinessTone === "warning" ? "warning" : readinessTone === "success" ? "confirmed" : "pending"}
      title={currentSectionLabel}
    >
      <ScrollPane className="grid gap-3 pr-1">
        <div className="grid gap-2 md:grid-cols-2">
          <SummaryMetric helper="Efectivo" label="Contado" tone="financial" value={countedCashText} />
          <SummaryMetric helper="Tarjeta" label="Contado" value={countedCardText} />
          <MetricCard helper="Lineas" value={countedLineCount} />
          <MetricCard helper="Unidades" value={countedUnitsText} />
          <MetricCard helper="Diferencias" value={blockerFindings.length + warningItems.length + infoFindings.length} />
          <MetricCard helper="Advertencias" value={warningItems.length} />
        </div>

        <PosBlockerPanel
          blockers={panelBlockerMessages.map((message, index) => ({
            key: `blocker-${index}`,
            message,
            tone: "warning",
          }))}
          title="Bloqueos del cierre"
        />

        {panelWarningMessages.length > 0 ? (
          <div className="grid gap-2">
            {panelWarningMessages.map((message) => (
              <PosInlineValidationMessage key={message} tone="warning">
                {message}
              </PosInlineValidationMessage>
            ))}
          </div>
        ) : null}

        {requiresCloseAcknowledgement && activeStep === CLOSE_WIZARD_STEP_SIGN_OFF ? (
          <PosInlineValidationMessage tone="info">
            El cierre dejara auditoria y outbox canonicos. La alerta dedicada a backoffice para diferencias altas sigue pendiente de contrato.
          </PosInlineValidationMessage>
        ) : null}
      </ScrollPane>
    </PosSummaryPanel>
  );

  useAppShellRightPanel(summaryPanel);

  if (accessToken === null) {
    return <Navigate to="/login" />;
  }

  if (bootstrapQuery.isPending) {
    return (
      <PosLoadingState
        description="Estamos preparando el contexto del cierre actual."
        title="Cargando cierre"
      />
    );
  }

  if (bootstrapQuery.isError || !bootstrapQuery.data) {
    return (
      <PosErrorState
        action={
          <PosButton
            onClick={() => void bootstrapQuery.refetch()}
            type="button"
          >
            Reintentar
          </PosButton>
        }
        description={toOperationalErrorMessage(
          bootstrapQuery.error,
          "No fue posible cargar el contexto del cierre.",
        )}
        title="No pudimos abrir el cierre"
      />
    );
  }

  return (
    <>
      <CentralWorkspaceSheet
        className="lg:h-full"
        contentClassName="min-h-0 overflow-y-auto px-3 pb-3 pt-2"
        header={
          <CompactPageHeader
            secondaryChips={
              currentOpenCashSession ? (
                <ModuleStateChip tone="primary">Caja abierta</ModuleStateChip>
              ) : (
                <ModuleStateChip tone="warning">Sin caja abierta</ModuleStateChip>
              )
            }
            stateChip={<ModuleStateChip tone={readinessTone}>{readinessLabel}</ModuleStateChip>}
            title="Wizard de cierre"
          >
            <FlowGuide
              activeStepKey={activeStep}
              ariaLabel="Etapas del cierre"
              onStepSelect={(stepKey) => handleStepSelect(stepKey as CashCloseWizardStep)}
              steps={closeStageSections.map((section) => ({
                key: section.key,
                label: section.label,
                state: section.status,
              }))}
              variant="process"
            />
          </CompactPageHeader>
        }
      >
        <PosModuleLayout className="lg:h-full" mobileSummary={summaryPanel}>
        {activeStep === CLOSE_WIZARD_STEP_VALIDATE ? (
          <div className="grid gap-3 lg:h-full lg:grid-cols-[minmax(0,1.1fr)_minmax(18rem,0.9fr)]">
            <div className="grid gap-3">
              <PosContextBanner
                description="El cierre solo puede comenzar sobre una caja abierta y con el contexto correcto de sucursal, estacion y operador."
                title="Paso 1 · Validar sesion y bloqueos"
              />

              {currentOpenCashSession === null ? (
                <PosErrorState
                  action={
                    <PosButton onClick={() => void navigate({ to: "/cash-session/open" })}>
                      Ir a apertura
                    </PosButton>
                  }
                  description="No hay una caja abierta para este punto de venta. Primero abre la sesion y vuelve al cierre."
                  title="No hay turno abierto"
                />
              ) : (
                <PosPanel className="grid gap-3 px-4 py-4">
                  <PosSectionTitle
                    description="Verifica que el turno activo corresponda exactamente a la caja que vas a cerrar."
                    title="Turno activo"
                  />
                  <div className="grid gap-2 md:grid-cols-2">
                    <KeyValueGroup tone="muted">
                      <KeyValueRow label="Sucursal" value={bootstrapQuery.data.branch.name} />
                      <KeyValueRow label="Caja" value={bootstrapQuery.data.workstation.name} />
                    </KeyValueGroup>
                    <KeyValueGroup tone="muted">
                      <KeyValueRow label="Cajero" value={bootstrapQuery.data.user.full_name} />
                      <KeyValueRow label="Abierto desde" value={sessionOpenedAtText} />
                    </KeyValueGroup>
                  </div>
                </PosPanel>
              )}
            </div>

            <PosPanel className="grid gap-3 px-4 py-4">
              <PosSectionTitle
                description="Estos hallazgos vienen del bootstrap del cierre antes de capturar conteos."
                title="Bloqueos y alertas"
              />
              <PosBlockerPanel
                blockers={
                  currentOpenCashSession === null
                    ? [{ key: "no-session", message: "No hay una sesion abierta para cerrar.", tone: "error" }]
                    : []
                }
                title="Bloqueo inicial"
              />
              {warningItems.length === 0 ? (
                <PosEmptyState
                  description="No hay alertas relevantes antes de comenzar con el cierre."
                  title="Sin alertas del turno"
                />
              ) : (
                <div className="grid gap-2">
                  {warningItems.map((warning) => (
                    <PosInlineValidationMessage key={warning.key} tone="warning">
                      <span className="font-semibold">{warning.title}.</span> {warning.description}
                    </PosInlineValidationMessage>
                  ))}
                </div>
              )}
            </PosPanel>
          </div>
        ) : null}

        {activeStep === CLOSE_WIZARD_STEP_SUMMARY ? (
          <div className="grid gap-3 lg:h-full lg:grid-cols-[minmax(0,1.1fr)_minmax(18rem,0.9fr)]">
            <div className="grid gap-3">
              <PosContextBanner
                description="Revisa el estado del turno antes de capturar conteos. Este resumen viene del backend y define el punto de partida del cierre."
                title="Paso 2 - Resumen del turno"
              />

              {summaryQuery.isPending ? (
                <PosLoadingState
                  description="Estamos reuniendo el resumen operativo del turno abierto."
                  title="Cargando resumen"
                />
              ) : summaryQuery.isError || !summaryQuery.data ? (
                <PosErrorState
                  action={
                    <PosButton onClick={() => void summaryQuery.refetch()} type="button">
                      Reintentar
                    </PosButton>
                  }
                  description={toOperationalErrorMessage(
                    summaryQuery.error,
                    "No fue posible cargar el resumen del cierre.",
                  )}
                  title="No pudimos preparar el resumen"
                />
              ) : (
                <>
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <MetricCard helper="Apertura" tone="financial" value={openingAmountText} />
                    <MetricCard
                      helper="Entradas de efectivo"
                      tone="financial"
                      value={formatCurrency(Number(summaryQuery.data.total_cash_in))}
                    />
                    <MetricCard
                      helper="Salidas de efectivo"
                      tone="financial"
                      value={formatCurrency(Number(summaryQuery.data.total_cash_out))}
                    />
                    <MetricCard helper="Efectivo esperado" tone="financial" value={expectedCashText} />
                  </div>

                  <PosPanel className="grid gap-3 px-4 py-4">
                    <PosSectionTitle
                      description="El backend resume los movimientos que afectan el cierre. Todavia no existe un reporte imprimible dedicado."
                      title="Desglose financiero"
                    />
                    {summaryQuery.data.movement_breakdown.length === 0 ? (
                      <PosEmptyState
                        description="No hay movimientos adicionales registrados en este turno."
                        title="Sin movimientos relevantes"
                      />
                    ) : (
                      <div className="grid gap-2">
                        {summaryQuery.data.movement_breakdown.map((row) => (
                          <div
                            className="flex items-center justify-between gap-3 rounded-2xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3"
                            key={`${row.direction}-${row.movement_type}`}
                          >
                            <div className="min-w-0">
                              <p className="text-sm font-semibold text-slate-950">{row.movement_type}</p>
                              <p className="mt-1 text-sm text-slate-600">
                                {row.direction} · {row.movement_count} movimiento(s)
                              </p>
                            </div>
                            <p className="text-sm font-semibold text-slate-950">
                              {formatCurrency(Number(row.total_amount))}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </PosPanel>
                </>
              )}
            </div>

            <PosPanel className="grid gap-3 px-4 py-4">
              <PosSectionTitle
                description="Este panel resume la base de conciliacion disponible antes de capturar efectivo y mostrador."
                title="Contexto de conciliacion"
              />
              {summaryQuery.data ? (
                <>
                  <KeyValueGroup tone="muted">
                    <KeyValueRow label="Estado del turno" value={summaryQuery.data.reconciliation_status} />
                    <KeyValueRow
                      label="Sesion abierta"
                      value={formatLocalDateTime(String(summaryQuery.data.cash_session.opened_at))}
                    />
                    <KeyValueRow
                      label="Snapshot base"
                      value={
                        summaryQuery.data.baseline_snapshot.is_available
                          ? summaryQuery.data.baseline_snapshot.snapshot_type ?? "Disponible"
                          : "Sin snapshot base"
                      }
                    />
                  </KeyValueGroup>

                  <div className="grid gap-3 md:grid-cols-2">
                    <MetricCard
                      helper="Clases pendientes"
                      value={summaryQuery.data.pending_class_capture.pending_class_capture_classes_count}
                    />
                    <MetricCard
                      helper="Unidades por clase"
                      value={summaryQuery.data.pending_class_capture.pending_class_capture_total_quantity}
                    />
                  </div>

                  {summaryQuery.data.warnings.length > 0 ? (
                    <div className="grid gap-2">
                      {summaryQuery.data.warnings.map((warning) => (
                        <PosInlineValidationMessage key={warning.code} tone="warning">
                          {warning.message}
                        </PosInlineValidationMessage>
                      ))}
                    </div>
                  ) : (
                    <PosEmptyState
                      description="No hay alertas adicionales en el resumen actual del turno."
                      title="Resumen listo"
                    />
                  )}
                </>
              ) : (
                <PosEmptyState
                  description="El resumen aparecera aqui cuando el backend responda con el detalle del turno."
                  title="Esperando contexto"
                />
              )}
            </PosPanel>
          </div>
        ) : null}

        {activeStep === CLOSE_WIZARD_STEP_CASH ? (
          <div className="grid gap-3 lg:h-full lg:grid-rows-[auto_minmax(0,1fr)]">
            <PosContextBanner
              description="El backend actual valida el total contado de efectivo por metodo. El desglose por denominaciones sigue pendiente y no se simula en frontend."
              title="Paso 3 · Conteo de efectivo"
            />

            <ScrollPane className="grid gap-4">
              <PosInlineValidationMessage tone="warning">
                El detalle por billete o moneda sigue diferido por contrato. Captura aqui el total contado real de efectivo.
              </PosInlineValidationMessage>

              {paymentMethodDraftRows
                .filter((row) => row.key === "CASH")
                .map((row) => {
                  const previewPaymentRow = validationResult?.payment_method_rows.find(
                    (previewRow) => previewRow.payment_method_code === row.key,
                  );
                  const countState = getCashCloseCountValueState(row.countedAmountText);
                  const expectedAmount =
                    previewPaymentRow?.expected_amount !== null &&
                    previewPaymentRow?.expected_amount !== undefined
                      ? formatCurrency(Number(previewPaymentRow.expected_amount))
                      : summaryQuery.data
                        ? formatCurrency(summaryQuery.data.expected_cash_amount)
                        : "Se revisa al cerrar";
                  const differenceAmount =
                    countState === "CAPTURED" &&
                    previewPaymentRow?.variance_amount !== null &&
                    previewPaymentRow?.variance_amount !== undefined
                      ? formatCurrency(Number(previewPaymentRow.variance_amount))
                      : countState === "CAPTURED" && summaryQuery.data
                        ? formatCurrency(
                            row.countedAmountCents / 100 - Number(summaryQuery.data.expected_cash_amount),
                          )
                        : null;

                  return (
                    <PaymentCountRow
                      countState={countState}
                      differenceAmount={differenceAmount}
                      expectedAmount={expectedAmount}
                      helperText="Enter o NumpadEnter avanza al paso de tarjeta y otros medios."
                      inputRef={(element) => {
                        paymentInputRefs.current[row.key] = element;
                      }}
                      isCashMethod
                      isDifferenceVisible={countState === "CAPTURED"}
                      key={row.key}
                      label={PAYMENT_METHOD_LABELS[row.key] ?? row.key}
                      onChange={(value) =>
                        updateDraftState((state) => ({
                          ...state,
                          countedPaymentAmounts: {
                            ...state.countedPaymentAmounts,
                            [row.key]: sanitizeMoneyInput(value),
                          },
                        }))
                      }
                      onInputKeyDown={handlePaymentFieldKeyDown(row.key)}
                      paymentMethodCode={row.key}
                      value={row.countedAmountText}
                    />
                  );
                })}
            </ScrollPane>
          </div>
        ) : null}

        {activeStep === CLOSE_WIZARD_STEP_PAYMENTS ? (
          <div className="grid gap-3 lg:h-full lg:grid-rows-[auto_minmax(0,1fr)]">
            <PosContextBanner
              description="Concuerda tarjeta y cualquier medio adicional realmente usado en el turno. Los pendientes no significan cero."
              title="Paso 4 · Tarjeta y otros medios"
            />

            <ScrollPane className="grid gap-4">
              <div className="grid gap-3">
                {paymentMethodDraftRows
                  .filter((row) => row.key !== "CASH")
                  .map((row) => {
                    const previewPaymentRow = validationResult?.payment_method_rows.find(
                      (previewRow) => previewRow.payment_method_code === row.key,
                    );
                    const countState = getCashCloseCountValueState(row.countedAmountText);
                    return (
                      <PaymentCountRow
                        countState={countState}
                        differenceAmount={
                          countState === "CAPTURED" &&
                          previewPaymentRow?.variance_amount !== null &&
                          previewPaymentRow?.variance_amount !== undefined
                            ? formatCurrency(Number(previewPaymentRow.variance_amount))
                            : null
                        }
                        expectedAmount={
                          previewPaymentRow?.expected_amount !== null &&
                          previewPaymentRow?.expected_amount !== undefined
                            ? formatCurrency(Number(previewPaymentRow.expected_amount))
                            : row.isExpectedSupported
                              ? "Se revisa al cerrar"
                              : "Referencia"
                        }
                        helperText={
                          row.isExpectedSupported
                            ? "Capturalo solo si participo en el cierre. Enter avanza al siguiente campo."
                            : "Se registra solo como referencia del cierre."
                        }
                        inputRef={(element) => {
                          paymentInputRefs.current[row.key] = element;
                        }}
                        isCashMethod={false}
                        isDifferenceVisible={countState === "CAPTURED"}
                        key={row.key}
                        label={PAYMENT_METHOD_LABELS[row.key] ?? row.key}
                        onChange={(value) =>
                          updateDraftState((state) => ({
                            ...state,
                            countedPaymentAmounts: {
                              ...state.countedPaymentAmounts,
                              [row.key]: sanitizeMoneyInput(value),
                            },
                          }))
                        }
                        onInputKeyDown={handlePaymentFieldKeyDown(row.key)}
                        paymentMethodCode={row.key}
                        value={row.countedAmountText}
                      />
                    );
                  })}

                {paymentMethodDraftRows.filter((row) => row.key !== "CASH").length === 0 ? (
                  <PosEmptyState
                    description="No hay otros medios configurados para este cierre. Puedes continuar al conteo fisico."
                    title="Sin metodos adicionales"
                  />
                ) : null}
              </div>
            </ScrollPane>
          </div>
        ) : null}

        {activeStep === CLOSE_WIZARD_STEP_PHYSICAL ? (
          <div className="grid gap-3 lg:h-full lg:grid-rows-[auto_auto_minmax(0,1fr)]">
            <PosContextBanner
              description="Cuenta el mostrador con la misma logica operativa del POS. El backend usara este conteo para conciliar ventas por clase y generar diferencias."
              title="Paso 5 · Mostrador y conciliacion por clase"
            />

            <div className="grid gap-3 md:grid-cols-3">
              <MetricCard helper="Clases pendientes" value={reconciliationQuery.data?.pending_class_capture.pending_class_capture_classes_count ?? 0} />
              <MetricCard helper="Unidades pendientes" value={reconciliationQuery.data?.pending_class_capture.pending_class_capture_total_quantity ?? "0"} />
              <MetricCard helper="Productos relevantes" value={reconciliationQuery.data?.relevant_products.length ?? 0} />
            </div>

            <div className="grid gap-3 lg:h-full lg:grid-cols-[minmax(0,1.25fr)_minmax(18rem,0.75fr)]">
            <div className="pos-tonal-surface grid h-full min-h-0 overflow-hidden px-3.5 py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <FlowGuide
                  activeStepKey={flowActiveStepKey}
                  steps={[
                    { key: "class", label: "Clase" },
                    { key: "product", label: "Producto" },
                    { key: "quantity", label: "Cantidad" },
                  ]}
                  variant="stepper"
                />

                {draftState.physicalControlState !== CLOSE_PHYSICAL_STATE_CLASS_SELECTION ? (
                  <Button
                    className={cn("h-10 px-3", posOutlineButtonClass)}
                    onClick={() =>
                      updateDraftState((state) => goBackFromCashClosePhysicalState(state))
                    }
                    type="button"
                    variant="outline"
                  >
                    <ArrowLeftIcon className="h-4 w-4" />
                    Regresar
                  </Button>
                ) : null}
              </div>

              {draftState.physicalControlState !== CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE ? (
                <div className="mt-[var(--pos-stack-gap)] border-t border-[var(--pos-shell-border)] pt-[var(--pos-stack-gap)]">
                  <SearchField
                    ariaLabel="Buscar en catalogo de cierre"
                    className="max-w-xl"
                    inputClassName={cn("h-11 rounded-2xl text-sm", posInputClass)}
                    onChange={(value) =>
                      updateDraftState((state) => setCashClosePhysicalSearchText(state, value))
                    }
                    placeholder={
                      draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION
                        ? "Buscar clase"
                        : "Buscar producto"
                    }
                    value={draftState.physicalSearchText}
                  />
                </div>
              ) : null}

              <ScrollPane className="mt-[var(--pos-stack-gap)]">
                {draftState.physicalControlState === CLOSE_PHYSICAL_STATE_CLASS_SELECTION ? (
                  catalogQuery.isPending ? (
                    <div className="rounded-2xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-sm text-slate-600">
                      Cargando clases activas para el conteo del mostrador...
                    </div>
                  ) : sortedClasses.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-sm text-slate-600">
                      No encontramos clases activas para este cierre.
                    </div>
                  ) : (
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                      {sortedClasses.map((productClass, index) => (
                        <CatalogSelectionCard
                          code={productClass.code}
                          isPrimaryControl={index === 0}
                          key={productClass.id}
                          name={productClass.name}
                          onSelect={() =>
                            updateDraftState((state) =>
                              selectClassForCashCloseCount(state, productClass),
                            )
                          }
                          shortcutLabel={getSelectionShortcutLabel(index)}
                          variant="pos"
                        />
                      ))}
                    </div>
                  )
                ) : null}

                {draftState.physicalControlState === CLOSE_PHYSICAL_STATE_PRODUCT_SELECTION ? (
                  classProductsQuery.isPending ? (
                    <div className="rounded-2xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-sm text-slate-600">
                      Cargando productos de {draftState.physicalPendingSelection?.productClass.name ?? "la clase"}...
                    </div>
                  ) : sortedProducts.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-sm text-slate-600">
                      No hay productos para la clase seleccionada.
                    </div>
                  ) : (
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                      {sortedProducts.map((product, index) => (
                        <CatalogSelectionCard
                          code={product.code}
                          isPrimaryControl={index === 0}
                          key={product.id}
                          name={product.name}
                          onSelect={() =>
                            updateDraftState((state) =>
                              selectProductForCashCloseCount(state, product),
                            )
                          }
                          shortcutLabel={getSelectionShortcutLabel(index)}
                          variant="pos"
                        />
                      ))}
                    </div>
                  )
                ) : null}

                {draftState.physicalControlState === CLOSE_PHYSICAL_STATE_QUANTITY_CAPTURE &&
                quantitySelection &&
                quantityProduct ? (
                  <div className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                    <div className="rounded-[24px] border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] p-3">
                      <CatalogVisual
                        className="min-h-[10rem]"
                        code={quantityProduct.code}
                        name={quantityProduct.name}
                      />
                    </div>

                    <div className="grid gap-3 rounded-[24px] border border-[var(--pos-shell-border)] bg-white p-4 shadow-[var(--ui-shadow-subtle)]">
                      <div>
                        <p className="text-sm font-semibold text-slate-950">
                          {quantitySelection.productClass.name}
                        </p>
                        <h3 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                          {quantityProduct.name}
                        </h3>
                        <p className="mt-1 text-sm text-slate-600">
                          Captura la cantidad fisica contada y agregala al borrador del cierre.
                        </p>
                      </div>

                      <label className="grid gap-2">
                        <span className="text-sm font-semibold text-slate-800">Cantidad</span>
                        <div className="relative">
                          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-slate-400">
                            <HashIcon className="h-4 w-4" />
                          </span>
                          <input
                            aria-label={`Cantidad contada de ${quantityProduct.name}`}
                            className={cn(
                              "h-12 w-full rounded-2xl pl-10 pr-4 text-lg font-semibold [font-variant-numeric:tabular-nums]",
                              posInputClass,
                            )}
                            inputMode="decimal"
                            onChange={(event) =>
                              updateDraftState((state) =>
                                setCashClosePendingQuantityText(state, event.target.value),
                              )
                            }
                            onKeyDown={(event) => {
                              if (
                                (event.key === "Enter" || event.key === "NumpadEnter") &&
                                (quantitySelection.quantityText.trim().length > 0)
                              ) {
                                event.preventDefault();
                                updateDraftState((state) => addCashClosePendingCountLine(state));
                              }
                            }}
                            placeholder="0"
                            ref={quantityInputRef}
                            value={quantitySelection.quantityText}
                          />
                        </div>
                      </label>

                      <div className="flex flex-wrap gap-2">
                        {[1, 2, 6, 12].map((preset) => (
                          <Button
                            className={cn("h-9 px-3", posOutlineButtonClass)}
                            key={preset}
                            onClick={() =>
                              updateDraftState((state) =>
                                setCashClosePendingQuantityText(state, String(preset)),
                              )
                            }
                            type="button"
                            variant="outline"
                          >
                            {preset}
                          </Button>
                        ))}
                      </div>

                      <div className="flex flex-wrap justify-end gap-2">
                        <Button
                          className={cn("h-10 px-4", posOutlineButtonClass)}
                          onClick={() =>
                            updateDraftState((state) => goBackFromCashClosePhysicalState(state))
                          }
                          type="button"
                          variant="outline"
                        >
                          Regresar
                        </Button>
                        <Button
                          className={cn("h-10 px-4", posPrimaryButtonClass)}
                          disabled={quantitySelection.quantityText.trim().length === 0}
                          onClick={() =>
                            updateDraftState((state) => addCashClosePendingCountLine(state))
                          }
                          type="button"
                        >
                          Agregar al conteo
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : null}
              </ScrollPane>

            </div>

            <div className="pos-tonal-surface grid h-full min-h-0 overflow-hidden px-3.5 py-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-slate-950">Lineas contadas</p>
              </div>

              <div className="mt-[var(--pos-stack-gap)] grid gap-3 border-t border-[var(--pos-shell-border)] pt-[var(--pos-stack-gap)] lg:h-full lg:grid-rows-[auto_minmax(0,1fr)]">
                <div className="grid gap-3 md:grid-cols-2">
                  <MetricCard helper="Lineas" value={countedLineCount} />
                  <MetricCard helper="Unidades" value={countedUnitsText} />
                </div>

                <div className="min-h-0 overflow-hidden rounded-2xl border border-[var(--pos-shell-border)] bg-white">
                <ScrollPane>
                {draftState.countedProductDraftLines.length === 0 ? (
                  <div className="px-4 py-8 text-center text-sm leading-6 text-slate-600">
                    Aun no agregas productos contados. Selecciona una clase para empezar.
                  </div>
                ) : (
                  draftState.countedProductDraftLines.map((line) => (
                    <CountedLineRow
                      key={line.key}
                      line={line}
                      onDecrement={() =>
                        updateDraftState((state) => {
                          const currentLine = state.countedProductDraftLines.find(
                            (draftLine) => draftLine.key === line.key,
                          );
                          if (!currentLine) {
                            return state;
                          }

                          const nextQuantity = currentLine.quantityMilliUnits - 1000;
                          return {
                            ...state,
                            countedProductDraftLines:
                              nextQuantity <= 0
                                ? removeCashCloseCountedLine(
                                    state.countedProductDraftLines,
                                    line.key,
                                  )
                                : state.countedProductDraftLines.map((draftLine) =>
                                    draftLine.key === line.key
                                      ? updateCashCloseCountedLineQuantity(
                                          draftLine,
                                          nextQuantity,
                                        )
                                      : draftLine,
                                  ),
                          };
                        })
                      }
                      onIncrement={() =>
                        updateDraftState((state) => ({
                          ...state,
                          countedProductDraftLines: state.countedProductDraftLines.map(
                            (draftLine) =>
                              draftLine.key === line.key
                                ? updateCashCloseCountedLineQuantity(
                                    draftLine,
                                    draftLine.quantityMilliUnits + 1000,
                                  )
                                : draftLine,
                          ),
                        }))
                      }
                      onRemove={() =>
                        updateDraftState((state) => ({
                          ...state,
                          countedProductDraftLines: removeCashCloseCountedLine(
                            state.countedProductDraftLines,
                            line.key,
                          ),
                        }))
                      }
                    />
                  ))
                )}
                </ScrollPane>
              </div>
              </div>
            </div>
          </div>
          </div>
        ) : null}

        {activeStep === CLOSE_WIZARD_STEP_DIFFERENCES ? (
          <div className="grid gap-3 lg:h-full lg:grid-rows-[auto_minmax(0,1fr)]">
            <PosContextBanner
              description="Esta etapa refleja exactamente la vista previa del backend: bloqueos, advertencias, conciliaciones por clase y documentos de diferencia preparados."
              title="Paso 6 · Revisión de diferencias"
            />

            <div className="grid gap-3 md:grid-cols-4">
              <MetricCard helper="Clases conciliadas" value={resolvedClassCount} />
              <MetricCard helper="Clases por revisar" value={unresolvedClassCount} />
              <MetricCard helper="Ajustes preparados" value={generatedAdjustmentCount} />
              <MetricCard helper="Diferencia de efectivo" tone="financial" value={cashVarianceText} />
            </div>

            <div className="grid min-h-0 gap-3 lg:grid-cols-[minmax(0,1fr)_20rem]">
              <ScrollPane className="grid gap-3">
                {livePreviewErrorMessage ? (
                  <PosInlineValidationMessage tone="error">{livePreviewErrorMessage}</PosInlineValidationMessage>
                ) : null}

                {validationResult === null ? (
                  <PosLoadingState
                    description="Estamos preparando la conciliacion del cierre con el conteo actual."
                    title="Actualizando diferencias"
                  />
                ) : (
                  <>
                    <CloseFindingsGroup
                      emptyMessage="No hay bloqueos criticos en la conciliacion actual."
                      findings={blockerFindings}
                      onResolve={(section) => setActiveStep(mapSectionToWizardStep(section))}
                      title="Bloqueos"
                    />

                    <CloseFindingsGroup
                      emptyMessage="No hay advertencias relevantes en la conciliacion actual."
                      findings={warningItems}
                      onResolve={(section) => setActiveStep(mapSectionToWizardStep(section))}
                      title="Advertencias"
                    />

                    {validationResult && Number(validationResult.cash_variance_amount ?? 0) !== 0 ? (
                      <PosInlineValidationMessage tone="warning">
                        El motivo manual para la diferencia de efectivo sigue pendiente de contrato backend. Revisa el desvio y continua con la validacion del cajero.
                      </PosInlineValidationMessage>
                    ) : null}

                    <PosPanel className="grid gap-3 px-4 py-4">
                      <PosSectionTitle
                        description="Los motivos de diferencia se calculan con la regla backend actual. El selector manual de motivos sigue pendiente de contrato."
                        title="Resoluciones preparadas"
                      />
                      {validationResult.discrepancy_resolutions.length === 0 ? (
                        <PosEmptyState
                          description="No se prepararon ajustes por diferencia para este cierre."
                          title="Sin resoluciones"
                        />
                      ) : (
                        <div className="grid gap-2">
                          {validationResult.discrepancy_resolutions.map((resolution) => (
                            <div
                              className="rounded-2xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3"
                              key={resolution.product_id}
                            >
                              <p className="text-sm font-semibold text-slate-950">{resolution.product_name}</p>
                              <p className="mt-1 text-sm text-slate-600">
                                Esperado {resolution.expected_quantity} · Contado {resolution.counted_quantity}
                              </p>
                              <p className="mt-1 text-sm text-slate-700">
                                Resolucion {resolution.resolution_type} · Motivo {resolution.reason_code ?? "automatico"}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </PosPanel>
                  </>
                )}
              </ScrollPane>

              <div className="grid gap-3">
                <PosPanel className="px-4 py-4">
                  <PosSectionTitle
                    description="Las conciliaciones por clase se resuelven con el conteo fisico capturado."
                    title="Estado de clases"
                  />
                  <div className="mt-3 grid gap-2">
                    {(validationResult?.class_reconciliations ?? reconciliationQuery.data?.class_reconciliations ?? []).length === 0 ? (
                      <p className="text-sm leading-6 text-slate-600">
                        No hay clases pendientes para conciliar en este cierre.
                      </p>
                    ) : (
                      (validationResult?.class_reconciliations ?? reconciliationQuery.data?.class_reconciliations ?? []).map((item) => (
                        <div className="rounded-2xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3" key={item.product_class_id}>
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-sm font-semibold text-slate-950">{item.product_class_name}</p>
                            <PosStatusBadge
                              status={
                                item.resolution_status === "AUTO_RESOLVED" ||
                                item.resolution_status === "MANUAL_RESOLVED"
                                  ? "confirmed"
                                  : "warning"
                              }
                            >
                              {item.resolution_status}
                            </PosStatusBadge>
                          </div>
                          <p className="mt-1 text-sm text-slate-600">
                            Pendiente {item.pending_quantity} · Final {item.final_attributed_quantity}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </PosPanel>
              </div>
            </div>
          </div>
        ) : null}

        {activeStep === CLOSE_WIZARD_STEP_SIGN_OFF ? (
          <div className="grid gap-3 lg:h-full lg:grid-cols-[minmax(0,1.1fr)_minmax(18rem,0.9fr)]">
            <div className="grid gap-3">
              <PosContextBanner
                description="El cajero autenticado es suficiente para cerrar. Si hay diferencias o resultados de alto impacto, deja aqui la validacion operativa antes del commit."
                title="Paso 7 · Validación del cajero"
              />

              <PosPanel className="grid gap-3 px-4 py-4">
                <PosSectionTitle
                  description="La identidad del cajero queda en el cierre persistido por backend."
                  title="Firmado por el operador actual"
                />
                <div className="grid gap-2 md:grid-cols-2">
                  <KeyValueGroup tone="muted">
                    <KeyValueRow label="Cajero" value={bootstrapQuery.data.user.full_name} />
                    <KeyValueRow label="Caja" value={bootstrapQuery.data.workstation.name} />
                  </KeyValueGroup>
                  <KeyValueGroup tone="muted">
                    <KeyValueRow label="Sucursal" value={bootstrapQuery.data.branch.name} />
                    <KeyValueRow label="Referencia del turno" value={sessionIdentityLabel} />
                  </KeyValueGroup>
                </div>
              </PosPanel>

              {requiresCloseAcknowledgement ? (
                <PosPanel className="grid gap-3 px-4 py-4" tone={hasLargeVarianceWarning ? "warning" : "muted"}>
                  <PosSectionTitle
                    description="Este reconocimiento no se persiste todavia como artefacto de backend. Sirve para no confirmar a ciegas un cierre con diferencias."
                    title="Reconocimiento requerido"
                  />
                  <label className="flex items-start gap-3 rounded-2xl border border-[var(--pos-shell-border)] bg-white px-3 py-3 text-sm leading-6 text-slate-700">
                    <input
                      checked={isCloseAcknowledged}
                      className="mt-1 h-4 w-4 rounded border-[var(--pos-shell-border)]"
                      onChange={(event) => setIsCloseAcknowledged(event.target.checked)}
                      type="checkbox"
                    />
                    <span>
                      Revise la diferencia neta, las advertencias y los ajustes preparados. Acepto cerrar con este resultado.
                    </span>
                  </label>
                </PosPanel>
              ) : (
                <PosEmptyState
                  description="No hay diferencias adicionales que requieran una validación manual del cajero."
                  title="Sin validación adicional"
                />
              )}
            </div>

            <PosPanel className="grid gap-3 px-4 py-4">
              <PosSectionTitle
                description="El cierre dejara auditoria y outbox canonicos. La alerta dedicada a backoffice para diferencias altas sigue pendiente del contrato backend."
                title="Backoffice y seguimiento"
              />
              <div className="grid gap-2">
                <PosInlineValidationMessage tone="info">
                  Diferencia de efectivo actual: {cashVarianceText}
                </PosInlineValidationMessage>
                <PosInlineValidationMessage tone={hasLargeVarianceWarning ? "warning" : "info"}>
                  {hasLargeVarianceWarning
                    ? "Existe una diferencia alta de efectivo. La alerta dedicada a backoffice sigue diferida, pero el cierre quedara auditado."
                    : "No hay una alerta dedicada a backoffice. El seguimiento depende de auditoria y outbox del cierre."}
                </PosInlineValidationMessage>
                {generatedAdjustmentCount > 0 ? (
                  <PosInlineValidationMessage tone="warning">
                    Se prepararon {generatedAdjustmentCount} documento(s) de diferencia para este cierre.
                  </PosInlineValidationMessage>
                ) : null}
              </div>
            </PosPanel>
          </div>
        ) : null}

        {activeStep === CLOSE_WIZARD_STEP_FINALIZE ? (
          completedCloseDetail ? (
            <div className="grid gap-3 lg:h-full lg:grid-rows-[auto_minmax(0,1fr)]">
              <PosContextBanner
                description="Este es el detalle persistido del cierre confirmado. No existe todavia un reporte imprimible ni exportable desde backend."
                title="Paso 8 · Resultado del cierre"
              />

              <div className="grid min-h-0 gap-3 lg:grid-cols-[minmax(0,1fr)_20rem]">
                <PosPanel className="grid gap-3 px-4 py-4">
                  <PosSectionTitle
                    description="El cierre ya fue guardado. Usa este resumen como reporte operativo inmediato."
                    title="Reporte disponible en pantalla"
                  />
                  <div className="grid gap-2 md:grid-cols-2">
                    <MetricCard helper="Referencia" value={completedCloseDetail.id} />
                    <MetricCard helper="Cerrado" value={formatLocalDateTime(String(completedCloseDetail.closed_at))} />
                    <MetricCard helper="Efectivo esperado" tone="financial" value={formatCurrency(Number(completedCloseDetail.expected_cash_amount))} />
                    <MetricCard helper="Efectivo contado" tone="financial" value={formatCurrency(Number(completedCloseDetail.counted_cash_amount))} />
                    <MetricCard helper="Diferencia" tone="financial" value={formatCurrency(Number(completedCloseDetail.cash_variance_amount))} />
                    <MetricCard helper="Documentos generados" value={completedCloseDetail.generated_discrepancy_documents.length} />
                  </div>
                </PosPanel>

                <PosPanel className="grid gap-3 px-4 py-4">
                  <PosSectionTitle
                    description="Acciones posteriores disponibles con el contrato actual."
                    title="Siguiente paso"
                  />
                  <div className="grid gap-2">
                    <PosButton onClick={() => void handleProceedToNextSession()} variant="primary">
                      Abrir nuevo turno
                    </PosButton>
                    <PosButton onClick={() => void handleExitAfterClose()} variant="neutral">
                      Salir al acceso
                    </PosButton>
                    <div className="flex flex-wrap items-center gap-2">
                      <CopyFolioAction
                        label={cashCloseReportAvailability.copyFolio.label}
                        referenceValue={completedCloseDetail.id}
                        variant="neutral"
                      />
                      <DocumentActionsMenu
                        actions={[
                          {
                            disabled: !cashCloseReportAvailability.print.isAvailable,
                            disabledReason: cashCloseReportAvailability.print.unavailableReason,
                            key: "cash-close-screen-print",
                            label: cashCloseReportAvailability.print.label,
                            onSelect: () => undefined,
                          },
                          {
                            disabled: !cashCloseReportAvailability.exportPdf.isAvailable,
                            disabledReason: cashCloseReportAvailability.exportPdf.unavailableReason,
                            key: "cash-close-screen-export-pdf",
                            label: cashCloseReportAvailability.exportPdf.label,
                            onSelect: () => undefined,
                          },
                        ]}
                      />
                    </div>
                  </div>
                </PosPanel>
              </div>
            </div>
          ) : (
            <div className="grid gap-3 lg:h-full lg:grid-rows-[auto_minmax(0,1fr)]">
              <PosContextBanner
                description="La vista previa se recalcula automaticamente con cada cambio y se valida una vez mas antes del commit final."
                title="Paso 8 · Cierre final y reporte"
              />

              <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_20rem]">
                <ScrollPane className="grid gap-3 rounded-[24px] border border-[var(--pos-shell-border)] bg-white p-4 shadow-[var(--ui-shadow-subtle)]">
                  {livePreviewErrorMessage ? (
                    <PosInlineValidationMessage tone="error">{livePreviewErrorMessage}</PosInlineValidationMessage>
                  ) : validationResult === null ? (
                    <PosLoadingState
                      description="Estamos preparando la revision final del cierre con el ultimo conteo registrado."
                      title="Calculando vista previa"
                    />
                  ) : (
                    <div className="grid gap-3">
                      <div className="rounded-2xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-4">
                        <p className="text-sm font-semibold text-slate-950">Resumen final</p>
                        <div className="mt-3 grid gap-2 text-sm text-slate-600">
                          <div className="flex items-center justify-between gap-3">
                            <span>Efectivo esperado</span>
                            <span className="font-semibold text-slate-950">{expectedCashText}</span>
                          </div>
                          <div className="flex items-center justify-between gap-3">
                            <span>Efectivo contado</span>
                            <span className="font-semibold text-slate-950">{countedCashText}</span>
                          </div>
                          <div className="flex items-center justify-between gap-3">
                            <span>Diferencia neta</span>
                            <span className="font-semibold text-slate-950">{cashVarianceText}</span>
                          </div>
                        </div>
                      </div>

                      <CloseFindingsGroup
                        emptyMessage="No hay bloqueos en la revision final."
                        findings={blockerFindings}
                        onResolve={(section) => setActiveStep(mapSectionToWizardStep(section))}
                        title="Bloqueos"
                      />

                      <CloseFindingsGroup
                        emptyMessage="No hay advertencias adicionales en la revision final."
                        findings={warningItems}
                        onResolve={(section) => setActiveStep(mapSectionToWizardStep(section))}
                        title="Advertencias"
                      />

                      <PosInlineValidationMessage tone="info">
                        El commit vuelve a ejecutar la vista previa antes de cerrar definitivamente el turno.
                      </PosInlineValidationMessage>
                    </div>
                  )}
                </ScrollPane>

                <PosPanel className="grid gap-3 px-4 py-4">
                  <PosSectionTitle
                    description="Sin folio ni reporte imprimible dedicados. El cierre se identifica por su ID persistido."
                    title="Resultado esperado"
                  />
                  <div className="grid gap-2">
                    <MetricCard helper="Efectivo contado" tone="financial" value={countedCashText} />
                    <MetricCard helper="Tarjeta contada" value={countedCardText} />
                    <MetricCard helper="Lineas contadas" value={countedLineCount} />
                    <MetricCard helper="Unidades" value={countedUnitsText} />
                  </div>
                </PosPanel>
              </div>
            </div>
          )
        ) : null}
        </PosModuleLayout>
      </CentralWorkspaceSheet>

      <CloseConfirmationDialog
        countedCashText={countedCashText}
        countedLineCount={countedLineCount}
        countedUnitsText={countedUnitsText}
        discrepancyText={cashVarianceText}
        expectedCashText={expectedCashText}
        isOpen={isConfirmDialogOpen}
        isPending={closeMutation.isPending}
        onCancel={() => setIsConfirmDialogOpen(false)}
        onConfirm={handleCommitAttempt}
        sessionLabel={sessionIdentityLabel}
        warningMessages={warningItems.map((warning) => warning.title)}
      />
    </>
  );
}

