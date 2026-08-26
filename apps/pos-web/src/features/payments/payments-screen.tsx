import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import { OperationalStatus } from "../../components/operational-status";
import { PosAuditSummary } from "../../components/pos-audit-summary";
import {
  PosConfirmationDialog,
  PosErrorState,
  PosInlineValidationMessage,
  PosLoadingState,
} from "../../components/pos-feedback";
import { PosButton, PosFieldLabel, PosStatusBadge } from "../../components/pos-foundations";
import { PosSummaryPanel } from "../../components/pos-module-layout";
import {
  PosFilterBar,
  PosRecordMeta,
  PosRecordTable,
  type PosRecordColumn,
} from "../../components/pos-records";
import { PlusIcon } from "../../components/pos-icons";
import {
  CentralWorkspaceSheet,
  CompactPageHeader,
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
import {
  formatCompactLocalDateTime,
  formatCurrency,
  formatLocalDateTime,
} from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import { isEditableTarget } from "../../lib/keyboard-shortcuts";
import { posMessageCatalog } from "../../lib/pos-messages";
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
      return "Hoy";
    case "RECENT":
      return "Recientes";
    default:
      return "Turno actual";
  }
}

function getEmptyListDescription(scopeLabel: string, query: string): string {
  if (query.trim().length > 0) {
    return "No hay pagos con ese folio, referencia o beneficiario.";
  }

  return `Sin pagos registrados en ${scopeLabel.toLowerCase()}.`;
}

