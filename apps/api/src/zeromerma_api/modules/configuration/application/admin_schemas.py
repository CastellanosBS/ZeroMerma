from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AdminSettingBackendContractView(BaseModel):
    list_endpoint: str = "GET /v1/admin/settings"
    detail_endpoint: str = "GET /v1/admin/settings/{key}"
    update_endpoint: str = "PATCH /v1/admin/settings/{key}"
    reset_endpoint: str = "POST /v1/admin/settings/{key}/reset"
    scoped_overrides_supported: bool = False
    secret_storage_supported: bool = False
    history_supported: bool = True
    export_supported: bool = False


class AdminSettingOptionView(BaseModel):
    id: str
    label: str


class AdminSettingCategoryView(BaseModel):
    id: str
    label: str
    description: str


class AdminSettingValidationRuleView(BaseModel):
    rule: str
    value: Any | None = None
    message: str


class AdminSettingDefinitionView(BaseModel):
    key: str
    label: str
    description: str
    category: str
    category_label: str
    type: str
    options: list[AdminSettingOptionView] = Field(default_factory=list)
    default_value: Any | None = None
    scope: str
    supported_scopes: list[str]
    is_required: bool
    is_sensitive: bool
    is_readonly: bool
    requires_restart: bool
    affects_modules: list[str]
    validation_rules: list[AdminSettingValidationRuleView] = Field(default_factory=list)


class AdminSettingValueView(BaseModel):
    key: str
    current_value: Any | None = None
    effective_value: Any | None = None
    inherited_from: str | None = None
    scope: str
    scope_id: str | None = None
    status: str
    warning_state: str
    updated_at: datetime | None = None
    updated_by: str | None = None


class AdminSettingWarningView(BaseModel):
    code: str
    message: str
    severity: str


class AdminSettingListItemView(BaseModel):
    definition: AdminSettingDefinitionView
    value: AdminSettingValueView
    warnings: list[AdminSettingWarningView] = Field(default_factory=list)
    available_actions: list[str] = Field(default_factory=list)


class AdminSettingMetricsView(BaseModel):
    active_settings: int
    warning_settings: int
    incomplete_required: int
    recent_changes: int | None = None
    sensitive_settings: int
    scoped_overrides: int
    integration_settings: int


class AdminSettingFilterOptionsView(BaseModel):
    categories: list[AdminSettingOptionView]
    statuses: list[AdminSettingOptionView]
    sensitivities: list[AdminSettingOptionView]
    readonly_states: list[AdminSettingOptionView]
    scopes: list[AdminSettingOptionView]
    modules: list[AdminSettingOptionView]


class AdminSettingsListResponse(BaseModel):
    backend_contract: AdminSettingBackendContractView = Field(
        default_factory=AdminSettingBackendContractView,
    )
    categories: list[AdminSettingCategoryView]
    filter_options: AdminSettingFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminSettingListItemView]
    metrics: AdminSettingMetricsView
    total: int


class AdminSettingValidationView(BaseModel):
    is_valid: bool
    messages: list[str] = Field(default_factory=list)


class AdminSettingHistoryItemView(BaseModel):
    changed_at: datetime
    changed_by: str | None = None
    old_value_masked: str
    new_value_masked: str
    scope: str
    note: str | None = None


class AdminSettingDetailView(BaseModel):
    definition: AdminSettingDefinitionView
    value: AdminSettingValueView
    validation: AdminSettingValidationView
    warnings: list[AdminSettingWarningView] = Field(default_factory=list)
    history: list[AdminSettingHistoryItemView] = Field(default_factory=list)
    available_actions: list[str] = Field(default_factory=list)


class AdminSettingUpdateRequest(BaseModel):
    value: Any
    change_note: str | None = None
    confirm_sensitive: bool = False


class AdminSettingResetRequest(BaseModel):
    change_note: str | None = None
    confirm_sensitive: bool = False
