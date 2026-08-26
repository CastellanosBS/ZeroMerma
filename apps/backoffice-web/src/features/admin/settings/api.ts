import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminSettingBackendContract,
  AdminSettingDefinition,
  AdminSettingDetail,
  AdminSettingFilterOptions,
  AdminSettingsFilters,
  AdminSettingsListResponse,
  AdminSettingUpdatePayload,
} from "./types";

type ApiBackendContract = components["schemas"]["AdminSettingBackendContractView"];
type ApiDefinition = components["schemas"]["AdminSettingDefinitionView"];
type ApiDetail = components["schemas"]["AdminSettingDetailView"];
type ApiFilterOptions = components["schemas"]["AdminSettingFilterOptionsView"];
type ApiListItem = components["schemas"]["AdminSettingListItemView"];
type ApiListResponse = components["schemas"]["AdminSettingsListResponse"];
type ApiOption = components["schemas"]["AdminSettingOptionView"];
type ApiUpdateRequest = components["schemas"]["AdminSettingUpdateRequest"];

export const adminSettingBackendContract: AdminSettingBackendContract = {
  detailEndpoint: "GET /v1/admin/settings/{key}",
  exportSupported: false,
  historySupported: true,
  listEndpoint: "GET /v1/admin/settings",
  resetEndpoint: "POST /v1/admin/settings/{key}/reset",
  scopedOverridesSupported: false,
  secretStorageSupported: false,
  updateEndpoint: "PATCH /v1/admin/settings/{key}",
};

function mapOption(option: ApiOption) {
  return { id: option.id, label: option.label };
}

function mapDefinition(definition: ApiDefinition): AdminSettingDefinition {
  return {
    affectsModules: definition.affects_modules,
    category: definition.category,
    categoryLabel: definition.category_label,
    defaultValue: definition.default_value ?? null,
    description: definition.description,
    isReadonly: definition.is_readonly,
    isRequired: definition.is_required,
    isSensitive: definition.is_sensitive,
    key: definition.key,
    label: definition.label,
    options: (definition.options ?? []).map(mapOption),
    requiresRestart: definition.requires_restart,
    scope: definition.scope,
    supportedScopes: definition.supported_scopes,
    type: definition.type,
    validationRules: (definition.validation_rules ?? []).map((rule) => ({
      message: rule.message,
      rule: rule.rule,
      value: rule.value ?? null,
    })),
  };
}

function mapBackendContract(contract?: ApiBackendContract): AdminSettingBackendContract {
  if (!contract) {
    return adminSettingBackendContract;
  }
  return {
    detailEndpoint: contract.detail_endpoint,
    exportSupported: contract.export_supported,
    historySupported: contract.history_supported,
    listEndpoint: contract.list_endpoint,
    resetEndpoint: contract.reset_endpoint,
    scopedOverridesSupported: contract.scoped_overrides_supported,
    secretStorageSupported: contract.secret_storage_supported,
    updateEndpoint: contract.update_endpoint,
  };
}

function mapFilterOptions(options: ApiFilterOptions): AdminSettingFilterOptions {
  return {
    categories: options.categories.map(mapOption),
    modules: options.modules.map(mapOption),
    readonlyStates: options.readonly_states.map(mapOption),
    scopes: options.scopes.map(mapOption),
    sensitivities: options.sensitivities.map(mapOption),
    statuses: options.statuses.map(mapOption),
  };
}

function mapListItem(item: ApiListItem) {
  return {
    availableActions: item.available_actions ?? [],
    definition: mapDefinition(item.definition),
    value: {
      currentValue: item.value.current_value ?? null,
      effectiveValue: item.value.effective_value ?? null,
      inheritedFrom: item.value.inherited_from ?? null,
      key: item.value.key,
      scope: item.value.scope,
      scopeId: item.value.scope_id ?? null,
      status: item.value.status,
      updatedAt: item.value.updated_at ?? null,
      updatedBy: item.value.updated_by ?? null,
      warningState: item.value.warning_state,
    },
    warnings: (item.warnings ?? []).map((warning) => ({
      code: warning.code,
      message: warning.message,
      severity: warning.severity,
    })),
  };
}

