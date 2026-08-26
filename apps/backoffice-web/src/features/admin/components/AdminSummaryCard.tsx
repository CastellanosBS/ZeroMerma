type AdminSummaryCardTone = "default" | "success" | "warning" | "danger" | "info";

interface AdminSummaryCardProps {
  title: string;
  value: string;
  description?: string;
  tone?: AdminSummaryCardTone;
}

const toneClasses: Record<AdminSummaryCardTone, string> = {
  default: "border-[var(--ui-color-border)] bg-white text-slate-950",
  success: "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]",
  warning: "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]",
  danger: "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]",
  info: "border-sky-200 bg-[var(--ui-color-info-soft)] text-[var(--ui-color-info)]",
};

export function AdminSummaryCard({
  title,
  value,
  description,
  tone = "default",
}: AdminSummaryCardProps) {
  return (
    <article className={`min-w-0 rounded-[20px] border px-3.5 py-3 shadow-sm ${toneClasses[tone]}`}>
      <p className="truncate text-[0.68rem] font-semibold uppercase tracking-[0.14em] opacity-75" title={title}>
        {title}
      </p>
      <p className="mt-1 truncate text-xl font-semibold tracking-tight" title={value}>
        {value}
      </p>
      {description ? (
        <p className="mt-1 line-clamp-2 text-xs leading-5 opacity-80" title={description}>
          {description}
        </p>
      ) : null}
    </article>
  );
}
