import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import { OperationalStatus } from "../../components/operational-status";
import { PosAuditSummary } from "../../components/pos-audit-summary";
import {
  PosConfirmationDialog,
  PosEmptyState,
  PosErrorState,
  PosInlineValidationMessage,
  PosLoadingState,
  PosOperationResultPanel,
} from "../../components/pos-feedback";
import { PosButton, PosFieldLabel, PosStatusBadge } from "../../components/pos-foundations";
import { PosSummaryPanel } from "../../components/pos-module-layout";
import {
  PosFilterBar,
  PosRecordMeta,
  PosRecordTable,
  type PosRecordColumn,
} from "../../components/pos-records";
import {
  CardIcon,
  CheckCircleIcon,
  ClipboardIcon,
  MoneyIcon,
  PlusIcon,
} from "../../components/pos-icons";
import {
  CentralWorkspaceSheet,
  CompactPageHeader,
  FlowGuide,
  ModuleStateChip,
  ScrollPane,
} from "../../components/pos-module-primitives";
import { appEnv } from "../../env";
import type {
  OperationalPaymentCategoryView,
  OperationalPaymentDetailResponse,
  OperationalPaymentFilterOptionView,
  OperationalPaymentListItemView,
  OperationalPaymentMethodView,
  OperationalPaymentScopeView,
} from "../../lib/api-contracts";
import { copyDocumentReferenceToClipboard } from "../../lib/document-actions";
import {
  formatCompactLocalDateTime,
  formatCurrency,
  formatLocalDateTime,
} from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import { isEditableTarget } from "../../lib/keyboard-shortcuts";
import {
  createOperationResultMessage,
  createToastAction,
  posMessageCatalog,
} from "../../lib/pos-messages";
import { cn } from "../../lib/utils";
import { usePosAuthStore } from "../auth/auth-store";
import {
  currentCashSessionQueryKey,
  useCurrentCashSessionQuery,
} from "../cash-session-open/queries";
import {
  cashCloseBootstrapQueryKey,
  cashCloseReconciliationQueryKey,
  cashCloseSummaryQueryKey,
} from "../cash-close/queries";
import { useModuleHotkeys } from "../pos-shell/keyboard";
import { posInputClass } from "../pos-theme/theme";
import { useStatusMessageStore } from "../status-messages/store";
import { createPayment } from "./payments-api";
import {
  buildCreateOperationalPaymentRequest,
  canCommitOperationalPaymentDraft,
  createInitialOperationalPaymentDraftState,
  doesOperationalPaymentAffectCashDrawer,
  getOperationalPaymentAmountCents,
  getOperationalPaymentBlockedReason,
  getOperationalPaymentBlockingMessages,
  getOperationalPaymentCreateStepKey,
  getOperationalPaymentMethod,
  getOperationalPaymentMethodLabel,
  getOperationalPaymentUiState,
  sanitizeOperationalPaymentAmountInput,
  type OperationalPaymentDraftState,
  type OperationalPaymentUiState,
} from "./model";
import {
  paymentDetailQueryKey,
  paymentsBootstrapQueryKey,
  usePaymentDetailQuery,
  usePaymentsBootstrapQuery,
  usePaymentsListQuery,
} from "./queries";

type PaymentsMode = "create" | "list";

const PAYMENT_CREATE_GUIDE_STEPS = [
  { icon: <ClipboardIcon className="h-4 w-4" />, key: "details", label: "Datos" },
  { icon: <MoneyIcon className="h-4 w-4" />, key: "amount", label: "Monto" },
  { icon: <CardIcon className="h-4 w-4" />, key: "method", label: "Metodo" },
  { icon: <CheckCircleIcon className="h-4 w-4" />, key: "save", label: "Guardar" },
] as const;

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

function getDraftAmountLabel(amountText: string): string {
  const amountCents = getOperationalPaymentAmountCents(amountText);
  return formatCurrency(amountCents === null ? 0 : amountCents / 100);
}

function getCaptureStateLabel(state: OperationalPaymentUiState): string {
  switch (state) {
    case "READY_TO_CONFIRM":
      return "Listo";
    case "CONFIRMING":
      return "Confirmando";
    case "CONFIRMED":
      return "Registrado";
    case "ERROR":
      return "Error";
    case "LIST_VIEW_READY":
      return "Consulta";
    case "NO_SELECTION":
      return "Sin seleccion";
    case "CAPTURING":
      return "Captura activa";
    default:
      return "Incompleto";
  }
}

function getCaptureStateTone(
  state: OperationalPaymentUiState,
): "muted" | "primary" | "success" | "warning" | "danger" {
  switch (state) {
    case "READY_TO_CONFIRM":
      return "success";
    case "CONFIRMING":
      return "primary";
    case "CONFIRMED":
      return "success";
    case "ERROR":
      return "danger";
    case "LIST_VIEW_READY":
      return "primary";
    case "NO_SELECTION":
      return "muted";
    default:
      return "warning";
  }
}

function getImpactTitle(affectsCash: boolean): string {
  return affectsCash ? "Afecta caja" : "No afecta caja";
}

