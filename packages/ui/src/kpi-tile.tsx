import type { ReactNode } from "react";

import { cn } from "./utils";

export function KpiTile({
  helper,
  label,
  tone = "default",
  value,
}: {
  helper?: ReactNode;
  label: ReactNode;
  tone?: "default" | "financial" | "negative" | "positive" | "warning";
  value: ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border px-4 py-3 shadow-[var(--ui-shadow-subtle)]",
        tone === "financial"
          ? "border-[var(--ui-color-financial-border)] bg-[var(--ui-color-financial-soft)]"
          : tone === "positive"
            ? "border-[var(--ui-color-success-soft)] bg-[var(--ui-color-success-soft)]"
            : tone === "negative"
              ? "border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)]"
              : tone === "warning"
                ? "border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)]"
                : "border-[var(--ui-color-border)] bg-[var(--ui-color-surface)]",
      )}
    >
      <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-[var(--ui-color-muted)]">{label}</p>
      <div className="mt-1 text-[1.75rem] font-semibold tracking-tight text-[var(--ui-color-foreground)] [font-variant-numeric:tabular-nums]">
        {value}
      </div>
      {helper ? <p className="mt-1 text-sm leading-5 text-[var(--ui-color-muted)]">{helper}</p> : null}
    </div>
  );
}
