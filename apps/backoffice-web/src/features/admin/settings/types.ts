export interface AdminSettingBackendContract {
  detailEndpoint: string;
  exportSupported: boolean;
  historySupported: boolean;
  listEndpoint: string;
  resetEndpoint: string;
  scopedOverridesSupported: boolean;
  secretStorageSupported: boolean;
  updateEndpoint: string;
}

export interface AdminSettingOption {
  id: string;
  label: string;
}

export interface AdminSettingCategory {
  id: string;
  label: string;
  description: string;
}

export interface AdminSettingValidationRule {
  rule: string;
  value: unknown | null;
  message: string;
}

export interface AdminSettingDefinition {
  affectsModules: string[];
  category: string;
  categoryLabel: string;
  defaultValue: unknown | null;
  description: string;
  isReadonly: boolean;
  isRequired: boolean;
  isSensitive: boolean;
  key: string;
  label: string;
  options: AdminSettingOption[];
  requiresRestart: boolean;
  scope: string;
  supportedScopes: string[];
  type: string;
  validationRules: AdminSettingValidationRule[];
}

export interface AdminSettingValue {
  currentValue: unknown | null;
  effectiveValue: unknown | null;
  inheritedFrom: string | null;
  key: string;
  scope: string;
  scopeId: string | null;
  status: string;
  updatedAt: string | null;
  updatedBy: string | null;
  warningState: string;
}

export interface AdminSettingWarning {
  code: string;
  message: string;
  severity: string;
}

export interface AdminSettingListItem {
  availableActions: string[];
  definition: AdminSettingDefinition;
  value: AdminSettingValue;
  warnings: AdminSettingWarning[];
}

export interface AdminSettingMetrics {
  activeSettings: string;
  warningSettings: string;
  incompleteRequired: string;
  recentChanges: string | null;
  sensitiveSettings: string;
  scopedOverrides: string;
  integrationSettings: string;
}

export interface AdminSettingFilterOptions {
  categories: AdminSettingOption[];
  modules: AdminSettingOption[];
  readonlyStates: AdminSettingOption[];
  scopes: AdminSettingOption[];
  sensitivities: AdminSettingOption[];
  statuses: AdminSettingOption[];
}

export interface AdminSettingsListResponse {
  backendContract: AdminSettingBackendContract;
  categories: AdminSettingCategory[];
  filterOptions: AdminSettingFilterOptions;
  isBackendConnected: boolean;
  items: AdminSettingListItem[];
  metrics: AdminSettingMetrics;
  total: number;
}

export interface AdminSettingValidation {
  isValid: boolean;
  messages: string[];
}

export interface AdminSettingHistoryItem {
  changedAt: string;
  changedBy: string | null;
  newValueMasked: string;
  note: string | null;
  oldValueMasked: string;
  scope: string;
}

export interface AdminSettingDetail {
  availableActions: string[];
  definition: AdminSettingDefinition;
  history: AdminSettingHistoryItem[];
  validation: AdminSettingValidation;
  value: AdminSettingValue;
  warnings: AdminSettingWarning[];
}

export interface AdminSettingsFilters {
  affectedModule: string;
  category: string;
  readonly: string;
  scope: string;
  search: string;
  sensitivity: string;
  status: string;
}

export interface AdminSettingUpdatePayload {
  changeNote?: string | null;
  confirmSensitive?: boolean;
  value: unknown;
}

export interface AdminSettingResetPayload {
  changeNote?: string | null;
  confirmSensitive?: boolean;
}
