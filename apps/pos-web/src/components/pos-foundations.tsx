import { Badge, Card, cn, type ButtonProps } from "@zeromerma/ui";
import { forwardRef, type HTMLAttributes, type LabelHTMLAttributes, type ReactNode } from "react";

import {
  getPosButtonVariantClass,
  getPosStatusBadgeClass,
  posFocusRingClass,
  type PosButtonVariant,
  type PosStatusBadgeVariant,
} from "../features/pos-theme/theme";
import { Button } from "./ui/button";

const posButtonBaseVariantMap: Record<PosButtonVariant, NonNullable<ButtonProps["variant"]>> = {
  danger: "danger",
  ghost: "ghost",
  neutral: "outline",
  primary: "primary",
  secondary: "secondary",
};

type PosSurfaceTone = "danger" | "default" | "financial" | "muted" | "success" | "warning";

export interface PosButtonProps extends Omit<ButtonProps, "variant"> {
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
  variant?: PosButtonVariant;
}

export const PosButton = forwardRef<HTMLButtonElement, PosButtonProps>(
  (
    {
      children,
      className,
      leadingIcon,
      size = "md",
      trailingIcon,
      type = "button",
      variant = "primary",
      ...props
    },
    ref,
  ) => (
    <Button
      className={cn(getPosButtonVariantClass(variant), className)}
      data-pos-button="true"
      ref={ref}
      size={size}
      type={type}
      variant={posButtonBaseVariantMap[variant]}
      {...props}
    >
      <span className="pos-button-icon-label">
        {leadingIcon ? (
          <span aria-hidden="true" className="pos-button-icon-label__icon">
            {leadingIcon}
          </span>
        ) : null}
        <span className="pos-button-icon-label__text">{children}</span>
        {trailingIcon ? (
          <span aria-hidden="true" className="pos-button-icon-label__icon">
            {trailingIcon}
          </span>
        ) : null}
      </span>
    </Button>
  ),
);

PosButton.displayName = "PosButton";

export function PosStatusBadge({
  children,
  className,
  icon,
  status = "draft",
  ...props
}: HTMLAttributes<HTMLSpanElement> & {
  icon?: ReactNode;
  status?: PosStatusBadgeVariant;
}) {
  return (
    <Badge
      className={cn(getPosStatusBadgeClass(status), className)}
      data-pos-status-badge="true"
      data-status={status}
      {...props}
    >
      {icon ? (
        <span aria-hidden="true" className="pos-icon-label__icon">
          {icon}
        </span>
      ) : null}
      <span>{children}</span>
    </Badge>
  );
}

export function PosPanel({
  children,
  className,
  tone = "default",
  ...props
}: HTMLAttributes<HTMLElement> & { tone?: PosSurfaceTone }) {
  return (
    <section className={cn("pos-foundation-panel", className)} data-tone={tone === "default" ? undefined : tone} {...props}>
      {children}
    </section>
  );
}

export function PosCard({
  children,
  className,
  tone = "default",
  ...props
}: HTMLAttributes<HTMLDivElement> & { tone?: Exclude<PosSurfaceTone, "financial"> }) {
  return (
    <Card className={cn("pos-foundation-card", className)} data-tone={tone === "default" ? undefined : tone} {...props}>
      {children}
    </Card>
  );
}

export function PosSectionTitle({
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
    <div className={cn("pos-section-title", className)} data-pos-section-title="true">
      {eyebrow ? <p className="pos-section-title__eyebrow">{eyebrow}</p> : null}
      <div className="pos-section-title__row">
        <div className="pos-section-title__text">
          <h2 className="pos-section-title__headline">{title}</h2>
          {description ? <div className="pos-section-title__description">{description}</div> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </div>
  );
}

export function PosFieldLabel({
  children,
  className,
  helper,
  required = false,
  ...props
}: LabelHTMLAttributes<HTMLLabelElement> & {
  helper?: ReactNode;
  required?: boolean;
}) {
  return (
    <label className={cn("pos-field-label-wrap", className)} {...props}>
      <span className="pos-field-label">
        <span>{children}</span>
        {required ? <span className="pos-field-label__required">*</span> : null}
      </span>
      {helper ? <span className="pos-field-label__helper">{helper}</span> : null}
    </label>
  );
}

export function PosFocusRing({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("pos-focus-ring", className, posFocusRingClass)} {...props}>
      {children}
    </div>
  );
}
