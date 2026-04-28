import type { ComponentPropsWithoutRef, ReactNode } from "react";

import { cn } from "../lib/utils";
import type { PosStatusBadgeVariant } from "../features/pos-theme/theme";
import { PosPanel, PosSectionTitle, PosStatusBadge } from "./pos-foundations";

export function PosModuleLayout({
  children,
  className,
  mobileSummary,
}: {
  children: ReactNode;
  className?: string;
  mobileSummary?: ReactNode;
}) {
  return (
    <div
      className={cn("grid gap-3 lg:h-full lg:grid-rows-[minmax(0,1fr)_auto]", className)}
      data-pos-module-layout="true"
    >
      {children}
      {mobileSummary ? <div className="lg:hidden">{mobileSummary}</div> : null}
    </div>
  );
}

export function PosSummaryPanel({
  action,
  children,
  className,
  description,
  footer,
  stateLabel,
  stateTone = "draft",
  title,
  ...panelProps
}: {
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  description?: ReactNode;
  footer?: ReactNode;
  stateLabel?: string;
  stateTone?: PosStatusBadgeVariant;
  title: ReactNode;
} & Omit<ComponentPropsWithoutRef<"section">, "title">) {
  return (
    <PosPanel
      className={cn("grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-3 px-3.5 py-3.5", className)}
      {...panelProps}
      data-pos-summary-panel="true"
    >
      <PosSectionTitle
        action={action ?? (stateLabel ? <PosStatusBadge status={stateTone}>{stateLabel}</PosStatusBadge> : null)}
        description={description}
        title={title}
      />
      <div className="min-h-0 overflow-hidden">{children}</div>
      {footer ? <div className="border-t border-[var(--pos-shell-border)] pt-3">{footer}</div> : null}
    </PosPanel>
  );
}

export function PosContextBanner({
  className,
  description,
  title,
}: {
  className?: string;
  description: ReactNode;
  title: ReactNode;
}) {
  return (
    <PosPanel
      className={cn(
        "border-[rgba(24,94,168,0.16)] bg-[rgba(24,94,168,0.04)] px-3.5 py-3",
        className,
      )}
      data-pos-context-banner="true"
    >
      <p className="text-sm font-semibold text-slate-950">{title}</p>
      <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
    </PosPanel>
  );
}
