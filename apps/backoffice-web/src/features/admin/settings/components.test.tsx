import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminSettingDetailPanel } from "./components/AdminSettingDetailPanel";
import { AdminSettingsFilters } from "./components/AdminSettingsFilters";
import { AdminSettingsList } from "./components/AdminSettingsList";
import { AdminSettingsPage } from "./pages/AdminSettingsPage";
import type {
  AdminSettingDetail,
  AdminSettingFilterOptions,
  AdminSettingListItem,
  AdminSettingsFilters as AdminSettingsFilterState,
} from "./types";

const filters: AdminSettingsFilterState = {
  affectedModule: "all",
  category: "all",
  readonly: "all",
  scope: "all",
  search: "",
  sensitivity: "all",
  status: "all",
};

const filterOptions: AdminSettingFilterOptions = {
  categories: [{ id: "tickets", label: "Tickets y comprobantes" }],
  modules: [{ id: "tickets", label: "Tickets" }],
  readonlyStates: [{ id: "editable", label: "Editables" }],
  scopes: [{ id: "global", label: "Global" }],
  sensitivities: [{ id: "sensitive", label: "Sensibles" }],
  statuses: [{ id: "warning", label: "Con advertencias" }],
};

const listItem: AdminSettingListItem = {
  availableActions: ["view", "edit"],
  definition: {
    affectsModules: ["tickets", "pos"],
    category: "tickets",
    categoryLabel: "Tickets y comprobantes",
    defaultValue: "Gracias por su compra.",
    description: "Texto operativo mostrado en comprobantes.",
    isReadonly: false,
    isRequired: false,
    isSensitive: false,
    key: "tickets.receipt_footer_text",
    label: "Pie de ticket",
    options: [],
    requiresRestart: false,
    scope: "global",
    supportedScopes: ["global"],
    type: "string",
    validationRules: [{ message: "Longitud maxima permitida.", rule: "max_length", value: 240 }],
  },
  value: {
    currentValue: "Gracias por su compra.",
    effectiveValue: "Gracias por su compra.",
    inheritedFrom: "default",
    key: "tickets.receipt_footer_text",
    scope: "global",
    scopeId: null,
    status: "ready",
    updatedAt: null,
    updatedBy: null,
    warningState: "ready",
  },
  warnings: [],
};

const sensitiveItem: AdminSettingListItem = {
  ...listItem,
  availableActions: ["view", "edit", "reset"],
  definition: {
    ...listItem.definition,
    category: "cash",
    categoryLabel: "Caja",
    isSensitive: true,
    key: "cash.cash_difference_tolerance",
    label: "Tolerancia de diferencia de caja",
    type: "money",
  },
  value: {
    ...listItem.value,
    effectiveValue: "valor sensible",
    key: "cash.cash_difference_tolerance",
    status: "warning",
    updatedAt: "2026-05-22T10:00:00Z",
    warningState: "warning",
  },
  warnings: [
    {
      code: "sensitive",
      message: "Cambiar este valor puede afectar operacion sensible.",
      severity: "warning",
    },
  ],
};

const detail: AdminSettingDetail = {
  availableActions: ["view", "edit"],
  definition: listItem.definition,
  history: [],
  validation: { isValid: true, messages: [] },
  value: listItem.value,
  warnings: [],
};

const sensitiveDetail: AdminSettingDetail = {
  availableActions: ["view", "edit", "reset"],
  definition: sensitiveItem.definition,
  history: [
    {
      changedAt: "2026-05-22T10:00:00Z",
      changedBy: "Admin",
      newValueMasked: "valor sensible",
      note: "Policy update",
      oldValueMasked: "valor sensible",
      scope: "global",
    },
  ],
  validation: { isValid: true, messages: [] },
  value: sensitiveItem.value,
  warnings: sensitiveItem.warnings,
};

function render(element: ReactElement) {
  return renderToString(element);
}

describe("admin settings UI components", () => {
  it("renders the page shell without a create action", () => {
    const queryClient = new QueryClient();
    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminSettingsPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Configuración");
    expect(html).toContain("Cambios auditables");
    expect(html).not.toContain("Nueva configuracion");
  });

  it("renders compact filter toolbar", () => {
    const html = render(
      <AdminSettingsFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Clave, modulo o descripcion");
    expect(html).toContain("Filtros");
    expect(html).toContain("Backend conectado");
    expect(html).not.toContain("Solo lectura");
  });

  it("renders category navigation, settings and empty state", () => {
    const emptyHtml = render(
      <AdminSettingsList
        categories={[]}
        items={[]}
        selectedCategory="all"
        selectedSettingKey={null}
        total={0}
        onSelectCategory={() => undefined}
        onSelectSetting={() => undefined}
      />,
    );
    expect(emptyHtml).toContain("No hay configuraciones que coincidan con los filtros seleccionados.");

    const html = render(
      <AdminSettingsList
        categories={[{ description: "Tickets", id: "tickets", label: "Tickets" }]}
        items={[listItem, sensitiveItem]}
        selectedCategory="all"
        selectedSettingKey="tickets.receipt_footer_text"
        total={2}
        onSelectCategory={() => undefined}
        onSelectSetting={() => undefined}
      />,
    );
    expect(html).toContain("Pie de ticket");
    expect(html).toContain("Tolerancia de diferencia de caja");
    expect(html).toContain("Sensible");
  });

  it("renders detail editor, validations and no-history state", () => {
    const html = render(
      <AdminSettingDetailPanel
        changeNote=""
        confirmSensitive={false}
        detail={detail}
        editorValue="Gracias por su compra."
        selectedSetting={listItem}
        onChangeEditorValue={() => undefined}
        onCopyKey={() => undefined}
        onReset={() => undefined}
        onSave={() => undefined}
        onSetChangeNote={() => undefined}
        onSetConfirmSensitive={() => undefined}
      />,
    );

    expect(html).toContain("Detalle de configuracion");
    expect(html).toContain("Pie de ticket");
    expect(html).toContain("Longitud maxima permitida.");
    expect(html).toContain("No hay historial de cambios disponible para esta configuracion.");
  });

  it("renders sensitive change preview, masked history and readonly state", () => {
    const sensitiveHtml = render(
      <AdminSettingDetailPanel
        changeNote="Policy update"
        confirmSensitive={false}
        detail={sensitiveDetail}
        editorValue="75"
        selectedSetting={sensitiveItem}
        onChangeEditorValue={() => undefined}
        onCopyKey={() => undefined}
        onReset={() => undefined}
        onSave={() => undefined}
        onSetChangeNote={() => undefined}
        onSetConfirmSensitive={() => undefined}
      />,
    );

    expect(sensitiveHtml).toContain("Confirmo que este cambio es sensible");
    expect(sensitiveHtml).toContain("valor sensible");
    expect(sensitiveHtml).toContain("Policy update");

    const readonlyHtml = render(
      <AdminSettingDetailPanel
        changeNote=""
        confirmSensitive={false}
        detail={{
          ...detail,
          definition: { ...detail.definition, isReadonly: true },
        }}
        editorValue=""
        selectedSetting={{
          ...listItem,
          definition: { ...listItem.definition, isReadonly: true },
        }}
        onChangeEditorValue={() => undefined}
        onCopyKey={() => undefined}
        onReset={() => undefined}
        onSave={() => undefined}
        onSetChangeNote={() => undefined}
        onSetConfirmSensitive={() => undefined}
      />,
    );
    expect(readonlyHtml).toContain(
      "Esta configuracion es de solo lectura y no puede modificarse desde Backoffice.",
    );
  });
});
