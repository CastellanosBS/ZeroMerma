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
  DiscountControlsView,
  OperationalDiscountCategoryView,
  OperationalDiscountDetailResponse,
  OperationalDiscountFilterOptionView,
  OperationalDiscountListItemView,
  OperationalDiscountMethodView,
  OperationalDiscountScopeView,
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
import { createDiscount } from "./discounts-api";
import {
  buildCreateOperationalDiscountRequest,
  canCommitOperationalDiscountDraft,
  createInitialOperationalDiscountDraftState,
  doesOperationalDiscountAffectCashDrawer,
  getOperationalDiscountAmountCents,
  getOperationalDiscountBlockedReason,
  getOperationalDiscountBlockingMessages,
  getOperationalDiscountCategoryLabel,
  getOperationalDiscountCreateStepKey,
  getOperationalDiscountMethod,
  getOperationalDiscountMethodLabel,
  getOperationalDiscountUiState,
  isOperationalDiscountHighValue,
  sanitizeOperationalDiscountAmountInput,
  type OperationalDiscountDraftState,
  type OperationalDiscountUiState,
} from "./model";
import {
  discountDetailQueryKey,
  discountsBootstrapQueryKey,
  useDiscountDetailQuery,
  useDiscountsBootstrapQuery,
  useDiscountsListQuery,
} from "./queries";

type DiscountsMode = "create" | "list";

const DISCOUNT_CREATE_GUIDE_STEPS = [
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
  const amountCents = getOperationalDiscountAmountCents(amountText);
  return formatCurrency(amountCents === null ? 0 : amountCents / 100);
}

function getCaptureStateLabel(state: OperationalDiscountUiState): string {
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
  state: OperationalDiscountUiState,
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
    ? "Este descuento registra un cobro interno y aumenta el efectivo esperado del turno."
    : "Este descuento queda auditado sin mover el efectivo esperado de la caja.";
}

function getCategoryLabel(
  categoryCode: string,
  categories: OperationalDiscountCategoryView[],
): string | null {
  return getOperationalDiscountCategoryLabel(categoryCode, categories);
}

function getScopeContextLabel(scope: string): string {
  switch (scope) {
    case "TODAY":
      return "Mostrando descuentos de hoy.";
    case "RECENT":
      return "Mostrando descuentos recientes de la estacion.";
    default:
      return "Mostrando descuentos del turno actual.";
  }
}

function getEmptyListDescription(scopeLabel: string, query: string): string {
  if (query.trim().length > 0) {
    return "No hay descuentos con ese folio, referencia, persona o categoria dentro del alcance actual.";
  }

  return `${scopeLabel} Los descuentos operativos registran cobros internos auditables como prestamos, seguros o cargos al personal. Crea uno cuando necesites dejar trazabilidad del descuento aplicado.`;
}

function getMethodFilterOptions(methods: OperationalDiscountMethodView[]) {
  return [{ label: "Todos los metodos", value: "" }].concat(
    methods.map((method) => ({
      label: method.label,
      value: method.code,
    })),
  );
}

function getCategoryFilterOptions(categories: OperationalDiscountCategoryView[]) {
  return [{ label: "Todas las categorias", value: "" }].concat(
    categories.map((category) => ({
      label: category.name,
      value: category.code,
    })),
  );
}

