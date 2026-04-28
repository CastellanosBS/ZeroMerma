import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "./utils";

export function DialogSurface({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-[var(--ui-color-border)] bg-[var(--ui-color-surface)] shadow-[var(--ui-shadow-overlay)]",
        className,
      )}
      {...props}
    />
  );
}

export function DialogHeader({
  action,
  children,
  className,
}: {
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-3 border-b border-[var(--ui-color-border)] px-5 py-4", className)}>
      <div className="min-w-0 flex-1">{children}</div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function DialogBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 py-4", className)} {...props} />;
}

export function DialogFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-wrap justify-end gap-2 border-t border-[var(--ui-color-border)] px-5 py-4", className)} {...props} />;
}
