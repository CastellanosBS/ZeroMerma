import type { ReactNode } from "react";

import { cn } from "./utils";

export function SectionHeader({
  action,
  className,
  description,
  eyebrow,
  title,
}: {
  action?: ReactNode;
  className?: string;
  description?: ReactNode;
  eyebrow?: ReactNode;
  title: ReactNode;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-3", className)}>
      <div className="min-w-0 flex-1">
        {eyebrow ? (
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-[var(--ui-color-primary)]">
            {eyebrow}
          </p>
        ) : null}
        <p className="mt-1 text-lg font-semibold tracking-tight text-[var(--ui-color-foreground)]">{title}</p>
        {description ? (
          <p className="mt-1 text-sm leading-5 text-[var(--ui-color-muted)]">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