function getEmptyListTitle(query: string, hasActiveFilters: boolean): string {
  return query.trim().length > 0 || hasActiveFilters ? "Sin resultados" : "Sin pagos registrados";
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
        "grid min-h-[3.25rem] gap-0.5 rounded-[var(--pos-radius-control)] border px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
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
          <p className="line-clamp-1 text-[11px] leading-4 text-slate-600">
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
    <div className="grid h-full min-h-0 content-start gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-2.5 shadow-sm">
        <div className="min-w-0">
          <p className="pos-label-text">Nuevo pago</p>
          <h2 className="text-base font-semibold text-slate-950">Registrar pago operativo</h2>
        </div>
        <PosStatusBadge status={affectsCash ? "warning" : "confirmed"}>
          {selectedMethod ? getImpactTitle(affectsCash) : "Pendiente"}
        </PosStatusBadge>
      </div>

      <form
        className="grid w-full gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <section className="grid gap-3 rounded-[var(--pos-radius-panel)] border border-[var(--pos-shell-border)] bg-[var(--pos-shell-surface)] px-3 py-3 shadow-[var(--pos-subtle-shadow)]">
          {createError ? (
            <PosInlineValidationMessage tone="error">{createError}</PosInlineValidationMessage>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2">
            <PosFieldLabel required>
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

            <PosFieldLabel required>
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

            <PosFieldLabel required>
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

            <PosFieldLabel required>
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
              <PosFieldLabel required>
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

            <details
              className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5 md:col-span-2"
              open={draft.notes.trim().length > 0}
            >
              <summary className="cursor-pointer text-sm font-semibold text-slate-950">
                {draft.notes.trim().length > 0 ? "Observacion" : "Agregar observacion"}
              </summary>
              <textarea
                aria-label="Notas del pago"
                className={cn(
                  posInputClass,
                  "mt-2 min-h-20 w-full rounded-[var(--pos-radius-control)] px-3 py-2.5 text-sm",
                )}
                onChange={(event) => onNotesChange(event.target.value)}
                placeholder="Detalle adicional del gasto."
                value={draft.notes}
              />
            </details>
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
  const detailRows = [
    { key: "reference", label: "Referencia", value: payment.concept },
    { key: "payee", label: "Beneficiario", value: payment.payee_name },
    { key: "category", label: "Categoria", value: payment.category_name ?? "Sin categoria" },
    {
      key: "method",
      label: "Metodo",
      value: `${getOperationalPaymentMethodLabel(payment.payment_method_code)} - ${getImpactTitle(
        payment.affects_cash_drawer,
      )}`,
    },
    { key: "operator", label: "Operador", value: payment.created_by.full_name },
    {
      key: "time",
      label: "Hora",
      value: formatLocalDateTime(payment.committed_at_utc, payment.branch.timezone),
    },
    {
      key: "branch",
      label: "Sucursal",
      value: `${payment.branch.name} - ${payment.workstation.name}`,
    },
    ...(payment.notes ? [{ key: "notes", label: "Observacion", value: payment.notes }] : []),
  ];

  return (
    <div className="grid gap-3">
      <div className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3">
        <p className="pos-label-text">Monto</p>
        <p className="mt-1 text-[1.75rem] font-semibold leading-tight text-slate-950 [font-variant-numeric:tabular-nums]">
          {formatCurrency(payment.total_amount)}
        </p>
      </div>

      <div className="overflow-hidden rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white text-sm">
        {detailRows.map((row) => (
          <div
            className="grid grid-cols-[6.25rem_minmax(0,1fr)] gap-2 border-t border-[var(--pos-shell-border)] px-3 py-2 first:border-t-0"
            key={row.key}
          >
            <span className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              {row.label}
            </span>
            <span className="truncate text-right font-semibold text-slate-950" title={row.value}>
              {row.value}
            </span>
          </div>
        ))}
      </div>

      <div className="hidden gap-2 text-sm text-slate-700">
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
  paymentCount,
  paymentDetail,
}: {
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
  paymentCount: number;
  paymentDetail: OperationalPaymentDetailResponse | null;
}) {
  if (mode === "create") {
    const draftCategoryLabel = getCategoryLabel(draft.categoryCode, categories);
    const amountLabel = getDraftAmountLabel(draft.totalAmountText);
    const draftRows = [
      {
        key: "payee",
        label: "Beneficiario",
        value: draft.payeeName.trim().length > 0 ? draft.payeeName.trim() : "Pendiente",
      },
      {
        key: "reference",
        label: "Referencia",
        value: draft.concept.trim().length > 0 ? draft.concept.trim() : "Pendiente",
      },
      { key: "category", label: "Categoria", value: draftCategoryLabel ?? "Pendiente" },
      {
        key: "method",
        label: "Metodo",
        value:
          draft.paymentMethodCode.length > 0
            ? getOperationalPaymentMethodLabel(draft.paymentMethodCode)
            : "Pendiente",
      },
    ];

    return (
      <PosSummaryPanel
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

          <div className="overflow-hidden rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white text-sm">
            {draftRows.map((row) => (
              <div
                className="grid grid-cols-[6rem_minmax(0,1fr)] gap-2 border-t border-[var(--pos-shell-border)] px-3 py-2 first:border-t-0"
                key={row.key}
              >
                <span className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                  {row.label}
                </span>
                <span className="truncate text-right font-semibold text-slate-950" title={row.value}>
                  {row.value}
                </span>
              </div>
            ))}
          </div>

          {blockedReason ? (
            <PosInlineValidationMessage tone="warning">{blockedReason}</PosInlineValidationMessage>
          ) : null}
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
        stateLabel="Consulta"
        stateTone="draft"
        title="Detalle del pago"
      >
        <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-white px-3 py-3 text-sm text-slate-600">
          {paymentCount > 0
            ? "Selecciona un pago para revisar su informacion."
            : "Registra un pago para comenzar."}
        </div>
      </PosSummaryPanel>
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
  const totalPaymentsAmount = useMemo(
    () => payments.reduce((sum, payment) => sum + Number(payment.total_amount), 0),
    [payments],
  );
  const availableUsers = useMemo(
    () => paymentsResponse?.available_users ?? [],
    [paymentsResponse?.available_users],
  );
  const hasActiveAdvancedFilters =
    selectedCategory.length > 0 ||
    selectedMethodFilter.length > 0 ||
    selectedCreatedByUserId.length > 0;
  const hasActiveListFilters = searchText.trim().length > 0 || hasActiveAdvancedFilters;
  const shouldShowAdvancedFilters = payments.length > 0 || hasActiveAdvancedFilters;
  const selectedPayment = paymentDetailQuery.data ?? null;
  const selectedMethod = getOperationalPaymentMethod(draftState.paymentMethodCode, methods);
  const affectsCash = doesOperationalPaymentAffectCashDrawer(draftState.paymentMethodCode, methods);
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
        if (actionKey === "newOperation") {
          handleOpenCreate();
        }
      }}
      paymentCount={payments.length}
      paymentDetail={selectedPayment}
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
              <div className="flex flex-wrap items-center gap-2">
                {mode === "create" ? (
                  <ModuleStateChip tone={getCaptureStateTone(captureUiState)}>
                    {getCaptureStateLabel(captureUiState)}
                  </ModuleStateChip>
                ) : (
                  <>
                    <ModuleStateChip>
                      {hasActiveListFilters ? "Filtro activo" : getScopeContextLabel(selectedScope)}
                    </ModuleStateChip>
                    <ModuleStateChip tone="muted">
                      {payments.length} pagos - {formatCurrency(totalPaymentsAmount)} salidas
                    </ModuleStateChip>
                  </>
                )}
              </div>
            }
            stateChip={
              <ModuleStateChip tone={mode === "create" ? "primary" : "muted"}>
                {mode === "create" ? "Captura activa" : "Consulta"}
              </ModuleStateChip>
            }
            title={mode === "create" ? "Nuevo pago" : "Pagos operativos"}
          />
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
          <div className="grid h-full min-h-0 content-start gap-3">
            <PosFilterBar
              actions={
                <PosButton
                  className="h-10"
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
              className="rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-3 shadow-sm"
              countLabel={
                <PosStatusBadge status="draft">
                  {payments.length} pagos - {formatCurrency(totalPaymentsAmount)}
                </PosStatusBadge>
              }
              searchInput={{
                ariaLabel: "Buscar pago por folio, referencia o beneficiario",
                hotkeyChords: ["Ctrl+F"],
                inputRef: searchInputRef,
                onChange: setSearchText,
                placeholder: "Buscar pago",
                value: searchText,
              }}
              selectFilters={
                shouldShowAdvancedFilters
                  ? [
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
                    ]
                  : []
              }
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
                emptyDescription={getEmptyListDescription(
                  getScopeContextLabel(selectedScope),
                  searchText,
                )}
                emptyTitle={getEmptyListTitle(searchText, hasActiveAdvancedFilters)}
                getKey={(payment) => payment.id}
                loading={paymentsListQuery.isPending}
                loadingTitle="Cargando pagos"
                onSelect={(payment) => {
                  setSelectedPaymentId(payment.id);
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
