import type { ReactNode } from "react";

import { cn } from "./utils";

export function EmptyState({
  action,
  className,
  description,
  icon,
  title,
}: {
  action?: ReactNode;
  className?: string;
  description: ReactNode;
  icon?: ReactNode;
  title: ReactNode;
}) {
  return (
    <div
      className={cn(
        "grid place-items-center gap-3 rounded-2xl border border-dashed border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] px-6 py-10 text-center",
        className,
      )}
    >
      {icon ? (
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--ui-color-surface)] text-[var(--ui-color-primary)] shadow-sm">
          {icon}
        </div>
      ) : null}
      <div className="grid gap-1">
        <p className="text-base font-semibold text-[var(--ui-color-foreground)]">{title}</p>
        <p className="max-w-md text-sm leading-6 text-[var(--ui-color-muted)]">{description}</p>
      </div>
      {action ? <div>{action}</div> : null}
    </div>
  );
}
