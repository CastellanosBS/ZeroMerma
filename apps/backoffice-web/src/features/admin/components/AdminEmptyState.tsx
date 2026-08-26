interface AdminEmptyStateProps {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function AdminEmptyState({ title, description, actionLabel, onAction }: AdminEmptyStateProps) {
  return (
    <div className="flex min-w-0 flex-col items-start gap-3 rounded-[18px] border border-dashed border-[var(--ui-color-border)] bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="truncate font-semibold text-slate-950" title={title}>
          {title}
        </p>
        {description ? <p className="mt-1 max-w-3xl text-sm leading-5 text-slate-600">{description}</p> : null}
      </div>
      {actionLabel ? (
        <button
          className="shrink-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onAction}
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
