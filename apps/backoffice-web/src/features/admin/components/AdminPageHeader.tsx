import type { ReactNode } from "react";
import type { PermissionCode } from "../../auth/authorization";
import { hasEffectiveCapability } from "../../auth/authorization";
import { useBackofficeAuthorization } from "../../auth/authorization-context";

interface AdminPageHeaderProps {
  title: string;
  description: string;
  actionLabel?: string;
  actionCapability?: PermissionCode;
  actionGlobalOnly?: boolean;
  actionDisabled?: boolean;
  meta?: ReactNode[];
  onAction?: () => void;
}

export function AdminPageHeader({
  title,
  description,
  actionLabel,
  actionCapability,
  actionGlobalOnly = false,
  actionDisabled = false,
  meta = [],
  onAction,
}: AdminPageHeaderProps) {
  const user = useBackofficeAuthorization();
  const canShowAction =
    actionCapability !== undefined &&
    hasEffectiveCapability(user, actionCapability, [], actionGlobalOnly);
  const isActionDisabled = actionDisabled || !onAction;

  return (
    <div className="flex min-w-0 shrink-0 flex-wrap items-start justify-between gap-3 border-b border-[var(--ui-color-border)] px-4 py-3">
      <div className="min-w-0">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <h2
            className="min-w-0 truncate text-xl font-semibold tracking-tight text-slate-950"
            title={title}
          >
            {title}
          </h2>
          {meta.map((item, index) =>
            typeof item === "string" ? (
              <span
                className="max-w-full truncate rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600"
                key={item}
                title={item}
              >
                {item}
              </span>
            ) : (
              <span className="min-w-0" key={`meta-${index}`}>
                {item}
              </span>
            ),
          )}
        </div>
        <p className="mt-1 max-w-3xl text-sm leading-5 text-slate-600">{description}</p>
      </div>

      {actionLabel && canShowAction ? (
        <button
          className="inline-flex h-10 shrink-0 items-center justify-center rounded-2xl bg-[var(--ui-color-primary)] px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--ui-color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isActionDisabled}
          title={isActionDisabled ? "Acción pendiente de integración" : actionLabel}
          type="button"
          onClick={onAction}
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
