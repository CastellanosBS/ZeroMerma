import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "./utils";

export type ButtonVariant = "danger" | "ghost" | "outline" | "primary" | "secondary";
export type ButtonSize = "icon" | "lg" | "md" | "sm";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  size?: ButtonSize;
  variant?: ButtonVariant;
}

export function buttonClassNames({
  size = "md",
  variant = "primary",
}: {
  size?: ButtonSize;
  variant?: ButtonVariant;
}): string {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-xl border font-medium transition-colors shadow-sm",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ui-color-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--ui-color-surface)]",
    "disabled:pointer-events-none disabled:opacity-50",
    size === "sm"
      ? "h-9 px-3 text-sm"
      : size === "lg"
        ? "h-12 px-5 text-base"
        : size === "icon"
          ? "h-11 w-11 p-0"
          : "h-11 px-4 text-sm",
    variant === "outline"
      ? "border-[var(--ui-color-border)] bg-[var(--ui-color-surface)] text-[var(--ui-color-foreground)] hover:bg-[var(--ui-color-surface-muted)]"
      : variant === "secondary"
        ? "border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] text-[var(--ui-color-foreground)] hover:bg-[var(--ui-color-surface-tint)]"
        : variant === "ghost"
          ? "border-transparent bg-transparent text-[var(--ui-color-foreground)] shadow-none hover:bg-[var(--ui-color-surface-muted)]"
          : variant === "danger"
            ? "border-[var(--ui-color-danger)] bg-[var(--ui-color-danger)] text-white hover:border-[var(--ui-color-danger-strong)] hover:bg-[var(--ui-color-danger-strong)]"
            : "border-[var(--ui-color-primary)] bg-[var(--ui-color-primary)] text-[var(--ui-color-primary-foreground)] hover:border-[var(--ui-color-primary-strong)] hover:bg-[var(--ui-color-primary-strong)]",
  );
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, size = "md", type = "button", variant = "primary", ...props }, ref) => (
    <button
      className={cn(buttonClassNames({ size, variant }), className)}
      ref={ref}
      type={type}
      {...props}
    />
  ),
);

Button.displayName = "Button";
