import type { ReactNode } from "react";

import { cn } from "./utils";

export function Field({
  children,
  className,
  error,
  helper,
  label,
  required = false,
}: {
  children: ReactNode;
  className?: string;
  error?: ReactNode;
  helper?: ReactNode;
  label: ReactNode;
  required?: boolean;
}) {
  return (
    <label className={cn("grid gap-1.5", className)}>
      <span className="text-sm font-medium text-[var(--ui-color-foreground)]">
        {label}
        {required ? <span className="ml-1 text-[var(--ui-color-danger)]">*</span> : null}
      </span>
      {children}
      {error ? (
        <span className="text-sm text-[var(--ui-color-danger)]">{error}</span>
      ) : helper ? (
        <span className="text-sm text-[var(--ui-color-muted)]">{helper}</span>
      ) : null}
    </label>
  );
}
