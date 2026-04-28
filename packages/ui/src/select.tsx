import { forwardRef } from "react";
import type { SelectHTMLAttributes } from "react";

import { cn } from "./utils";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(({ className, ...props }, ref) => (
  <select
    className={cn(
      "flex h-11 w-full rounded-xl border border-[var(--ui-color-border)] bg-[var(--ui-color-surface)] px-3 text-sm text-[var(--ui-color-foreground)] shadow-sm transition-colors",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:opacity-60",
      className,
    )}
    ref={ref}
    {...props}
  />
));

Select.displayName = "Select";
