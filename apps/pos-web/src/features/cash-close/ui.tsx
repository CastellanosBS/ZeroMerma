import type { KeyboardEventHandler, Ref } from "react";

import { MetricCard } from "../../components/pos-module-primitives";
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  MoneyIcon,
  TrashIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import { cn } from "../../lib/utils";
import type { CashCloseCountValueState, CashCloseDraftState, CashCloseSection } from "./model";
import { getCloseToneClasses } from "./ui-support";

type CloseTone = "danger" | "info" | "success" | "warning";
type CloseStepperStatus = "blocked" | "completed" | "current" | "upcoming";

function getStepperStatusClasses(status: CloseStepperStatus) {
  switch (status) {
    case "current":
      return {
        container: "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)] shadow-[var(--ui-shadow-subtle)]",
        marker: "bg-white text-[var(--pos-primary)] border-[var(--pos-primary)]",
        text: "text-slate-950",
      };
    case "completed":
      return {
        container: "border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)]",
        marker: "bg-white text-[var(--ui-color-success)] border-transparent",
        text: "text-slate-700",
      };
    case "blocked":
      return {
        container: "border-dashed border-[var(--pos-shell-border)] bg-transparent opacity-70",
        marker: "bg-transparent text-slate-400 border-[var(--pos-shell-border)]",
        text: "text-slate-400",
      };
    default:
      return {
        container: "border-transparent bg-transparent hover:border-[var(--pos-shell-border)] hover:bg-[var(--pos-shell-muted)]",
        marker: "bg-[var(--pos-shell-muted)] text-slate-500 border-[var(--pos-shell-border)]",
        text: "text-slate-700",
      };
  }
}

function getCountStateTone(state: CashCloseCountValueState): "muted" | "primary" {
  return state === "CAPTURED" ? "primary" : "muted";
}

export function CloseStageStrip({
  activeSection,
  onSelect,
  sections,
}: {
  activeSection: CashCloseSection;
  onSelect: (section: CashCloseSection) => void;
  sections: Array<{
    description: string;
    isClickable: boolean;
    key: CashCloseSection;
    label: string;
    status: CloseStepperStatus;
  }>;
}) {
  return (
    <div className="grid gap-2 rounded-[24px] border border-[var(--pos-shell-border)] bg-white p-2 shadow-[var(--pos-subtle-shadow)] lg:grid-cols-5">
      {sections.map((section, index) => {
        const statusClasses = getStepperStatusClasses(section.status);
        const isCurrent = section.key === activeSection;

        return (
          <button
            aria-current={isCurrent ? "step" : undefined}
            className={cn(
              "grid min-w-0 gap-1 rounded-2xl border px-3 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]",
              statusClasses.container,
              !section.isClickable && "cursor-not-allowed",
            )}
            disabled={!section.isClickable}
            key={section.key}
            onClick={() => onSelect(section.key)}
            type="button"
          >
            <div className="flex min-w-0 items-center gap-2">
              <span
                className={cn(
                  "inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[12px] font-semibold",
                  statusClasses.marker,
                )}
              >
                {section.status === "completed" ? (
                  <CheckCircleIcon className="h-4 w-4" />
                ) : section.status === "current" ? (
                  <ClockIcon className="h-4 w-4" />
                ) : (
                  index + 1
                )}
              </span>
              <span className={cn("min-w-0 text-sm font-semibold", statusClasses.text)}>
                {section.label}
              </span>
            </div>
            <p className="hidden text-[13px] leading-5 text-slate-600 xl:block">
              {section.description}
            </p>
          </button>
        );
      })}
    </div>
  );
}