function getUserFilterOptions(users: OperationalDiscountFilterOptionView[]) {
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
  method: OperationalDiscountMethodView;
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

function DiscountCaptureWorkspace({
  categories,
  controls,
  createError,
  draft,
  methods,
  onCategoryChange,
  onConceptChange,
  onHighValueAcknowledgedChange,
  onMethodChange,
  onNotesChange,
  onSubjectChange,
  onSubmit,
  onTotalAmountChange,
}: {
  categories: OperationalDiscountCategoryView[];
  controls: DiscountControlsView | null;
  createError: string | null;
  draft: OperationalDiscountDraftState;
  methods: OperationalDiscountMethodView[];
  onCategoryChange: (value: string) => void;
  onConceptChange: (value: string) => void;
  onHighValueAcknowledgedChange: (value: boolean) => void;
  onMethodChange: (value: string) => void;
  onNotesChange: (value: string) => void;
  onSubjectChange: (value: string) => void;
  onSubmit: () => void;
  onTotalAmountChange: (value: string) => void;
}) {
  const selectedMethod = getOperationalDiscountMethod(draft.paymentMethodCode, methods);
  const affectsCash = doesOperationalDiscountAffectCashDrawer(draft.paymentMethodCode, methods);
  const isHighValue = isOperationalDiscountHighValue(draft, controls);

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
            <p className="pos-label-text">Nuevo descuento</p>
            <h2 className="text-lg font-semibold text-slate-950">Registrar descuento operativo</h2>
            <p className="text-sm text-slate-600">
              Captura persona o entidad, categoria, motivo o referencia, monto, metodo y notas operativas.
            </p>
          </div>

          {createError ? (
            <PosInlineValidationMessage tone="error">{createError}</PosInlineValidationMessage>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <PosFieldLabel helper="Nombre de la persona o entidad a la que se aplica." required>
              Persona o entidad
              <input
                aria-label="Persona o entidad del descuento"
                autoFocus
                className={cn(
                  posInputClass,
                  "mt-1 h-11 w-full rounded-[var(--pos-radius-control)] px-3 text-sm",
                )}
                onChange={(event) => onSubjectChange(event.target.value)}
                placeholder="Nombre o razon social"
                value={draft.subjectName}
              />
            </PosFieldLabel>

            <PosFieldLabel helper="Clasifica el descuento para auditoria y filtros." required>
              Categoria
              <select
                aria-label="Categoria del descuento"
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

            <PosFieldLabel helper="Motivo operativo o referencia que justifica el descuento." required>
              Motivo o referencia
              <input
                aria-label="Motivo o referencia del descuento"
                className={cn(
                  posInputClass,
                  "mt-1 h-11 w-full rounded-[var(--pos-radius-control)] px-3 text-sm",
                )}
                onChange={(event) => onConceptChange(event.target.value)}
                placeholder="Prestamo interno abril"
                value={draft.concept}
              />
            </PosFieldLabel>

            <PosFieldLabel helper="Monto total del descuento." required>
              Monto
              <input
                aria-label="Monto del descuento"
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
              <PosFieldLabel helper="Selecciona como se registro el descuento." required>
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
                aria-label="Notas del descuento"
                className={cn(
                  posInputClass,
                  "mt-1 min-h-[7.5rem] w-full rounded-[var(--pos-radius-control)] px-3 py-2.5 text-sm",
                )}
                onChange={(event) => onNotesChange(event.target.value)}
                placeholder="Detalle adicional del descuento o evidencia textual."
                value={draft.notes}
              />
            </PosFieldLabel>

            {isHighValue ? (
              <label className="grid gap-2 rounded-[var(--pos-radius-control)] border border-[var(--ui-color-warning)] bg-amber-50 px-3 py-3 text-sm text-slate-700 md:col-span-2">
                <span className="font-medium text-slate-950">
                  Descuento alto. Confirma que ya validaste el monto antes de registrar.
                </span>
                <span className="flex items-center gap-2">
                  <input
                    checked={draft.highValueAcknowledged}
                    className="h-4 w-4 rounded border-slate-300 text-[var(--pos-primary)] focus:ring-[var(--pos-ring)]"
                    onChange={(event) => onHighValueAcknowledgedChange(event.target.checked)}
                    type="checkbox"
                  />
                  Confirmo el descuento de alto valor.
                </span>
              </label>
            ) : null}
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

function DiscountDetailSummary({
  discount,
}: {
  discount: OperationalDiscountDetailResponse;
}) {
  return (
    <div className="grid gap-3">
      <div className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3">
        <p className="pos-label-text">Monto</p>
        <p className="mt-1 text-[1.75rem] font-semibold leading-tight text-slate-950 [font-variant-numeric:tabular-nums]">
          {formatCurrency(discount.total_amount)}
        </p>
      </div>

      <div className="grid gap-2 text-sm text-slate-700">
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Motivo o referencia</span>
          <p className="font-semibold text-slate-950">{discount.concept}</p>
        </div>
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Persona o entidad</span>
          <p className="font-semibold text-slate-950">{discount.subject_name}</p>
        </div>
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Categoria</span>
          <p className="font-semibold text-slate-950">{discount.category_name ?? "Sin categoria"}</p>
        </div>
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Metodo e impacto</span>
          <p className="font-semibold text-slate-950">
            {getOperationalDiscountMethodLabel(discount.payment_method_code)} ·{" "}
            {getImpactTitle(discount.affects_cash_drawer)}
          </p>
        </div>
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Operador</span>
          <p className="font-semibold text-slate-950">{discount.created_by.full_name}</p>
          <p className="text-xs text-slate-500">
            {formatLocalDateTime(discount.committed_at_utc, discount.branch.timezone)}
          </p>
        </div>
        <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
          <span className="pos-label-text">Sucursal y estacion</span>
          <p className="font-semibold text-slate-950">
            {discount.branch.name} · {discount.workstation.name}
          </p>
        </div>
        {discount.notes ? (
          <div className="grid gap-1 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
            <span className="pos-label-text">Notas</span>
            <p className="whitespace-pre-wrap text-slate-700">{discount.notes}</p>
          </div>
        ) : null}
      </div>

      <PosAuditSummary
        auditSummary={discount.audit_summary}
        timeZone={discount.branch.timezone}
      />
    </div>
  );
}

export function DiscountsRightPanel({
  blockedMessages,
  blockedReason,
  categories,
  controls,
  createError,
  draft,
  isCreateHighValue,
  isConfirmPending,
  isDetailPending,
  mode,
  onCancelCreate,
  onCommitCreate,
  onResultAction,
  discountDetail,
  recentCreatedDiscountId,
}: {
  blockedMessages: string[];
  blockedReason: string | null;
  categories: OperationalDiscountCategoryView[];
  controls: DiscountControlsView | null;
  createError: string | null;
  draft: OperationalDiscountDraftState;
  isCreateHighValue: boolean;
  isConfirmPending: boolean;
  isDetailPending: boolean;
  mode: DiscountsMode;
  onCancelCreate: () => void;
  onCommitCreate: () => void;
  onResultAction: (actionKey: string) => void;
  discountDetail: OperationalDiscountDetailResponse | null;
  recentCreatedDiscountId: string | null;
}) {
  if (mode === "create") {
    const draftCategoryLabel = getCategoryLabel(draft.categoryCode, categories);
    const amountLabel = getDraftAmountLabel(draft.totalAmountText);

    return (
      <PosSummaryPanel
        description="Resume el descuento antes de registrarlo."
        stateLabel="Captura activa"
        stateTone="draft"
        title="Nuevo descuento"
        footer={
          <div className="grid gap-2">
            <PosButton disabled={isConfirmPending} onClick={onCancelCreate} variant="neutral">
              Cancelar
            </PosButton>
            <PosButton disabled={isConfirmPending} onClick={onCommitCreate}>
              {isConfirmPending ? "Guardando..." : "Guardar descuento"}
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
              <span className="pos-label-text">Persona o entidad</span>
              <p className="font-semibold text-slate-950">
                {draft.subjectName.trim().length > 0 ? draft.subjectName.trim() : "Pendiente"}
              </p>
            </div>
            <div className="rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-2.5">
              <span className="pos-label-text">Motivo o referencia</span>
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
                  ? getOperationalDiscountMethodLabel(draft.paymentMethodCode)
                  : "Pendiente"}
              </p>
            </div>
          </div>

          {isCreateHighValue ? (
            <PosInlineValidationMessage tone="warning">
              Este descuento supera{" "}
              {formatCurrency(controls?.high_value_amount_threshold ?? "0")} y requiere
              confirmacion explicita.
            </PosInlineValidationMessage>
          ) : null}

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
        description="Recuperando el descuento seleccionado."
        stateLabel="Cargando"
        stateTone="pending"
        title="Descuento seleccionado"
      >
        <PosLoadingState
          description="Consultando el resumen operativo del descuento."
          title="Cargando descuento"
        />
      </PosSummaryPanel>
    );
  }

  if (!discountDetail) {
    return (
      <PosSummaryPanel
        description="El panel derecho muestra el resumen operativo y el resultado del registro."
        stateLabel="Sin seleccion"
        stateTone="draft"
        title="Selecciona un descuento"
      >
        <PosEmptyState
          description="Selecciona un descuento para revisar su contexto operativo o crea uno nuevo para registrar una salida auditada."
          title="Sin descuento seleccionado"
        />
      </PosSummaryPanel>
    );
  }

  if (discountDetail.id === recentCreatedDiscountId) {
    const resultMessage = createOperationResultMessage({
      description: `Motivo o referencia ${discountDetail.concept}. Usa el historial para seguir auditando el turno o registra un nuevo descuento.`,
      nextActions: [createToastAction("viewHistory"), createToastAction("newOperation")],
      operationType: "discount",
      referenceId: discountDetail.folio,
    });

    return (
      <div className="grid gap-3">
        <PosOperationResultPanel message={resultMessage} onSelectAction={onResultAction} />
        <PosAuditSummary
          auditSummary={discountDetail.audit_summary}
          timeZone={discountDetail.branch.timezone}
        />
      </div>
    );
  }

  return (
    <PosSummaryPanel
      description={formatLocalDateTime(discountDetail.committed_at_utc, discountDetail.branch.timezone)}
      stateLabel={discountDetail.affects_cash_drawer ? "Afecta caja" : "Auditado"}
      stateTone={discountDetail.affects_cash_drawer ? "warning" : "confirmed"}
      title={discountDetail.folio}
      footer={
        <div className="grid gap-2">
          <PosButton onClick={() => onResultAction("newOperation")}>Nuevo descuento</PosButton>
        </div>
      }
    >
      <ScrollPane className="grid gap-3">
        <DiscountDetailSummary discount={discountDetail} />
      </ScrollPane>
    </PosSummaryPanel>
  );
}

export function DiscountsScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const queryClient = useQueryClient();
  const searchInputRef = useRef<HTMLInputElement>(null);

  const discountsBootstrapQuery = useDiscountsBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const [mode, setMode] = useState<DiscountsMode>("list");
  const [selectedScope, setSelectedScope] = useState("CURRENT_SHIFT");
  const [searchText, setSearchText] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedMethodFilter, setSelectedMethodFilter] = useState("");
  const [selectedCreatedByUserId, setSelectedCreatedByUserId] = useState("");
  const [selectedDiscountId, setSelectedDiscountId] = useState<string | null>(null);
  const [draftState, setDraftState] = useState<OperationalDiscountDraftState>(
    createInitialOperationalDiscountDraftState(),
  );
  const [createError, setCreateError] = useState<string | null>(null);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [recentCreatedDiscountId, setRecentCreatedDiscountId] = useState<string | null>(null);

  const debouncedSearchText = useDebouncedValue(searchText, 220);
  const discountsListQuery = useDiscountsListQuery(
    selectedScope,
    debouncedSearchText,
    selectedCategory,
    selectedMethodFilter,
    selectedCreatedByUserId,
  );
  const discountDetailQuery = useDiscountDetailQuery(mode === "list" ? selectedDiscountId : null);

  const bootstrapData = discountsBootstrapQuery.data;
  const discountControls = bootstrapData?.discount_controls ?? null;
  const methods = useMemo(
    () => bootstrapData?.active_discount_methods ?? [],
    [bootstrapData?.active_discount_methods],
  );
  const categories = useMemo(
    () => bootstrapData?.active_categories ?? [],
    [bootstrapData?.active_categories],
  );
  const scopes = useMemo(
    () => bootstrapData?.available_scopes ?? [],
    [bootstrapData?.available_scopes],
  );
  const discountsResponse = discountsListQuery.data;
  const discounts = useMemo(
    () => discountsResponse?.discounts ?? [],
    [discountsResponse?.discounts],
  );
  const availableUsers = useMemo(
    () => discountsResponse?.available_users ?? [],
    [discountsResponse?.available_users],
  );
  const selectedDiscount = discountDetailQuery.data ?? null;
  const selectedMethod = getOperationalDiscountMethod(draftState.paymentMethodCode, methods);
  const affectsCash = doesOperationalDiscountAffectCashDrawer(draftState.paymentMethodCode, methods);
  const createBlockedMessages = getOperationalDiscountBlockingMessages(
    draftState,
    methods,
    categories,
    discountControls,
  );
  const createBlockedReason = getOperationalDiscountBlockedReason(
    draftState,
    methods,
    categories,
    discountControls,
  );
  const isCreateHighValue = isOperationalDiscountHighValue(draftState, discountControls);
  const captureUiState = getOperationalDiscountUiState({
    categories,
    controls: discountControls,
    draft: draftState,
    hasCommitError: createError !== null,
    hasConfirmedDraft: false,
    hasSelectedDiscount: false,
    isCaptureActive: true,
    isCommitPending: false,
    methods,
  });
  const canCommitDraft = canCommitOperationalDiscountDraft(
    draftState,
    methods,
    categories,
    discountControls,
  );
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
    if (mode !== "list" || selectedDiscountId === null) {
      return;
    }

    if (discounts.some((discount) => discount.id === selectedDiscountId)) {
      return;
    }

    setSelectedDiscountId(null);
  }, [mode, discounts, selectedDiscountId]);

  useEffect(() => {
    setCreateError(null);
  }, [
    draftState.categoryCode,
    draftState.concept,
    draftState.notes,
    draftState.subjectName,
    draftState.paymentMethodCode,
    draftState.totalAmountText,
    draftState.highValueAcknowledged,
  ]);

  const handleOpenCreate = useCallback(() => {
    setMode("create");
    setDraftState(createInitialOperationalDiscountDraftState());
    setCreateError(null);
    setIsConfirmDialogOpen(false);
  }, []);

  const handleCancelCreate = useCallback(() => {
    setMode("list");
    setDraftState(createInitialOperationalDiscountDraftState());
    setCreateError(null);
    setIsConfirmDialogOpen(false);
  }, []);

  const createDiscountMutation = useMutation({
    mutationFn: async () => {
      if (!accessToken) {
        throw new Error("Necesitas iniciar sesion antes de registrar un descuento.");
      }

      return createDiscount({
        accessToken,
        payload: buildCreateOperationalDiscountRequest(
          appEnv.VITE_POS_WORKSTATION_CODE,
          draftState,
          methods,
          categories,
          discountControls,
        ),
        requestId: createRequestId("operational-discount"),
      });
    },
    onSuccess: async (result) => {
      setMode("list");
      setSelectedScope(defaultScope);
      setSearchText("");
      setSelectedCategory("");
      setSelectedMethodFilter("");
      setSelectedCreatedByUserId("");
      setSelectedDiscountId(result.id);
      setRecentCreatedDiscountId(result.id);
      setDraftState(createInitialOperationalDiscountDraftState());
      setCreateError(null);
      setIsConfirmDialogOpen(false);
      showSuccess(`Descuento ${result.folio} registrado por ${formatCurrency(result.total_amount)}.`);

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: discountsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: ["discounts-list", appEnv.VITE_POS_WORKSTATION_CODE],
        }),
        queryClient.invalidateQueries({
          queryKey: discountDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, result.id),
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
      const message = toOperationalErrorMessage(error, "No fue posible registrar el descuento.");
      setCreateError(message);
      setIsConfirmDialogOpen(false);
      showError(message);
    },
  });
  const commitDiscountAsync = createDiscountMutation.mutateAsync;
  const isCreateDiscountPending = createDiscountMutation.isPending;

  const handleCommit = useCallback(() => {
    if (!canCommitDraft) {
      return;
    }

    setIsConfirmDialogOpen(true);
  }, [canCommitDraft]);

  const keyboardShortcuts = useMemo(
    () => [
      {
        chords: ["Ctrl+N", "Meta+N"],
        description: "Abre una nueva captura de descuento operativo.",
        group: "Descuentos",
        handler: () => {
          if (mode === "list") {
            handleOpenCreate();
          }
        },
        id: "discounts-new",
        label: "Nuevo descuento",
        priority: 120,
      },
      {
        chords: ["Escape"],
        description:
          mode === "create"
            ? "Cancela la captura actual o cierra la confirmacion."
            : "Limpia la seleccion actual del descuento.",
        group: "Descuentos",
        handler: () => {
          if (isConfirmDialogOpen) {
            setIsConfirmDialogOpen(false);
            return;
          }

          if (mode === "create") {
            handleCancelCreate();
            return;
          }

          if (selectedDiscountId !== null) {
            setSelectedDiscountId(null);
          }
        },
        id: "discounts-escape",
        label: "Cancelar flujo activo",
        priority: 110,
      },
      {
        chords: ["Enter", "NumpadEnter"],
        description: "Guarda el descuento actual cuando la captura ya esta completa.",
        group: "Descuentos",
        handler: () => {
          if (mode !== "create" || isConfirmDialogOpen || !canCommitDraft) {
            return;
          }

          handleCommit();
        },
        id: "discounts-submit",
        isEnabled: () => mode === "create" && canCommitDraft,
        label: "Guardar descuento",
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
      selectedDiscountId,
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
    <DiscountsRightPanel
      blockedMessages={createBlockedMessages}
      blockedReason={createBlockedReason}
      categories={categories}
      controls={discountControls}
      createError={createError}
      draft={draftState}
      isCreateHighValue={isCreateHighValue}
      isConfirmPending={isCreateDiscountPending}
      isDetailPending={selectedDiscountId !== null && discountDetailQuery.isPending}
      mode={mode}
      onCancelCreate={handleCancelCreate}
      onCommitCreate={handleCommit}
      onResultAction={(actionKey) => {
        if (actionKey === "viewHistory") {
          setRecentCreatedDiscountId(null);
          return;
        }

        if (actionKey === "newOperation") {
          handleOpenCreate();
        }
      }}
      discountDetail={selectedDiscount}
      recentCreatedDiscountId={recentCreatedDiscountId}
    />,
  );

  const isBootstrapPending = discountsBootstrapQuery.isPending || currentCashSessionQuery.isPending;

  if (isBootstrapPending) {
    return (
      <OperationalStatus
        description="Consultando la caja activa y el contexto operativo."
        title="Cargando descuentos"
      />
    );
  }

  if (discountsBootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<PosButton onClick={() => discountsBootstrapQuery.refetch()}>Reintentar</PosButton>}
        description={toOperationalErrorMessage(
          discountsBootstrapQuery.error,
          "Confirma la configuracion de la estacion y el contexto operativo.",
        )}
        title="No fue posible cargar Descuentos"
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

  const listColumns: PosRecordColumn<OperationalDiscountListItemView>[] = [
    {
      header: "Folio",
      key: "folio",
      renderCell: (discount) => (
        <div className="grid gap-1">
          <PosRecordMeta
            reference={discount.folio}
            status={discount.affects_cash_drawer ? "Afecta caja" : "Auditado"}
            statusTone={discount.affects_cash_drawer ? "warning" : "confirmed"}
            timeZone={bootstrapData!.branch.timezone}
            timestamp={discount.created_at_utc}
          />
          <p className="truncate text-xs text-slate-500">{discount.concept}</p>
        </div>
      ),
      width: "18%",
    },
    {
      header: "Persona o entidad",
      key: "subject",
      renderCell: (discount) => (
        <div className="grid gap-1">
          <p className="truncate font-semibold text-slate-950">{discount.subject_name}</p>
          <p className="truncate text-xs text-slate-500">
            {discount.operator_full_name} · {discount.workstation_name}
          </p>
        </div>
      ),
      width: "24%",
    },
    {
      header: "Categoria",
      key: "category",
      renderCell: (discount) => discount.category_name ?? "Sin categoria",
      width: "18%",
    },
    {
      header: "Metodo",
      key: "method",
      renderCell: (discount) => getOperationalDiscountMethodLabel(discount.payment_method_code),
      width: "12%",
    },
    {
      header: "Fecha",
      key: "date",
      renderCell: (discount) =>
        formatCompactLocalDateTime(discount.created_at_utc, bootstrapData!.branch.timezone),
      width: "16%",
    },
    {
      align: "right",
      header: "Monto",
      key: "amount",
      renderCell: (discount) => formatCurrency(discount.total_amount),
      width: "12%",
    },
  ];

  const confirmationTitle = affectsCash
    ? "Confirmar descuento con impacto en caja"
    : "Confirmar descuento auditado";
  const confirmationDescription = affectsCash
    ? `Registraras ${getDraftAmountLabel(draftState.totalAmountText)} para ${draftState.subjectName.trim() || "esta persona o entidad"}. Este descuento aumentara el efectivo esperado del turno.`
    : `Registraras ${getDraftAmountLabel(draftState.totalAmountText)} para ${draftState.subjectName.trim() || "esta persona o entidad"}. El movimiento quedara auditado sin mover el efectivo esperado de la caja.`;

  return (
    <>
      <PosConfirmationDialog
        confirmation={posMessageCatalog.confirmation.warningOperation(
          confirmationTitle,
          confirmationDescription,
          "Confirmar descuento",
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
        isPending={isCreateDiscountPending}
        onCancel={() => setIsConfirmDialogOpen(false)}
        onConfirm={() => {
          void commitDiscountAsync();
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
                  : selectedDiscountId
                    ? "Descuento en vista"
                    : "Sin seleccion"}
              </ModuleStateChip>
            }
            title="Descuentos operativos"
          >
            <FlowGuide
              activeStepKey={
                mode === "create"
                  ? getOperationalDiscountCreateStepKey(draftState, methods, categories)
                  : selectedDiscountId === null
                    ? "list"
                    : "detail"
              }
              steps={
                mode === "create"
                  ? [...DISCOUNT_CREATE_GUIDE_STEPS]
                  : [
                      {
                        key: "list",
                        label: "Consulta",
                        state: selectedDiscountId ? "completed" : "current",
                      },
                      {
                        key: "detail",
                        label: "Detalle",
                        state: selectedDiscountId ? "current" : "upcoming",
                      },
                    ]
              }
              variant={mode === "create" ? "process" : "compact"}
            />
          </CompactPageHeader>
        }
      >
        {mode === "create" ? (
          <DiscountCaptureWorkspace
            categories={categories}
            controls={discountControls}
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
            onHighValueAcknowledgedChange={(value) =>
              setDraftState((current) => ({
                ...current,
                highValueAcknowledged: value,
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
            onSubjectChange={(value) =>
              setDraftState((current) => ({
                ...current,
                subjectName: value,
              }))
            }
            onSubmit={handleCommit}
            onTotalAmountChange={(value) =>
              setDraftState((current) => ({
                ...current,
                totalAmountText: sanitizeOperationalDiscountAmountInput(value),
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
                  Nuevo descuento
                </PosButton>
              }
              chipFilters={(scopes.length > 0
                ? scopes
                : [{ code: "CURRENT_SHIFT", label: "Turno actual" }]
              ).map((scope: OperationalDiscountScopeView) => ({
                isActive: selectedScope === scope.code,
                key: scope.code,
                label: scope.label,
                onSelect: () => setSelectedScope(scope.code),
              }))}
              countLabel={<PosStatusBadge status="draft">{discounts.length} descuentos</PosStatusBadge>}
              searchInput={{
                ariaLabel: "Buscar descuento por folio, persona o entidad, categoria o referencia",
                hotkeyChords: ["Ctrl+F"],
                inputRef: searchInputRef,
                onChange: setSearchText,
                placeholder: "Buscar por folio, persona o entidad, categoria o referencia",
                value: searchText,
              }}
              selectFilters={[
                {
                  ariaLabel: "Filtrar descuentos por categoria",
                  key: "category",
                  onChange: setSelectedCategory,
                  options: getCategoryFilterOptions(categories),
                  value: selectedCategory,
                },
                {
                  ariaLabel: "Filtrar descuentos por metodo",
                  key: "method",
                  onChange: setSelectedMethodFilter,
                  options: getMethodFilterOptions(methods),
                  value: selectedMethodFilter,
                },
                {
                  ariaLabel: "Filtrar descuentos por operador",
                  key: "user",
                  onChange: setSelectedCreatedByUserId,
                  options: getUserFilterOptions(availableUsers),
                  value: selectedCreatedByUserId,
                },
              ]}
              title="Descuentos registrados"
            />

            {discountsListQuery.error ? (
              <PosErrorState
                description={toOperationalErrorMessage(
                  discountsListQuery.error,
                  "No fue posible consultar los descuentos operativos de la estacion.",
                )}
                title="La lista no esta disponible"
              />
            ) : discountsListQuery.isPending && !discountsResponse ? (
              <PosLoadingState
                description="Recuperando los descuentos operativos del alcance actual."
                title="Cargando descuentos"
              />
            ) : (
              <PosRecordTable
                columns={listColumns}
                emptyAction={
                  <PosButton
                    leadingIcon={<PlusIcon className="h-4 w-4" />}
                    onClick={handleOpenCreate}
                  >
                    Nuevo descuento
                  </PosButton>
                }
                emptyDescription={getEmptyListDescription(
                  getScopeContextLabel(selectedScope),
                  searchText,
                )}
                emptyTitle="Sin descuentos para esta vista"
                getKey={(discount) => discount.id}
                getRowActions={(discount) => [
                  {
                    key: `${discount.id}-copy-folio`,
                    label: "Copiar folio",
                    onSelect: () => {
                      void copyDocumentReferenceToClipboard(discount.folio)
                        .then(() => showSuccess("Folio copiado."))
                        .catch(() => showError("No se pudo copiar el folio."));
                    },
                  },
                ]}
                loading={discountsListQuery.isPending}
                loadingTitle="Cargando descuentos"
                onSelect={(discount) => {
                  setSelectedDiscountId(discount.id);
                  setRecentCreatedDiscountId((current) =>
                    current === discount.id ? current : null,
                  );
                }}
                records={discounts}
                selectedKey={selectedDiscountId}
                tableAriaLabel="Tabla de descuentos operativos"
              />
            )}
          </div>
        )}
      </CentralWorkspaceSheet>
    </>
  );
}




