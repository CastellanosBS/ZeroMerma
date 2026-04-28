import { forwardRef } from "react";
import type { TextareaHTMLAttributes } from "react";

import { cn } from "./utils";

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, rows = 4, ...props }, ref) => (
  <textarea
    className={cn(
      "flex min-h-24 w-full rounded-xl border border-[var(--ui-color-border)] bg-[var(--ui-color-surface)] px-3 py-2.5 text-sm text-[var(--ui-color-foreground)] shadow-sm transition-colors",
      "placeholder:text-[var(--ui-color-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-color-ring)]",
      "disabled:cursor-not-allowed disabled:opacity-60",
      className,
    )}
    ref={ref}
    rows={rows}
    {...props}
  />
));

Textarea.displayName = "Textarea";