function getImpactDescription(affectsCash: boolean): string {
  return affectsCash
    ? "Este pago reduce el efectivo esperado del turno y queda auditado como salida de caja."
    : "Este pago queda auditado sin reducir el efectivo esperado del turno.";
}

function getCategoryLabel(
  categoryCode: string,
  categories: OperationalPaymentCategoryView[],
): string | null {
  return categories.find((category) => category.code === categoryCode)?.name ?? null;
}

function getScopeContextLabel(scope: string): string {
  switch (scope) {
    case "TODAY":
      return "Mostrando pagos de hoy.";
    case "RECENT":
      return "Mostrando pagos recientes de la estacion.";
    default:
      return "Mostrando pagos del turno actual.";
  }
}

function getEmptyListDescription(scopeLabel: string, query: string): string {
  if (query.trim().length > 0) {
    return "No hay pagos con ese folio, referencia o beneficiario dentro del alcance actual.";
  }

  return `${scopeLabel} Los pagos operativos registran salidas auditables como proveedores, servicios o logistica. Crea uno cuando necesites dejar trazabilidad del gasto.`;
}

function getMethodFilterOptions(methods: OperationalPaymentMethodView[]) {
  return [{ label: "Todos los metodos", value: "" }].concat(
    methods.map((method) => ({
      label: method.label,
      value: method.code,
    })),
  );
}

function getCategoryFilterOptions(categories: OperationalPaymentCategoryView[]) {
  return [{ label: "Todas las categorias", value: "" }].concat(
    categories.map((category) => ({
      label: category.name,
      value: category.code,
    })),
  );
}

function getUserFilterOptions(users: OperationalPaymentFilterOptionView[]) {
  return [{ label: "Todos los operadores", value: "" }].concat(
    users.map((user) => ({
      label: user.label,
      value: user.value,
    })),
  );
}

function PaymentMethodButton({
  isActive,
  method,
  onSelect,
}: {
  isActive: boolean;
  method: OperationalPaymentMethodView;
  onSelect: () => void;
}) {
  return (
    <button
      className={cn(
        "grid min-h-[4.25rem] gap-1.5 rounded-[var(--pos-radius-control)] border px-3 py-2.5 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
        isActive
          ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)]"
          : "border-[var(--pos-shell-border)] bg-white hover:border-[var(--pos-primary)] hover:bg-[var(--pos-shell-muted)]",
        !method.is_enabled && "cursor-not-allowed opacity-55",
      )}
      disabled={!method.is_enabled}
      onClick={onSelect}
      type="button"
    >
      <div className="min-w-0">
        <p className="text-sm font-semibold text-slate-950">{method.label}</p>
        {method.helper_text ? (
          <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-slate-600">
            {method.helper_text}
          </p>
        ) : null}
      </div>
    </button>
  );
}

