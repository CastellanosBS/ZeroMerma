import { useEffect, useRef, type ReactNode } from "react";

import { adminFilterInputClassName } from "./adminFilterStyles";

export interface AdminFilterChip {
  key: string;
  label: string;
  value: string;
  onRemove: () => void;
}

interface AdminDataToolbarProps {
  actions?: ReactNode;
  children?: ReactNode;
  filterCount?: number;
  isSearchDisabled?: boolean;
  onOpenFilters: () => void;
  onSearchChange: (value: string) => void;
  searchId: string;
  searchLabel?: string;
  searchPlaceholder: string;
  searchValue: string;
  status?: ReactNode;
}

interface AdminAdvancedFiltersSheetProps {
  children: ReactNode;
  isOpen: boolean;
  onClear?: () => void;
  onClose: () => void;
  title?: string;
}

interface AdminActiveFilterChipsProps {
  chips: AdminFilterChip[];
  onClearAll?: () => void;
}

interface AdminFilterFieldProps {
  children: ReactNode;
  className?: string;
  id?: string;
  label: string;
}

export function AdminFilterField({ children, className = "", id, label }: AdminFilterFieldProps) {
  return (
    <label
      className={`grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 ${className}`}
      htmlFor={id}
      title={label}
    >
      <span className="truncate">{label}</span>
      {children}
    </label>
  );
}

export function AdminActiveFilterChips({ chips, onClearAll }: AdminActiveFilterChipsProps) {
  if (chips.length === 0) {
    return null;
  }

  return (
    <div
      aria-label="Filtros activos"
      className="flex max-h-16 min-w-0 flex-wrap gap-1.5 overflow-y-auto pr-1 text-xs"
      role="list"
    >
      {chips.map((chip) => (
        <span
          className="inline-flex max-w-full items-center gap-1 rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 font-semibold text-slate-650 shadow-sm"
          key={chip.key}
          role="listitem"
          title={`${chip.label}: ${chip.value}`}
        >
          <span className="max-w-[16rem] truncate">
            {chip.label}: {chip.value}
          </span>
          <button
            aria-label={`Quitar filtro ${chip.label}`}
            className="rounded-full px-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={chip.onRemove}
          >
            x
          </button>
        </span>
      ))}
      {chips.length > 1 && onClearAll ? (
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClearAll}
        >
          Limpiar todo
        </button>
      ) : null}
    </div>
  );
}

export function AdminDataToolbar({
  actions,
  children,
  filterCount = 0,
  isSearchDisabled = false,
  onOpenFilters,
  onSearchChange,
  searchId,
  searchLabel = "Buscar",
  searchPlaceholder,
  searchValue,
  status,
}: AdminDataToolbarProps) {
  return (
    <section className="grid min-w-0 gap-2 rounded-[20px] border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] p-2.5">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <label className="min-w-[14rem] flex-1" htmlFor={searchId}>
          <span className="sr-only">{searchLabel}</span>
          <input
            className={adminFilterInputClassName()}
            disabled={isSearchDisabled}
            id={searchId}
            placeholder={searchPlaceholder}
            title={searchPlaceholder}
            type="search"
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </label>

        <div className="ml-auto flex min-w-0 flex-wrap items-center justify-end gap-2">
          {status ? (
            <span className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-600">
              {status}
            </span>
          ) : null}
          <button
            aria-label={`Abrir filtros${filterCount > 0 ? `, ${filterCount} activos` : ""}`}
            className="inline-flex h-10 items-center gap-2 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-[var(--ui-color-info)] hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={onOpenFilters}
          >
            Filtros
            {filterCount > 0 ? (
              <span className="rounded-full bg-[var(--ui-color-info)] px-2 py-0.5 text-[0.7rem] font-bold text-white">
                {filterCount}
              </span>
            ) : null}
          </button>
          {actions}
        </div>
      </div>
      {children}
    </section>
  );
}

export function AdminAdvancedFiltersSheet({
  children,
  isOpen,
  onClear,
  onClose,
  title = "Filtros",
}: AdminAdvancedFiltersSheetProps) {
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50" role="presentation">
      <button
        aria-label="Cerrar filtros"
        className="absolute inset-0 h-full w-full cursor-default bg-slate-950/25"
        type="button"
        onClick={onClose}
      />
      <aside
        aria-label={title}
        aria-modal="true"
        className="absolute right-0 top-0 flex h-full w-full max-w-[28rem] flex-col border-l border-[var(--ui-color-border)] bg-white shadow-2xl"
        role="dialog"
      >
        <header className="flex shrink-0 items-start justify-between gap-3 border-b border-[var(--ui-color-border)] px-4 py-3">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold text-slate-950">{title}</h2>
            <p className="mt-0.5 text-sm text-slate-500">Ajusta criterios sin ocupar espacio permanente.</p>
          </div>
          <button
            ref={closeButtonRef}
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={onClose}
          >
            Cerrar
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">{children}</div>

        <footer className="flex shrink-0 items-center justify-between gap-2 border-t border-[var(--ui-color-border)] px-4 py-3">
          {onClear ? (
            <button
              className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              type="button"
              onClick={onClear}
            >
              Limpiar
            </button>
          ) : (
            <span />
          )}
          <button
            className="rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--ui-color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={onClose}
          >
            Aplicar filtros
          </button>
        </footer>
      </aside>
    </div>
  );
}
