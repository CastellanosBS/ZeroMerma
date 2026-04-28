import { type ButtonHTMLAttributes, type ReactNode, type Ref, useEffect, useRef } from "react";

import { focusEdgeItem, focusRelativeItem } from "../lib/keyboard-shortcuts";
import { cn } from "../lib/utils";
import { CatalogVisual } from "./catalog-visual";

function assignRef<TValue>(targetRef: Ref<TValue> | undefined, value: TValue) {
  if (!targetRef) {
    return;
  }

  if (typeof targetRef === "function") {
    targetRef(value);
    return;
  }

  (targetRef as { current: TValue }).current = value;
}

export function CatalogSelectionCard({
  badge,
  buttonRef,
  code,
  isActive = false,
  isDisabled = false,
  isPrimaryControl = false,
  name,
  onCardFocus,
  onCardKeyDown,
  onSelect,
  priceText,
  shortcutLabel,
  tabIndex,
  variant = "default",
}: {
  badge?: ReactNode;
  buttonRef?: Ref<HTMLButtonElement>;
  code: string;
  isActive?: boolean;
  isDisabled?: boolean;
  isPrimaryControl?: boolean;
  name: string;
  onCardFocus?: ButtonHTMLAttributes<HTMLButtonElement>["onFocus"];
  onCardKeyDown?: ButtonHTMLAttributes<HTMLButtonElement>["onKeyDown"];
  onSelect: () => void;
  priceText?: string | null;
  shortcutLabel?: string | null;
  tabIndex?: number;
  variant?: "default" | "pos";
}) {
  const internalButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (isPrimaryControl && !isDisabled) {
      internalButtonRef.current?.focus();
    }
  }, [isDisabled, isPrimaryControl]);

  return (
    <button
      data-pos-catalog-card="true"
      className={cn(
        "group grid grid-rows-[minmax(0,1fr)_auto] gap-2 overflow-hidden rounded-[1.1rem] border bg-white p-2 text-left shadow-[var(--ui-shadow-subtle)] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]",
        variant === "pos" ? "min-h-[13rem]" : "min-h-[13rem]",
        (isPrimaryControl || isActive) &&
          !isDisabled &&
          "border-[var(--pos-primary)] ring-2 ring-[var(--pos-ring)]",
        isDisabled
          ? "cursor-not-allowed border-[var(--pos-shell-border)] opacity-50"
          : "border-[var(--pos-shell-border)] hover:-translate-y-0.5 hover:border-[var(--pos-primary)] hover:shadow-[0_12px_28px_rgba(15,23,42,0.08)]",
      )}
      disabled={isDisabled}
      onClick={onSelect}
      onFocus={onCardFocus}
      onKeyDown={(event) => {
        onCardKeyDown?.(event);
        if (event.defaultPrevented) {
          return;
        }

        if (event.key === "ArrowRight" || event.key === "ArrowDown") {
          if (
            focusRelativeItem({
              currentTarget: event.currentTarget,
              direction: 1,
              selector: "[data-pos-catalog-card='true']",
            })
          ) {
            event.preventDefault();
          }
          return;
        }

        if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
          if (
            focusRelativeItem({
              currentTarget: event.currentTarget,
              direction: -1,
              selector: "[data-pos-catalog-card='true']",
            })
          ) {
            event.preventDefault();
          }
          return;
        }

        if (event.key === "Home") {
          if (
            focusEdgeItem({
              currentTarget: event.currentTarget,
              edge: "first",
              selector: "[data-pos-catalog-card='true']",
            })
          ) {
            event.preventDefault();
          }
          return;
        }

        if (event.key === "End") {
          if (
            focusEdgeItem({
              currentTarget: event.currentTarget,
              edge: "last",
              selector: "[data-pos-catalog-card='true']",
            })
          ) {
            event.preventDefault();
          }
        }
      }}
      ref={(node) => {
        internalButtonRef.current = node;
        assignRef(buttonRef, node);
      }}
      tabIndex={tabIndex}
      type="button"
    >
      <div className="min-h-0 rounded-[0.95rem] bg-[var(--pos-shell-muted)]/60 p-1">
        <CatalogVisual
          className={cn(
            "h-full border-white/75",
            variant === "pos" ? "min-h-[8.6rem]" : "min-h-[8.6rem]",
          )}
          code={code}
          name={name}
        />
      </div>

      <div className="grid min-h-[1.85rem] min-w-0 gap-1 border-t border-[var(--pos-shell-border)] px-0.5 pt-1.5">
        {badge ? <div className="flex min-w-0 items-center gap-1.5">{badge}</div> : null}
        <div className="flex min-w-0 items-center gap-2">
          <p className="min-w-0 flex-1 truncate text-[0.93rem] font-semibold leading-5 text-slate-950">
            {name}
          </p>
          {priceText ? (
            <span className="shrink-0 text-[13px] font-semibold text-[var(--pos-primary)] [font-variant-numeric:tabular-nums]">
              {priceText}
            </span>
          ) : null}
          {shortcutLabel ? (
            <span className="inline-flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full border border-[var(--pos-shell-border)] bg-[var(--pos-primary-soft)] px-1.5 text-[11px] font-semibold text-[var(--pos-primary)]">
              {shortcutLabel}
            </span>
          ) : null}
        </div>
      </div>
    </button>
  );
}
