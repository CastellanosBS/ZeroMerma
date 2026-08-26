import type { ReactNode } from "react";

import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminSettingDetail, AdminSettingListItem } from "../types";

interface AdminSettingDetailPanelProps {
  detail: AdminSettingDetail | null;
  editorValue: string;
  errorMessage?: string | null;
  isLoading?: boolean;
  onChangeEditorValue: (value: string) => void;
  onCopyKey: (key: string) => void;
  onReset: () => void;
  onSave: () => void;
  onSetChangeNote: (value: string) => void;
  onSetConfirmSensitive: (value: boolean) => void;
  resetPending?: boolean;
  savePending?: boolean;
  changeNote: string;
  confirmSensitive: boolean;
  selectedSetting: AdminSettingListItem | null;
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h4 className="text-sm font-semibold text-slate-950">{title}</h4>
      <div className="mt-2 min-w-0">{children}</div>
    </section>
  );
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <span className="block truncate text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
        {label}
      </span>
      <span className="mt-0.5 block min-w-0 truncate text-sm font-semibold text-slate-950">
        {value}
      </span>
    </div>
  );
}

function formatValue(value: unknown): string {
  if (typeof value === "boolean") {
    return value ? "Habilitado" : "Deshabilitado";
  }
  if (value === null || value === undefined || value === "") {
    return "Sin valor";
  }
  return String(value);
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "No disponible";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function renderEditor(
  detail: AdminSettingDetail,
  editorValue: string,
  onChangeEditorValue: (value: string) => void,
) {
  const definition = detail.definition;
  const commonClass =
    "h-10 w-full rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]";

  if (definition.isReadonly) {
    return (
      <AdminEmptyState
        description="Esta configuracion es de solo lectura y no puede modificarse desde Backoffice."
        title="Solo lectura"
      />
    );
  }

  if (definition.type === "boolean") {
    return (
      <select
        className={commonClass}
        value={editorValue}
        onChange={(event) => onChangeEditorValue(event.target.value)}
      >
        <option value="">Selecciona un valor</option>
        <option value="true">Habilitado</option>
        <option value="false">Deshabilitado</option>
      </select>
    );
  }

  if (definition.type === "enum") {
    return (
      <select
        className={commonClass}
        value={editorValue}
        onChange={(event) => onChangeEditorValue(event.target.value)}
      >
        <option value="">Selecciona un valor</option>
        {definition.options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }

  if (["money", "number", "percentage", "duration"].includes(definition.type)) {
    return (
      <input
        className={commonClass}
        inputMode="decimal"
        placeholder={definition.isSensitive ? "Captura nuevo valor" : "0"}
        type="number"
        value={editorValue}
        onChange={(event) => onChangeEditorValue(event.target.value)}
      />
    );
  }

  return (
    <input
      className={commonClass}
      placeholder={definition.isSensitive ? "Captura nuevo valor" : definition.label}
      value={editorValue}
      onChange={(event) => onChangeEditorValue(event.target.value)}
    />
  );
}

export function AdminSettingDetailPanel({
  changeNote,
  confirmSensitive,
  detail,
  editorValue,
  errorMessage,
  isLoading = false,
  onChangeEditorValue,
  onCopyKey,
  onReset,
  onSave,
  onSetChangeNote,
  onSetConfirmSensitive,
  resetPending = false,
  savePending = false,
  selectedSetting,
}: AdminSettingDetailPanelProps) {
  if (!selectedSetting) {
    return (
      <AdminEmptyState
        description="Selecciona una configuracion para revisar valor, alcance, validaciones e historial de cambios."
        title="Sin configuracion seleccionada"
      />
    );
  }

  if (isLoading) {
    return (
      <AdminEmptyState
        description="Consultando definicion, valor efectivo, validaciones e historial."
        title="Cargando configuracion"
      />
    );
  }

  if (errorMessage) {
    return <AdminEmptyState description={errorMessage} title="No se pudo cargar configuracion" />;
  }

  if (!detail) {
    return (
      <AdminEmptyState
        description="Selecciona una configuracion para revisar valor, alcance, validaciones e historial de cambios."
        title="Sin configuracion seleccionada"
      />
    );
  }

  const hasEditorValue = editorValue.trim().length > 0;
  const saveDisabled =
    detail.definition.isReadonly ||
    savePending ||
    !hasEditorValue ||
    (detail.definition.isSensitive && !confirmSensitive);
  const resetEnabled = detail.availableActions.includes("reset");

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/70">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] bg-white px-3 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Detalle de configuracion
            </p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
              {detail.definition.label}
            </h3>
            <p className="mt-1 truncate text-sm text-slate-600">{detail.definition.key}</p>
          </div>
          <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
            {detail.value.status}
          </span>
        </div>
      </div>

      <div className="grid min-h-0 gap-2 overflow-y-auto p-2.5">
        <Section title="Resumen">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Clave" value={detail.definition.key} />
            <Fact label="Categoria" value={detail.definition.categoryLabel} />
            <Fact label="Valor efectivo" value={formatValue(detail.value.effectiveValue)} />
            <Fact label="Valor por defecto" value={formatValue(detail.definition.defaultValue)} />
            <Fact label="Alcance" value={detail.value.scope} />
            <Fact label="Heredado de" value={detail.value.inheritedFrom ?? "Valor propio"} />
            <Fact label="Actualizado" value={formatDateTime(detail.value.updatedAt)} />
            <Fact label="Actualizado por" value={detail.value.updatedBy ?? "No disponible"} />
          </div>
          <p className="mt-3 text-sm leading-5 text-slate-600">{detail.definition.description}</p>
        </Section>

        <Section title="Modulos afectados">
          <div className="flex min-w-0 flex-wrap gap-2">
            {detail.definition.affectsModules.map((module) => (
              <span
                className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600"
                key={module}
              >
                {module}
              </span>
            ))}
          </div>
        </Section>

        <Section title="Editor de valor">
          <div className="grid gap-2">
            {renderEditor(detail, editorValue, onChangeEditorValue)}

            <label>
              <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                Nota del cambio
              </span>
              <textarea
                className="min-h-20 w-full rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                placeholder="Motivo operativo del cambio"
                value={changeNote}
                onChange={(event) => onSetChangeNote(event.target.value)}
              />
            </label>

            {detail.definition.isSensitive ? (
              <label className="flex items-start gap-2 rounded-2xl border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-xs font-semibold text-[var(--ui-color-warning)]">
                <input
                  checked={confirmSensitive}
                  className="mt-0.5"
                  type="checkbox"
                  onChange={(event) => onSetConfirmSensitive(event.target.checked)}
                />
                <span>
                  Confirmo que este cambio es sensible. Valor anterior:{" "}
                  {formatValue(detail.value.effectiveValue)}. Valor nuevo:{" "}
                  {editorValue || "sin capturar"}. No es aprobacion de supervisor; queda auditado.
                </span>
              </label>
            ) : null}

            <div className="flex min-w-0 flex-wrap justify-end gap-2">
              <button
                className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                type="button"
                onClick={() => onCopyKey(detail.definition.key)}
              >
                Copiar clave
              </button>
              <button
                className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:opacity-40"
                disabled={!resetEnabled || resetPending}
                type="button"
                onClick={onReset}
              >
                Restablecer
              </button>
              <button
                className="rounded-2xl border border-[var(--ui-color-info)] bg-[var(--ui-color-info)] px-3 py-2 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-40"
                disabled={saveDisabled}
                type="button"
                onClick={onSave}
              >
                Guardar cambio
              </button>
            </div>
          </div>
        </Section>

        <Section title="Validaciones y advertencias">
          {detail.warnings.length > 0 || detail.definition.validationRules.length > 0 ? (
            <div className="grid gap-2">
              {detail.warnings.map((warning) => (
                <p
                  className="rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-warning)]"
                  key={warning.code}
                >
                  {warning.message}
                </p>
              ))}
              {detail.definition.validationRules.map((rule) => (
                <p
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-600"
                  key={`${rule.rule}-${String(rule.value)}`}
                >
                  {rule.message} {rule.value === null ? "" : String(rule.value)}
                </p>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Sin advertencias de validacion para esta configuracion.
            </p>
          )}
        </Section>

        <Section title="Historial">
          {detail.history.length > 0 ? (
            <div className="grid gap-2">
              {detail.history.map((item) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm text-slate-600"
                  key={`${item.changedAt}-${item.newValueMasked}`}
                >
                  <p className="font-semibold text-slate-950">
                    {item.oldValueMasked}
                    {" -> "}
                    {item.newValueMasked}
                  </p>
                  <p className="mt-1 text-xs">
                    {formatDateTime(item.changedAt)} - {item.changedBy ?? "Sistema"} -{" "}
                    {item.scope}
                  </p>
                  <p className="mt-1 text-xs">{item.note ?? "Sin nota"}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              No hay historial de cambios disponible para esta configuracion.
            </p>
          )}
        </Section>

        {!detail.definition.supportedScopes.includes("branch") ? (
          <p className="rounded-[18px] border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm text-slate-600">
            Este alcance aun no esta disponible para esta configuracion. La version actual es
            global.
          </p>
        ) : null}
      </div>
    </aside>
  );
}
