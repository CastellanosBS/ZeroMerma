import type { ReactNode } from "react";

import { AdminDataTablePlaceholder } from "./AdminDataTablePlaceholder";
import { AdminDetailPlaceholder } from "./AdminDetailPlaceholder";
import { AdminPageHeader } from "./AdminPageHeader";
import { AdminPreparationBadge } from "./AdminPreparationBadge";
import { AdminScopeFilters } from "./AdminScopeFilters";
import { AdminSummaryCard } from "./AdminSummaryCard";
import { useAdminModuleRecords } from "../adminData";
import type { AdminModuleDefinition } from "../adminTypes";

interface AdminPageShellProps {
  children?: ReactNode;
  module: AdminModuleDefinition;
  onAction?: () => void;
}

export function AdminPageShell({ children, module, onAction }: AdminPageShellProps) {
  const moduleData = useAdminModuleRecords(module);
  const contentRowsClass = children
    ? "lg:grid-rows-[auto_auto_auto_minmax(0,1fr)]"
    : "lg:grid-rows-[auto_auto_minmax(0,1fr)]";

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionDisabled={module.status === "planned" || module.status === "preparation"}
        actionLabel={module.actionLabel}
        description={module.description}
        meta={[<AdminPreparationBadge key="status" status={module.status} />]}
        onAction={onAction}
        title={module.title}
      />

      <div className={`grid min-h-0 min-w-0 flex-1 gap-3 overflow-hidden p-3 ${contentRowsClass}`}>
        <AdminScopeFilters filters={module.filters} />

        <div className="grid min-w-0 grid-cols-[repeat(auto-fit,minmax(12rem,1fr))] gap-3">
          {module.metrics.map((metric) => (
            <AdminSummaryCard
              key={metric.key}
              description={metric.description ?? "Pendiente de conectar a datos reales."}
              title={metric.label}
              tone={metric.tone}
              value={metric.value}
            />
          ))}
        </div>

        {children ? <div className="min-w-0">{children}</div> : null}

        <div className="grid min-h-0 min-w-0 items-start gap-3 overflow-hidden 2xl:grid-cols-[minmax(0,1fr)_minmax(17rem,21rem)]">
          <AdminDataTablePlaceholder module={module} records={moduleData.records} />
          <AdminDetailPlaceholder module={module} />
        </div>
      </div>
    </section>
  );
}
