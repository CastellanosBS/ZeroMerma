import type { HTMLAttributes } from "react";

import { cn } from "./utils";

export type BadgeTone = "danger" | "default" | "info" | "primary" | "success" | "warning";

export function Badge({
  className,
  tone = "default",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium",
        tone === "primary"
          ? "bg-[var(--ui-color-primary-soft)] text-[var(--ui-color-primary)]"
          : tone === "success"
            ? "bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]"
            : tone === "warning"
              ? "bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]"
              : tone === "danger"
                ? "bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]"
                : tone === "info"
                  ? "bg-[var(--ui-color-info-soft)] text-[var(--ui-color-info)]"
                  : "bg-[var(--ui-color-surface-muted)] text-[var(--ui-color-muted)]",
        className,
      )}
      {...props}
    />
  );
}

export function StatusBadge(props: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return <Badge {...props} />;
}
