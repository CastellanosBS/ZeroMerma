import type { ReactNode } from "react";
import { hasEffectiveCapability, type PermissionCode } from "../../auth/authorization";
import { useBackofficeAuthorization } from "../../auth/authorization-context";

export interface AdminRowActionItem {
  destructive?: boolean;
  capability?: PermissionCode;
  branchIds?: readonly string[];
  globalOnly?: boolean;
  disabled?: boolean;
  label: string;
  onSelect: () => void;
}

interface AdminRowActionsMenuProps {
  actions: AdminRowActionItem[];
  label?: string;
}

export function AdminRowActionsMenu({ actions, label = "Acciones" }: AdminRowActionsMenuProps) {
  const user = useBackofficeAuthorization();
  return (
    <details className="relative inline-block text-left">
      <summary
        aria-label={label}
        className="list-none rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition marker:hidden hover:border-[var(--ui-color-info)] hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
        role="button"
      >
        ...
      </summary>
      <div className="absolute right-0 top-8 z-30 grid min-w-[10rem] gap-1 rounded-2xl border border-[var(--ui-color-border)] bg-white p-1.5 shadow-xl">
        {actions.map((action) => (
          <button
            className={[
              "w-full rounded-xl px-3 py-2 text-left text-xs font-semibold transition focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:opacity-50",
              action.destructive
                ? "text-[var(--ui-color-danger)] hover:bg-[var(--ui-color-danger-soft)]"
                : "text-slate-700 hover:bg-slate-50",
            ].join(" ")}
            disabled={
              action.disabled ||
              (action.capability !== undefined &&
                !hasEffectiveCapability(
                  user,
                  action.capability,
                  action.branchIds,
                  action.globalOnly,
                ))
            }
            key={action.label}
            type="button"
            onClick={(event) => {
              event.preventDefault();
              action.onSelect();
            }}
          >
            {action.label}
          </button>
        ))}
      </div>
    </details>
  );
}

interface AdminBulkActionBarProps {
  actions?: ReactNode;
  entityLabel: string;
  onClearSelection: () => void;
  selectedCount: number;
}

export function AdminBulkActionBar({
  actions,
  entityLabel,
  onClearSelection,
  selectedCount,
}: AdminBulkActionBarProps) {
  if (selectedCount === 0) {
    return null;
  }

  return (
    <section
      aria-live="polite"
      className="flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-[18px] border border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)] px-3 py-2 text-sm"
    >
      <span className="font-semibold text-slate-950">
        {selectedCount} {entityLabel} seleccionados
      </span>
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        {actions}
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClearSelection}
        >
          Limpiar seleccion
        </button>
      </div>
    </section>
  );
}
