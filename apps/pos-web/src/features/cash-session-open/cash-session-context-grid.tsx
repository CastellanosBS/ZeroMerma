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
            {typeof item.value === "string" ? (
              <span className="block truncate">{item.value}</span>
            ) : (
              item.value
            )}
          </div>
          {item.helper ? (
            <p className="mt-1 text-xs leading-5 text-slate-500">{item.helper}</p>
          ) : null}
        </PosCard>
      ))}
    </div>
  );
}

export interface CashSessionContextSummaryGroup {
  icon?: ReactNode;
  items: Array<{
    className?: string;
    icon?: ReactNode;
    key: string;
    label: string;
    valueClassName?: string;
    title?: string;
    value: ReactNode;
  }>;
  key: string;
  title: string;
}

export function CashSessionContextSummary({
  className,
  groups,
}: {
  className?: string;
  groups: CashSessionContextSummaryGroup[];
}) {
  const summaryItems = groups.flatMap((group) =>
    group.items.map((item) => ({
      ...item,
      icon: item.icon ?? group.icon,
      key: `${group.key}-${item.key}`,
    })),
  );

  return (
    <PosCard className={cn("px-3 py-2.5", className)} tone="muted">
      <div className="grid gap-y-2 sm:grid-cols-2 md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1.2fr)_minmax(8rem,0.85fr)] md:gap-y-0">
        {summaryItems.map((item) => (
          <section
            className={cn(
              "min-w-0 overflow-hidden px-2 py-1 md:border-l md:border-slate-200/80 md:first:border-l-0",
              item.className,
            )}
            key={item.key}
          >
            <div className="flex min-w-0 items-center gap-1.5 text-[var(--pos-primary)]">
              {item.icon ? <span className="shrink-0">{item.icon}</span> : null}
              <span className="truncate text-[0.66rem] font-semibold uppercase tracking-[0.08em] text-slate-500">
                {item.label}
              </span>
            </div>
            <div
              aria-label={item.title ?? (typeof item.value === "string" ? item.value : undefined)}
              className={cn(
                "mt-0.5 block min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-sm font-semibold text-slate-950",
                item.valueClassName,
              )}
              title={item.title ?? (typeof item.value === "string" ? item.value : undefined)}
            >
              {typeof item.value === "string" ? (
                <span className="block min-w-0 overflow-hidden text-ellipsis whitespace-nowrap">
                  {item.value}
                </span>
              ) : (
                item.value
              )}
            </div>
          </section>
        ))}
      </div>
    </PosCard>
  );
}
