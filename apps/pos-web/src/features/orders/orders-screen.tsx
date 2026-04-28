import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import {
  DialogBody,
  DialogFooter,
  DialogHeader,
  DialogSurface,
} from "@zeromerma/ui";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import { CatalogSelectionCard } from "../../components/catalog-selection-card";
import { CatalogVisual } from "../../components/catalog-visual";
import { OperationalStatus } from "../../components/operational-status";
import {
  PosEmptyState,
  PosErrorState,
  PosInlineValidationMessage,
  PosLoadingState,
} from "../../components/pos-feedback";
import { PosButton } from "../../components/pos-foundations";
import {
  PosPaymentInputCard,
  PosPaymentMethodButton as SharedPosPaymentMethodButton,
  PosPaymentValueCard,
} from "../../components/pos-payment-controls";
import { PosFilterBar, PosRecordList } from "../../components/pos-records";
import {
  ContinuousWorkspaceSheet,
  FlowGuide,
  InlineNotice,
  ListDetailColumn,
  ResponsivePaneLayout,
  ModuleStateChip,
  OperationalField,
  KeyValueGroup,
  KeyValueRow,
  CompactPageHeader,
  SearchField,
  ScrollPane,
} from "../../components/pos-module-primitives";
import {
  BagIcon,
  ArrowLeftIcon,
  CardIcon,
  CheckCircleIcon,
  ClockIcon,
  ClipboardIcon,
  HashIcon,
  MoneyIcon,
  OperatorIcon,
  PackageIcon,
  PlusIcon,
  ReceiptIcon,
  SplitIcon,
  TrashIcon,
  XIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import { appEnv } from "../../env";
import type {
  CancelCustomerOrderRequest,
  CreateCustomerOrderRequest,
  CustomerOrderDetailResponse,
  CustomerOrderListItemView,
  OrderActionRequest,
  OrderStatusCounterView,
} from "../../lib/api-contracts";
import { formatCurrency, formatLocalDateTime } from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import {
  getSelectionShortcutIndex,
  getSelectionShortcutLabel,
  isEditableTarget,
} from "../../lib/keyboard-shortcuts";
import { getCustomerCommunicationActionState } from "../../lib/customer-communication";
import { cn } from "../../lib/utils";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import {
  CARD_PAYMENT_METHOD_CODE,
  CASH_PAYMENT_METHOD_CODE,
  formatMoneyFromCents,
  MIXED_PAYMENT_METHOD_CODE,
  parseMoneyToCents,
  parseQuantityToMilliUnits,
  sanitizeMoneyInput,
} from "../pos-terminal/model";
import { posInputClass, posOutlineButtonClass, posPrimaryButtonClass } from "../pos-theme/theme";
import { useStatusMessageStore } from "../status-messages/store";
import { cancelOrder, createOrder, deliverOrder, markOrderReady } from "./orders-api";
import {
  addPendingSelectionLine,
  buildDeliverOrderSettlementPayments,
  buildCreateOrderAdvancePayments,
  buildCreateOrderItems,
  CONTROL_STATE_CLASS_SELECTION,
  CONTROL_STATE_PRODUCT_SELECTION,
  CONTROL_STATE_QUANTITY_CAPTURE,
  createInitialOrderCreateDraftState,
  getOrderAdvanceAmountCents,
  getOrderCreateBlockingMessage,
  getOrderCreateChecklistMessages,
  getOrderCreateUiState,
  getOrderLineCount,
  getOrderLineTotalCents,
  getOrderSubtotalCents,
  getRemainingBalanceCents,
  goBackFromOrderControlState,
  removeOrderLine,
  selectClassForOrder,
  selectProductForOrder,
  setPendingQuantityText,
  sortOrdersCatalogClasses,
  sortOrdersCatalogProducts,
  updateOrderLineQuantity,
} from "./model";
import {
  orderDetailQueryKey,
  ordersBootstrapQueryKey,
  useOrderDetailQuery,
  useOrdersBootstrapQuery,
  useOrdersCatalogQuery,
  useOrdersClassProductsQuery,
  useOrdersListQuery,
} from "./queries";

type OrdersMode = "list" | "create";

interface CancelableOrderSummary {
  advance_amount: string;
  cancellation_refund_amount: string;
  cancellation_refund_eligible: boolean;
  customer_name: string;
  folio: string;
  id: string;
  status: string;
}

interface RequestedForDraftState {
  date: string;
  hour: string;
  minute: string;
}

const ORDER_STATUS_OPTIONS = [
  { label: "Pendientes", status: "PENDING" },
  { label: "Listos para entrega", status: "READY" },
  { label: "Entregados", status: "DELIVERED" },
  { label: "Cancelados", status: "CANCELED" },
] as const;

const PAYMENT_METHOD_OPTIONS = [
  { label: "Efectivo", value: CASH_PAYMENT_METHOD_CODE },
  { label: "Tarjeta", value: CARD_PAYMENT_METHOD_CODE },
  { label: "Mixto", value: MIXED_PAYMENT_METHOD_CODE },
] as const;

const PICKUP_HOUR_MIN = 0;
const PICKUP_HOUR_MAX = 23;
const PICKUP_MINUTE_MIN = 0;
const PICKUP_MINUTE_MAX = 30;
const PICKUP_MINUTE_STEP = 30;
const ORDER_CREATE_GUIDE_STEPS: Array<{
  icon: ReactNode;
  label: string;
  key: string;
}> = [
  { icon: <ClipboardIcon className="h-4 w-4" />, key: "details", label: "Datos" },
  { icon: <PackageIcon className="h-4 w-4" />, key: "products", label: "Productos" },
  { icon: <MoneyIcon className="h-4 w-4" />, key: "summary", label: "Resumen" },
];

type OrderActionDialogState =
  | { kind: "discard" }
  | { kind: "cancel"; order: CancelableOrderSummary };

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

function roundDateToPickupSlot(date: Date): Date {
  const rounded = new Date(date);
  rounded.setSeconds(0, 0);

  const minutes = rounded.getMinutes();
  if (minutes === 0 || minutes === 30) {
    return rounded;
  }

  if (minutes < 30) {
    rounded.setMinutes(30, 0, 0);
    return rounded;
  }

  rounded.setHours(rounded.getHours() + 1, 0, 0, 0);
  return rounded;
}

function createInitialRequestedForDraftState(
  referenceTimestamp?: string | null,
): RequestedForDraftState {
  const referenceDate = referenceTimestamp ? new Date(referenceTimestamp) : new Date();
  const safeReference = Number.isNaN(referenceDate.getTime()) ? new Date() : referenceDate;
  const roundedReference = roundDateToPickupSlot(safeReference);

  return {
    date: "",
    hour: roundedReference.getHours().toString().padStart(2, "0"),
    minute: roundedReference.getMinutes() >= 30 ? "30" : "00",
  };
}

function buildRequestedForInput(requestedForDraft: RequestedForDraftState): string {
  if (requestedForDraft.date.trim().length === 0) {
    return "";
  }

  const hourValue = parsePickupHourInput(requestedForDraft.hour);
  const minuteValue = parsePickupMinuteInput(requestedForDraft.minute);
  if (hourValue === null || minuteValue === null) {
    return "";
  }

  return `${requestedForDraft.date}T${hourValue.toString().padStart(2, "0")}:${minuteValue.toString().padStart(2, "0")}`;
}

function sanitizePickupNumericInput(value: string): string {
  return value.replace(/\D/g, "").slice(0, 2);
}

function parsePickupHourInput(value: string): number | null {
  const sanitizedValue = sanitizePickupNumericInput(value);
  if (sanitizedValue.length === 0) {
    return null;
  }

  const numericValue = Number.parseInt(sanitizedValue, 10);
  if (Number.isNaN(numericValue) || numericValue < PICKUP_HOUR_MIN || numericValue > PICKUP_HOUR_MAX) {
    return null;
  }

  return numericValue;
}

function parsePickupMinuteInput(value: string): number | null {
  const sanitizedValue = sanitizePickupNumericInput(value);
  if (sanitizedValue.length === 0) {
    return null;
  }

  if (sanitizedValue === "0" || sanitizedValue === "00") {
    return 0;
  }

  if (sanitizedValue === "3" || sanitizedValue === "30") {
    return 30;
  }

  return null;
}

function finalizePickupHourInput(value: string, fallback: string): string {
  const parsedValue = parsePickupHourInput(value);
  if (parsedValue === null) {
    return fallback;
  }

  return parsedValue.toString().padStart(2, "0");
}

function finalizePickupMinuteInput(value: string, fallback: string): string {
  const sanitizedValue = sanitizePickupNumericInput(value);
  if (sanitizedValue.length === 0) {
    return fallback;
  }

  if (sanitizedValue === "0" || sanitizedValue === "00") {
    return "00";
  }

  if (sanitizedValue === "3" || sanitizedValue === "30") {
    return "30";
  }

  const numericValue = Number.parseInt(sanitizedValue, 10);
  if (Number.isNaN(numericValue)) {
    return fallback;
  }

  return numericValue >= 15 ? "30" : "00";
}

function stepPickupHourInput(value: string, delta: number): string {
  const currentValue = parsePickupHourInput(value) ?? PICKUP_HOUR_MIN;
  const nextValue = Math.min(PICKUP_HOUR_MAX, Math.max(PICKUP_HOUR_MIN, currentValue + delta));
  return nextValue.toString().padStart(2, "0");
}

function stepPickupMinuteInput(value: string, delta: number): string {
  const currentValue = parsePickupMinuteInput(value) ?? PICKUP_MINUTE_MIN;
  const nextValue = Math.min(
    PICKUP_MINUTE_MAX,
    Math.max(PICKUP_MINUTE_MIN, currentValue + delta * PICKUP_MINUTE_STEP),
  );
  return nextValue.toString().padStart(2, "0");
}

function getOrderGuidedFieldClass({
  isActive,
  isLocked = false,
}: {
  isActive: boolean;
  isLocked?: boolean;
}): string {
  return cn(
    "rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-2.5 transition focus-within:border-[var(--pos-primary)] focus-within:bg-white focus-within:shadow-sm",
    isActive &&
      "border-[var(--pos-primary)] bg-white shadow-[0_0_0_2px_var(--pos-primary-soft)]",
    isLocked && "opacity-75",
  );
}

function getOrderGuidedSectionClass(isActive: boolean, isLocked: boolean): string {
  return cn(
    "pos-tonal-surface grid min-h-0 overflow-hidden p-3 lg:grid-rows-[auto_minmax(0,1fr)]",
    isActive && "border-[var(--pos-primary)] shadow-[0_0_0_2px_var(--pos-primary-soft)]",
    isLocked && "bg-[var(--pos-shell-muted)]/90",
  );
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "PENDING":
      return "Pendiente";
    case "READY":
      return "Listo para entrega";
    case "DELIVERED":
      return "Entregado";
    case "CANCELED":
      return "Cancelado";
    default:
      return status;
  }
}

function getStatusVisualConfig(status: string) {
  switch (status) {
    case "READY":
      return {
        badgeClass:
          "border border-[var(--ui-color-info-soft)] bg-[var(--ui-color-info-soft)] text-[var(--ui-color-info)]",
        chipClass:
          "border-[var(--ui-color-info-soft)] bg-[var(--ui-color-info-soft)] text-[var(--ui-color-info)] hover:border-[var(--ui-color-info)]/35 hover:bg-[var(--ui-color-info-soft)]",
        icon: <BagIcon className="h-3.5 w-3.5" />,
        iconClass: "bg-[var(--ui-color-info-soft)] text-[var(--ui-color-info)]",
        rowClass:
          "border-[var(--ui-color-info)]/25 bg-[var(--ui-color-info-soft)]/70 hover:border-[var(--ui-color-info)]/40 hover:bg-[var(--ui-color-info-soft)]",
        selectedRowClass:
          "border-[var(--ui-color-info)]/45 bg-[var(--ui-color-info-soft)] shadow-[0_0_0_1px_rgba(36,95,145,0.12)]",
        rowIconClass:
          "border-[var(--ui-color-info)]/20 bg-white/70 text-[var(--ui-color-info)]",
        summaryPillClass: "bg-white/75 text-[var(--ui-color-info)]",
      };
    case "DELIVERED":
      return {
        badgeClass:
          "border border-[var(--ui-color-success-soft)] bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]",
        chipClass:
          "border-[var(--ui-color-success-soft)] bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)] hover:border-[var(--ui-color-success)]/35 hover:bg-[var(--ui-color-success-soft)]",
        icon: <CheckCircleIcon className="h-3.5 w-3.5" />,
        iconClass: "bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]",
        rowClass:
          "border-[var(--ui-color-success)]/22 bg-[var(--ui-color-success-soft)]/72 hover:border-[var(--ui-color-success)]/38 hover:bg-[var(--ui-color-success-soft)]",
        selectedRowClass:
          "border-[var(--ui-color-success)]/42 bg-[var(--ui-color-success-soft)] shadow-[0_0_0_1px_rgba(18,122,90,0.12)]",
        rowIconClass:
          "border-[var(--ui-color-success)]/18 bg-white/75 text-[var(--ui-color-success)]",
        summaryPillClass: "bg-white/78 text-[var(--ui-color-success)]",
      };
    case "CANCELED":
      return {
        badgeClass:
          "border border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]",
        chipClass:
          "border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)] hover:border-[var(--ui-color-danger)]/35 hover:bg-[var(--ui-color-danger-soft)]",
        icon: <XIcon className="h-3.5 w-3.5" />,
        iconClass: "bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]",
        rowClass:
          "border-[var(--ui-color-danger)]/24 bg-[var(--ui-color-danger-soft)]/72 hover:border-[var(--ui-color-danger)]/40 hover:bg-[var(--ui-color-danger-soft)]",
        selectedRowClass:
          "border-[var(--ui-color-danger)]/44 bg-[var(--ui-color-danger-soft)] shadow-[0_0_0_1px_rgba(180,35,24,0.12)]",
        rowIconClass:
          "border-[var(--ui-color-danger)]/18 bg-white/75 text-[var(--ui-color-danger)]",
        summaryPillClass: "bg-white/78 text-[var(--ui-color-danger)]",
      };
    default:
      return {
        badgeClass:
          "border border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]",
        chipClass:
          "border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)] hover:border-[var(--ui-color-warning)]/35 hover:bg-[var(--ui-color-warning-soft)]",
        icon: <ClockIcon className="h-3.5 w-3.5" />,
        iconClass: "bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]",
        rowClass:
          "border-[var(--ui-color-warning)]/24 bg-[var(--ui-color-warning-soft)]/72 hover:border-[var(--ui-color-warning)]/40 hover:bg-[var(--ui-color-warning-soft)]",
        selectedRowClass:
          "border-[var(--ui-color-warning)]/42 bg-[var(--ui-color-warning-soft)] shadow-[0_0_0_1px_rgba(148,98,0,0.12)]",
        rowIconClass:
          "border-[var(--ui-color-warning)]/18 bg-white/75 text-[var(--ui-color-warning)]",
        summaryPillClass: "bg-white/78 text-[var(--ui-color-warning)]",
      };
  }
}

