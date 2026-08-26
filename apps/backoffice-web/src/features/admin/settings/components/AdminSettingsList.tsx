import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminSettingCategory, AdminSettingListItem } from "../types";

interface AdminSettingsListProps {
  categories: AdminSettingCategory[];
  errorMessage?: string | null;
  isLoading?: boolean;
  items: AdminSettingListItem[];
  onSelectCategory: (category: string) => void;
  onSelectSetting: (item: AdminSettingListItem) => void;
  selectedCategory: string;
  selectedSettingKey: string | null;
  total: number;
}

function statusLabel(value: string): string {
  return {
    missing: "Pendiente",
    ready: "Lista",
    warning: "Advertencia",
  }[value] ?? value;
}

function badgeClass(value: string): string {
  if (value === "ready") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "missing" || value === "critical") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
}

function valueSummary(value: unknown): string {
  if (typeof value === "boolean") {
    return value ? "Habilitado" : "Deshabilitado";
  }
  if (value === null || value === undefined || value === "") {
    return "Sin valor";
  }
  return String(value);
}

export function AdminSettingsList({
  categories,
  errorMessage,
  isLoading = false,
  items,
  onSelectCategory,
  onSelectSetting,
  selectedCategory,
  selectedSettingKey,
  total,
}: AdminSettingsListProps) {
  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="flex min-w-0 items-center justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold text-slate-950">
              Configuraciones
            </h3>
            <p className="truncate text-xs text-slate-500">
              Registro tipado, alcance, valor efectivo y advertencias.
            </p>
          </div>
          <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
            {total} ajustes
          </span>
        </div>

        <div className="mt-2 flex min-w-0 gap-2 overflow-x-auto pb-1">
          <button
            className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-semibold ${
              selectedCategory === "all"
                ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)] text-[var(--ui-color-info)]"
                : "border-[var(--ui-color-border)] bg-white text-slate-600"
            }`}
            type="button"
            onClick={() => onSelectCategory("all")}
          >
            Todas
          </button>
          {categories.map((category) => (
            <button
              className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-semibold ${
                selectedCategory === category.id
                  ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)] text-[var(--ui-color-info)]"
                  : "border-[var(--ui-color-border)] bg-white text-slate-600"
              }`}
              key={category.id}
              title={category.description}
              type="button"
              onClick={() => onSelectCategory(category.id)}
            >
              {category.label}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando configuraciones desde el backend."
            title="Cargando configuracion"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudo cargar configuracion" />
        ) : items.length > 0 ? (
          <div className="grid gap-2">
            {items.map((item) => {
              const selected = item.definition.key === selectedSettingKey;
              return (
                <button
                  className={[
                    "grid gap-2 rounded-[18px] border p-3 text-left transition",
                    selected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={item.definition.key}
                  type="button"
                  onClick={() => onSelectSetting(item)}
                >
                  <div className="flex min-w-0 items-start justify-between gap-2">
                    <div className="min-w-0">
                      <span className="block truncate text-sm font-semibold text-slate-950">
                        {item.definition.label}
                      </span>
                      <span className="block truncate text-xs text-slate-500">
                        {item.definition.key}
                      </span>
                    </div>
                    <span
                      className={`shrink-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.value.status,
                      )}`}
                    >
                      {statusLabel(item.value.status)}
                    </span>
                  </div>

                  <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
                    <p className="truncate">
                      <span className="font-semibold text-slate-700">Valor:</span>{" "}
                      {valueSummary(item.value.effectiveValue)}
                    </p>
                    <p className="truncate">
                      <span className="font-semibold text-slate-700">Alcance:</span>{" "}
                      {item.value.scope}
                    </p>
                    <p className="truncate">
                      <span className="font-semibold text-slate-700">Categoria:</span>{" "}
                      {item.definition.categoryLabel}
                    </p>
                    <p className="truncate">
                      <span className="font-semibold text-slate-700">Modulos:</span>{" "}
                      {item.definition.affectsModules.join(", ")}
                    </p>
                  </div>

                  <div className="flex min-w-0 flex-wrap gap-1.5">
                    {item.definition.isSensitive ? (
                      <span className="rounded-full border border-amber-200 bg-[var(--ui-color-warning-soft)] px-2 py-1 text-xs font-semibold text-[var(--ui-color-warning)]">
                        Sensible
                      </span>
                    ) : null}
                    {item.definition.isReadonly ? (
                      <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-600">
                        Solo lectura
                      </span>
                    ) : null}
                    {item.value.inheritedFrom ? (
                      <span className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-600">
                        Hereda {item.value.inheritedFrom}
                      </span>
                    ) : null}
                  </div>
                </button>
              );
            })}
          </div>
        ) : (
          <AdminEmptyState
            description="No hay configuraciones que coincidan con los filtros seleccionados."
            title="Sin configuraciones"
          />
        )}
      </div>
    </section>
  );
}
