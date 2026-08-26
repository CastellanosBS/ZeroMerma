import {
  type ButtonHTMLAttributes,
  type ReactNode,
  type Ref,
  useEffect,
  useId,
  useMemo,
  useRef,
} from "react";

import {
  formatCompactLocalDateTime,
  formatRecordReference,
  formatRecordStatus,
} from "../lib/formatters";
import { cn } from "../lib/utils";
import { useModuleHotkeys, useRovingFocusGrid } from "../features/pos-shell/keyboard";
import { posInputClass } from "../features/pos-theme/theme";
import { PosEmptyState, PosLoadingState } from "./pos-feedback";
import { PosButton, PosPanel, PosSectionTitle, PosStatusBadge } from "./pos-foundations";
import { FilterButton, ScrollPane, SearchField } from "./pos-module-primitives";
import { ArrowLeftIcon, ChevronRightIcon, MenuIcon } from "./pos-icons";

type PosRecordActionTone = "danger" | "neutral";
type PosRecordTableAlign = "center" | "left" | "right";

export interface PosFilterChipOption {
  className?: string;
  count?: number;
  isActive: boolean;
  key: string;
  label: string;
  onSelect: () => void;
}

export interface PosFilterSelectOption {
  label: string;
  value: string;
}

export interface PosFilterSelectConfig {
  ariaLabel: string;
  key: string;
  onChange: (value: string) => void;
  options: PosFilterSelectOption[];
  value: string;
}

export interface PosRecordAction {
  disabled?: boolean;
  key: string;
  label: string;
  onSelect: () => void;
  tone?: PosRecordActionTone;
}

export interface PosRecordColumn<TRecord> {
  align?: PosRecordTableAlign;
  cellClassName?: string;
  header: ReactNode;
  headerClassName?: string;
  key: string;
  renderCell: (record: TRecord) => ReactNode;
  width?: string;
}

export interface PosSearchInputProps {
  ariaLabel: string;
  className?: string;
  disabled?: boolean;
  hotkeyChords?: readonly string[];
  hotkeyDescription?: string;
  hotkeyEnabled?: boolean;
  hotkeyLabel?: string;
  inputRef?: Ref<HTMLInputElement>;
  onChange: (value: string) => void;
  placeholder: string;
  value: string;
}

const DEFAULT_SEARCH_HOTKEY_CHORDS = ["Ctrl+F", "Meta+F"] as const;

interface PosRecordRenderState {
  index: number;
  isSelected: boolean;
}

function assignRef<TValue>(targetRef: Ref<TValue> | undefined, value: TValue) {
  if (!targetRef) {
    return;
  }

  if (typeof targetRef === "function") {
    targetRef(value);
    return;
  }

  (targetRef as { current: TValue }).current = value;
}

function getCellAlignmentClass(align: PosRecordTableAlign): string {
  if (align === "right") {
    return "text-right";
  }

  if (align === "center") {
    return "text-center";
  }

  return "text-left";
}

