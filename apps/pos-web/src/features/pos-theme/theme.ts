import type { CSSProperties } from "react";

import type { PosBootstrapResponse } from "../../lib/api-contracts";
import { cn } from "../../lib/utils";

export type PosBranchBrandKey = "EL_MEJOR_PAN" | "MERENNA";

interface PosBranchTheme {
  brandKey: PosBranchBrandKey;
  brandMark: string;
  style: CSSProperties;
}

export type PosButtonVariant = "danger" | "ghost" | "neutral" | "primary" | "secondary";
export type PosStatusBadgeVariant =
  | "blocked"
  | "confirmed"
  | "draft"
  | "error"
  | "pending"
  | "ready"
  | "success"
  | "warning";

const branchBrandMapping: Record<string, PosBranchBrandKey> = {
  MAIN: "EL_MEJOR_PAN",
};

const branchThemes: Record<PosBranchBrandKey, PosBranchTheme> = {
  EL_MEJOR_PAN: {
    brandKey: "EL_MEJOR_PAN",
    brandMark: "EMP",
    style: {
      "--pos-accent": "#C5A46A",
      "--pos-accent-soft": "#F8F1E4",
      "--pos-brand-mark-bg": "#1F4B6E",
      "--pos-brand-mark-fg": "#FFFFFF",
    } as CSSProperties,
  },
  MERENNA: {
    brandKey: "MERENNA",
    brandMark: "MER",
    style: {
      "--pos-accent": "#856788",
      "--pos-accent-soft": "#F2EDF4",
      "--pos-brand-mark-bg": "#49637B",
      "--pos-brand-mark-fg": "#FFFFFF",
    } as CSSProperties,
  },
};

export const posPrimaryButtonClass =
  cn(
    "inline-flex items-center justify-center gap-2 rounded-[var(--pos-radius-control)] border font-medium transition-colors shadow-sm",
    "disabled:pointer-events-none disabled:opacity-50",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
    "border-[var(--pos-button-primary-border)] bg-[var(--pos-button-primary-bg)] text-[var(--pos-button-primary-fg)] hover:border-[var(--pos-button-primary-hover-border)] hover:bg-[var(--pos-button-primary-hover-bg)]",
  );

export const posOutlineButtonClass =
  cn(
    "inline-flex items-center justify-center gap-2 rounded-[var(--pos-radius-control)] border font-medium transition-colors shadow-sm",
    "disabled:pointer-events-none disabled:opacity-50",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
    "border-[var(--pos-button-neutral-border)] bg-[var(--pos-button-neutral-bg)] text-[var(--pos-button-neutral-fg)] hover:border-[var(--pos-button-neutral-hover-border)] hover:bg-[var(--pos-button-neutral-hover-bg)]",
  );

export const posSecondaryButtonClass = cn(
  "inline-flex items-center justify-center gap-2 rounded-[var(--pos-radius-control)] border font-medium transition-colors shadow-sm",
  "disabled:pointer-events-none disabled:opacity-50",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
  "border-[var(--pos-button-secondary-border)] bg-[var(--pos-button-secondary-bg)] text-[var(--pos-button-secondary-fg)] hover:border-[var(--pos-button-secondary-hover-border)] hover:bg-[var(--pos-button-secondary-hover-bg)]",
);

export const posNeutralButtonClass = posOutlineButtonClass;

export const posDangerButtonClass = cn(
  "inline-flex items-center justify-center gap-2 rounded-[var(--pos-radius-control)] border font-medium transition-colors shadow-sm",
  "disabled:pointer-events-none disabled:opacity-50",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
  "border-[var(--pos-button-danger-border)] bg-[var(--pos-button-danger-bg)] text-[var(--pos-button-danger-fg)] hover:border-[var(--pos-button-danger-hover-border)] hover:bg-[var(--pos-button-danger-hover-bg)]",
);

export const posGhostButtonClass = cn(
  "inline-flex items-center justify-center gap-2 rounded-[var(--pos-radius-control)] border border-transparent bg-transparent font-medium shadow-none transition-colors",
  "disabled:pointer-events-none disabled:opacity-50",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white",
  "text-[var(--pos-button-ghost-fg)] hover:bg-[var(--pos-button-ghost-hover-bg)] hover:text-[var(--pos-button-ghost-hover-fg)]",
);

export const posFocusRingClass =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-white";

export const posInputClass =
  cn(
    "border border-[var(--pos-shell-border)] bg-white text-slate-950 outline-none shadow-sm transition",
    "placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-60",
    "focus:border-[var(--pos-primary)] focus:ring-2 focus:ring-[var(--pos-ring)]",
  );

export function getPosButtonVariantClass(variant: PosButtonVariant): string {
  if (variant === "secondary") {
    return posSecondaryButtonClass;
  }

  if (variant === "neutral") {
    return posNeutralButtonClass;
  }

  if (variant === "danger") {
    return posDangerButtonClass;
  }

  if (variant === "ghost") {
    return posGhostButtonClass;
  }

  return posPrimaryButtonClass;
}

export function getPosStatusBadgeClass(status: PosStatusBadgeVariant): string {
  return cn("pos-status-badge", `pos-status-badge--${status}`);
}

export function getCaptureModeBadgeClass(captureMode: string): string {
  return captureMode === "CLASS_CAPTURE"
    ? cn(getPosStatusBadgeClass("confirmed"), "bg-[var(--pos-badge-class-bg)] text-[var(--pos-badge-class-fg)]")
    : cn(getPosStatusBadgeClass("ready"), "bg-[var(--pos-badge-product-bg)] text-[var(--pos-badge-product-fg)]");
}

export function getPosBranchTheme(bootstrap: PosBootstrapResponse): PosBranchTheme {
  const brandKey = branchBrandMapping[bootstrap.branch.code] ?? "EL_MEJOR_PAN";
  return branchThemes[brandKey];
}
