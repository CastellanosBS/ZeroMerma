import type { ReactNode } from "react";

import { PosCard } from "../../components/pos-foundations";
import { cn } from "../../lib/utils";

type CashSessionContextTone = "default" | "muted" | "success" | "warning";

export interface CashSessionContextItem {
  helper?: ReactNode;
  icon?: ReactNode;
  key: string;
  label: string;
  tone?: CashSessionContextTone;
  value: ReactNode;
}

export function CashSessionContextGrid({
  className,
  items,
}: {
  className?: string;
  items: CashSessionContextItem[];
}) {
  return (
    <div className={cn("grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4", className)}>
      {items.map((item) => (
        <PosCard className="px-3 py-3" key={item.key} tone={item.tone ?? "muted"}>
          <div className="flex items-center gap-2 text-[var(--pos-primary)]">
            {item.icon ? <span className="shrink-0">{item.icon}</span> : null}
            <span className="pos-label-text">{item.label}</span>
          </div>
          <div className="mt-2 min-w-0 text-sm font-semibold text-slate-950">
            {typeof item.value === "string" ? <span className="block truncate">{item.value}</span> : item.value}
          </div>
          {item.helper ? <p className="mt-1 text-xs leading-5 text-slate-500">{item.helper}</p> : null}
        </PosCard>
      ))}
    </div>
  );
}
