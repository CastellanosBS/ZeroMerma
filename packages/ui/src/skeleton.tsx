import type { HTMLAttributes } from "react";

import { cn } from "./utils";

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-xl bg-[var(--ui-color-surface-tint)]", className)}
      {...props}
    />
  );
}
