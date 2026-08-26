import type { AdminModuleStatus } from "../adminTypes";

const statusLabels: Record<AdminModuleStatus, string> = {
  ready: "Activo",
  partial: "Parcial",
  preparation: "En preparación",
  planned: "Planeado",
};

const statusClasses: Record<AdminModuleStatus, string> = {
  ready: "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]",
  partial: "border-sky-200 bg-[var(--ui-color-info-soft)] text-[var(--ui-color-info)]",
  preparation: "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]",
  planned: "border-[var(--ui-color-border)] bg-white text-slate-600",
};

export function AdminPreparationBadge({ status }: { status: AdminModuleStatus }) {
  return (
    <span
      className={`inline-flex max-w-full shrink-0 items-center truncate rounded-full border px-3 py-1 text-xs font-semibold ${statusClasses[status]}`}
      title={statusLabels[status]}
    >
      {statusLabels[status]}
    </span>
  );
}