function PaymentCaptureWorkspace({
  categories,
  createError,
  draft,
  methods,
  onCategoryChange,
  onConceptChange,
  onMethodChange,
  onNotesChange,
  onPayeeChange,
  onSubmit,
  onTotalAmountChange,
}: {
  categories: OperationalPaymentCategoryView[];
  createError: string | null;
  draft: OperationalPaymentDraftState;
  methods: OperationalPaymentMethodView[];
  onCategoryChange: (value: string) => void;
  onConceptChange: (value: string) => void;
  onMethodChange: (value: string) => void;
  onNotesChange: (value: string) => void;
  onPayeeChange: (value: string) => void;
  onSubmit: () => void;
  onTotalAmountChange: (value: string) => void;
}) {
  const selectedMethod = getOperationalPaymentMethod(draft.paymentMethodCode, methods);
  const affectsCash = doesOperationalPaymentAffectCashDrawer(draft.paymentMethodCode, methods);

  return (
    <div className="grid h-full min-h-0 place-items-center py-4">
      <form
        className="grid w-full max-w-4xl gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <section className="grid gap-4 rounded-[var(--pos-radius-panel)] border border-[var(--pos-shell-border)] bg-[var(--pos-shell-surface)] px-4 py-4 shadow-[var(--pos-subtle-shadow)]">
          <div className="grid gap-1">
            <p className="pos-label-text">Nuevo pago</p>
            <h2 className="text-lg font-semibold text-slate-950">Registrar pago operativo</h2>
            <p className="text-sm text-slate-600">
              Captura beneficiario, categoria, referencia, monto, metodo y notas operativas.
            </p>
          </div>

          {createError ? (
            <PosInlineValidationMessage tone="error">{createError}</PosInlineValidationMessage>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <PosFieldLabel helper="Nombre de quien recibe el pago." required>
              Beneficiario
              <input
                aria-label="Beneficiario del pago"
                autoFocus
                className={cn(
                  posInputClass,
                  "mt-1 h-11 w-full rounded-[var(--pos-radius-control)] px-3 text-sm",
                )}
                onChange={(event) => onPayeeChange(event.target.value)}
                placeholder="Nombre o razon social"
                value={draft.payeeName}
              />
            </PosFieldLabel>

            <PosFieldLabel helper="Clasifica el pago para auditoria y filtros." required>
              Categoria
              <select
                aria-label="Categoria del pago"
                className={cn(
                  posInputClass,
                  "mt-1 h-11 w-full rounded-[var(--pos-radius-control)] px-3 text-sm",
                )}
                onChange={(event) => onCategoryChange(event.target.value)}
                value={draft.categoryCode}
              >
                <option value="">Selecciona una categoria</option>
                {categories.map((category) => (
                  <option key={category.code} value={category.code}>
                    {category.name}
                  </option>
                ))}
              </select>
            </PosFieldLabel>

            <PosFieldLabel helper="Factura, folio externo o referencia interna." required>
              Referencia
              <input
                aria-label="Referencia del pago"
                className={cn(
                  posInputClass,
                  "mt-1 h-11 w-full rounded-[var(--pos-radius-control)] px-3 text-sm",
                )}
                onChange={(event) => onConceptChange(event.target.value)}
                placeholder="REF-001"
                value={draft.concept}
              />
            </PosFieldLabel>

            <PosFieldLabel helper="Monto total del pago." required>
              Monto
              <input
                aria-label="Monto del pago"
                className={cn(
                  posInputClass,
                  "mt-1 h-12 w-full rounded-[var(--pos-radius-control)] px-3 text-lg font-semibold [font-variant-numeric:tabular-nums]",
                )}
                inputMode="decimal"
                onChange={(event) => onTotalAmountChange(event.target.value)}
                placeholder="0.00"
                value={draft.totalAmountText}
              />
            </PosFieldLabel>

            <div className="grid gap-2 md:col-span-2">
              <PosFieldLabel helper="Selecciona como se registro el pago." required>
                Metodo
              </PosFieldLabel>
              <div className="grid gap-2 sm:grid-cols-3">
                {methods.map((method) => (
                  <PaymentMethodButton
                    isActive={draft.paymentMethodCode === method.code}
                    key={method.code}
                    method={method}
                    onSelect={() => onMethodChange(method.code)}
                  />
                ))}
              </div>
            </div>

            <PosFieldLabel
              className="md:col-span-2"
              helper="Observaciones operativas. Se guardan en auditoria si capturas contenido."
            >
              Notas
              <textarea
                aria-label="Notas del pago"
                className={cn(
                  posInputClass,
                  "mt-1 min-h-[7.5rem] w-full rounded-[var(--pos-radius-control)] px-3 py-2.5 text-sm",
                )}
                onChange={(event) => onNotesChange(event.target.value)}
                placeholder="Detalle adicional del gasto o evidencia textual."
                value={draft.notes}
              />
            </PosFieldLabel>
          </div>

          {selectedMethod ? (
            <PosInlineValidationMessage tone={affectsCash ? "warning" : "info"}>
              {getImpactDescription(affectsCash)}
            </PosInlineValidationMessage>
          ) : null}
        </section>
      </form>
    </div>
  );
}

function PaymentDetailSummary({
  payment,
}: {
  payment: OperationalPaymentDetailResponse;
}) {
  return (
    <div className="grid gap-3">
      <div className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3">
        <p className="pos-label-text">Monto</p>
        <p className="mt-1 text-[1.75rem] font-semibold leading-tight text-slate-950 [font-variant-numeric:tabular-nums]">
          {formatCurrency(payment.total_amount)}
        </p>
      </div>

      <div className="grid gap-2 text-sm text-slate-700">
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Referencia</span>
          <p className="font-semibold text-slate-950">{payment.concept}</p>
        </div>
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Beneficiario</span>
          <p className="font-semibold text-slate-950">{payment.payee_name}</p>
        </div>
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Categoria</span>
          <p className="font-semibold text-slate-950">{payment.category_name ?? "Sin categoria"}</p>
        </div>
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Metodo e impacto</span>
          <p className="font-semibold text-slate-950">
            {getOperationalPaymentMethodLabel(payment.payment_method_code)} ·{" "}
            {getImpactTitle(payment.affects_cash_drawer)}
          </p>
        </div>
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Operador</span>
          <p className="font-semibold text-slate-950">{payment.created_by.full_name}</p>
          <p className="text-xs text-slate-500">
            {formatLocalDateTime(payment.committed_at_utc, payment.branch.timezone)}
          </p>
        </div>
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Sucursal y estacion</span>
          <p className="font-semibold text-slate-950">
            {payment.branch.name} · {payment.workstation.name}
          </p>
        </div>
        {payment.notes ? (
          <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
            <span className="pos-label-text">Notas</span>
            <p className="whitespace-pre-wrap text-slate-700">{payment.notes}</p>
          </div>
        ) : null}
      </div>

      <PosAuditSummary
        auditSummary={payment.audit_summary}
        timeZone={payment.branch.timezone}
      />
    </div>
  );
}

export function PaymentsRightPanel({
  blockedMessages,
  blockedReason,
  categories,
  createError,
  draft,
  isConfirmPending,
  isDetailPending,
  mode,
  onCancelCreate,
  onCommitCreate,
  onResultAction,
  paymentDetail,
  recentCreatedPaymentId,
}: {
  blockedMessages: string[];
  blockedReason: string | null;
  categories: OperationalPaymentCategoryView[];
  createError: string | null;
  draft: OperationalPaymentDraftState;
  isConfirmPending: boolean;
  isDetailPending: boolean;
  mode: PaymentsMode;
  onCancelCreate: () => void;
  onCommitCreate: () => void;
  onResultAction: (actionKey: string) => void;
  paymentDetail: OperationalPaymentDetailResponse | null;
  recentCreatedPaymentId: string | null;
}) {
  if (mode === "create") {
    const draftCategoryLabel = getCategoryLabel(draft.categoryCode, categories);
    const amountLabel = getDraftAmountLabel(draft.totalAmountText);

    return (
      <PosSummaryPanel
        description="Resume el pago antes de registrarlo."
        stateLabel="Captura activa"
        stateTone="draft"
        title="Nuevo pago"
        footer={
          <div className="grid gap-2">
            <PosButton disabled={isConfirmPending} onClick={onCancelCreate} variant="neutral">
              Cancelar
            </PosButton>
            <PosButton disabled={isConfirmPending} onClick={onCommitCreate}>
              {isConfirmPending ? "Guardando..." : "Guardar pago"}
            </PosButton>
            {blockedReason ? (
              <p className="text-sm leading-6 text-slate-600">{blockedReason}</p>
            ) : null}
          </div>
        }
      >
        <ScrollPane className="grid gap-3">
          {createError ? (
            <PosInlineValidationMessage tone="error">{createError}</PosInlineValidationMessage>
          ) : null}

          <div className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3">
            <p className="pos-label-text">Monto</p>
            <p className="mt-1 text-[1.75rem] font-semibold leading-tight text-slate-950 [font-variant-numeric:tabular-nums]">
              {amountLabel}
            </p>
          </div>

          <div className="grid gap-2 text-sm text-slate-700">
            <div className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
              <span className="pos-label-text">Beneficiario</span>
              <p className="font-semibold text-slate-950">
                {draft.payeeName.trim().length > 0 ? draft.payeeName.trim() : "Pendiente"}
              </p>
            </div>
            <div className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
              <span className="pos-label-text">Referencia</span>
              <p className="font-semibold text-slate-950">
                {draft.concept.trim().length > 0 ? draft.concept.trim() : "Pendiente"}
              </p>
            </div>
            <div className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
              <span className="pos-label-text">Categoria</span>
              <p className="font-semibold text-slate-950">{draftCategoryLabel ?? "Pendiente"}</p>
            </div>
            <div className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
              <span className="pos-label-text">Metodo</span>
              <p className="font-semibold text-slate-950">
                {draft.paymentMethodCode.length > 0
                  ? getOperationalPaymentMethodLabel(draft.paymentMethodCode)
                  : "Pendiente"}
              </p>
            </div>
          </div>

          {blockedMessages.map((message) => (
            <PosInlineValidationMessage key={message} tone="warning">
              {message}
            </PosInlineValidationMessage>
          ))}
        </ScrollPane>
      </PosSummaryPanel>
    );
  }

  if (isDetailPending) {
    return (
      <PosSummaryPanel
        description="Recuperando el pago seleccionado."
        stateLabel="Cargando"
        stateTone="pending"
        title="Pago seleccionado"
      >
        <PosLoadingState
          description="Consultando el resumen operativo del pago."
          title="Cargando pago"
        />
      </PosSummaryPanel>
    );
  }

  if (!paymentDetail) {
    return (
      <PosSummaryPanel
        description="El panel derecho muestra el resumen operativo y el resultado del registro."
        stateLabel="Sin seleccion"
        stateTone="draft"
        title="Selecciona un pago"
      >
        <PosEmptyState
          description="Selecciona un pago para revisar su contexto operativo o crea uno nuevo para registrar una salida auditada."
          title="Sin pago seleccionado"
        />
      </PosSummaryPanel>
    );
  }

  if (paymentDetail.id === recentCreatedPaymentId) {
    const resultMessage = createOperationResultMessage({
      description: `Referencia ${paymentDetail.concept}. Usa el historial para seguir auditando el turno o registra un nuevo pago.`,
      nextActions: [createToastAction("viewHistory"), createToastAction("newOperation")],
      operationType: "payment",
      referenceId: paymentDetail.folio,
    });

    return (
      <div className="grid gap-3">
        <PosOperationResultPanel message={resultMessage} onSelectAction={onResultAction} />
        <PosAuditSummary
          auditSummary={paymentDetail.audit_summary}
          timeZone={paymentDetail.branch.timezone}
        />
      </div>
    );
  }

  return (
    <PosSummaryPanel
      description={formatLocalDateTime(paymentDetail.committed_at_utc, paymentDetail.branch.timezone)}
      stateLabel={paymentDetail.affects_cash_drawer ? "Afecta caja" : "Auditado"}
      stateTone={paymentDetail.affects_cash_drawer ? "warning" : "confirmed"}
      title={paymentDetail.folio}
      footer={
        <div className="grid gap-2">
          <PosButton onClick={() => onResultAction("newOperation")}>Nuevo pago</PosButton>
        </div>
      }
    >
      <ScrollPane className="grid gap-3">
        <PaymentDetailSummary payment={paymentDetail} />
      </ScrollPane>
    </PosSummaryPanel>
  );
}

export function PaymentsScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const queryClient = useQueryClient();
  const searchInputRef = useRef<HTMLInputElement>(null);

  const paymentsBootstrapQuery = usePaymentsBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const [mode, setMode] = useState<PaymentsMode>("list");
  const [selectedScope, setSelectedScope] = useState("CURRENT_SHIFT");
  const [searchText, setSearchText] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedMethodFilter, setSelectedMethodFilter] = useState("");
  const [selectedCreatedByUserId, setSelectedCreatedByUserId] = useState("");
  const [selectedPaymentId, setSelectedPaymentId] = useState<string | null>(null);
  const [draftState, setDraftState] = useState<OperationalPaymentDraftState>(
    createInitialOperationalPaymentDraftState(),
  );
  const [createError, setCreateError] = useState<string | null>(null);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [recentCreatedPaymentId, setRecentCreatedPaymentId] = useState<string | null>(null);

  const debouncedSearchText = useDebouncedValue(searchText, 220);
  const paymentsListQuery = usePaymentsListQuery(
    selectedScope,
    debouncedSearchText,
    selectedCategory,
    selectedMethodFilter,
    selectedCreatedByUserId,
  );
  const paymentDetailQuery = usePaymentDetailQuery(mode === "list" ? selectedPaymentId : null);

  const bootstrapData = paymentsBootstrapQuery.data;
  const methods = useMemo(
    () => bootstrapData?.active_payment_methods ?? [],
    [bootstrapData?.active_payment_methods],
  );
  const categories = useMemo(
    () => bootstrapData?.active_categories ?? [],
    [bootstrapData?.active_categories],
  );
  const scopes = useMemo(
    () => bootstrapData?.available_scopes ?? [],
    [bootstrapData?.available_scopes],
  );
  const paymentsResponse = paymentsListQuery.data;
  const payments = useMemo(
    () => paymentsResponse?.payments ?? [],
    [paymentsResponse?.payments],
  );
  const availableUsers = useMemo(
    () => paymentsResponse?.available_users ?? [],
    [paymentsResponse?.available_users],
  );
  const selectedPayment = paymentDetailQuery.data ?? null;
  const selectedMethod = getOperationalPaymentMethod(draftState.paymentMethodCode, methods);
  const affectsCash = doesOperationalPaymentAffectCashDrawer(draftState.paymentMethodCode, methods);
  const createBlockedMessages = getOperationalPaymentBlockingMessages(
    draftState,
    methods,
    categories,
  );
  const createBlockedReason = getOperationalPaymentBlockedReason(
    draftState,
    methods,
    categories,
  );
  const captureUiState = getOperationalPaymentUiState({
    categories,
    draft: draftState,
    hasCommitError: createError !== null,
    hasConfirmedDraft: false,
    hasSelectedPayment: false,
    isCaptureActive: true,
    isCommitPending: false,
    methods,
  });
  const canCommitDraft = canCommitOperationalPaymentDraft(draftState, methods, categories);
  const defaultScope = bootstrapData?.default_scope ?? "CURRENT_SHIFT";

  useEffect(() => {
    if (!bootstrapData) {
      return;
    }

    setSelectedScope((currentScope) =>
      currentScope.trim().length > 0 ? currentScope : bootstrapData.default_scope,
    );
  }, [bootstrapData]);

  useEffect(() => {
    if (mode !== "list" || selectedPaymentId === null) {
      return;
    }

    if (payments.some((payment) => payment.id === selectedPaymentId)) {
      return;
    }

    setSelectedPaymentId(null);
  }, [mode, payments, selectedPaymentId]);

  useEffect(() => {
    setCreateError(null);
  }, [
    draftState.categoryCode,
    draftState.concept,
    draftState.notes,
    draftState.payeeName,
    draftState.paymentMethodCode,
    draftState.totalAmountText,
  ]);

  const handleOpenCreate = useCallback(() => {
    setMode("create");
    setDraftState(createInitialOperationalPaymentDraftState());
    setCreateError(null);
    setIsConfirmDialogOpen(false);
  }, []);

  const handleCancelCreate = useCallback(() => {
    setMode("list");
    setDraftState(createInitialOperationalPaymentDraftState());
    setCreateError(null);
    setIsConfirmDialogOpen(false);
  }, []);

  const createPaymentMutation = useMutation({
    mutationFn: async () => {
      if (!accessToken) {
        throw new Error("Necesitas iniciar sesion antes de registrar un pago.");
      }

      return createPayment({
        accessToken,
        payload: buildCreateOperationalPaymentRequest(
          appEnv.VITE_POS_WORKSTATION_CODE,
          draftState,
          methods,
          categories,
        ),
        requestId: createRequestId("operational-payment"),
      });
    },
    onSuccess: async (result) => {
      setMode("list");
      setSelectedScope(defaultScope);
      setSearchText("");
      setSelectedCategory("");
      setSelectedMethodFilter("");
      setSelectedCreatedByUserId("");
      setSelectedPaymentId(result.id);
      setRecentCreatedPaymentId(result.id);
      setDraftState(createInitialOperationalPaymentDraftState());
      setCreateError(null);
      setIsConfirmDialogOpen(false);
      showSuccess(`Pago ${result.folio} registrado por ${formatCurrency(result.total_amount)}.`);

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: paymentsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: ["payments-list", appEnv.VITE_POS_WORKSTATION_CODE],
        }),
        queryClient.invalidateQueries({
          queryKey: paymentDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, result.id),
        }),
        queryClient.invalidateQueries({
          queryKey: currentCashSessionQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: cashCloseBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: cashCloseSummaryQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: cashCloseReconciliationQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
      ]);
    },
    onError: (error) => {
      const message = toOperationalErrorMessage(error, "No fue posible registrar el pago.");
      setCreateError(message);
      setIsConfirmDialogOpen(false);
      showError(message);
    },
  });
  const commitPaymentAsync = createPaymentMutation.mutateAsync;
  const isCreatePaymentPending = createPaymentMutation.isPending;

  const handleCommit = useCallback(() => {
    if (!canCommitDraft) {
      return;
    }

    if (affectsCash) {
      setIsConfirmDialogOpen(true);
      return;
    }

    void commitPaymentAsync();
  }, [affectsCash, canCommitDraft, commitPaymentAsync]);

  const keyboardShortcuts = useMemo(
    () => [
      {
        chords: ["Ctrl+N", "Meta+N"],
        description: "Abre una nueva captura de pago operativo.",
        group: "Pagos",
        handler: () => {
          if (mode === "list") {
            handleOpenCreate();
          }
        },
        id: "payments-new",
        label: "Nuevo pago",
        priority: 120,
      },
      {
        chords: ["Escape"],
        description:
          mode === "create"
            ? "Cancela la captura actual o cierra la confirmacion."
            : "Limpia la seleccion actual del pago.",
        group: "Pagos",
        handler: () => {
          if (isConfirmDialogOpen) {
            setIsConfirmDialogOpen(false);
            return;
          }

          if (mode === "create") {
            handleCancelCreate();
            return;
          }

          if (selectedPaymentId !== null) {
            setSelectedPaymentId(null);
          }
        },
        id: "payments-escape",
        label: "Cancelar flujo activo",
        priority: 110,
      },
      {
        chords: ["Enter", "NumpadEnter"],
        description: "Guarda el pago actual cuando la captura ya esta completa.",
        group: "Pagos",
        handler: () => {
          if (mode !== "create" || isConfirmDialogOpen || !canCommitDraft) {
            return;
          }

          handleCommit();
        },
        id: "payments-submit",
        isEnabled: () => mode === "create" && canCommitDraft,
        label: "Guardar pago",
        priority: 100,
      },
    ],
    [
      canCommitDraft,
      handleCancelCreate,
      handleCommit,
      handleOpenCreate,
      isConfirmDialogOpen,
      mode,
      selectedPaymentId,
    ],
  );

  useModuleHotkeys(keyboardShortcuts, true);

  useEffect(() => {
    const handleEditableEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || !isEditableTarget(event.target)) {
        return;
      }

      if (isConfirmDialogOpen) {
        event.preventDefault();
        setIsConfirmDialogOpen(false);
      }
    };

    window.addEventListener("keydown", handleEditableEscape);
    return () => window.removeEventListener("keydown", handleEditableEscape);
  }, [isConfirmDialogOpen]);

  useAppShellRightPanel(
    <PaymentsRightPanel
      blockedMessages={createBlockedMessages}
      blockedReason={createBlockedReason}
      categories={categories}
      createError={createError}
      draft={draftState}
      isConfirmPending={isCreatePaymentPending}
      isDetailPending={selectedPaymentId !== null && paymentDetailQuery.isPending}
      mode={mode}
      onCancelCreate={handleCancelCreate}
      onCommitCreate={handleCommit}
      onResultAction={(actionKey) => {
        if (actionKey === "viewHistory") {
          setRecentCreatedPaymentId(null);
          return;
        }

        if (actionKey === "newOperation") {
          handleOpenCreate();
        }
      }}
      paymentDetail={selectedPayment}
      recentCreatedPaymentId={recentCreatedPaymentId}
    />,
  );

  const isBootstrapPending = paymentsBootstrapQuery.isPending || currentCashSessionQuery.isPending;

  if (isBootstrapPending) {
    return (
      <OperationalStatus
        description="Consultando la caja activa y el contexto operativo."
        title="Cargando pagos"
      />
    );
  }

  if (paymentsBootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<PosButton onClick={() => paymentsBootstrapQuery.refetch()}>Reintentar</PosButton>}
        description={toOperationalErrorMessage(
          paymentsBootstrapQuery.error,
          "Confirma la configuracion de la estacion y el contexto operativo.",
        )}
        title="No fue posible cargar Pagos"
      />
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <OperationalStatus
        action={<PosButton onClick={() => currentCashSessionQuery.refetch()}>Reintentar</PosButton>}
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

  if (currentCashSessionQuery.data.user_id !== bootstrapData!.user.id) {
    return (
      <OperationalStatus
        description="La caja abierta de esta estacion pertenece a otro cajero. Inicia sesion con el operador correcto o espera el relevo."
        title="La caja activa no coincide con este cajero"
      />
    );
  }

  const listColumns: PosRecordColumn<OperationalPaymentListItemView>[] = [
    {
      header: "Folio",
      key: "folio",
      renderCell: (payment) => (
        <div className="grid gap-1">
          <PosRecordMeta
            reference={payment.folio}
            status={payment.affects_cash_drawer ? "Afecta caja" : "Auditado"}
            statusTone={payment.affects_cash_drawer ? "warning" : "confirmed"}
            timeZone={bootstrapData!.branch.timezone}
            timestamp={payment.created_at_utc}
          />
          <p className="truncate text-xs text-slate-500">{payment.concept}</p>
        </div>
      ),
      width: "18%",
    },
    {
      header: "Beneficiario",
      key: "payee",
      renderCell: (payment) => (
        <div className="grid gap-1">
          <p className="truncate font-semibold text-slate-950">{payment.payee_name}</p>
          <p className="truncate text-xs text-slate-500">
            {payment.operator_full_name} · {payment.workstation_name}
          </p>
        </div>
      ),
      width: "24%",
    },
    {
      header: "Categoria",
      key: "category",
      renderCell: (payment) => payment.category_name ?? "Sin categoria",
      width: "18%",
    },
    {
      header: "Metodo",
      key: "method",
      renderCell: (payment) => getOperationalPaymentMethodLabel(payment.payment_method_code),
      width: "12%",
    },
    {
      header: "Fecha",
      key: "date",
      renderCell: (payment) =>
        formatCompactLocalDateTime(payment.created_at_utc, bootstrapData!.branch.timezone),
      width: "16%",
    },
    {
      align: "right",
      header: "Monto",
      key: "amount",
      renderCell: (payment) => formatCurrency(payment.total_amount),
      width: "12%",
    },
  ];

  return (
    <>
      <PosConfirmationDialog
        confirmation={posMessageCatalog.confirmation.warningOperation(
          "Confirmar salida de caja",
          `Registraras ${getDraftAmountLabel(draftState.totalAmountText)} por ${draftState.payeeName.trim() || "este beneficiario"}. Este movimiento reducira el efectivo esperado del turno.`,
          "Confirmar pago",
        )}
        details={
          <div className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3 text-sm text-slate-700">
            <p>
              Referencia:{" "}
              <span className="font-semibold text-slate-950">
                {draftState.concept.trim() || "Pendiente"}
              </span>
            </p>
            <p>
              Categoria:{" "}
              <span className="font-semibold text-slate-950">
                {getCategoryLabel(draftState.categoryCode, categories) ?? "Pendiente"}
              </span>
            </p>
            <p>
              Metodo:{" "}
              <span className="font-semibold text-slate-950">
                {selectedMethod?.label ?? "Pendiente"}
              </span>
            </p>
          </div>
        }
        isOpen={isConfirmDialogOpen}
        isPending={isCreatePaymentPending}
        onCancel={() => setIsConfirmDialogOpen(false)}
        onConfirm={() => {
          void commitPaymentAsync();
        }}
      />
      <CentralWorkspaceSheet
        className="lg:h-full"
        contentClassName="min-h-0 overflow-hidden px-3 pb-3 pt-2"
        header={
          <CompactPageHeader
            secondaryChips={
              mode === "create" ? (
                <ModuleStateChip tone={getCaptureStateTone(captureUiState)}>
                  {getCaptureStateLabel(captureUiState)}
                </ModuleStateChip>
              ) : (
                <ModuleStateChip>
                  {searchText.trim().length > 0 ||
                  selectedCategory.length > 0 ||
                  selectedMethodFilter.length > 0 ||
                  selectedCreatedByUserId.length > 0
                    ? "Filtro activo"
                    : getScopeContextLabel(selectedScope)}
                </ModuleStateChip>
              )
            }
            stateChip={
              <ModuleStateChip tone={mode === "create" ? "primary" : "muted"}>
                {mode === "create"
                  ? "Captura activa"
                  : selectedPaymentId
                    ? "Pago en vista"
                    : "Sin seleccion"}
              </ModuleStateChip>
            }
            title="Pagos operativos"
          >
            <FlowGuide
              activeStepKey={
                mode === "create"
                  ? getOperationalPaymentCreateStepKey(draftState, methods, categories)
                  : selectedPaymentId === null
                    ? "list"
                    : "detail"
              }
              steps={
                mode === "create"
                  ? [...PAYMENT_CREATE_GUIDE_STEPS]
                  : [
                      {
                        key: "list",
                        label: "Consulta",
                        state: selectedPaymentId ? "completed" : "current",
                      },
                      {
                        key: "detail",
                        label: "Detalle",
                        state: selectedPaymentId ? "current" : "upcoming",
                      },
                    ]
              }
              variant={mode === "create" ? "process" : "compact"}
            />
          </CompactPageHeader>
        }
      >
        {mode === "create" ? (
          <PaymentCaptureWorkspace
            categories={categories}
            createError={createError}
            draft={draftState}
            methods={methods}
            onCategoryChange={(value) =>
              setDraftState((current) => ({
                ...current,
                categoryCode: value,
              }))
            }
            onConceptChange={(value) =>
              setDraftState((current) => ({
                ...current,
                concept: value,
              }))
            }
            onMethodChange={(value) =>
              setDraftState((current) => ({
                ...current,
                paymentMethodCode: value,
              }))
            }
            onNotesChange={(value) =>
              setDraftState((current) => ({
                ...current,
                notes: value,
              }))
            }
            onPayeeChange={(value) =>
              setDraftState((current) => ({
                ...current,
                payeeName: value,
              }))
            }
            onSubmit={handleCommit}
            onTotalAmountChange={(value) =>
              setDraftState((current) => ({
                ...current,
                totalAmountText: sanitizeOperationalPaymentAmountInput(value),
              }))
            }
          />
        ) : (
          <div className="grid h-full min-h-0 gap-3">
            <PosFilterBar
              actions={
                <PosButton
                  leadingIcon={<PlusIcon className="h-4 w-4" />}
                  onClick={handleOpenCreate}
                >
                  Nuevo pago
                </PosButton>
              }
              chipFilters={(scopes.length > 0
                ? scopes
                : [{ code: "CURRENT_SHIFT", label: "Turno actual" }]
              ).map((scope: OperationalPaymentScopeView) => ({
                isActive: selectedScope === scope.code,
                key: scope.code,
                label: scope.label,
                onSelect: () => setSelectedScope(scope.code),
              }))}
              countLabel={<PosStatusBadge status="draft">{payments.length} pagos</PosStatusBadge>}
              searchInput={{
                ariaLabel: "Buscar pago por folio, referencia o beneficiario",
                hotkeyChords: ["Ctrl+F"],
                inputRef: searchInputRef,
                onChange: setSearchText,
                placeholder: "Buscar por folio, referencia o beneficiario",
                value: searchText,
              }}
              selectFilters={[
                {
                  ariaLabel: "Filtrar pagos por categoria",
                  key: "category",
                  onChange: setSelectedCategory,
                  options: getCategoryFilterOptions(categories),
                  value: selectedCategory,
                },
                {
                  ariaLabel: "Filtrar pagos por metodo",
                  key: "method",
                  onChange: setSelectedMethodFilter,
                  options: getMethodFilterOptions(methods),
                  value: selectedMethodFilter,
                },
                {
                  ariaLabel: "Filtrar pagos por operador",
                  key: "user",
                  onChange: setSelectedCreatedByUserId,
                  options: getUserFilterOptions(availableUsers),
                  value: selectedCreatedByUserId,
                },
              ]}
              title="Pagos registrados"
            />

            {paymentsListQuery.error ? (
              <PosErrorState
                description={toOperationalErrorMessage(
                  paymentsListQuery.error,
                  "No fue posible consultar los pagos operativos de la estacion.",
                )}
                title="La lista no esta disponible"
              />
            ) : paymentsListQuery.isPending && !paymentsResponse ? (
              <PosLoadingState
                description="Recuperando los pagos operativos del alcance actual."
                title="Cargando pagos"
              />
            ) : (
              <PosRecordTable
                columns={listColumns}
                emptyAction={
                  <PosButton
                    leadingIcon={<PlusIcon className="h-4 w-4" />}
                    onClick={handleOpenCreate}
                  >
                    Nuevo pago
                  </PosButton>
                }
                emptyDescription={getEmptyListDescription(
                  getScopeContextLabel(selectedScope),
                  searchText,
                )}
                emptyTitle="Sin pagos para esta vista"
                getKey={(payment) => payment.id}
                getRowActions={(payment) => [
                  {
                    key: `${payment.id}-copy-folio`,
                    label: "Copiar folio",
                    onSelect: () => {
                      void copyDocumentReferenceToClipboard(payment.folio)
                        .then(() => showSuccess("Folio copiado."))
                        .catch(() => showError("No se pudo copiar el folio."));
                    },
                  },
                ]}
                loading={paymentsListQuery.isPending}
                loadingTitle="Cargando pagos"
                onSelect={(payment) => {
                  setSelectedPaymentId(payment.id);
                  setRecentCreatedPaymentId((current) =>
                    current === payment.id ? current : null,
                  );
                }}
                records={payments}
                selectedKey={selectedPaymentId}
                tableAriaLabel="Tabla de pagos operativos"
              />
            )}
          </div>
        )}
      </CentralWorkspaceSheet>
    </>
  );
}