function getOrderStatusCount(counters: OrderStatusCounterView[], status: string): number {
  return counters.find((entry) => entry.status === status)?.count ?? 0;
}

function getOrderCreateUiLabel(uiState: ReturnType<typeof getOrderCreateUiState>): string {
  switch (uiState) {
    case "DETAILS_PENDING":
      return "Faltan datos";
    case "PRODUCTS_PENDING":
      return "Sin productos";
    case "SUMMARY_PENDING":
      return "Revisa resumen";
    case "READY_TO_SAVE":
      return "Listo para guardar";
    case "SAVING":
      return "Guardando...";
    default:
      return "Borrador";
  }
}

function getOrderCreateUiTone(
  uiState: ReturnType<typeof getOrderCreateUiState>,
): "muted" | "primary" | "success" | "warning" {
  switch (uiState) {
    case "READY_TO_SAVE":
      return "success";
    case "SAVING":
      return "primary";
    case "SUMMARY_PENDING":
      return "warning";
    default:
      return "muted";
  }
}

function formatOrderRequestedForLabel(
  requestedForAt: string | null | undefined,
  timezone: string,
): string {
  return requestedForAt
    ? formatLocalDateTime(requestedForAt, timezone)
    : "Sin hora solicitada";
}

function getDateKeyForTimeZone(date: Date, timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone,
    year: "numeric",
  }).format(date);
}

function getOrderUrgency(order: CustomerOrderListItemView, timezone: string): {
  label: string | null;
  tone: "muted" | "warning" | "primary";
} {
  if (!order.requested_for_at || order.status === "DELIVERED" || order.status === "CANCELED") {
    return { label: null, tone: "muted" };
  }

  const requestedAt = new Date(order.requested_for_at);
  const now = new Date();
  const isToday =
    getDateKeyForTimeZone(requestedAt, timezone) === getDateKeyForTimeZone(now, timezone);

  if (requestedAt.getTime() < now.getTime() && order.status !== "READY") {
    return { label: "Atrasado", tone: "warning" };
  }

  if (order.status === "READY") {
    return { label: "Listo", tone: "primary" };
  }

  if (isToday) {
    return { label: "Hoy", tone: "warning" };
  }

  return { label: null, tone: "muted" };
}

function getOrderEmptyListDescription({
  dateFrom,
  dateTo,
  searchText,
  status,
}: {
  dateFrom: string;
  dateTo: string;
  searchText: string;
  status: string;
}): string {
  if (searchText.trim().length > 0) {
    return "No hay pedidos que coincidan con ese folio, cliente o telefono dentro del filtro actual.";
  }

  if (dateFrom.trim().length > 0 || dateTo.trim().length > 0) {
    return "No hay pedidos programados dentro del rango de fechas seleccionado.";
  }

  switch (status) {
    case "READY":
      return "No hay pedidos listos para entrega en esta vista operativa.";
    case "DELIVERED":
      return "No hay pedidos entregados en esta vista operativa.";
    case "CANCELED":
      return "No hay pedidos cancelados en esta vista operativa.";
    default:
      return "No hay pedidos pendientes para esta consulta.";
  }
}

function StatusBadge({ status }: { status: string }) {
  const config = getStatusVisualConfig(status);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[12px] font-medium",
        config.badgeClass,
      )}
    >
      <span className={cn("rounded-full p-0.5", config.iconClass)}>{config.icon}</span>
      {getStatusLabel(status)}
    </span>
  );
}

function OrderOperationalChip({
  icon,
  label,
  tone,
}: {
  icon?: ReactNode;
  label: string;
  tone: "muted" | "success" | "warning" | "danger" | "info";
}) {
  return (
    <span
      className={cn(
        "inline-flex min-h-9 max-w-full items-center gap-2 rounded-xl border px-2.5 py-1.5 text-sm font-semibold leading-4 shadow-sm",
        tone === "success"
          ? "border-[#9fd3b3] bg-[#e8f8ef] text-[var(--ui-color-success)]"
          : tone === "warning"
            ? "border-[#e4bc67] bg-[#fff1cf] text-[var(--ui-color-warning)]"
            : tone === "danger"
              ? "border-[#e1a0a8] bg-[#fff1f3] text-[var(--ui-color-danger)]"
              : tone === "info"
                ? "border-[#a9c7eb] bg-[#edf5ff] text-[var(--ui-color-info)]"
                : "border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] text-slate-700",
      )}
    >
      {icon ? <span className="flex shrink-0 items-center justify-center">{icon}</span> : null}
      <span className="min-w-0 break-words">{label}</span>
    </span>
  );
}