function mapDetail(detail: ApiDetail): AdminSettingDetail {
  return {
    availableActions: detail.available_actions ?? [],
    definition: mapDefinition(detail.definition),
    history: (detail.history ?? []).map((item) => ({
      changedAt: item.changed_at,
      changedBy: item.changed_by ?? null,
      newValueMasked: item.new_value_masked,
      note: item.note ?? null,
      oldValueMasked: item.old_value_masked,
      scope: item.scope,
    })),
    validation: {
      isValid: detail.validation.is_valid,
      messages: detail.validation.messages ?? [],
    },
    value: {
      currentValue: detail.value.current_value ?? null,
      effectiveValue: detail.value.effective_value ?? null,
      inheritedFrom: detail.value.inherited_from ?? null,
      key: detail.value.key,
      scope: detail.value.scope,
      scopeId: detail.value.scope_id ?? null,
      status: detail.value.status,
      updatedAt: detail.value.updated_at ?? null,
      updatedBy: detail.value.updated_by ?? null,
      warningState: detail.value.warning_state,
    },
    warnings: (detail.warnings ?? []).map((warning) => ({
      code: warning.code,
      message: warning.message,
      severity: warning.severity,
    })),
  };
}

function mapListResponse(response: ApiListResponse): AdminSettingsListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    categories: response.categories.map((category) => ({
      description: category.description,
      id: category.id,
      label: category.label,
    })),
    filterOptions: mapFilterOptions(response.filter_options),
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapListItem),
    metrics: {
      activeSettings: String(response.metrics.active_settings),
      incompleteRequired: String(response.metrics.incomplete_required),
      integrationSettings: String(response.metrics.integration_settings),
      recentChanges:
        response.metrics.recent_changes === null || response.metrics.recent_changes === undefined
          ? null
          : String(response.metrics.recent_changes),
      scopedOverrides: String(response.metrics.scoped_overrides),
      sensitiveSettings: String(response.metrics.sensitive_settings),
      warningSettings: String(response.metrics.warning_settings),
    },
    total: response.total,
  };
}

function appendOptionalParam(
  params: URLSearchParams,
  key: string,
  value: string | null | undefined,
) {
  if (!value || value === "all") {
    return;
  }
  params.set(key, value);
}

function buildSearchParams(filters: AdminSettingsFilters): URLSearchParams {
  const params = new URLSearchParams();
  appendOptionalParam(params, "affected_module", filters.affectedModule);
  appendOptionalParam(params, "category", filters.category);
  appendOptionalParam(params, "readonly", filters.readonly);
  appendOptionalParam(params, "scope", filters.scope);
  appendOptionalParam(params, "search", filters.search);
  appendOptionalParam(params, "sensitivity", filters.sensitivity);
  appendOptionalParam(params, "status", filters.status);
  return params;
}

export async function fetchAdminSettings(
  accessToken: string,
  filters: AdminSettingsFilters,
): Promise<AdminSettingsListResponse> {
  const params = buildSearchParams(filters);
  const suffix = params.toString();
  const response = await requestJson<ApiListResponse>({
    accessToken,
    path: `/v1/admin/settings${suffix ? `?${suffix}` : ""}`,
  });
  return mapListResponse(response);
}

export async function fetchAdminSettingDetail(
  accessToken: string,
  settingKey: string,
): Promise<AdminSettingDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/settings/${encodeURIComponent(settingKey)}`,
  });
  return mapDetail(response);
}

export async function updateAdminSetting(
  accessToken: string,
  settingKey: string,
  payload: AdminSettingUpdatePayload,
): Promise<AdminSettingDetail> {
  const body: ApiUpdateRequest = {
    change_note: payload.changeNote ?? null,
    confirm_sensitive: payload.confirmSensitive ?? false,
    value: payload.value,
  };
  const response = await requestJson<ApiDetail>({
    accessToken,
    body,
    method: "PATCH",
    path: `/v1/admin/settings/${encodeURIComponent(settingKey)}`,
  });
  return mapDetail(response);
}

export async function resetAdminSetting(
  accessToken: string,
  settingKey: string,
  payload: { changeNote?: string | null; confirmSensitive?: boolean },
): Promise<AdminSettingDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    body: {
      change_note: payload.changeNote ?? null,
      confirm_sensitive: payload.confirmSensitive ?? false,
    },
    method: "POST",
    path: `/v1/admin/settings/${encodeURIComponent(settingKey)}/reset`,
  });
  return mapDetail(response);
}
