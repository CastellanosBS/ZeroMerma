import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";

import { cn } from "./utils";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(({ className, type = "text", ...props }, ref) => (
  <input
    className={cn(
      "flex h-11 w-full rounded-xl border border-[var(--ui-color-border)] bg-[var(--ui-color-surface)] px-3 text-sm text-[var(--ui-color-foreground)] shadow-sm transition-colors",
      "placeholder:text-[var(--ui-color-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-color-ring)]",
      "disabled:cursor-not-allowed disabled:opacity-60",
      className,
    )}
    ref={ref}
    type={type}
    {...props}
  />
));

Input.displayName = "Input";
