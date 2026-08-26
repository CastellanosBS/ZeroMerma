import type { ReactNode } from "react";

import { cn } from "../lib/utils";

type PosPaymentSurfaceTone = "default" | "fixed" | "input" | "pending" | "success";

function getSurfaceToneClass(tone: PosPaymentSurfaceTone): string {
  if (tone === "fixed") {
    return "border-[#747474] bg-[#747474]";
  }

  if (tone === "input") {
    return "border-[#7aaef7] bg-[#e8f3ff]";
  }

  if (tone === "pending") {
    return "border-[#e1a0a8] bg-[#fff1f3]";
  }

  if (tone === "success") {
    return "border-[#9fd3b3] bg-[#e8f8ef]";
  }

  return "border-[var(--pos-shell-border)] bg-white";
}

function getIconClass(tone: PosPaymentSurfaceTone): string {
  if (tone === "fixed") {
    return "text-slate-100";
  }

  if (tone === "pending") {
    return "text-[var(--ui-color-danger)]";
  }

  if (tone === "success") {
    return "text-[var(--ui-color-success)]";
  }

  return "text-[var(--pos-primary)]";
}

function getLabelClass(tone: PosPaymentSurfaceTone): string {
  if (tone === "fixed") {
    return "text-slate-100";
  }

  if (tone === "pending") {
    return "text-[var(--ui-color-danger-strong)]";
  }

  if (tone === "success") {
    return "text-[var(--ui-color-success)]";
  }

  return "text-slate-800";
}

function getValueClass(tone: PosPaymentSurfaceTone): string {
  return tone === "fixed" ? "text-white" : "text-slate-950";
}

export function PosPaymentMethodButton({
  className,
  disabled = false,
  icon,
  isActive,
  label,
  onClick,
  shortcutLabel,
}: {
  className?: string;
  disabled?: boolean;
  icon: ReactNode;
  isActive: boolean;
  label: string;
  onClick: () => void;
  shortcutLabel?: string;
}) {
  return (
    <button
      aria-pressed={isActive}
      className={cn(
        "pos-shortcut-corner grid min-h-[4.75rem] min-w-0 justify-items-center gap-1.5 rounded-xl border px-2 py-2.5 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
        isActive
          ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)] text-[var(--pos-primary)] shadow-sm"
          : "border-[var(--pos-shell-border)] bg-white text-slate-700 hover:border-[var(--pos-primary)] hover:bg-[var(--pos-shell-muted)] hover:text-slate-950",
        disabled &&
          "cursor-not-allowed opacity-60 hover:border-[var(--pos-shell-border)] hover:bg-white hover:text-slate-700",
        className,
      )}
      data-shortcut={shortcutLabel ?? undefined}
      data-shortcut-tone={isActive ? "primary" : "default"}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <span className="flex shrink-0 items-center justify-center text-[var(--pos-primary)]">
        {icon}
      </span>
      <span className="text-center leading-4">{label}</span>
    </button>
  );
}

export function PosPaymentInlineCard({
  children,
  className,
  icon,
  label,
  tone = "default",
}: {
  children: ReactNode;
  className?: string;
  icon: ReactNode;
  label: string;
  tone?: PosPaymentSurfaceTone;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-xl border px-3 py-2.5 shadow-sm",
        getSurfaceToneClass(tone),
        className,
      )}
    >
      <div className="flex min-w-0 items-center gap-2.5">
        <span className={cn("flex shrink-0 items-center justify-center", getIconClass(tone))}>
          {icon}
        </span>
        <span
          className={cn(
            "truncate text-[0.98rem] font-semibold leading-5 tracking-[-0.01em]",
            getLabelClass(tone),
          )}
        >
          {label}
        </span>
      </div>
      {children}
    </div>
  );
}

export function PosPaymentValueCard({
  className,
  icon,
  label,
  tone = "default",
  value,
}: {
  className?: string;
  icon: ReactNode;
  label: string;
  tone?: PosPaymentSurfaceTone;
  value: string;
}) {
  return (
    <PosPaymentInlineCard className={className} icon={icon} label={label} tone={tone}>
      <p
        className={cn(
          "min-w-[6.25rem] text-right text-[1.72rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
          getValueClass(tone),
        )}
      >
        {value}
      </p>
    </PosPaymentInlineCard>
  );
}

export function PosPaymentInputCard({
  children,
  className,
  icon,
  label,
  tone = "input",
}: {
  children: ReactNode;
  className?: string;
  icon: ReactNode;
  label: string;
  tone?: Extract<PosPaymentSurfaceTone, "default" | "input">;
}) {
  return (
    <PosPaymentInlineCard className={className} icon={icon} label={label} tone={tone}>
      <div className="w-full min-w-[7.25rem] max-w-[8.5rem]">{children}</div>
    </PosPaymentInlineCard>
  );
}