function CatalogSubflow({
  activeKey,
}: {
  activeKey: "class" | "product" | "quantity";
}) {
  const steps = [
    { key: "class", label: "Clase" },
    { key: "product", label: "Producto" },
    { key: "quantity", label: "Cantidad" },
  ] as const;
  const activeIndex = steps.findIndex((step) => step.key === activeKey);

  return (
    <ol className="flex flex-wrap items-center gap-2" aria-label="Subflujo del catalogo">
      {steps.map((step, index) => {
        const isActive = index === activeIndex;
        const isCompleted = index < activeIndex;

        return (
          <li className="flex items-center gap-2" key={step.key}>
            {index > 0 ? (
              <span
                aria-hidden="true"
                className={cn(
                  "hidden h-px w-3 rounded-full lg:block",
                  isCompleted || isActive ? "bg-[var(--pos-primary)]/35" : "bg-slate-300",
                )}
              />
            ) : null}
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
                isActive
                  ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)] text-[var(--pos-primary)]"
                  : isCompleted
                    ? "border-transparent bg-[var(--pos-primary-soft)]/70 text-[var(--pos-primary)]"
                    : "border-[var(--pos-shell-border)] bg-white text-slate-500",
              )}
            >
              <span
                className={cn(
                  "inline-flex h-4.5 w-4.5 items-center justify-center rounded-full text-[10px]",
                  isActive || isCompleted
                    ? "bg-white text-[var(--pos-primary)]"
                    : "bg-[var(--pos-shell-muted)] text-slate-500",
                )}
              >
                {isCompleted ? <CheckCircleIcon className="h-3 w-3" /> : index + 1}
              </span>
              {step.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function OrderActionConfirmDialog({
  cancelReason,
  cancelReasonError,
  isPending,
  onCancel,
  onCancelReasonChange,
  onConfirm,
  state,
}: {
  cancelReason: string;
  cancelReasonError: string | null;
  isPending: boolean;
  onCancel: () => void;
  onCancelReasonChange: (value: string) => void;
  onConfirm: () => void;
  state: OrderActionDialogState | null;
}) {
  if (state === null) {
    return null;
  }

  const order = "order" in state ? state.order : null;
  const isCancel = state.kind === "cancel";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-4 backdrop-blur-[2px]">
      <DialogSurface className="w-full max-w-md">
        <DialogHeader
          action={
            <Button
              aria-label="Cerrar confirmacion"
              className={cn("h-10 w-10 p-0", posOutlineButtonClass)}
              disabled={isPending}
              onClick={onCancel}
              size="icon"
              type="button"
              variant="outline"
            >
              <XIcon className="h-4 w-4" />
            </Button>
          }
        >
          <div>
            <p className="pos-label-text">{isCancel ? "Confirma la cancelacion" : "Confirma"}</p>
            <h2 className="mt-1 text-lg font-semibold text-slate-950">
              {isCancel ? "Cancelar pedido" : "Descartar borrador"}
            </h2>
          </div>
        </DialogHeader>
        <DialogBody className="grid gap-3">
          {order !== null ? (
            <>
              <div className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3">
                <p className="text-sm font-semibold text-slate-950">{order.folio}</p>
                <p className="mt-1 text-sm text-slate-700">{order.customer_name}</p>
                <p className="mt-1 text-sm text-slate-600">{getStatusLabel(order.status)}</p>
              </div>

              {isCancel ? (
                <div className="grid gap-3">
                  <div className="rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-3 text-sm leading-6 text-slate-700">
                    <p className="font-medium text-slate-950">
                      El pedido se cancelara de forma inmediata.
                    </p>
                    <p className="mt-1">
                      {order.cancellation_refund_eligible
                        ? `Se reembolsara el anticipo de ${formatCurrency(order.cancellation_refund_amount)} y se registrara el movimiento en caja.`
                        : (parseMoneyToCents(order.advance_amount) ?? 0) > 0
                          ? "El anticipo no se reembolsa porque la cancelacion ocurre despues del umbral de un dia previo a la entrega."
                          : "No hay anticipo por devolver."}
                    </p>
                  </div>

                  <label className="grid gap-2">
                    <span className="text-sm font-semibold text-slate-950">
                      Motivo de cancelacion
                    </span>
                    <textarea
                      className={cn(
                        posInputClass,
                        "min-h-[5.5rem] rounded-xl px-3 py-2 text-sm leading-6 shadow-none",
                      )}
                      disabled={isPending}
                      onChange={(event) => onCancelReasonChange(event.target.value)}
                      placeholder="Describe por que se cancela el pedido."
                      value={cancelReason}
                    />
                    <p className="text-xs leading-5 text-slate-500">
                      Este motivo queda registrado en el pedido y en la trazabilidad operativa.
                    </p>
                    {cancelReasonError ? (
                      <PosInlineValidationMessage>
                        {cancelReasonError}
                      </PosInlineValidationMessage>
                    ) : null}
                  </label>
                </div>
              ) : null}
            </>
          ) : (
            <p className="text-sm leading-6 text-slate-700">
              El borrador actual se perdera. Confirmas descartarlo?
            </p>
          )}
        </DialogBody>
        <DialogFooter>
          <Button
            className={cn("h-10 px-4", posOutlineButtonClass)}
            disabled={isPending}
            onClick={onCancel}
            type="button"
            variant="outline"
          >
            Volver
          </Button>
          <Button
            className={cn("h-10 px-4", posPrimaryButtonClass)}
            disabled={isPending || (isCancel && cancelReason.trim().length < 4)}
            onClick={onConfirm}
            type="button"
          >
            {isPending
              ? isCancel
                ? "Cancelando..."
                : "Descartando..."
              : isCancel
                ? "Confirmar cancelacion"
                : "Descartar borrador"}
          </Button>
        </DialogFooter>
      </DialogSurface>
    </div>
  );
}

export function OrderRecordCard({
  isSelected,
  order,
  timezone,
}: {
  isSelected: boolean;
  order: CustomerOrderListItemView;
  timezone: string;
}) {
  const deliveryLabel = formatOrderRequestedForLabel(order.requested_for_at, timezone);
  const urgency = getOrderUrgency(order, timezone);
  const config = getStatusVisualConfig(order.status);
  const hasPhone = Boolean(order.customer_phone && order.customer_phone.trim().length > 0);

  return (
    <div
      className={cn(
        "grid gap-2",
        isSelected ? "text-slate-950" : "text-slate-900",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="pos-label-text">Entrega</p>
          <p className="mt-0.5 truncate text-[1.02rem] font-semibold leading-5 text-slate-950">
            {deliveryLabel}
          </p>
        </div>

        <div className="shrink-0 text-right">
          <p className="pos-label-text">Total</p>
          <p className="mt-0.5 text-[1.05rem] font-semibold leading-5 text-slate-950 [font-variant-numeric:tabular-nums]">
            {formatCurrency(order.total_amount)}
          </p>
        </div>
      </div>

      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          <p className="text-sm font-semibold text-slate-950">{order.folio}</p>
          <StatusBadge status={order.status} />
          {urgency.label ? (
            <span className="pos-chip" data-tone={urgency.tone}>
              {urgency.label}
            </span>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 text-[13px]">
        <div className="flex min-w-0 items-center gap-1.5 text-slate-700">
          <OperatorIcon className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span className="truncate font-medium text-slate-800" title={order.customer_name}>
            {order.customer_name}
          </span>
          {hasPhone ? (
            <span
              className="truncate text-slate-500"
              title={order.customer_phone ?? undefined}
            >
              | {order.customer_phone}
            </span>
          ) : null}
        </div>

        <div className="shrink-0 whitespace-nowrap text-right text-[12px] text-slate-600 [font-variant-numeric:tabular-nums]">
          <span>Ant. {formatCurrency(order.advance_amount)}</span>
          <span className="mx-1 text-slate-400">|</span>
          <span>Fal. {formatCurrency(order.remaining_balance_amount)}</span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 text-xs font-medium text-slate-600">
        <span className={cn("inline-flex items-center gap-1 rounded-full px-1.5 py-0.5", config.summaryPillClass)}>
          <PackageIcon className="h-3.5 w-3.5" />
          {order.line_count} lineas
        </span>
        <span className={cn("inline-flex items-center gap-1 rounded-full px-1.5 py-0.5", config.summaryPillClass)}>
          <HashIcon className="h-3.5 w-3.5" />
          {Number(order.total_units).toFixed(3)} uds
        </span>
        <span className={cn("inline-flex items-center gap-1 rounded-full px-1.5 py-0.5", config.summaryPillClass)}>
          <MoneyIcon className="h-3.5 w-3.5" />
          Saldo {formatCurrency(order.remaining_balance_amount)}
        </span>
      </div>
    </div>
  );
}

function DraftLineRow({
  line,
  onDecrement,
  onIncrement,
  onRemove,
}: {
  line: ReturnType<typeof createInitialOrderCreateDraftState>["lines"][number];
  onDecrement: () => void;
  onIncrement: () => void;
  onRemove: () => void;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto_auto_auto] items-center gap-1 border-t border-[var(--pos-shell-border)] px-2 py-1.5 first:border-t-0">
      <p
        className="truncate pr-1 text-[12px] font-medium leading-4 text-slate-950"
        title={line.productName}
      >
        {line.productName}
      </p>

      <div className="flex items-center gap-0 rounded-md border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-0 py-0.5">
        <button
          className="flex h-6 w-6 items-center justify-center rounded-sm text-[12px] font-medium text-slate-900 hover:bg-white"
          onClick={onDecrement}
          type="button"
        >
          -
        </button>
        <span className="min-w-4 px-0.5 text-center text-[12px] font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
          {line.quantityText}
        </span>
        <button
          className="flex h-6 w-6 items-center justify-center rounded-sm text-[12px] font-medium text-slate-900 hover:bg-white"
          onClick={onIncrement}
          type="button"
        >
          +
        </button>
      </div>

      <span className="min-w-[3.75rem] text-right text-[12px] font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
        {formatCurrency(formatMoneyFromCents(getOrderLineTotalCents(line)))}
      </span>

      <button
        aria-label={`Eliminar ${line.productName}`}
        className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)]"
        onClick={onRemove}
        type="button"
      >
        <TrashIcon className="h-3 w-3" />
      </button>
    </div>
  );
}

function OrderPaymentMethodButton({
  icon,
  isActive,
  label,
  onClick,
}: {
  icon: ReactNode;
  isActive: boolean;
  label: string;
  onClick: () => void;
}) {
  return <SharedPosPaymentMethodButton icon={icon} isActive={isActive} label={label} onClick={onClick} />;
}

function OrderPaymentMetricTile({
  icon,
  label,
  tone,
  value,
}: {
  icon: ReactNode;
  label: string;
  tone: "advance" | "financial" | "pending" | "success";
  value: string;
}) {
  return (
    <PosPaymentValueCard
      icon={icon}
      label={label}
      tone={
        tone === "financial"
          ? "fixed"
          : tone === "advance"
            ? "input"
            : tone === "success"
              ? "success"
              : "pending"
      }
      value={value}
    />
  );
}

function OrdersDecisionPanel({
  bootstrap,
  createChecklistMessages,
  createOrderBlockingMessage,
  createOrderDisabled,
  createUiState,
  deliverySettlementFlowActive,
  deliveryMixedCardAmountText,
  deliveryMixedCashAmountText,
  deliveryPaymentMethodCode,
  deliveryReceivedAmountText,
  draftAdvanceAmountText,
  draftMixedAdvanceCardAmountText,
  draftMixedAdvanceCashAmountText,
  draftAdvancePaymentMethodCode,
  draftCustomerName,
  draftLines,
  draftRequestedForLabel,
  isCreateSaving,
  isSelectedOrderPending,
  mode,
  onCreateOrder,
  onDismissDeliverySettlementFlow,
  onDeliveryPaymentMethodChange,
  onSetDeliveryMixedCardAmountText,
  onSetDeliveryMixedCashAmountText,
  onSetDeliveryReceivedAmountText,
  onDraftLineDecrement,
  onDraftLineIncrement,
  onDraftLineRemove,
  onMarkReady,
  onRequestCancelDraft,
  onRequestCancelOrder,
  onRequestDeliverOrder,
  onSetAdvanceAmountText,
  onSetMixedAdvanceCardAmountText,
  onSetMixedAdvanceCashAmountText,
  onSetAdvancePaymentMethodCode,
  orderDetail,
  orderDetailError,
  orderDetailIsPending,
}: {
  bootstrap: ReturnType<typeof useOrdersBootstrapQuery>["data"];
  createChecklistMessages: string[];
  createOrderBlockingMessage: string | null;
  createOrderDisabled: boolean;
  createUiState: ReturnType<typeof getOrderCreateUiState>;
  deliverySettlementFlowActive: boolean;
  deliveryMixedCardAmountText: string;
  deliveryMixedCashAmountText: string;
  deliveryPaymentMethodCode: string;
  deliveryReceivedAmountText: string;
  draftAdvanceAmountText: string;
  draftMixedAdvanceCardAmountText: string;
  draftMixedAdvanceCashAmountText: string;
  draftAdvancePaymentMethodCode: string;
  draftCustomerName: string;
  draftLines: ReturnType<typeof createInitialOrderCreateDraftState>["lines"];
  draftRequestedForLabel: string;
  isCreateSaving: boolean;
  isSelectedOrderPending: boolean;
  mode: OrdersMode;
  onCreateOrder: () => void;
  onDismissDeliverySettlementFlow: () => void;
  onDeliveryPaymentMethodChange: (value: string) => void;
  onSetDeliveryMixedCardAmountText: (value: string) => void;
  onSetDeliveryMixedCashAmountText: (value: string) => void;
  onSetDeliveryReceivedAmountText: (value: string) => void;
  onDraftLineDecrement: (lineKey: string) => void;
  onDraftLineIncrement: (lineKey: string) => void;
  onDraftLineRemove: (lineKey: string) => void;
  onMarkReady: () => void;
  onRequestCancelDraft: () => void;
  onRequestCancelOrder: () => void;
  onRequestDeliverOrder: () => void;
  onSetAdvanceAmountText: (value: string) => void;
  onSetMixedAdvanceCardAmountText: (value: string) => void;
  onSetMixedAdvanceCashAmountText: (value: string) => void;
  onSetAdvancePaymentMethodCode: (value: string) => void;
  orderDetail: CustomerOrderDetailResponse | null | undefined;
  orderDetailError: unknown;
  orderDetailIsPending: boolean;
}) {
  const advanceInputRef = useRef<HTMLInputElement>(null);
  const deliveryMixedCashInputRef = useRef<HTMLInputElement>(null);
  const deliveryReceivedInputRef = useRef<HTMLInputElement>(null);
  const mixedAdvanceCashInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (mode !== "list" || !deliverySettlementFlowActive) {
      return;
    }

    requestAnimationFrame(() => {
      if (deliveryPaymentMethodCode === MIXED_PAYMENT_METHOD_CODE) {
        deliveryMixedCashInputRef.current?.focus();
        deliveryMixedCashInputRef.current?.select();
        return;
      }

      deliveryReceivedInputRef.current?.focus();
      deliveryReceivedInputRef.current?.select();
    });
  }, [deliveryPaymentMethodCode, deliverySettlementFlowActive, mode]);

  if (!bootstrap) {
    return null;
  }

  if (mode === "create") {
    const subtotalCents = getOrderSubtotalCents(draftLines);
    const advanceCents = getOrderAdvanceAmountCents({
      advanceAmountText: draftAdvanceAmountText,
      mixedCardAmountText: draftMixedAdvanceCardAmountText,
      mixedCashAmountText: draftMixedAdvanceCashAmountText,
      paymentMethodCode: draftAdvancePaymentMethodCode,
    });
    const remainingCents = getRemainingBalanceCents(draftLines, advanceCents);
    const isMixedAdvance = draftAdvancePaymentMethodCode === MIXED_PAYMENT_METHOD_CODE;
    const paymentStateChip =
      subtotalCents > 0 && advanceCents > 0
        ? remainingCents === 0
          ? { label: "Pagado al crear", tone: "success" as const }
          : { label: "Anticipo registrado", tone: "info" as const }
        : null;
    const ensureDefaultAdvanceMethod = () => {
      if (draftAdvancePaymentMethodCode.trim().length === 0) {
        onSetAdvancePaymentMethodCode(CASH_PAYMENT_METHOD_CODE);
      }
    };

    return (
      <div className="pos-shell-panel grid h-full min-h-0 grid-rows-[auto_auto_minmax(0,1fr)_auto] gap-[var(--pos-section-gap)] p-[var(--pos-shell-workstation-padding)]">
        <div className="grid gap-2">
          <div className="flex flex-wrap items-start justify-between gap-2.5">
            <div className="min-w-0">
              <p className="pos-label-text">Pedido</p>
              <h2 className="mt-0.5 text-base font-semibold text-slate-950">
                Pedido en construcción
              </h2>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <span className="pos-chip" data-tone={getOrderCreateUiTone(createUiState)}>
                {getOrderCreateUiLabel(createUiState)}
              </span>
              <span className="pos-chip" data-tone="muted">
                {getOrderLineCount(draftLines)} lineas
              </span>
            </div>
          </div>
          <KeyValueGroup tone="muted">
            <KeyValueRow
              label="Cliente"
              title={draftCustomerName.trim()}
              value={draftCustomerName.trim().length > 0 ? draftCustomerName : "Pendiente"}
            />
            <KeyValueRow
              label="Recoleccion"
              title={draftRequestedForLabel}
              value={draftRequestedForLabel}
            />
          </KeyValueGroup>
        </div>

        <div className="grid gap-2.5">
          <div className="grid gap-3 rounded-xl border border-[var(--pos-shell-border)] bg-white p-3 shadow-[var(--ui-shadow-subtle)]">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--pos-shell-muted)] text-[var(--pos-primary)]">
                  <MoneyIcon className="h-4 w-4" />
                </span>
                <p className="truncate whitespace-nowrap text-[15px] font-semibold leading-5 text-slate-950">
                  Cobro del pedido
                </p>
              </div>
            </div>

            {paymentStateChip ? (
              <div className="flex justify-start">
                <span className="pos-chip" data-tone={paymentStateChip.tone}>
                  {paymentStateChip.label}
                </span>
              </div>
            ) : null}

            <div className="grid grid-cols-3 gap-2">
              {PAYMENT_METHOD_OPTIONS.map((option) => (
                <OrderPaymentMethodButton
                  icon={
                    option.value === CASH_PAYMENT_METHOD_CODE ? (
                      <MoneyIcon className="h-5 w-5" />
                    ) : option.value === MIXED_PAYMENT_METHOD_CODE ? (
                      <SplitIcon className="h-5 w-5" />
                    ) : (
                      <CardIcon className="h-5 w-5" />
                    )
                  }
                  isActive={draftAdvancePaymentMethodCode === option.value}
                  key={option.value}
                  label={option.label}
                  onClick={() => {
                    onSetAdvancePaymentMethodCode(option.value);
                    if (advanceCents <= 0) {
                      if (option.value === MIXED_PAYMENT_METHOD_CODE) {
                        mixedAdvanceCashInputRef.current?.focus();
                        mixedAdvanceCashInputRef.current?.select();
                        return;
                      }
                      advanceInputRef.current?.focus();
                      advanceInputRef.current?.select();
                    }
                  }}
                />
              ))}
            </div>

            {isMixedAdvance ? (
              <div className="grid gap-2">
                <div className="grid gap-2">
                  <PosPaymentInputCard icon={<MoneyIcon className="h-5 w-5" />} label="Efectivo">
                    <div className="relative w-full">
                      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-500">
                        $
                      </span>
                      <input
                        className={cn(
                          "h-11 w-full rounded-xl pl-7 pr-3 text-right text-[1.15rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
                          posInputClass,
                        )}
                        inputMode="decimal"
                        onChange={(event) => onSetMixedAdvanceCashAmountText(event.target.value)}
                        placeholder="0.00"
                        ref={mixedAdvanceCashInputRef}
                        value={draftMixedAdvanceCashAmountText}
                      />
                    </div>
                  </PosPaymentInputCard>

                  <PosPaymentInputCard icon={<CardIcon className="h-5 w-5" />} label="Tarjeta">
                    <div className="relative w-full">
                      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-500">
                        $
                      </span>
                      <input
                        className={cn(
                          "h-11 w-full rounded-xl pl-7 pr-3 text-right text-[1.15rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
                          posInputClass,
                        )}
                        inputMode="decimal"
                        onChange={(event) => onSetMixedAdvanceCardAmountText(event.target.value)}
                        placeholder="0.00"
                        value={draftMixedAdvanceCardAmountText}
                      />
                    </div>
                  </PosPaymentInputCard>
                </div>
              </div>
            ) : (
              <PosPaymentInputCard icon={<MoneyIcon className="h-5 w-5" />} label="Anticipo">
                <div className="relative w-full">
                  <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-500">
                    $
                  </span>
                  <input
                    className={cn(
                      "h-11 w-full rounded-xl pl-7 pr-3 text-right text-[1.2rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
                      posInputClass,
                    )}
                    inputMode="decimal"
                    onChange={(event) => onSetAdvanceAmountText(event.target.value)}
                    onFocus={ensureDefaultAdvanceMethod}
                    placeholder="0.00"
                    ref={advanceInputRef}
                    value={draftAdvanceAmountText}
                  />
                </div>
              </PosPaymentInputCard>
            )}

            <div className="grid gap-2">
              <OrderPaymentMetricTile
                icon={<ReceiptIcon className="h-5 w-5" />}
                label="Total"
                tone="financial"
                value={formatCurrency(formatMoneyFromCents(subtotalCents))}
              />
              <OrderPaymentMetricTile
                icon={<ClockIcon className="h-5 w-5" />}
                label="Pendiente"
                tone="pending"
                value={formatCurrency(formatMoneyFromCents(remainingCents))}
              />
            </div>
          </div>
        </div>

        <div className="grid min-h-0 grid-rows-[minmax(0,1fr)_auto] gap-2.5">
          <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white">
            {draftLines.length === 0 ? (
              <div className="flex min-h-[7rem] items-center justify-center px-4 py-4 text-center text-sm leading-6 text-slate-600">
                Agrega productos desde el catalogo para formar el pedido.
              </div>
            ) : (
              <ScrollPane className="h-full">
                {draftLines.map((line) => (
                  <DraftLineRow
                    key={line.key}
                    line={line}
                    onDecrement={() => onDraftLineDecrement(line.key)}
                    onIncrement={() => onDraftLineIncrement(line.key)}
                    onRemove={() => onDraftLineRemove(line.key)}
                  />
                ))}
              </ScrollPane>
            )}
          </div>

          <div className="grid gap-1.5">
            {createChecklistMessages.length > 0 ? (
              <div className="grid gap-1.5">
                {createChecklistMessages.slice(0, 4).map((message) => (
                  <InlineNotice key={message} tone="warning">
                    {message}
                  </InlineNotice>
                ))}
              </div>
            ) : (
              <InlineNotice tone="success">Pedido listo para guardar.</InlineNotice>
            )}
            {createOrderBlockingMessage && createChecklistMessages.length === 0 ? (
              <InlineNotice tone="warning">{createOrderBlockingMessage}</InlineNotice>
            ) : null}
          </div>
        </div>

        <div className="grid gap-2 border-t border-[var(--pos-shell-border)] pt-2">
          <div className="grid grid-cols-[1fr_1fr] gap-2">
            <Button
              className={cn("h-10", posOutlineButtonClass)}
              onClick={onRequestCancelDraft}
              type="button"
              variant="outline"
            >
              Descartar
            </Button>
            <Button
              className={cn("h-11", posPrimaryButtonClass)}
              disabled={createOrderDisabled || isCreateSaving}
              onClick={onCreateOrder}
              type="button"
            >
              {isCreateSaving ? "Guardando..." : "Guardar pedido"}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (orderDetailIsPending) {
    return (
      <div className="pos-shell-panel grid h-full min-h-0 p-[var(--pos-shell-workstation-padding)]">
        <OperationalStatus description="Cargando el pedido seleccionado." title="Pedido seleccionado" />
      </div>
    );
  }

  if (orderDetailError) {
    return (
      <div className="pos-shell-panel grid h-full min-h-0 p-[var(--pos-shell-workstation-padding)]">
        <OperationalStatus
          description={toOperationalErrorMessage(
            orderDetailError,
            "No fue posible cargar el pedido seleccionado.",
          )}
          title="Pedido no disponible"
        />
      </div>
    );
  }

  if (!orderDetail) {
    return (
      <div className="pos-shell-panel grid h-full min-h-0 p-[var(--pos-shell-workstation-padding)]">
        <div className="grid h-full place-items-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-center">
          <div className="grid max-w-xs gap-2">
            <p className="text-sm font-semibold text-slate-950">Sin pedido seleccionado.</p>
            <p className="text-sm leading-6 text-slate-600">
              Selecciona un pedido para revisar el resumen y ejecutar la siguiente acción.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const requiresSettlement =
    orderDetail.requires_settlement_on_delivery &&
    orderDetail.remaining_balance_amount !== "0.00";
  const showDeliverySettlementFlow =
    orderDetail.can_deliver && requiresSettlement && deliverySettlementFlowActive;
  const remainingBalanceCents = parseMoneyToCents(orderDetail.remaining_balance_amount) ?? 0;
  const sanitizedDeliveryReceivedAmount = sanitizeMoneyInput(deliveryReceivedAmountText);
  const deliveryReceivedAmountCents =
    parseMoneyToCents(sanitizedDeliveryReceivedAmount) ?? 0;
  const deliveryMixedSettlementPayments = buildDeliverOrderSettlementPayments({
    mixedCardAmountText: deliveryMixedCardAmountText,
    mixedCashAmountText: deliveryMixedCashAmountText,
    paymentMethodCode: deliveryPaymentMethodCode,
  });
  const deliveryMixedCashAmountCents =
    parseMoneyToCents(sanitizeMoneyInput(deliveryMixedCashAmountText)) ?? 0;
  const deliveryMixedCardAmountCents =
    parseMoneyToCents(sanitizeMoneyInput(deliveryMixedCardAmountText)) ?? 0;
  const isMixedDeliverySettlement = deliveryPaymentMethodCode === MIXED_PAYMENT_METHOD_CODE;
  const deliveryCapturedAmountCents = isMixedDeliverySettlement
    ? deliveryMixedCashAmountCents + deliveryMixedCardAmountCents
    : deliveryReceivedAmountCents;
  const deliveryChangeCents = isMixedDeliverySettlement
    ? 0
    : Math.max(deliveryCapturedAmountCents - remainingBalanceCents, 0);
  const deliveryMissingCents = Math.max(remainingBalanceCents - deliveryCapturedAmountCents, 0);
  const deliveryMixedDifferenceCents = Math.abs(deliveryCapturedAmountCents - remainingBalanceCents);
  const isMixedDeliverySettlementReady =
    deliveryMixedSettlementPayments.length === 2 &&
    deliveryCapturedAmountCents === remainingBalanceCents;
  const isDeliverySettlementReady =
    showDeliverySettlementFlow &&
    deliveryPaymentMethodCode.trim().length > 0 &&
    (isMixedDeliverySettlement
      ? isMixedDeliverySettlementReady
      : sanitizedDeliveryReceivedAmount.length > 0 && deliveryMissingCents === 0);
  const primaryActionLabel = orderDetail.can_mark_ready
    ? "Marcar listo para entrega"
    : orderDetail.can_deliver
      ? showDeliverySettlementFlow
        ? "Cobrar y entregar"
        : requiresSettlement
          ? "Cobrar saldo para entregar"
          : "Entregar pedido"
      : null;
  const primaryActionTone =
    orderDetail.can_mark_ready
      ? "info"
      : orderDetail.can_deliver
        ? requiresSettlement
          ? "warning"
          : "success"
        : orderDetail.status === "DELIVERED"
          ? "success"
        : orderDetail.status === "CANCELED"
          ? "warning"
          : "info";
  const operationalStateTone =
    orderDetail.can_deliver
      ? requiresSettlement
        ? "danger"
        : "success"
      : orderDetail.can_mark_ready
        ? "warning"
        : orderDetail.status === "DELIVERED"
          ? "success"
          : orderDetail.status === "CANCELED"
            ? "danger"
            : "info";
  const operationalStateLabel =
    orderDetail.can_deliver
      ? requiresSettlement
        ? "Pago pendiente"
        : "Pedido liquidado"
      : orderDetail.can_mark_ready
        ? "Pendiente"
        : orderDetail.status === "DELIVERED"
          ? "Pedido entregado"
          : orderDetail.status === "CANCELED"
            ? "Pedido cancelado"
            : "Sin accion";
  const operationalActionTone =
    primaryActionTone === "warning"
      ? "warning"
      : primaryActionTone === "success"
        ? "success"
        : "info";
  const readyNotificationAction = getCustomerCommunicationActionState({
    customerPhone: orderDetail.customer_phone,
    intent: "orderReady",
  });

  return (
    <div className="pos-shell-panel grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-[var(--pos-section-gap)] p-[var(--pos-shell-workstation-padding)]">
      <div className="grid gap-2">
        <div className="flex flex-wrap items-start justify-between gap-2.5">
          <div className="min-w-0">
            <p className="pos-label-text">Operacion</p>
            <h2 className="mt-0.5 text-base font-semibold text-slate-950">
              Entrega y cobro
            </h2>
          </div>
          <StatusBadge status={orderDetail.status} />
        </div>
      </div>

      <div className="grid min-h-0 content-start gap-2 overflow-y-auto pr-1">
        <KeyValueGroup tone="muted">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-950" title={orderDetail.folio}>
              {orderDetail.folio}
            </p>
          </div>
          <KeyValueRow
            label="Cliente"
            title={orderDetail.customer_name}
            value={orderDetail.customer_name}
          />
          <KeyValueRow
            label="Recoleccion"
            title={formatOrderRequestedForLabel(orderDetail.requested_for_at, orderDetail.branch.timezone)}
            value={formatOrderRequestedForLabel(orderDetail.requested_for_at, orderDetail.branch.timezone)}
          />
        </KeyValueGroup>

        <div className="grid gap-2 rounded-xl border border-[var(--pos-shell-border)] bg-white px-3 py-3">
          <div className="flex flex-wrap gap-2">
            <OrderOperationalChip
              icon={
                orderDetail.can_deliver ? (
                  requiresSettlement ? (
                    <ClockIcon className="h-4 w-4" />
                  ) : (
                    <CheckCircleIcon className="h-4 w-4" />
                  )
                ) : orderDetail.can_mark_ready ? (
                  <BagIcon className="h-4 w-4" />
                ) : orderDetail.status === "CANCELED" ? (
                  <XIcon className="h-4 w-4" />
                ) : (
                  <CheckCircleIcon className="h-4 w-4" />
                )
              }
              label={operationalStateLabel}
              tone={operationalStateTone}
            />
            <OrderOperationalChip
              icon={
                showDeliverySettlementFlow ? (
                  <MoneyIcon className="h-4 w-4" />
                ) : orderDetail.can_mark_ready ? (
                  <BagIcon className="h-4 w-4" />
                ) : orderDetail.can_deliver ? (
                  requiresSettlement ? (
                    <MoneyIcon className="h-4 w-4" />
                  ) : (
                    <CheckCircleIcon className="h-4 w-4" />
                  )
                ) : orderDetail.status === "CANCELED" ? (
                  <XIcon className="h-4 w-4" />
                ) : (
                  <CheckCircleIcon className="h-4 w-4" />
                )
              }
              label={primaryActionLabel ?? "Sin accion disponible"}
              tone={operationalActionTone}
            />
            {orderDetail.can_deliver && !requiresSettlement ? (
              <OrderOperationalChip
                icon={<CheckCircleIcon className="h-4 w-4" />}
                label="Entrega directa"
                tone="success"
              />
            ) : null}
          </div>

        {requiresSettlement ? (
          showDeliverySettlementFlow ? (
            <div className="grid gap-3 rounded-xl border border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)] px-3 py-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-[var(--ui-color-warning)]">
                    <MoneyIcon className="h-4 w-4" />
                  </span>
                  <p className="truncate text-[15px] font-semibold leading-5 text-slate-950">
                    Cobro de entrega
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                {PAYMENT_METHOD_OPTIONS.map((option) => (
                  <OrderPaymentMethodButton
                    icon={
                      option.value === CASH_PAYMENT_METHOD_CODE ? (
                        <MoneyIcon className="h-5 w-5" />
                      ) : option.value === MIXED_PAYMENT_METHOD_CODE ? (
                        <SplitIcon className="h-5 w-5" />
                      ) : (
                        <CardIcon className="h-5 w-5" />
                      )
                    }
                    isActive={deliveryPaymentMethodCode === option.value}
                    key={option.value}
                    label={option.label}
                    onClick={() => onDeliveryPaymentMethodChange(option.value)}
                  />
                ))}
              </div>

              <div className="grid gap-2">
                {isMixedDeliverySettlement ? (
                  <div className="grid gap-2">
                    <PosPaymentInputCard icon={<MoneyIcon className="h-5 w-5" />} label="Efectivo">
                      <div className="relative w-full">
                        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-500">
                          $
                        </span>
                        <input
                          className={cn(
                            "h-11 w-full rounded-xl pl-7 pr-3 text-right text-[1.15rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
                            posInputClass,
                          )}
                          inputMode="decimal"
                          onChange={(event) =>
                            onSetDeliveryMixedCashAmountText(
                              event.target.value.includes("-")
                                ? ""
                                : sanitizeMoneyInput(event.target.value),
                            )
                          }
                          placeholder="0.00"
                          ref={deliveryMixedCashInputRef}
                          value={deliveryMixedCashAmountText}
                        />
                      </div>
                    </PosPaymentInputCard>

                    <PosPaymentInputCard icon={<CardIcon className="h-5 w-5" />} label="Tarjeta">
                      <div className="relative w-full">
                        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-500">
                          $
                        </span>
                        <input
                          className={cn(
                            "h-11 w-full rounded-xl pl-7 pr-3 text-right text-[1.15rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
                            posInputClass,
                          )}
                          inputMode="decimal"
                          onChange={(event) =>
                            onSetDeliveryMixedCardAmountText(
                              event.target.value.includes("-")
                                ? ""
                                : sanitizeMoneyInput(event.target.value),
                            )
                          }
                          placeholder="0.00"
                          value={deliveryMixedCardAmountText}
                        />
                      </div>
                    </PosPaymentInputCard>
                  </div>
                ) : (
                  <PosPaymentInputCard icon={<MoneyIcon className="h-5 w-5" />} label="Recibe">
                    <div className="relative w-full">
                      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-500">
                        $
                      </span>
                      <input
                        className={cn(
                          "h-11 w-full rounded-xl pl-7 pr-3 text-right text-[1.2rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
                          posInputClass,
                        )}
                        inputMode="decimal"
                        onChange={(event) =>
                          onSetDeliveryReceivedAmountText(
                            event.target.value.includes("-")
                              ? ""
                              : sanitizeMoneyInput(event.target.value),
                          )
                        }
                        placeholder={orderDetail.remaining_balance_amount}
                        ref={deliveryReceivedInputRef}
                        value={deliveryReceivedAmountText}
                      />
                    </div>
                  </PosPaymentInputCard>
                )}

                <OrderPaymentMetricTile
                  icon={<MoneyIcon className="h-5 w-5" />}
                  label="Saldo a cobrar"
                  tone="advance"
                  value={formatCurrency(orderDetail.remaining_balance_amount)}
                />
                <OrderPaymentMetricTile
                  icon={
                    (isMixedDeliverySettlement
                      ? deliveryCapturedAmountCents !== remainingBalanceCents
                      : deliveryMissingCents > 0) ? (
                      <ClockIcon className="h-5 w-5" />
                    ) : (
                      <CheckCircleIcon className="h-5 w-5" />
                    )
                  }
                  label={
                    isMixedDeliverySettlement
                      ? deliveryCapturedAmountCents < remainingBalanceCents
                        ? "Por asignar"
                        : deliveryCapturedAmountCents > remainingBalanceCents
                          ? "Excedente"
                          : "Cuadre"
                      : deliveryMissingCents > 0
                        ? "Falta"
                        : deliveryChangeCents > 0
                          ? "Cambio"
                          : "Exacto"
                  }
                  tone={
                    isMixedDeliverySettlement
                      ? deliveryCapturedAmountCents === remainingBalanceCents
                        ? "success"
                        : "pending"
                      : deliveryMissingCents > 0
                        ? "pending"
                        : "success"
                  }
                  value={formatCurrency(
                    formatMoneyFromCents(
                      isMixedDeliverySettlement
                        ? deliveryMixedDifferenceCents
                        : deliveryMissingCents > 0
                          ? deliveryMissingCents
                          : deliveryChangeCents,
                    ),
                  )}
                />
              </div>
            </div>
          ) : null
        ) : null}

        <div className="grid gap-1 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-2.5">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="font-medium text-slate-600">Total</span>
            <span className="text-right font-semibold text-slate-950">
              {formatCurrency(orderDetail.total_amount)}
            </span>
          </div>
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="font-medium text-slate-600">Anticipo</span>
            <span className="text-right font-semibold text-slate-950">
              {formatCurrency(orderDetail.advance_amount)}
            </span>
          </div>
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="font-medium text-slate-600">Saldo</span>
            <span className="text-right font-semibold text-slate-950">
              {formatCurrency(orderDetail.remaining_balance_amount)}
            </span>
          </div>
        </div>
        </div>
      </div>

      <div className="grid gap-2 border-t border-[var(--pos-shell-border)] pt-2">
        {orderDetail.can_mark_ready ? (
          <Button
            className={cn("h-12 text-base font-semibold", posPrimaryButtonClass)}
            disabled={isSelectedOrderPending}
            onClick={onMarkReady}
            type="button"
          >
            {isSelectedOrderPending ? "Guardando..." : "Marcar listo para entrega"}
          </Button>
        ) : null}

        {orderDetail.can_deliver ? (
          showDeliverySettlementFlow ? (
            <div className="grid grid-cols-[1fr_1fr] gap-2">
              <Button
                className={cn("h-10", posOutlineButtonClass)}
                disabled={isSelectedOrderPending}
                onClick={onDismissDeliverySettlementFlow}
                type="button"
                variant="outline"
              >
                Cancelar cobro
              </Button>
              <Button
                className={cn("h-12 text-base font-semibold", posPrimaryButtonClass)}
                disabled={isSelectedOrderPending || !isDeliverySettlementReady}
                onClick={onRequestDeliverOrder}
                type="button"
              >
                {isSelectedOrderPending ? "Cobrando..." : "Cobrar y entregar"}
              </Button>
            </div>
          ) : (
            <Button
              className={cn("h-12 text-base font-semibold", posPrimaryButtonClass)}
              disabled={isSelectedOrderPending}
              onClick={onRequestDeliverOrder}
              type="button"
            >
              {isSelectedOrderPending
                ? "Entregando..."
                : requiresSettlement
                  ? "Cobrar saldo para entregar"
                  : "Entregar pedido"}
            </Button>
          )
        ) : null}

        {orderDetail.status === "READY" ? (
          <div className="grid gap-1">
            <Button
              className={cn("h-10", posOutlineButtonClass)}
              disabled={readyNotificationAction.disabled}
              title={readyNotificationAction.disabledReason}
              type="button"
              variant="outline"
            >
              {readyNotificationAction.label}
            </Button>
            <p className="text-xs leading-5 text-slate-500">
              {readyNotificationAction.disabledReason || readyNotificationAction.helperText}
            </p>
          </div>
        ) : null}

        {orderDetail.can_cancel ? (
          <Button
            className={cn("h-10", posOutlineButtonClass)}
            disabled={isSelectedOrderPending}
            onClick={onRequestCancelOrder}
            type="button"
            variant="outline"
          >
            {isSelectedOrderPending ? "Cancelando..." : "Cancelar pedido"}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function OrderConsultationDetailSurface({
  onRequestCancelOrder,
  orderDetail,
  orderDetailError,
  orderDetailIsPending,
}: {
  onRequestCancelOrder: () => void;
  orderDetail: CustomerOrderDetailResponse | null | undefined;
  orderDetailError: unknown;
  orderDetailIsPending: boolean;
}) {
  if (orderDetailIsPending) {
    return (
      <ListDetailColumn
        contentClassName="min-h-0 overflow-hidden"
        description="Cargando el detalle del pedido seleccionado."
        title="Detalle del pedido"
      >
        <PosLoadingState
          description="Consultando lineas, montos y estado del pedido."
          title="Cargando detalle"
        />
      </ListDetailColumn>
    );
  }

  if (orderDetailError) {
    return (
      <ListDetailColumn
        contentClassName="min-h-0 overflow-hidden"
        description="No fue posible abrir el pedido seleccionado."
        title="Detalle del pedido"
      >
        <PosErrorState
          description={toOperationalErrorMessage(
            orderDetailError,
            "No fue posible cargar el detalle del pedido seleccionado.",
          )}
          title="Detalle no disponible"
        />
      </ListDetailColumn>
    );
  }

  if (!orderDetail) {
    return (
      <ListDetailColumn
        contentClassName="min-h-0 overflow-hidden"
        description="Selecciona un pedido para revisar lineas, estado y saldo pendiente."
        title="Detalle del pedido"
      >
        <PosEmptyState
          description="Selecciona un pedido de la lista para revisar el detalle y decidir la siguiente accion."
          title="Sin pedido seleccionado"
        />
      </ListDetailColumn>
    );
  }

  const totalUnits = orderDetail.items.reduce((sum, item) => {
    const quantity = Number(item.quantity);
    return Number.isFinite(quantity) ? sum + quantity : sum;
  }, 0);
  const canShowCancelAction =
    orderDetail.status === "PENDING" || orderDetail.status === "READY";
  const requiresSettlement =
    orderDetail.requires_settlement_on_delivery &&
    orderDetail.remaining_balance_amount !== "0.00";

  return (
    <ListDetailColumn
      contentClassName="min-h-0 overflow-hidden"
      description="Detalle del pedido seleccionado con lineas, pickup y notas operativas."
      title={orderDetail.folio}
    >
      <div className="grid min-h-0 gap-3 lg:grid-rows-[auto_minmax(0,1fr)]">
        <div className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-base font-semibold text-slate-950">{orderDetail.customer_name}</p>
                <StatusBadge status={orderDetail.status} />
              </div>
              <div className="mt-2 grid gap-1.5 text-sm text-slate-600">
                <p className="truncate">{orderDetail.customer_phone ?? "Sin telefono"}</p>
                <p className="truncate">
                  {formatOrderRequestedForLabel(
                    orderDetail.requested_for_at,
                    orderDetail.branch.timezone,
                  )}
                </p>
                {orderDetail.cancellation_reason ? (
                  <p className="text-[var(--ui-color-danger)]">
                    Motivo: {orderDetail.cancellation_reason}
                  </p>
                ) : null}
              </div>
            </div>
            <div className="text-right text-sm text-slate-600">
              <p>{orderDetail.items.length} lineas</p>
              <p className="mt-1">{totalUnits.toFixed(3)} uds</p>
            </div>
          </div>
          {canShowCancelAction ? (
            <div className="mt-3 flex justify-end border-t border-[var(--pos-shell-border)] pt-3">
              <Button
                className={cn(
                  "h-9 border-[var(--ui-color-danger)]/25 px-3 text-sm text-[var(--ui-color-danger)] hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)]",
                  posOutlineButtonClass,
                )}
                disabled={!orderDetail.can_cancel}
                onClick={onRequestCancelOrder}
                title={
                  orderDetail.can_cancel
                    ? "Cancelar pedido"
                    : "No disponible mientras exista anticipo registrado."
                }
                type="button"
                variant="outline"
              >
                Cancelar pedido
              </Button>
            </div>
          ) : null}
        </div>

        <div className="grid min-h-0 gap-3 xl:grid-cols-[minmax(0,1fr)_18rem]">
          <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white">
            <div className="border-b border-[var(--pos-shell-border)] px-3 py-2.5">
              <p className="text-sm font-semibold text-slate-950">Lineas del pedido</p>
            </div>
            <ScrollPane className="divide-y divide-[var(--pos-shell-border)]">
              {orderDetail.items.map((item) => (
                <div
                  className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 px-3 py-2.5"
                  key={item.id}
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-950">
                      {item.product_name_snapshot}
                    </p>
                  </div>
                  <span className="text-sm font-medium text-slate-600">{item.quantity}</span>
                  <span className="text-sm font-semibold text-slate-950">
                    {formatCurrency(item.line_total_amount)}
                  </span>
                </div>
              ))}
            </ScrollPane>
          </div>

          <div className="grid min-h-0 gap-3 xl:grid-rows-[auto_minmax(0,1fr)]">
            <div
              className={cn(
                "rounded-xl border px-3 py-3",
                orderDetail.can_deliver && requiresSettlement
                  ? "border-[#e1a0a8] bg-[#fff1f3]"
                  : orderDetail.can_deliver
                    ? "border-[#9fd3b3] bg-[#e8f8ef]"
                    : "border-[var(--pos-shell-border)] bg-white",
              )}
            >
              <p className="text-sm font-semibold text-slate-950">Cumplimiento</p>
              <p
                className={cn(
                  "mt-1 text-sm",
                  orderDetail.can_deliver && requiresSettlement
                    ? "text-[var(--ui-color-danger)]"
                    : orderDetail.can_deliver
                      ? "text-[var(--ui-color-success)]"
                      : "text-slate-600",
                )}
              >
                {requiresSettlement
                  ? `Debe cubrir ${formatCurrency(orderDetail.remaining_balance_amount)} al entregar.`
                  : "Sin saldo pendiente para la entrega."}
              </p>
            </div>

            <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] p-3">
              <div className="flex items-center justify-between gap-3 border-b border-[var(--pos-shell-border)] pb-2.5">
                <p className="text-sm font-semibold text-slate-950">Notas</p>
                <span className="pos-chip" data-tone="muted">
                  {orderDetail.notes && orderDetail.notes.trim().length > 0 ? "Activas" : "Sin notas"}
                </span>
              </div>
              <ScrollPane className="mt-3 text-sm leading-6 text-slate-700">
                {orderDetail.notes && orderDetail.notes.trim().length > 0
                  ? orderDetail.notes
                  : "Este pedido no tiene notas adicionales."}
              </ScrollPane>
            </div>
          </div>
        </div>
      </div>
    </ListDetailColumn>
  );
}

export function OrdersScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const queryClient = useQueryClient();
  const quantityInputRef = useRef<HTMLInputElement>(null);
  const quantitySelectionKeyRef = useRef<string | null>(null);
  const customerPhoneInputRef = useRef<HTMLInputElement>(null);
  const pickupDateInputRef = useRef<HTMLInputElement>(null);
  const pickupHourInputRef = useRef<HTMLInputElement>(null);
  const pickupMinuteInputRef = useRef<HTMLInputElement>(null);
  const catalogSearchInputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<OrdersMode>("list");
  const [selectedStatus, setSelectedStatus] = useState("PENDING");
  const [searchText, setSearchText] = useState("");
  const [requestedDateFrom, setRequestedDateFrom] = useState("");
  const [requestedDateTo, setRequestedDateTo] = useState("");
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [deliveryPaymentMethodCode, setDeliveryPaymentMethodCode] = useState("");
  const [deliveryMixedCashAmountText, setDeliveryMixedCashAmountText] = useState("");
  const [deliveryMixedCardAmountText, setDeliveryMixedCardAmountText] = useState("");
  const [deliveryReceivedAmountText, setDeliveryReceivedAmountText] = useState("");
  const [orderActionDialog, setOrderActionDialog] = useState<OrderActionDialogState | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelReasonError, setCancelReasonError] = useState<string | null>(null);
  const [isDeliverySettlementFlowActive, setIsDeliverySettlementFlowActive] = useState(false);
  const [hasNegativeAdvanceAttempt, setHasNegativeAdvanceAttempt] = useState(false);
  const [selectionErrorMessage, setSelectionErrorMessage] = useState<string | null>(null);
  const [draftState, setDraftState] = useState(createInitialOrderCreateDraftState());
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const ordersBootstrapQuery = useOrdersBootstrapQuery();
  const initialRequestedForDraft = useMemo(
    () => createInitialRequestedForDraftState(ordersBootstrapQuery.data?.local_timestamp ?? null),
    [ordersBootstrapQuery.data?.local_timestamp],
  );
  const [requestedForDraft, setRequestedForDraft] = useState<RequestedForDraftState>(() =>
    createInitialRequestedForDraftState(),
  );

  const openCancelDialog = useCallback((order: CancelableOrderSummary) => {
    setSelectedOrderId(order.id);
    setCancelReason("");
    setCancelReasonError(null);
    setOrderActionDialog({ kind: "cancel", order });
  }, []);
  const [pickupKeyboardStage, setPickupKeyboardStage] = useState<"hour" | "minute" | null>(null);
  const [orderNotes, setOrderNotes] = useState("");
  const [advanceAmountText, setAdvanceAmountText] = useState("");
  const [mixedAdvanceCashAmountText, setMixedAdvanceCashAmountText] = useState("");
  const [mixedAdvanceCardAmountText, setMixedAdvanceCardAmountText] = useState("");
  const [advancePaymentMethodCode, setAdvancePaymentMethodCode] = useState("");

  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const debouncedListSearch = useDebouncedValue(searchText, 180);
  const hasInvalidRequestedDateRange =
    requestedDateFrom.trim().length > 0 &&
    requestedDateTo.trim().length > 0 &&
    requestedDateFrom > requestedDateTo;
  const ordersListQuery = useOrdersListQuery(
    selectedStatus,
    debouncedListSearch,
    requestedDateFrom,
    requestedDateTo,
    !hasInvalidRequestedDateRange,
  );
  const orderDetailQuery = useOrderDetailQuery(mode === "list" ? selectedOrderId : null);
  const debouncedCatalogSearch = useDebouncedValue(draftState.searchText, 180);
  const ordersCatalogQuery = useOrdersCatalogQuery(
    draftState.controlState === CONTROL_STATE_CLASS_SELECTION ? debouncedCatalogSearch : "",
    mode === "create",
  );
  const ordersClassProductsQuery = useOrdersClassProductsQuery(
    draftState.pendingSelection?.productClass.id ?? null,
    draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ? debouncedCatalogSearch : "",
    mode === "create",
  );

  const sortedClasses = useMemo(
    () => sortOrdersCatalogClasses(ordersCatalogQuery.data?.classes ?? []),
    [ordersCatalogQuery.data?.classes],
  );
  const sortedProducts = useMemo(
    () => sortOrdersCatalogProducts(ordersClassProductsQuery.data?.products ?? []),
    [ordersClassProductsQuery.data?.products],
  );
  const quantitySelectionKey =
    draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE &&
    draftState.pendingSelection?.product !== null &&
    draftState.pendingSelection !== null
      ? `${draftState.pendingSelection.productClass.id}:${draftState.pendingSelection.product.id}`
      : null;
  const advanceCents = useMemo(
    () =>
      getOrderAdvanceAmountCents({
        advanceAmountText,
        mixedCardAmountText: mixedAdvanceCardAmountText,
        mixedCashAmountText: mixedAdvanceCashAmountText,
        paymentMethodCode: advancePaymentMethodCode,
      }),
    [advanceAmountText, advancePaymentMethodCode, mixedAdvanceCardAmountText, mixedAdvanceCashAmountText],
  );
  const requestedForInput = useMemo(
    () => buildRequestedForInput(requestedForDraft),
    [requestedForDraft],
  );
  const hasCustomerName = customerName.trim().length > 0;
  const hasCustomerPhone = customerPhone.trim().length > 0;
  const hasRequestedFor = requestedForInput.trim().length > 0;
  const hasAnyAdvanceCapture =
    advanceAmountText.trim().length > 0 ||
    mixedAdvanceCashAmountText.trim().length > 0 ||
    mixedAdvanceCardAmountText.trim().length > 0;
  const areCustomerDetailsComplete = hasCustomerName && hasCustomerPhone && hasRequestedFor;
  const activeCreateTarget =
    !hasCustomerName
      ? "customer"
      : !hasCustomerPhone
        ? "phone"
        : !hasRequestedFor || pickupKeyboardStage !== null
          ? "pickup"
          : "products";

  const openPickupDatePicker = useCallback(() => {
    const input = pickupDateInputRef.current;
    if (!input) {
      return;
    }

    input.focus();
    if (typeof input.showPicker === "function") {
      try {
        input.showPicker();
      } catch {
        // Ignore browsers or contexts that reject imperative picker opening.
      }
    }
  }, []);

  const focusFirstOrderCatalogTarget = useCallback(() => {
    window.requestAnimationFrame(() => {
      const firstCatalogCard = document.querySelector<HTMLButtonElement>(
        "[data-pos-catalog-card='true']:not(:disabled)",
      );

      if (firstCatalogCard) {
        firstCatalogCard.focus();
        return;
      }

      catalogSearchInputRef.current?.focus();
    });
  }, []);
  const requestedForLabel = useMemo(() => {
    if (requestedForInput.trim().length === 0) {
      return "Sin fecha de recoleccion";
    }

    return formatLocalDateTime(
      new Date(requestedForInput).toISOString(),
      ordersBootstrapQuery.data?.branch.timezone ?? "America/Hermosillo",
    );
  }, [ordersBootstrapQuery.data?.branch.timezone, requestedForInput]);

  useEffect(() => {
    if (areCustomerDetailsComplete || draftState.controlState === CONTROL_STATE_CLASS_SELECTION) {
      return;
    }

    setDraftState((state) => ({
      ...state,
      controlState: CONTROL_STATE_CLASS_SELECTION,
      pendingSelection: null,
      searchText: "",
    }));
  }, [areCustomerDetailsComplete, draftState.controlState]);

  useEffect(() => {
    if (!hasCustomerName || !hasCustomerPhone || requestedForDraft.date.trim().length === 0) {
      setPickupKeyboardStage(null);
    }
  }, [hasCustomerName, hasCustomerPhone, requestedForDraft.date]);

  const resetCreateDraft = useCallback(() => {
    setDraftState(createInitialOrderCreateDraftState());
    setCustomerName("");
    setCustomerPhone("");
    setRequestedForDraft(
      createInitialRequestedForDraftState(ordersBootstrapQuery.data?.local_timestamp ?? null),
    );
    setPickupKeyboardStage(null);
    setOrderNotes("");
    setAdvanceAmountText("");
    setMixedAdvanceCashAmountText("");
    setMixedAdvanceCardAmountText("");
    setAdvancePaymentMethodCode("");
    setHasNegativeAdvanceAttempt(false);
    setOrderActionDialog(null);
    setIsDeliverySettlementFlowActive(false);
    setSelectionErrorMessage(null);
  }, [ordersBootstrapQuery.data?.local_timestamp]);

  useEffect(() => {
    if (mode !== "create") {
      setSelectionErrorMessage(null);
      quantitySelectionKeyRef.current = null;
      return;
    }

    if (quantitySelectionKey === null) {
      quantitySelectionKeyRef.current = null;
      return;
    }

    requestAnimationFrame(() => {
      quantityInputRef.current?.focus();
      if (quantitySelectionKeyRef.current === quantitySelectionKey) {
        return;
      }

      quantityInputRef.current?.select();
      quantitySelectionKeyRef.current = quantitySelectionKey;
    });
  }, [mode, quantitySelectionKey]);

  useEffect(() => {
    if (mode !== "list") {
      return;
    }

    const firstOrderId = ordersListQuery.data?.orders[0]?.id ?? null;
    if (selectedOrderId === null && firstOrderId !== null) {
      setSelectedOrderId(firstOrderId);
      return;
    }

    if (
      selectedOrderId !== null &&
      ordersListQuery.data !== undefined &&
      ordersListQuery.data.orders.every((order) => order.id !== selectedOrderId)
    ) {
      setSelectedOrderId(firstOrderId);
    }
  }, [mode, ordersListQuery.data, selectedOrderId]);

  useEffect(() => {
    setDeliveryPaymentMethodCode("");
    setDeliveryMixedCashAmountText("");
    setDeliveryMixedCardAmountText("");
    setDeliveryReceivedAmountText("");
    setOrderActionDialog(null);
    setIsDeliverySettlementFlowActive(false);
  }, [selectedOrderId]);

  useEffect(() => {
    if (
      !isDeliverySettlementFlowActive ||
      orderDetailQuery.data === undefined ||
      deliveryPaymentMethodCode.trim().length === 0 ||
      deliveryPaymentMethodCode === MIXED_PAYMENT_METHOD_CODE ||
      deliveryReceivedAmountText.trim().length > 0 ||
      orderDetailQuery.data.remaining_balance_amount === "0.00"
    ) {
      return;
    }

    setDeliveryReceivedAmountText(sanitizeMoneyInput(orderDetailQuery.data.remaining_balance_amount));
  }, [
    deliveryPaymentMethodCode,
    deliveryReceivedAmountText,
    isDeliverySettlementFlowActive,
    orderDetailQuery.data,
  ]);

  useEffect(() => {
    if (advanceCents <= 0 && !hasAnyAdvanceCapture) {
      setAdvancePaymentMethodCode("");
    }
  }, [advanceCents, hasAnyAdvanceCapture]);

  useEffect(() => {
    const hasDraftContent =
      customerName.trim().length > 0 ||
      customerPhone.trim().length > 0 ||
      requestedForInput.trim().length > 0 ||
      orderNotes.trim().length > 0 ||
      advanceAmountText.trim().length > 0 ||
      mixedAdvanceCashAmountText.trim().length > 0 ||
      mixedAdvanceCardAmountText.trim().length > 0 ||
      draftState.lines.length > 0;

    function handleKeyboard(event: KeyboardEvent) {
      if (orderActionDialog !== null && event.key === "Escape") {
        event.preventDefault();
        setOrderActionDialog(null);
        return;
      }

      if (isDeliverySettlementFlowActive && event.key === "Escape") {
        event.preventDefault();
        setIsDeliverySettlementFlowActive(false);
        setDeliveryPaymentMethodCode("");
        setDeliveryMixedCashAmountText("");
        setDeliveryMixedCardAmountText("");
        setDeliveryReceivedAmountText("");
        return;
      }

      if (mode === "list") {
        if (event.key === "Escape") {
          if (searchText.trim().length > 0) {
            event.preventDefault();
            setSearchText("");
            return;
          }

          if (selectedOrderId !== null) {
            event.preventDefault();
            setSelectedOrderId(null);
          }
        }

        return;
      }

      if (event.key === "Escape") {
        if (
          draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ||
          draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE
        ) {
          event.preventDefault();
          setDraftState((state) => goBackFromOrderControlState(state));
          return;
        }

        if (draftState.searchText.trim().length > 0) {
          event.preventDefault();
          setDraftState((state) => ({
            ...state,
            searchText: "",
          }));
          return;
        }

        event.preventDefault();
        if (hasDraftContent) {
          setOrderActionDialog({ kind: "discard" });
        } else {
          resetCreateDraft();
          setMode("list");
        }
        return;
      }

      if (isEditableTarget(event.target)) {
        return;
      }

      if (!areCustomerDetailsComplete) {
        return;
      }

      const shortcutIndex = getSelectionShortcutIndex(event.key);
      if (shortcutIndex === null) {
        return;
      }

      if (draftState.controlState === CONTROL_STATE_CLASS_SELECTION) {
        const productClass = sortedClasses[shortcutIndex];
        if (productClass) {
          event.preventDefault();
          setDraftState((state) => selectClassForOrder(state, productClass));
        }
        return;
      }

      if (draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION) {
        const product = sortedProducts[shortcutIndex];
        if (product) {
          event.preventDefault();
          setDraftState((state) => selectProductForOrder(state, product));
        }
      }
    }

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [
    draftState.controlState,
    draftState.lines.length,
    draftState.searchText,
    areCustomerDetailsComplete,
    isDeliverySettlementFlowActive,
    mode,
    orderActionDialog,
    customerName,
    customerPhone,
    requestedForInput,
    orderNotes,
    advanceAmountText,
    mixedAdvanceCashAmountText,
    mixedAdvanceCardAmountText,
    resetCreateDraft,
    searchText,
    selectedOrderId,
    sortedClasses,
    sortedProducts,
  ]);

  const refreshOrdersData = useCallback(
    async (orderId: string | null) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ordersBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
        }),
        queryClient.invalidateQueries({
          queryKey: ["orders-list", appEnv.VITE_POS_WORKSTATION_CODE],
        }),
        orderId
          ? queryClient.invalidateQueries({
              queryKey: orderDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, orderId),
            })
          : Promise.resolve(),
      ]);
    },
    [queryClient],
  );

  const createOrderMutation = useMutation({
    mutationFn: async () => {
      if (accessToken === null || ordersBootstrapQuery.data === undefined) {
        throw new Error("Se requiere autenticacion y contexto para registrar pedidos.");
      }

      const blockingMessage = getOrderCreateBlockingMessage({
        advanceAmountText,
        advancePaymentMethodCode,
        customerName,
        customerPhone,
        mixedCardAmountText: mixedAdvanceCardAmountText,
        mixedCashAmountText: mixedAdvanceCashAmountText,
        hasNegativeAdvanceAttempt,
        lines: draftState.lines,
        requestedForInput,
      });
      if (blockingMessage) {
        throw new Error(blockingMessage);
      }

      const payload: CreateCustomerOrderRequest = {
        workstation_code: ordersBootstrapQuery.data.workstation.code,
        customer_name: customerName.trim(),
        customer_phone: customerPhone.trim().length > 0 ? customerPhone.trim() : null,
        requested_for_at:
          requestedForInput.trim().length > 0 ? new Date(requestedForInput).toISOString() : null,
        notes: orderNotes.trim().length > 0 ? orderNotes.trim() : null,
        items: buildCreateOrderItems(draftState.lines),
        advance_amount: advanceCents > 0 ? formatMoneyFromCents(advanceCents) : "0.00",
        advance_payment_method_code: advanceCents > 0 ? advancePaymentMethodCode : null,
        advance_payments: buildCreateOrderAdvancePayments({
          advanceAmountText,
          mixedCardAmountText: mixedAdvanceCardAmountText,
          mixedCashAmountText: mixedAdvanceCashAmountText,
          paymentMethodCode: advancePaymentMethodCode,
        }),
      };

      return createOrder({
        accessToken,
        payload,
        requestId: createRequestId("orders-create"),
      });
    },
    onSuccess: async (orderDetail) => {
      await refreshOrdersData(orderDetail.id);
      setSelectedStatus(orderDetail.status);
      setSelectedOrderId(orderDetail.id);
      setMode("list");
      resetCreateDraft();
      setOrderActionDialog(null);
      showSuccess(`Pedido guardado. Folio ${orderDetail.folio}.`);
    },
    onError: (error) => {
      showError(
        toOperationalErrorMessage(
          error,
          "No fue posible guardar el pedido. Confirma el cliente, los productos y el anticipo.",
        ),
      );
    },
  });

  const markReadyMutation = useMutation({
    mutationFn: async () => {
      if (
        accessToken === null ||
        ordersBootstrapQuery.data === undefined ||
        selectedOrderId === null
      ) {
        throw new Error("Selecciona un pedido antes de marcarlo como listo.");
      }

      const payload: OrderActionRequest = {
        workstation_code: ordersBootstrapQuery.data.workstation.code,
      };

      return markOrderReady({
        accessToken,
        orderId: selectedOrderId,
        payload,
        requestId: createRequestId("orders-ready"),
      });
    },
    onSuccess: async (orderDetail) => {
      await refreshOrdersData(orderDetail.id);
      setSelectedStatus(orderDetail.status);
      setSelectedOrderId(orderDetail.id);
      setOrderActionDialog(null);
      showSuccess("El pedido quedo listo para entrega.");
    },
    onError: (error) => {
      showError(
        toOperationalErrorMessage(
          error,
          "No fue posible marcar el pedido como listo para entrega.",
        ),
      );
    },
  });

  const deliverMutation = useMutation({
    mutationFn: async () => {
      if (
        accessToken === null ||
        ordersBootstrapQuery.data === undefined ||
        selectedOrderId === null ||
        orderDetailQuery.data === undefined
      ) {
        throw new Error("Selecciona un pedido listo para entrega.");
      }

      return deliverOrder({
        accessToken,
        orderId: selectedOrderId,
        payload: {
          workstation_code: ordersBootstrapQuery.data.workstation.code,
          settlement_amount:
            orderDetailQuery.data.remaining_balance_amount !== "0.00"
              ? orderDetailQuery.data.remaining_balance_amount
              : null,
          settlement_payment_method_code:
            orderDetailQuery.data.remaining_balance_amount !== "0.00"
              ? deliveryPaymentMethodCode
              : null,
          settlement_payments:
            orderDetailQuery.data.remaining_balance_amount !== "0.00"
              ? buildDeliverOrderSettlementPayments({
                  mixedCardAmountText: deliveryMixedCardAmountText,
                  mixedCashAmountText: deliveryMixedCashAmountText,
                  paymentMethodCode: deliveryPaymentMethodCode,
                })
              : [],
        },
        requestId: createRequestId("orders-deliver"),
      });
    },
    onSuccess: async (orderDetail) => {
      await refreshOrdersData(orderDetail.id);
      setSelectedStatus(orderDetail.status);
      setSelectedOrderId(orderDetail.id);
      setOrderActionDialog(null);
      setIsDeliverySettlementFlowActive(false);
      setDeliveryPaymentMethodCode("");
      setDeliveryMixedCashAmountText("");
      setDeliveryMixedCardAmountText("");
      setDeliveryReceivedAmountText("");
      showSuccess("El pedido fue entregado correctamente.");
    },
    onError: (error) => {
      showError(
        toOperationalErrorMessage(
          error,
          "No fue posible entregar el pedido. Revisa la liquidacion final.",
        ),
      );
    },
  });

  const cancelMutation = useMutation({
    mutationFn: async () => {
      if (
        accessToken === null ||
        ordersBootstrapQuery.data === undefined ||
        selectedOrderId === null
      ) {
        throw new Error("Selecciona un pedido antes de cancelarlo.");
      }

      const payload: CancelCustomerOrderRequest = {
        cancellation_reason: cancelReason.trim(),
        workstation_code: ordersBootstrapQuery.data.workstation.code,
      };

      return cancelOrder({
        accessToken,
        orderId: selectedOrderId,
        payload,
        requestId: createRequestId("orders-cancel"),
      });
    },
    onSuccess: async (orderDetail) => {
      await refreshOrdersData(orderDetail.id);
      setSelectedStatus(orderDetail.status);
      setSelectedOrderId(orderDetail.id);
      setOrderActionDialog(null);
      setCancelReason("");
      setCancelReasonError(null);
      setIsDeliverySettlementFlowActive(false);
      setDeliveryPaymentMethodCode("");
      setDeliveryMixedCashAmountText("");
      setDeliveryMixedCardAmountText("");
      setDeliveryReceivedAmountText("");
      const cancellationRefundAmount = orderDetail.payments.reduce((sum, payment) => {
        if (payment.payment_type !== "REFUND") {
          return sum;
        }

        const paymentAmountCents = parseMoneyToCents(payment.amount);
        return paymentAmountCents === null ? sum : sum + paymentAmountCents;
      }, 0);

      showSuccess(
        cancellationRefundAmount > 0
          ? `El pedido fue cancelado. Procede la devolucion del anticipo por ${formatCurrency(formatMoneyFromCents(cancellationRefundAmount))}.`
          : "El pedido fue cancelado.",
      );
    },
    onError: (error) => {
      showError(
        toOperationalErrorMessage(error, "No fue posible cancelar el pedido con el estado actual."),
      );
    },
  });

  const createOrderBlockingMessage = getOrderCreateBlockingMessage({
    advanceAmountText,
    advancePaymentMethodCode,
    customerName,
    customerPhone,
    mixedCardAmountText: mixedAdvanceCardAmountText,
    mixedCashAmountText: mixedAdvanceCashAmountText,
    hasNegativeAdvanceAttempt,
    lines: draftState.lines,
    requestedForInput,
  });
  const createChecklistMessages = getOrderCreateChecklistMessages({
    advanceAmountText,
    advancePaymentMethodCode,
    customerName,
    customerPhone,
    mixedCardAmountText: mixedAdvanceCardAmountText,
    mixedCashAmountText: mixedAdvanceCashAmountText,
    hasNegativeAdvanceAttempt,
    lines: draftState.lines,
    requestedForInput,
  });
  const createUiState = getOrderCreateUiState({
    customerName,
    customerPhone,
    hasBlockingMessage: createOrderBlockingMessage !== null,
    isSaving: createOrderMutation.isPending,
    lineCount: draftState.lines.length,
    requestedForInput,
  });
  const saveOrderDisabled = createOrderBlockingMessage !== null;

  const summaryPanel = useMemo(
    () => (
      <OrdersDecisionPanel
        bootstrap={ordersBootstrapQuery.data}
        createChecklistMessages={createChecklistMessages}
        createOrderBlockingMessage={createOrderBlockingMessage}
        createOrderDisabled={saveOrderDisabled}
        createUiState={createUiState}
        deliverySettlementFlowActive={isDeliverySettlementFlowActive}
        deliveryMixedCardAmountText={deliveryMixedCardAmountText}
        deliveryMixedCashAmountText={deliveryMixedCashAmountText}
        deliveryPaymentMethodCode={deliveryPaymentMethodCode}
        deliveryReceivedAmountText={deliveryReceivedAmountText}
        draftAdvanceAmountText={advanceAmountText}
        draftMixedAdvanceCardAmountText={mixedAdvanceCardAmountText}
        draftMixedAdvanceCashAmountText={mixedAdvanceCashAmountText}
        draftAdvancePaymentMethodCode={advancePaymentMethodCode}
        draftCustomerName={customerName}
        draftLines={draftState.lines}
        draftRequestedForLabel={requestedForLabel}
        isCreateSaving={createOrderMutation.isPending}
        isSelectedOrderPending={
          markReadyMutation.isPending || deliverMutation.isPending || cancelMutation.isPending
        }
        mode={mode}
        onCreateOrder={() => {
          void createOrderMutation.mutateAsync();
        }}
        onDismissDeliverySettlementFlow={() => {
          setIsDeliverySettlementFlowActive(false);
          setDeliveryPaymentMethodCode("");
          setDeliveryMixedCashAmountText("");
          setDeliveryMixedCardAmountText("");
          setDeliveryReceivedAmountText("");
        }}
        onDeliveryPaymentMethodChange={(value) => {
          const remainingBalanceAmount = orderDetailQuery.data?.remaining_balance_amount;
          setDeliveryPaymentMethodCode(value);
          if (value === MIXED_PAYMENT_METHOD_CODE) {
            setDeliveryReceivedAmountText("");
            return;
          }

          setDeliveryMixedCashAmountText("");
          setDeliveryMixedCardAmountText("");
          if (remainingBalanceAmount !== undefined && remainingBalanceAmount !== "0.00") {
            setDeliveryReceivedAmountText((currentValue) =>
              currentValue.trim().length > 0
                ? currentValue
                : sanitizeMoneyInput(remainingBalanceAmount),
            );
          }
        }}
        onSetDeliveryMixedCardAmountText={setDeliveryMixedCardAmountText}
        onSetDeliveryMixedCashAmountText={setDeliveryMixedCashAmountText}
        onSetDeliveryReceivedAmountText={setDeliveryReceivedAmountText}
        onDraftLineDecrement={(lineKey) => {
          setDraftState((state) => ({
            ...state,
            lines: state.lines
              .map((entry) =>
                entry.key === lineKey
                  ? updateOrderLineQuantity(entry, Math.max(entry.quantityMilliUnits - 1000, 0))
                  : entry,
              )
              .filter((entry) => entry.quantityMilliUnits > 0),
          }));
        }}
        onDraftLineIncrement={(lineKey) => {
          setDraftState((state) => ({
            ...state,
            lines: state.lines.map((entry) =>
              entry.key === lineKey
                ? updateOrderLineQuantity(entry, entry.quantityMilliUnits + 1000)
                : entry,
            ),
          }));
        }}
        onDraftLineRemove={(lineKey) => {
          setDraftState((state) => ({
            ...state,
            lines: removeOrderLine(state.lines, lineKey),
          }));
        }}
        onMarkReady={() => {
          void markReadyMutation.mutateAsync();
        }}
        onRequestCancelDraft={() => {
          setOrderActionDialog({ kind: "discard" });
        }}
        onRequestCancelOrder={() => {
          if (orderDetailQuery.data) {
            openCancelDialog({
              advance_amount: orderDetailQuery.data.advance_amount,
              cancellation_refund_amount: orderDetailQuery.data.cancellation_refund_amount,
              cancellation_refund_eligible: orderDetailQuery.data.cancellation_refund_eligible,
              customer_name: orderDetailQuery.data.customer_name,
              folio: orderDetailQuery.data.folio,
              id: orderDetailQuery.data.id,
              status: orderDetailQuery.data.status,
            });
          }
        }}
        onRequestDeliverOrder={() => {
          if (orderDetailQuery.data) {
            const requiresSettlement =
              orderDetailQuery.data.requires_settlement_on_delivery &&
              orderDetailQuery.data.remaining_balance_amount !== "0.00";

            if (requiresSettlement && !isDeliverySettlementFlowActive) {
              setIsDeliverySettlementFlowActive(true);
              setDeliveryPaymentMethodCode((currentValue) =>
                currentValue.trim().length > 0 ? currentValue : CASH_PAYMENT_METHOD_CODE,
              );
              setDeliveryMixedCashAmountText("");
              setDeliveryMixedCardAmountText("");
              setDeliveryReceivedAmountText((currentValue) =>
                currentValue.trim().length > 0
                  ? currentValue
                  : sanitizeMoneyInput(orderDetailQuery.data.remaining_balance_amount),
              );
              return;
            }

            void deliverMutation.mutateAsync();
          }
        }}
        onSetAdvanceAmountText={(value) => {
          const hasNegativeValue = value.includes("-");
          setHasNegativeAdvanceAttempt(hasNegativeValue);
          setAdvanceAmountText(hasNegativeValue ? "" : sanitizeMoneyInput(value));
        }}
        onSetMixedAdvanceCardAmountText={(value) => {
          const hasNegativeValue = value.includes("-");
          setHasNegativeAdvanceAttempt(hasNegativeValue);
          setMixedAdvanceCardAmountText(hasNegativeValue ? "" : sanitizeMoneyInput(value));
        }}
        onSetMixedAdvanceCashAmountText={(value) => {
          const hasNegativeValue = value.includes("-");
          setHasNegativeAdvanceAttempt(hasNegativeValue);
          setMixedAdvanceCashAmountText(hasNegativeValue ? "" : sanitizeMoneyInput(value));
        }}
        onSetAdvancePaymentMethodCode={setAdvancePaymentMethodCode}
        orderDetail={orderDetailQuery.data}
        orderDetailError={orderDetailQuery.error}
        orderDetailIsPending={orderDetailQuery.isPending}
      />
    ),
    [
      advanceAmountText,
      advancePaymentMethodCode,
      cancelMutation.isPending,
      createChecklistMessages,
      createOrderBlockingMessage,
      createOrderMutation,
      createUiState,
      customerName,
      deliverMutation,
      isDeliverySettlementFlowActive,
      deliveryMixedCardAmountText,
      deliveryMixedCashAmountText,
      deliveryPaymentMethodCode,
      deliveryReceivedAmountText,
      draftState.lines,
      markReadyMutation,
      mixedAdvanceCardAmountText,
      mixedAdvanceCashAmountText,
      mode,
      openCancelDialog,
      orderDetailQuery.data,
      orderDetailQuery.error,
      orderDetailQuery.isPending,
      ordersBootstrapQuery.data,
      requestedForLabel,
      saveOrderDisabled,
    ],
  );
  useAppShellRightPanel(summaryPanel);

  const isPending =
    ordersBootstrapQuery.isPending ||
    currentCashSessionQuery.isPending ||
    ordersListQuery.isPending;

  if (isPending) {
    return (
      <OperationalStatus
        description="Consultando la caja activa y el estado actual de los pedidos."
        title="Cargando pedidos"
      />
    );
  }

  if (ordersBootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<PosButton onClick={() => ordersBootstrapQuery.refetch()}>Reintentar</PosButton>}
        description={toOperationalErrorMessage(
          ordersBootstrapQuery.error,
          "Confirma la configuracion de la estacion y el contexto operativo.",
        )}
        title="No fue posible cargar Pedidos"
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

  if (currentCashSessionQuery.data.user_id !== ordersBootstrapQuery.data.user.id) {
    return (
      <OperationalStatus
        description="La caja abierta de esta estacion pertenece a otro cajero. Inicia sesion con el operador correcto o espera el relevo."
        title="La caja activa no coincide con este cajero"
      />
    );
  }

  const isCreateMode = mode === "create";
  const isSelectionLoading =
    isCreateMode &&
    ((draftState.controlState === CONTROL_STATE_CLASS_SELECTION && ordersCatalogQuery.isPending) ||
      (draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION &&
        ordersClassProductsQuery.isPending));
  const selectionError =
    draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
      ? ordersClassProductsQuery.error
      : ordersCatalogQuery.error;
  const quantitySelection =
    draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE ? draftState.pendingSelection : null;
  const quantityProduct = quantitySelection?.product ?? null;
  const pendingQuantityMilliUnits =
    quantitySelection !== null ? parseQuantityToMilliUnits(quantitySelection.quantityText) : null;
  const canAddPendingLine =
    quantitySelection !== null &&
    quantityProduct !== null &&
    pendingQuantityMilliUnits !== null &&
    pendingQuantityMilliUnits > 0;
  const catalogSearchPlaceholder =
    draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
      ? "Buscar producto..."
      : "Buscar clase...";
  const catalogStepKey =
    draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION
      ? "product"
      : draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE
        ? "quantity"
        : "class";
  const createGuideStepKey =
    !areCustomerDetailsComplete
      ? "details"
      : draftState.lines.length === 0
        ? "products"
        : "summary";

  return (
    <ContinuousWorkspaceSheet
      className="lg:h-full"
      contentClassName="min-h-0 overflow-hidden px-3 pb-3 pt-2"
      header={
        <CompactPageHeader
        secondaryChips={
          mode === "create" ? (
            <ModuleStateChip tone="muted">
              {draftState.lines.length} lineas
            </ModuleStateChip>
          ) : (
            <ModuleStateChip tone="muted">
              {getOrderStatusCount(ordersBootstrapQuery.data.status_counters, selectedStatus)} en
              vista
            </ModuleStateChip>
          )
        }
        stateChip={
          <ModuleStateChip tone={mode === "create" ? "primary" : selectedOrderId ? "primary" : "muted"}>
            {mode === "create" ? "Captura activa" : selectedOrderId ? "1 en vista" : "Sin seleccion"}
          </ModuleStateChip>
        }
        title="Pedidos"
        >
          <FlowGuide
            activeStepKey={
              mode === "create" ? createGuideStepKey : selectedOrderId ? "detail" : "list"
            }
            steps={
              mode === "create"
                ? ORDER_CREATE_GUIDE_STEPS
                : [
                    {
                      key: "list",
                      label: "Consulta",
                      state: selectedOrderId ? "completed" : "current",
                    },
                    {
                      key: "detail",
                      label: "Detalle",
                      state: selectedOrderId ? "current" : "upcoming",
                    },
                    {
                      key: "action",
                      label: "Entrega y cobro",
                      state: selectedOrderId ? "upcoming" : "blocked",
                    },
                  ]
            }
            variant={mode === "create" ? "process" : "compact"}
          />
        </CompactPageHeader>
      }
      toolbar={
        <div className="flex justify-end">
          {mode === "list" ? (
            <PosButton
              onClick={() => {
                resetCreateDraft();
                setMode("create");
              }}
              type="button"
              variant="primary"
            >
              <PlusIcon className="mr-2 h-4 w-4" />
              Nuevo pedido
            </PosButton>
          ) : (
            <PosButton
              onClick={() => setMode("list")}
              type="button"
              variant="neutral"
            >
              Cancelar captura
            </PosButton>
          )}
        </div>
      }
    >
      <div className="grid min-h-0 gap-3 lg:h-full lg:overflow-hidden">
        {mode === "list" ? (
            <ResponsivePaneLayout
              className="h-full gap-2.5"
              compactMode="stack"
              detail={
                <OrderConsultationDetailSurface
                  onRequestCancelOrder={() => {
                    if (!orderDetailQuery.data) {
                      return;
                    }

                    openCancelDialog({
                      advance_amount: orderDetailQuery.data.advance_amount,
                      cancellation_refund_amount: orderDetailQuery.data.cancellation_refund_amount,
                      cancellation_refund_eligible: orderDetailQuery.data.cancellation_refund_eligible,
                      customer_name: orderDetailQuery.data.customer_name,
                      folio: orderDetailQuery.data.folio,
                      id: orderDetailQuery.data.id,
                      status: orderDetailQuery.data.status,
                    });
                  }}
                  orderDetail={orderDetailQuery.data}
                  orderDetailError={orderDetailQuery.error}
                  orderDetailIsPending={selectedOrderId !== null && orderDetailQuery.isPending}
                />
              }
              detailClassName="min-h-0"
              list={
                <ListDetailColumn
                  contentClassName="min-h-0 overflow-hidden"
                  title="Resultados"
                  toolbar={
                    <PosFilterBar
                      actions={
                        <div className="flex flex-wrap items-center gap-2">
                          <input
                            aria-label="Fecha inicial de entrega"
                            className={cn("h-10 min-w-[9.75rem] rounded-lg px-3 text-sm", posInputClass)}
                            onChange={(event) => setRequestedDateFrom(event.target.value)}
                            type="date"
                            value={requestedDateFrom}
                          />
                          <input
                            aria-label="Fecha final de entrega"
                            className={cn("h-10 min-w-[9.75rem] rounded-lg px-3 text-sm", posInputClass)}
                            onChange={(event) => setRequestedDateTo(event.target.value)}
                            type="date"
                            value={requestedDateTo}
                          />
                        </div>
                      }
                      chipFilters={ORDER_STATUS_OPTIONS.map((option) => ({
                        count: getOrderStatusCount(
                          ordersBootstrapQuery.data.status_counters,
                          option.status,
                        ),
                        isActive: selectedStatus === option.status,
                        key: option.status,
                        label: option.label,
                        onSelect: () => {
                          setSelectedStatus(option.status);
                          setSelectedOrderId(null);
                        },
                      }))}
                      countLabel={
                        <ModuleStateChip tone="muted">
                          {ordersListQuery.data?.orders.length ?? 0} pedidos
                        </ModuleStateChip>
                      }
                      searchInput={{
                        ariaLabel: "Buscar pedido por folio, cliente o telefono",
                        className: "min-w-[18rem]",
                        onChange: setSearchText,
                        placeholder: "Buscar por folio, cliente o telefono",
                        value: searchText,
                      }}
                      title="Pedidos registrados"
                    />
                  }
                  tone="muted"
                >
                  {hasInvalidRequestedDateRange ? (
                    <PosEmptyState
                      description="La fecha inicial no puede ser mayor que la fecha final."
                      title="Rango de entrega invalido"
                    />
                  ) : ordersListQuery.error ? (
                    <OperationalStatus
                      action={
                        <PosButton onClick={() => ordersListQuery.refetch()}>
                          Reintentar
                        </PosButton>
                      }
                      description={toOperationalErrorMessage(
                        ordersListQuery.error,
                        "No fue posible consultar la lista de pedidos actual.",
                      )}
                      title="La lista no esta disponible"
                    />
                  ) : (
                    <PosRecordList
                      emptyAction={
                        <PosButton
                          onClick={() => {
                            resetCreateDraft();
                            setMode("create");
                          }}
                          type="button"
                          variant="primary"
                        >
                          <PlusIcon className="mr-2 h-4 w-4" />
                          Nuevo pedido
                        </PosButton>
                      }
                      emptyDescription={getOrderEmptyListDescription({
                        dateFrom: requestedDateFrom,
                        dateTo: requestedDateTo,
                        searchText,
                        status: selectedStatus,
                      })}
                      emptyTitle="Sin pedidos para esta vista"
                      getKey={(order) => order.id}
                      loading={ordersListQuery.isPending}
                      loadingTitle="Consultando pedidos"
                      onSelect={(order) => setSelectedOrderId(order.id)}
                      records={ordersListQuery.data?.orders ?? []}
                      renderContent={(order, state) => (
                        <OrderRecordCard
                          isSelected={state.isSelected}
                          order={order}
                          timezone={ordersBootstrapQuery.data.branch.timezone}
                        />
                      )}
                      selectedKey={selectedOrderId}
                    />
                  )}
                </ListDetailColumn>
              }
              listClassName="min-h-0"
            />
        ) : (
          <div className="grid min-h-0 gap-3 lg:h-full lg:grid-rows-[auto_minmax(0,1fr)]">
            <div className="grid gap-3 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)_minmax(0,1.25fr)]">
              <OperationalField
                className={getOrderGuidedFieldClass({
                  isActive: activeCreateTarget === "customer",
                })}
                label="Cliente"
              >
                <input
                  autoFocus
                  className={cn("h-10 rounded-lg px-3 text-sm shadow-none", posInputClass)}
                  onChange={(event) => setCustomerName(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key !== "Enter") {
                      return;
                    }

                    event.preventDefault();
                    if (event.currentTarget.value.trim().length === 0) {
                      return;
                    }

                    customerPhoneInputRef.current?.focus();
                    customerPhoneInputRef.current?.select();
                  }}
                  placeholder="Nombre del cliente"
                  value={customerName}
                />
              </OperationalField>

              <OperationalField
                className={getOrderGuidedFieldClass({
                  isActive: activeCreateTarget === "phone",
                })}
                label="Telefono"
              >
                <input
                  className={cn("h-10 rounded-lg px-3 text-sm shadow-none", posInputClass)}
                  onChange={(event) => setCustomerPhone(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key !== "Enter") {
                      return;
                    }

                    event.preventDefault();
                    if (event.currentTarget.value.trim().length === 0) {
                      return;
                    }

                    setPickupKeyboardStage("hour");
                    openPickupDatePicker();
                  }}
                  placeholder="Telefono"
                  ref={customerPhoneInputRef}
                  value={customerPhone}
                />
              </OperationalField>

              <OperationalField
                className={getOrderGuidedFieldClass({
                  isActive: activeCreateTarget === "pickup",
                })}
                label="Fecha y hora de recoleccion"
              >
                <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_7rem_6.5rem]">
                  <input
                    className={cn("h-10 rounded-lg px-3 text-sm shadow-none", posInputClass)}
                    onClick={openPickupDatePicker}
                    onChange={(event) => {
                      setRequestedForDraft((state) => ({
                        ...state,
                        date: event.target.value,
                      }));
                      setPickupKeyboardStage("hour");
                      window.requestAnimationFrame(() => {
                        pickupHourInputRef.current?.focus();
                        pickupHourInputRef.current?.select();
                      });
                    }}
                    onKeyDown={(event) => {
                      if (event.key !== "Enter") {
                        return;
                      }

                      event.preventDefault();
                      openPickupDatePicker();
                    }}
                    ref={pickupDateInputRef}
                    type="date"
                    value={requestedForDraft.date}
                  />
                  <input
                    className={cn("h-10 rounded-lg px-3 text-sm shadow-none", posInputClass)}
                    inputMode="numeric"
                    maxLength={2}
                    onBlur={() =>
                      setRequestedForDraft((state) => ({
                        ...state,
                        hour: finalizePickupHourInput(state.hour, initialRequestedForDraft.hour),
                      }))
                    }
                    onChange={(event) =>
                      setRequestedForDraft((state) => ({
                        ...state,
                        hour: sanitizePickupNumericInput(event.target.value),
                      }))
                    }
                    onKeyDown={(event) => {
                      if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                        event.preventDefault();
                        setRequestedForDraft((state) => ({
                          ...state,
                          hour: stepPickupHourInput(state.hour, event.key === "ArrowUp" ? 1 : -1),
                        }));
                        return;
                      }

                      if (event.key !== "Enter") {
                        return;
                      }

                      event.preventDefault();
                      setRequestedForDraft((state) => ({
                        ...state,
                        hour: finalizePickupHourInput(state.hour, initialRequestedForDraft.hour),
                      }));
                      setPickupKeyboardStage("minute");
                      pickupMinuteInputRef.current?.focus();
                      pickupMinuteInputRef.current?.select();
                    }}
                    placeholder="00"
                    ref={pickupHourInputRef}
                    type="text"
                    value={requestedForDraft.hour}
                  />
                  <input
                    className={cn("h-10 rounded-lg px-3 text-sm shadow-none", posInputClass)}
                    inputMode="numeric"
                    maxLength={2}
                    onBlur={() =>
                      setRequestedForDraft((state) => ({
                        ...state,
                        minute: finalizePickupMinuteInput(
                          state.minute,
                          initialRequestedForDraft.minute,
                        ),
                      }))
                    }
                    onChange={(event) =>
                      setRequestedForDraft((state) => ({
                        ...state,
                        minute: sanitizePickupNumericInput(event.target.value),
                      }))
                    }
                    onKeyDown={(event) => {
                      if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                        event.preventDefault();
                        setRequestedForDraft((state) => ({
                          ...state,
                          minute: stepPickupMinuteInput(
                            state.minute,
                            event.key === "ArrowUp" ? 1 : -1,
                          ),
                        }));
                        return;
                      }

                      if (event.key !== "Enter") {
                        return;
                      }

                      event.preventDefault();
                      setRequestedForDraft((state) => ({
                        ...state,
                        minute: finalizePickupMinuteInput(
                          state.minute,
                          initialRequestedForDraft.minute,
                        ),
                      }));
                      setPickupKeyboardStage(null);
                      focusFirstOrderCatalogTarget();
                    }}
                    placeholder="00"
                    ref={pickupMinuteInputRef}
                    type="text"
                    value={requestedForDraft.minute}
                  />
                </div>
              </OperationalField>
            </div>

            <div className="grid min-h-0 gap-3 lg:grid-rows-[minmax(0,1fr)]">
              <section
                className={getOrderGuidedSectionClass(
                  activeCreateTarget === "products",
                  !areCustomerDetailsComplete,
                )}
                data-tone="muted"
              >
                <div className="flex min-w-0 flex-wrap items-start justify-between gap-3 border-b border-[var(--pos-shell-border)] pb-2">
                  <div className="flex min-w-0 items-start gap-3">
                    {draftState.controlState !== CONTROL_STATE_CLASS_SELECTION ? (
                      <Button
                        aria-label="Regresar"
                        className={cn("h-10 px-3", posOutlineButtonClass)}
                        onClick={() => setDraftState((state) => goBackFromOrderControlState(state))}
                        title="Regresar"
                        type="button"
                        variant="outline"
                      >
                        <ArrowLeftIcon className="h-4 w-4" />
                      </Button>
                    ) : null}

                    <div className="min-w-0">
                      <h2 className="text-base font-semibold text-slate-950">
                        {draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION &&
                        draftState.pendingSelection
                          ? draftState.pendingSelection.productClass.name
                          : draftState.controlState === CONTROL_STATE_QUANTITY_CAPTURE &&
                              quantityProduct
                            ? quantityProduct.name
                            : "Agregar lineas al pedido"}
                      </h2>
                      {!areCustomerDetailsComplete ? (
                        <p className="mt-1 text-sm text-slate-600">
                          {activeCreateTarget === "customer"
                            ? "Captura el nombre del cliente para habilitar productos."
                            : activeCreateTarget === "phone"
                              ? "Captura el telefono para habilitar productos."
                              : "Captura la fecha de recoleccion para habilitar productos."}
                        </p>
                      ) : null}
                      <div className="mt-2">
                        <CatalogSubflow activeKey={catalogStepKey} />
                      </div>
                    </div>
                  </div>

                  {draftState.controlState !== CONTROL_STATE_QUANTITY_CAPTURE ? (
                    <SearchField
                      ariaLabel="Buscar en el catalogo del pedido"
                      className="w-full min-w-[14rem] max-w-xs"
                      disabled={!areCustomerDetailsComplete}
                      inputRef={catalogSearchInputRef}
                      inputClassName={cn("h-10 rounded-lg text-sm shadow-sm", posInputClass)}
                      onChange={(value) =>
                        setDraftState((state) => ({
                          ...state,
                          searchText: value,
                        }))
                      }
                      placeholder={catalogSearchPlaceholder}
                      value={draftState.searchText}
                    />
                  ) : null}
                </div>

                <ScrollPane className="pt-3">
                  {isSelectionLoading ? (
                    <OperationalStatus
                      description="Consultando el catalogo disponible para pedidos."
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
                              ? ordersClassProductsQuery.refetch()
                              : ordersCatalogQuery.refetch()
                          }
                        >
                          Reintentar
                        </Button>
                      }
                      description={toOperationalErrorMessage(
                        selectionError,
                        "No fue posible cargar el catalogo para pedidos.",
                      )}
                      title="La seleccion no esta disponible"
                    />
                  ) : null}

                  {!isSelectionLoading &&
                  !selectionError &&
                  draftState.controlState === CONTROL_STATE_CLASS_SELECTION ? (
                    sortedClasses.length > 0 ? (
                      <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                        {sortedClasses.map((productClass, index) => (
                          <CatalogSelectionCard
                            code={productClass.code}
                            isDisabled={!areCustomerDetailsComplete}
                            isPrimaryControl={index === 0}
                            key={productClass.id}
                            name={productClass.name}
                            onSelect={() =>
                              setDraftState((state) => selectClassForOrder(state, productClass))
                            }
                            shortcutLabel={getSelectionShortcutLabel(index)}
                            variant="pos"
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-6 text-sm text-slate-600">
                        No hay clases disponibles para la busqueda actual.
                      </div>
                    )
                  ) : null}

                  {!isSelectionLoading &&
                  !selectionError &&
                  draftState.controlState === CONTROL_STATE_PRODUCT_SELECTION ? (
                    sortedProducts.length > 0 ? (
                      <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                        {sortedProducts.map((product, index) => (
                          <CatalogSelectionCard
                            code={product.code}
                            isDisabled={!areCustomerDetailsComplete}
                            isPrimaryControl={index === 0}
                            key={product.id}
                            name={product.name}
                            onSelect={() =>
                              setDraftState((state) => selectProductForOrder(state, product))
                            }
                            priceText={formatCurrency(product.unit_price)}
                            shortcutLabel={getSelectionShortcutLabel(index)}
                            variant="pos"
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-6 text-sm text-slate-600">
                        No hay productos exactos para esta busqueda.
                      </div>
                    )
                  ) : null}

                  {quantitySelection !== null && quantityProduct !== null ? (
                    <div className="mx-auto grid max-w-3xl gap-4 rounded-2xl border border-[var(--pos-shell-border)] bg-white p-4 shadow-sm">
                      <div className="grid gap-4 lg:grid-cols-[7rem_minmax(0,1fr)]">
                        <CatalogVisual
                          className="min-h-[7rem]"
                          code={quantityProduct.code}
                          name={quantityProduct.name}
                        />

                        <div className="grid gap-3">
                          <div className="min-w-0">
                            <p className="truncate text-base font-semibold text-slate-950">
                              {quantityProduct.name}
                            </p>
                            <p className="mt-1 truncate text-sm text-slate-600">
                              {quantitySelection.productClass.name}
                            </p>
                            <div className="mt-3 flex flex-wrap items-center gap-2">
                              <span
                                className="pos-chip"
                                data-tone={canAddPendingLine ? "primary" : "warning"}
                              >
                                {canAddPendingLine ? "Cantidad lista" : "Pendiente"}
                              </span>
                              <span className="pos-chip" data-tone="muted">
                                Enter agrega
                              </span>
                              <span className="pos-chip" data-tone="muted">
                                Esc regresa
                              </span>
                            </div>
                          </div>

                          <div className="grid justify-items-center gap-3">
                            <input
                              className={cn(
                                "h-14 w-full max-w-[15rem] rounded-xl px-4 text-center text-[2rem] font-semibold tracking-tight shadow-none",
                                posInputClass,
                              )}
                              inputMode="decimal"
                              onChange={(event) =>
                                setDraftState((state) =>
                                  setPendingQuantityText(state, event.target.value),
                                )
                              }
                              onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                  event.preventDefault();
                                  if (!canAddPendingLine) {
                                    setSelectionErrorMessage(
                                      "Captura una cantidad valida antes de agregar la linea.",
                                    );
                                    return;
                                  }

                                  try {
                                    setDraftState((state) => addPendingSelectionLine(state));
                                    setSelectionErrorMessage(null);
                                  } catch (error) {
                                    setSelectionErrorMessage(
                                      toOperationalErrorMessage(
                                        error,
                                        "Captura una cantidad valida antes de agregar la linea.",
                                      ),
                                    );
                                  }
                                }

                                if (event.key === "Escape") {
                                  event.preventDefault();
                                  setDraftState((state) => goBackFromOrderControlState(state));
                                }
                              }}
                              placeholder="0"
                              ref={quantityInputRef}
                              value={quantitySelection.quantityText}
                            />

                            <Button
                              className={cn("h-10 px-5", posPrimaryButtonClass)}
                              disabled={!canAddPendingLine}
                              onClick={() => {
                                if (!canAddPendingLine) {
                                  setSelectionErrorMessage(
                                    "Captura una cantidad valida antes de agregar la linea.",
                                  );
                                  return;
                                }

                                try {
                                  setDraftState((state) => addPendingSelectionLine(state));
                                  setSelectionErrorMessage(null);
                                } catch (error) {
                                  setSelectionErrorMessage(
                                    toOperationalErrorMessage(
                                      error,
                                      "Captura una cantidad valida antes de agregar la linea.",
                                    ),
                                  );
                                }
                              }}
                              type="button"
                            >
                              Agregar linea
                            </Button>
                          </div>

                          {selectionErrorMessage ? (
                            <InlineNotice tone="error">{selectionErrorMessage}</InlineNotice>
                          ) : !canAddPendingLine ? (
                            <InlineNotice tone="info">
                              Captura una cantidad mayor que cero.
                            </InlineNotice>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  ) : null}
                </ScrollPane>
              </section>

            </div>
          </div>
        )}
      </div>
      <OrderActionConfirmDialog
        cancelReason={cancelReason}
        cancelReasonError={cancelReasonError}
        isPending={
          createOrderMutation.isPending ||
          markReadyMutation.isPending ||
          deliverMutation.isPending ||
          cancelMutation.isPending
        }
        onCancel={() => {
          setOrderActionDialog(null);
          setCancelReason("");
          setCancelReasonError(null);
        }}
        onCancelReasonChange={(value) => {
          setCancelReason(value);
          if (cancelReasonError !== null) {
            setCancelReasonError(null);
          }
        }}
        onConfirm={() => {
          if (orderActionDialog === null) {
            return;
          }

          if (orderActionDialog.kind === "discard") {
            resetCreateDraft();
            setMode("list");
            return;
          }

          if (cancelReason.trim().length < 4) {
            setCancelReasonError("Captura un motivo claro antes de cancelar el pedido.");
            return;
          }

          void cancelMutation.mutateAsync();
        }}
        state={orderActionDialog}
      />
    </ContinuousWorkspaceSheet>
  );
}