export function PaymentCountRow({
  countState,
  differenceAmount,
  expectedAmount,
  helperText,
  inputRef,
  isCashMethod,
  isDifferenceVisible,
  label,
  onChange,
  onInputKeyDown,
  paymentMethodCode,
  value,
}: {
  countState: CashCloseCountValueState;
  differenceAmount: string | null;
  expectedAmount: string;
  helperText: string;
  inputRef?: Ref<HTMLInputElement>;
  isCashMethod: boolean;
  isDifferenceVisible: boolean;
  label: string;
  onChange: (value: string) => void;
  onInputKeyDown?: KeyboardEventHandler<HTMLInputElement>;
  paymentMethodCode: string;
  value: string;
}) {
  return (
    <div
      className={cn(
        "grid gap-3 rounded-[22px] border px-4 py-4",
        isCashMethod
          ? "border-[var(--pos-financial-border)] bg-[var(--pos-financial-bg)]"
          : "border-[var(--pos-shell-border)] bg-white",
      )}
    >
      <div className="flex min-w-0 items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                isCashMethod
                  ? "bg-white text-[var(--pos-primary)]"
                  : "bg-[var(--pos-shell-muted)] text-slate-500",
              )}
            >
              <MoneyIcon className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-950">{label}</p>
              <p className="mt-0.5 text-[13px] leading-5 text-slate-600">{helperText}</p>
            </div>
          </div>
        </div>
        <span className="pos-chip" data-tone={getCountStateTone(countState)}>
          {countState === "CAPTURED" ? "Capturado" : "Pendiente"}
        </span>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,12rem)_repeat(2,minmax(0,1fr))]">
        <label className="grid gap-1.5">
          <span className="text-sm font-semibold text-slate-800">Contado</span>
          <input
            aria-label={`Total contado en ${label}`}
            className={cn(
              "h-12 rounded-2xl border border-[var(--pos-shell-border)] bg-white px-3 text-right text-xl font-semibold text-slate-950 outline-none ring-0 transition [font-variant-numeric:tabular-nums] focus:border-[var(--pos-primary)] focus:ring-2 focus:ring-[var(--pos-ring)]",
              countState === "PENDING" && "text-slate-400",
            )}
            id={`close-payment-method-${paymentMethodCode}`}
            inputMode="decimal"
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={onInputKeyDown}
            placeholder="0.00"
            ref={inputRef}
            value={value}
          />
        </label>

        <div className="rounded-2xl border border-[var(--pos-shell-border)] bg-white px-3 py-3">
          <p className="text-[13px] font-medium text-slate-600">Esperado</p>
          <p className="mt-1 text-base font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
            {expectedAmount}
          </p>
        </div>

        <div className="rounded-2xl border border-[var(--pos-shell-border)] bg-white px-3 py-3">
          <p className="text-[13px] font-medium text-slate-600">Diferencia</p>
          <p className="mt-1 text-base font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
            {isDifferenceVisible && differenceAmount !== null ? differenceAmount : "Pendiente"}
          </p>
        </div>
      </div>
    </div>
  );
}

