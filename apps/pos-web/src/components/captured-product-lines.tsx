import type { KeyboardEvent, ReactNode, Ref } from "react";

import { cn } from "../lib/utils";
import { MinusIcon, PlusIcon, TrashIcon } from "./pos-icons";
import { posInputClass } from "../features/pos-theme/theme";

type CapturedProductQuantityMode = "display" | "input";

export function CapturedProductLineList({
  children,
  className,
  emptyState,
}: {
  children?: ReactNode;
  className?: string;
  emptyState?: ReactNode;
}) {
  return (
    <div className={cn("overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white", className)}>
      {children ?? emptyState}
    </div>
  );
}

export function CapturedProductLineRow({
  amount,
  amountTitle,
  disabled = false,
  inputRef,
  isSelected = false,
  name,
  onBeginQuantityEdit,
  onCancelQuantityEdit,
  onCommitQuantity,
  onDecrement,
  onIncrement,
  onQuantityChange,
  onRemove,
  onSelect,
  quantityMode = "display",
  quantityText,
  quantityWidthClassName,
  removeLabel,
}: {
  amount?: ReactNode;
  amountTitle?: string;
  disabled?: boolean;
  inputRef?: Ref<HTMLInputElement>;
  isSelected?: boolean;
  name: string;
  onBeginQuantityEdit?: () => void;
  onCancelQuantityEdit?: () => void;
  onCommitQuantity?: () => void;
  onDecrement?: () => void;
  onIncrement?: () => void;
  onQuantityChange?: (value: string) => void;
  onRemove?: () => void;
  onSelect?: () => void;
  quantityMode?: CapturedProductQuantityMode;
  quantityText: string;
  quantityWidthClassName?: string;
  removeLabel?: string;
}) {
  const hasAmount = amount !== undefined && amount !== null;

  function handleInputKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    event.stopPropagation();
    if (event.key === "Enter" || event.key === "NumpadEnter") {
      event.preventDefault();
      onCommitQuantity?.();
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      onCancelQuantityEdit?.();
    }
  }

  return (
    <div
      aria-selected={onSelect ? isSelected : undefined}
      className={cn(
        "grid items-center gap-1.5 border-t border-[var(--pos-shell-border)] px-2 py-1.5 first:border-t-0",
        hasAmount
          ? "grid-cols-[minmax(0,1fr)_auto_auto_auto]"
          : "grid-cols-[minmax(0,1fr)_auto_auto]",
        isSelected && "bg-[var(--pos-primary-soft)]/70",
      )}
      onClick={onSelect}
      onFocusCapture={onSelect}
      role={onSelect ? "row" : undefined}
      tabIndex={onSelect ? 0 : undefined}
    >
      <p className="min-w-0 truncate text-[13px] font-medium leading-5 text-slate-950" title={name}>
        {name}
      </p>

      <div className="flex items-center gap-0 rounded-md border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-0.5 py-0.5">
        {onDecrement ? (
          <button
            aria-label={`Restar cantidad de ${name}`}
            className="flex h-7 w-7 items-center justify-center rounded-sm text-slate-900 transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] disabled:pointer-events-none disabled:opacity-45"
            disabled={disabled}
            onClick={(event) => {
              event.stopPropagation();
              onDecrement();
            }}
            type="button"
          >
            <MinusIcon className="h-3 w-3" />
          </button>
        ) : null}

        <div className={cn("w-[3.1rem]", quantityWidthClassName)}>
          {quantityMode === "input" ? (
            <input
              aria-label={`Cantidad de ${name}`}
              className={cn(
                "h-7 w-full rounded-sm px-1 text-center text-[13px] font-semibold text-slate-950 [font-variant-numeric:tabular-nums]",
                posInputClass,
              )}
              disabled={disabled}
              inputMode="decimal"
              onBlur={onCommitQuantity}
              onChange={(event) => onQuantityChange?.(event.target.value)}
              onClick={(event) => event.stopPropagation()}
              onKeyDown={handleInputKeyDown}
              ref={inputRef}
              value={quantityText}
            />
          ) : onBeginQuantityEdit ? (
            <button
              aria-label={`Editar cantidad de ${name}`}
              className="h-7 w-full rounded-sm px-1 text-center text-[13px] font-semibold text-slate-950 transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] disabled:pointer-events-none disabled:opacity-45 [font-variant-numeric:tabular-nums]"
              disabled={disabled}
              onClick={(event) => {
                event.stopPropagation();
                onBeginQuantityEdit();
              }}
              type="button"
            >
              {quantityText}
            </button>
          ) : (
            <span className="flex h-7 w-full items-center justify-center rounded-sm px-1 text-center text-[13px] font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
              {quantityText}
            </span>
          )}
        </div>

        {onIncrement ? (
          <button
            aria-label={`Sumar cantidad de ${name}`}
            className="flex h-7 w-7 items-center justify-center rounded-sm text-slate-900 transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] disabled:pointer-events-none disabled:opacity-45"
            disabled={disabled}
            onClick={(event) => {
              event.stopPropagation();
              onIncrement();
            }}
            type="button"
          >
            <PlusIcon className="h-3 w-3" />
          </button>
        ) : null}
      </div>

      {hasAmount ? (
        <div
          className="min-w-[3.8rem] overflow-hidden text-ellipsis whitespace-nowrap text-right text-[13px] font-semibold text-slate-950 [font-variant-numeric:tabular-nums]"
          title={amountTitle}
        >
          {amount}
        </div>
      ) : null}

      {onRemove ? (
        <button
          aria-label={removeLabel ?? `Eliminar ${name}`}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] disabled:pointer-events-none disabled:opacity-45"
          disabled={disabled}
          onClick={(event) => {
            event.stopPropagation();
            onRemove();
          }}
          title="Eliminar"
          type="button"
        >
          <TrashIcon className="h-3.5 w-3.5" />
        </button>
      ) : null}
    </div>
  );
}