function PosFilterSelect({
  ariaLabel,
  className,
  onChange,
  options,
  value,
}: PosFilterSelectConfig & { className?: string }) {
  return (
    <select
      aria-label={ariaLabel}
      className={cn(
        posInputClass,
        "h-10 min-w-[11rem] rounded-[var(--pos-radius-control)] px-3 py-2 text-sm font-medium",
        className,
      )}
      onChange={(event) => onChange(event.target.value)}
      value={value}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

export function PosSearchInput({
  ariaLabel,
  className,
  disabled = false,
  hotkeyChords = DEFAULT_SEARCH_HOTKEY_CHORDS,
  hotkeyDescription = "Enfoca la búsqueda del listado actual.",
  hotkeyEnabled = true,
  hotkeyLabel = "Buscar en lista",
  inputRef,
  onChange,
  placeholder,
  value,
}: PosSearchInputProps) {
  const internalRef = useRef<HTMLInputElement | null>(null);
  const hotkeyId = useId();

  const shortcuts = useMemo(
    () =>
      hotkeyEnabled
        ? [
            {
              allowInEditable: true,
              chords: hotkeyChords,
              description: hotkeyDescription,
              group: "Consulta",
              handler: () => {
                internalRef.current?.focus();
                internalRef.current?.select();
              },
              id: `pos-search-input-${hotkeyId}`,
              label: hotkeyLabel,
              priority: 150,
            },
          ]
        : [],
    [hotkeyChords, hotkeyDescription, hotkeyEnabled, hotkeyId, hotkeyLabel],
  );

  useModuleHotkeys(shortcuts, hotkeyEnabled);

  return (
    <SearchField
      ariaLabel={ariaLabel}
      className={className}
      disabled={disabled}
      inputClassName={cn(posInputClass, "h-10 rounded-[var(--pos-radius-control)] py-2 text-sm")}
      inputRef={(node) => {
        internalRef.current = node;
        assignRef(inputRef, node);
      }}
      onChange={onChange}
      placeholder={placeholder}
      value={value}
    />
  );
}

export function PosFilterBar({
  actions,
  chipFilters = [],
  className,
  countLabel,
  searchInput,
  selectFilters = [],
  title,
}: {
  actions?: ReactNode;
  chipFilters?: PosFilterChipOption[];
  className?: string;
  countLabel?: ReactNode;
  searchInput?: PosSearchInputProps;
  selectFilters?: PosFilterSelectConfig[];
  title?: ReactNode;
}) {
  const hasHeader = Boolean(title) || Boolean(countLabel) || Boolean(actions);
  const hasControls = Boolean(searchInput) || selectFilters.length > 0;

  return (
    <div className={cn("pos-filter-bar", className)} data-pos-filter-bar="true">
      {hasHeader ? (
        <div className="pos-filter-bar__header">
          <div className="min-w-0">
            {title ? <h2 className="pos-filter-bar__title">{title}</h2> : null}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            {countLabel}
            {actions}
          </div>
        </div>
      ) : null}

      {hasControls ? (
        <div className="pos-filter-bar__controls">
          {searchInput ? (
            <PosSearchInput
              {...searchInput}
              className={cn("min-w-0 flex-1", searchInput.className)}
            />
          ) : null}
          {selectFilters.map(({ key, ...selectFilter }) => (
            <PosFilterSelect key={key} {...selectFilter} />
          ))}
        </div>
      ) : null}

      {chipFilters.length > 0 ? (
        <div className="pos-filter-bar__chips">
          {chipFilters.map((filter) => (
            <FilterButton
              className={filter.className}
              count={filter.count}
              isActive={filter.isActive}
              key={filter.key}
              label={filter.label}
              onClick={filter.onSelect}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function PosRecordActionMenu({
  actions,
  className,
  triggerLabel = "Acciones del registro",
}: {
  actions: PosRecordAction[];
  className?: string;
  triggerLabel?: string;
}) {
  const menuRef = useRef<HTMLDetailsElement | null>(null);

  if (actions.length === 0) {
    return null;
  }

  return (
    <details className={cn("pos-record-action-menu", className)} ref={menuRef}>
      <summary
        aria-label={triggerLabel}
        className="pos-record-action-menu__trigger"
        onClick={(event) => event.stopPropagation()}
      >
        <MenuIcon className="h-4 w-4" />
        <span className="sr-only">{triggerLabel}</span>
      </summary>
      <div className="pos-record-action-menu__surface" role="menu">
        {actions.map((action) => (
          <button
            className={cn(
              "pos-record-action-menu__item",
              action.tone === "danger" && "pos-record-action-menu__item--danger",
            )}
            disabled={action.disabled}
            key={action.key}
            onClick={(event) => {
              event.stopPropagation();
              action.onSelect();
              menuRef.current?.removeAttribute("open");
            }}
            role="menuitem"
            type="button"
          >
            {action.label}
          </button>
        ))}
      </div>
    </details>
  );
}

export function PosRecordCard({
  actions = [],
  buttonRef,
  children,
  className,
  isSelected = false,
  onFocus,
  onKeyDown,
  onSelect,
  tabIndex = 0,
}: {
  actions?: PosRecordAction[];
  buttonRef?: Ref<HTMLButtonElement>;
  children: ReactNode;
  className?: string;
  isSelected?: boolean;
  onFocus?: ButtonHTMLAttributes<HTMLButtonElement>["onFocus"];
  onKeyDown?: ButtonHTMLAttributes<HTMLButtonElement>["onKeyDown"];
  onSelect: () => void;
  tabIndex?: number;
}) {
  return (
    <div className={cn("pos-record-card-shell", className)} data-selected={isSelected || undefined}>
      <div className="flex items-start gap-2">
        <button
          className="pos-record-card__button"
          onClick={onSelect}
          onFocus={onFocus}
          onKeyDown={onKeyDown}
          ref={buttonRef}
          tabIndex={tabIndex}
          type="button"
        >
          {children}
        </button>
        {actions.length > 0 ? (
          <div className="shrink-0 pt-1">
            <PosRecordActionMenu actions={actions} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function PosRecordListSkeleton({ itemCount = 5 }: { itemCount?: number }) {
  return (
    <div className="grid gap-2">
      {Array.from({ length: itemCount }, (_, index) => (
        <div className="pos-record-card-shell animate-pulse" key={`list-skeleton-${index}`}>
          <div className="grid gap-2 rounded-[var(--pos-radius-control)] border border-[var(--pos-shell-border)] bg-white px-3 py-3">
            <div className="h-4 w-32 rounded bg-slate-200" />
            <div className="h-3 w-full rounded bg-slate-100" />
            <div className="h-3 w-2/3 rounded bg-slate-100" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function PosRecordList<TRecord>({
  className,
  emptyAction,
  emptyDescription = "No hay registros para los filtros seleccionados.",
  emptyTitle = "Sin resultados",
  getKey,
  getRowActions,
  loading = false,
  loadingTitle = "Cargando registros",
  onSelect,
  records,
  renderContent,
  selectedKey,
}: {
  className?: string;
  emptyAction?: ReactNode;
  emptyDescription?: string;
  emptyTitle?: string;
  getKey: (record: TRecord) => string;
  getRowActions?: (record: TRecord) => PosRecordAction[];
  loading?: boolean;
  loadingTitle?: string;
  onSelect: (record: TRecord) => void;
  records: TRecord[];
  renderContent: (record: TRecord, state: PosRecordRenderState) => ReactNode;
  selectedKey?: string | null;
}) {
  const { getItemProps, setActiveIndex } = useRovingFocusGrid({
    itemCount: records.length,
    onActivate: (index) => {
      const record = records[index];
      if (record) {
        onSelect(record);
      }
    },
  });

  useEffect(() => {
    if (!selectedKey) {
      return;
    }

    const selectedIndex = records.findIndex((record) => getKey(record) === selectedKey);
    if (selectedIndex >= 0) {
      setActiveIndex(selectedIndex);
    }
  }, [getKey, records, selectedKey, setActiveIndex]);

  if (loading) {
    return (
      <div className={className}>
        <PosLoadingState
          description="Recuperando los registros disponibles."
          title={loadingTitle}
        />
        <div className="mt-3">
          <PosRecordListSkeleton />
        </div>
      </div>
    );
  }

  if (records.length === 0) {
    return <PosEmptyState action={emptyAction} description={emptyDescription} title={emptyTitle} />;
  }

  return (
    <ScrollPane className={cn("grid gap-2", className)}>
      {records.map((record, index) => {
        const key = getKey(record);
        const isSelected = key === selectedKey;
        const itemProps = getItemProps(index);

        return (
          <PosRecordCard
            actions={getRowActions?.(record) ?? []}
            buttonRef={itemProps.ref}
            isSelected={isSelected}
            key={key}
            onFocus={itemProps.onFocus}
            onKeyDown={itemProps.onKeyDown}
            onSelect={() => onSelect(record)}
            tabIndex={itemProps.tabIndex}
          >
            {renderContent(record, { index, isSelected })}
          </PosRecordCard>
        );
      })}
    </ScrollPane>
  );
}

function PosRecordTableSkeleton<TRecord>({
  columns,
  hasActionColumn = false,
  rowCount = 5,
}: {
  columns: PosRecordColumn<TRecord>[];
  hasActionColumn?: boolean;
  rowCount?: number;
}) {
  return (
    <tbody>
      {Array.from({ length: rowCount }, (_, rowIndex) => (
        <tr
          className="animate-pulse border-t border-[var(--pos-shell-border)]"
          key={`table-skeleton-${rowIndex}`}
        >
          {columns.map((column, columnIndex) => (
            <td className="px-3 py-3" key={`${column.key}-${columnIndex}`}>
              <div className="h-3.5 rounded bg-slate-100" />
            </td>
          ))}
          {hasActionColumn ? (
            <td className="px-3 py-3">
              <div className="h-8 w-8 rounded-full bg-slate-100" />
            </td>
          ) : null}
        </tr>
      ))}
    </tbody>
  );
}

export function PosRecordTable<TRecord>({
  className,
  columns,
  emptyAction,
  emptyDescription = "No hay registros disponibles para esta consulta.",
  emptyTitle = "Sin resultados",
  getKey,
  getRowActions,
  getRowClassName,
  loading = false,
  loadingTitle = "Cargando registros",
  onSelect,
  records,
  selectedKey,
  tableAriaLabel,
}: {
  className?: string;
  columns: PosRecordColumn<TRecord>[];
  emptyAction?: ReactNode;
  emptyDescription?: string;
  emptyTitle?: string;
  getKey: (record: TRecord) => string;
  getRowActions?: (record: TRecord) => PosRecordAction[];
  getRowClassName?: (record: TRecord, state: PosRecordRenderState) => string | undefined;
  loading?: boolean;
  loadingTitle?: string;
  onSelect: (record: TRecord) => void;
  records: TRecord[];
  selectedKey?: string | null;
  tableAriaLabel: string;
}) {
  const { getItemProps, setActiveIndex } = useRovingFocusGrid({
    itemCount: records.length,
    onActivate: (index) => {
      const record = records[index];
      if (record) {
        onSelect(record);
      }
    },
  });

  useEffect(() => {
    if (!selectedKey) {
      return;
    }

    const selectedIndex = records.findIndex((record) => getKey(record) === selectedKey);
    if (selectedIndex >= 0) {
      setActiveIndex(selectedIndex);
    }
  }, [getKey, records, selectedKey, setActiveIndex]);

  const showActionColumn = Boolean(getRowActions);

  if (!loading && records.length === 0) {
    return <PosEmptyState action={emptyAction} description={emptyDescription} title={emptyTitle} />;
  }

  return (
    <div className={cn("pos-record-table-shell", className)}>
      {loading ? (
        <PosLoadingState
          description="Recuperando los registros del historial."
          title={loadingTitle}
        />
      ) : null}
      <div className={cn("pos-record-table-frame", loading && "mt-3")}>
        <ScrollPane className="!pb-0">
          <table aria-label={tableAriaLabel} className="pos-record-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th
                    className={cn(
                      "pos-record-table__header-cell",
                      getCellAlignmentClass(column.align ?? "left"),
                      column.headerClassName,
                    )}
                    key={column.key}
                    scope="col"
                    style={column.width ? { width: column.width } : undefined}
                  >
                    {column.header}
                  </th>
                ))}
                {showActionColumn ? (
                  <th className="pos-record-table__header-cell text-right" scope="col">
                    Acciones
                  </th>
                ) : null}
              </tr>
            </thead>
            {loading ? (
              <PosRecordTableSkeleton columns={columns} hasActionColumn={showActionColumn} />
            ) : (
              <tbody>
                {records.map((record, index) => {
                  const key = getKey(record);
                  const isSelected = key === selectedKey;
                  const rowActions = getRowActions?.(record) ?? [];
                  const itemProps = getItemProps(index);
                  const rowClassName = getRowClassName?.(record, { index, isSelected });

                  return (
                    <tr
                      aria-selected={isSelected}
                      className={cn("pos-record-table__row", rowClassName)}
                      data-selected={isSelected || undefined}
                      key={key}
                      onClick={() => onSelect(record)}
                      onFocus={itemProps.onFocus}
                      onKeyDown={itemProps.onKeyDown}
                      ref={itemProps.ref as Ref<HTMLTableRowElement>}
                      tabIndex={itemProps.tabIndex}
                    >
                      {columns.map((column) => (
                        <td
                          className={cn(
                            "pos-record-table__cell",
                            getCellAlignmentClass(column.align ?? "left"),
                            column.cellClassName,
                          )}
                          key={column.key}
                        >
                          {column.renderCell(record)}
                        </td>
                      ))}
                      {showActionColumn ? (
                        <td
                          className="pos-record-table__cell text-right"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <PosRecordActionMenu actions={rowActions} />
                        </td>
                      ) : null}
                    </tr>
                  );
                })}
              </tbody>
            )}
          </table>
        </ScrollPane>
      </div>
    </div>
  );
}

export function PosRecordDetailPanel({
  action,
  badge,
  children,
  className,
  description,
  footer,
  title,
}: {
  action?: ReactNode;
  badge?: ReactNode;
  children: ReactNode;
  className?: string;
  description?: ReactNode;
  footer?: ReactNode;
  title: ReactNode;
}) {
  return (
    <PosPanel className={cn("flex h-full min-h-0 min-w-0 flex-col px-3.5 py-3", className)}>
      <PosSectionTitle action={action ?? badge} description={description} title={title} />
      <div className="mt-3 min-h-0 flex-1 overflow-hidden">{children}</div>
      {footer ? (
        <div className="mt-3 border-t border-[var(--pos-shell-border)] pt-3">{footer}</div>
      ) : null}
    </PosPanel>
  );
}

export function PosHistoryView({
  action,
  children,
  className,
  description,
  footer,
  title,
  toolbar,
}: {
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  description?: ReactNode;
  footer?: ReactNode;
  title: ReactNode;
  toolbar?: ReactNode;
}) {
  return (
    <PosPanel className={cn("flex h-full min-h-0 min-w-0 flex-col px-3.5 py-3", className)}>
      <PosSectionTitle action={action} description={description} title={title} />
      {toolbar ? (
        <div className="mt-3 border-t border-[var(--pos-shell-border)] pt-3">{toolbar}</div>
      ) : null}
      <div className="mt-3 min-h-0 flex-1 overflow-hidden">{children}</div>
      {footer ? (
        <div className="mt-3 border-t border-[var(--pos-shell-border)] pt-3">{footer}</div>
      ) : null}
    </PosPanel>
  );
}

export function PosPagination({
  className,
  itemLabel = "registros",
  onPageChange,
  page,
  pageCount,
  totalItems,
}: {
  className?: string;
  itemLabel?: string;
  onPageChange: (page: number) => void;
  page: number;
  pageCount: number;
  totalItems?: number;
}) {
  if (pageCount <= 1) {
    return null;
  }

  const canGoBack = page > 1;
  const canGoForward = page < pageCount;

  return (
    <div className={cn("pos-record-pagination", className)}>
      <PosButton
        disabled={!canGoBack}
        leadingIcon={<ArrowLeftIcon className="h-4 w-4" />}
        onClick={() => onPageChange(page - 1)}
        variant="neutral"
      >
        Anterior
      </PosButton>
      <div className="text-center">
        <p className="text-sm font-semibold text-slate-950">
          Pagina {page} de {pageCount}
        </p>
        {typeof totalItems === "number" ? (
          <p className="text-xs text-slate-500">
            {totalItems} {itemLabel}
          </p>
        ) : null}
      </div>
      <PosButton
        disabled={!canGoForward}
        onClick={() => onPageChange(page + 1)}
        trailingIcon={<ChevronRightIcon className="h-4 w-4" />}
        variant="neutral"
      >
        Siguiente
      </PosButton>
    </div>
  );
}

export function PosRecordMeta({
  className,
  reference,
  status,
  statusTone = "draft",
  timeZone,
  timestamp,
}: {
  className?: string;
  reference?: string | null;
  status?: string | null;
  statusTone?:
    | "blocked"
    | "confirmed"
    | "draft"
    | "error"
    | "pending"
    | "ready"
    | "success"
    | "warning";
  timeZone?: string;
  timestamp?: string | null;
}) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2 text-xs text-slate-500", className)}>
      <span className="font-semibold text-slate-700">{formatRecordReference(reference)}</span>
      {status ? (
        <PosStatusBadge status={statusTone}>{formatRecordStatus(status)}</PosStatusBadge>
      ) : null}
      {timestamp && timeZone ? (
        <span>{formatCompactLocalDateTime(timestamp, timeZone)}</span>
      ) : null}
    </div>
  );
}