export function CountedLineRow({
  line,
  onDecrement,
  onIncrement,
  onRemove,
}: {
  line: CashCloseDraftState["countedProductDraftLines"][number];
  onDecrement: () => void;
  onIncrement: () => void;
  onRemove: () => void;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 border-t border-[var(--pos-shell-border)] px-3 py-2.5 first:border-t-0">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-slate-950">{line.productName}</p>
        <p className="mt-0.5 truncate text-[13px] leading-5 text-slate-600">
          {line.productClassName}
        </p>
      </div>

      <div className="flex items-center gap-1.5 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-1.5 py-1">
        <button
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--pos-shell-border)] bg-white text-sm font-medium text-slate-900 transition hover:border-[var(--pos-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
          onClick={onDecrement}
          type="button"
        >
          -
        </button>
        <span className="min-w-12 text-center text-sm font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
          {line.quantityText}
        </span>
        <button
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--pos-shell-border)] bg-white text-sm font-medium text-slate-900 transition hover:border-[var(--pos-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
          onClick={onIncrement}
          type="button"
        >
          +
        </button>
      </div>

      <button
        aria-label={`Eliminar ${line.productName}`}
        className="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
        onClick={onRemove}
        type="button"
      >
        <TrashIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

export function CloseSummaryPanel({
  actionDisabled,
  actionDisabledReason,
  actionLabel,
  blockerMessages,
  countedCardText,
  countedCashText,
  countedLineCount,
  countedUnitsText,
  currentSectionLabel,
  detectedDifferenceCount,
  errorMessage,
  helperText,
  isSubmitting,
  onAction,
  readinessLabel,
  readinessTone,
  sessionStateLabel,
  warningCount,
  warningMessages,
}: {
  actionDisabled: boolean;
  actionDisabledReason: string | null;
  actionLabel: string;
  blockerMessages: string[];
  countedCardText: string;
  countedCashText: string;
  countedLineCount: number;
  countedUnitsText: string;
  currentSectionLabel: string;
  detectedDifferenceCount: number;
  errorMessage: string | null;
  helperText: string;
  isSubmitting: boolean;
  onAction: () => void;
  readinessLabel: string;
  readinessTone: CloseTone;
  sessionStateLabel: string;
  warningCount: number;
  warningMessages: string[];
}) {
  const controlTitle =
    blockerMessages.length > 0
      ? "Bloqueos del cierre"
      : warningMessages.length > 0
        ? "Advertencias del cierre"
        : "Estado del cierre";
  const controlMessages =
    blockerMessages.length > 0 ? blockerMessages : warningMessages.length > 0 ? warningMessages : [];

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_auto_minmax(0,1fr)_auto] gap-3 rounded-[24px] border border-[var(--pos-shell-border)] bg-white p-3 shadow-[var(--pos-subtle-shadow)]">
      <div className="grid gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--pos-primary)]">
          Cerrar turno
        </p>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-slate-950">{currentSectionLabel}</h2>
            <p className="mt-1 text-sm leading-5 text-slate-600">{sessionStateLabel}</p>
          </div>
          <span
            className={cn(
              "rounded-full px-2 py-1 text-xs font-semibold whitespace-nowrap",
              getCloseToneClasses(readinessTone),
            )}
          >
            {readinessLabel}
          </span>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <MetricCard helper="Efectivo" tone="financial" value={countedCashText} />
        <MetricCard helper="Tarjeta" value={countedCardText} />
        <MetricCard helper="Lineas" value={countedLineCount} />
        <MetricCard helper="Unidades" value={countedUnitsText} />
        <MetricCard helper="Diferencias" value={detectedDifferenceCount} />
        <MetricCard helper="Advertencias" value={warningCount} />
      </div>

      <div className="grid min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-2 rounded-2xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">{controlTitle}</p>
          <p className="mt-1 text-sm leading-5 text-slate-600">{helperText}</p>
        </div>

        <div className="min-h-0 overflow-y-auto pr-1">
          {controlMessages.length > 0 ? (
            <div className="grid gap-2">
              {controlMessages.map((message) => (
                <div
                  className={cn(
                    "flex items-start gap-2 rounded-xl border px-3 py-2 text-sm",
                    blockerMessages.length > 0
                      ? getCloseToneClasses("danger")
                      : getCloseToneClasses("warning"),
                  )}
                  key={message}
                >
                  <AlertTriangleIcon className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{message}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className={cn("rounded-xl border px-3 py-2 text-sm", getCloseToneClasses("info"))}>
              {actionDisabledReason ?? "El cierre esta listo para continuar."}
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-2 border-t border-[var(--pos-shell-border)] pt-2">
        {errorMessage ? (
          <div className={cn("rounded-xl border px-3 py-2 text-sm", getCloseToneClasses("danger"))}>
            {errorMessage}
          </div>
        ) : null}
        <Button
          className="h-11 w-full"
          disabled={actionDisabled}
          onClick={onAction}
          type="button"
        >
          {isSubmitting ? "Procesando..." : actionLabel}
        </Button>
        {actionDisabledReason ? (
          <p className="text-sm leading-5 text-slate-600">{actionDisabledReason}</p>
        ) : null}
      </div>
    </div>
  );
}
