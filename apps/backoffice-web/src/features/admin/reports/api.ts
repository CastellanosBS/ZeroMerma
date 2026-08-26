import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminReportBackendContract,
  AdminReportCatalogFilters,
  AdminReportDefinitionsResponse,
  AdminReportDefinition,
  AdminReportExportResponse,
  AdminReportFilterDefinition,
  AdminReportFilterOption,
  AdminReportPreview,
  AdminReportRelatedLink,
  AdminReportRow,
} from "./types";

type ApiBackendContract = components["schemas"]["AdminReportBackendContractView"];
type ApiDefinition = components["schemas"]["AdminReportDefinitionView"];
type ApiDefinitionsResponse = components["schemas"]["AdminReportDefinitionsResponse"];
type ApiExportResponse = components["schemas"]["AdminReportExportResponse"];
type ApiFilterDefinition = components["schemas"]["AdminReportFilterDefinitionView"];
type ApiFilterOption = components["schemas"]["AdminReportFilterOptionView"];
type ApiPreviewResponse = components["schemas"]["AdminReportPreviewResponse"];
type ApiRelatedLink = components["schemas"]["AdminReportRelatedLinkView"];
type ApiRow = components["schemas"]["AdminReportRowView"];

export const adminReportBackendContract: AdminReportBackendContract = {
  asyncJobsSupported: false,
  definitionsEndpoint: "GET /v1/admin/reports",
  exportEndpoint: "POST /v1/admin/reports/{report_code}/export",
  generationHistorySupported: false,
  previewEndpoint: "POST /v1/admin/reports/{report_code}/preview",
  savedConfigurationsSupported: false,
  supportedExportFormats: ["json"],
};

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

function mapOption(option: ApiFilterOption): AdminReportFilterOption {
  return { id: option.code, label: option.label };
}

function mapFilterDefinition(filter: ApiFilterDefinition): AdminReportFilterDefinition {
  return {
    defaultValue: filter.default_value ?? null,
    key: filter.key,
    label: filter.label,
    options: (filter.options ?? []).map(mapOption),
    optionsSource: filter.options_source ?? null,
    required: filter.required,
    type: filter.type,
  };
}

function mapDefinition(definition: ApiDefinition): AdminReportDefinition {
  return {
    availableFilters: definition.available_filters.map(mapFilterDefinition),
    backendEndpoint: definition.backend_endpoint ?? null,
    category: definition.category,
    categoryLabel: definition.category_label,
    code: definition.code,
    description: definition.description,
    isSensitive: definition.is_sensitive,
    name: definition.name,
    previewKind: definition.preview_kind,
    requiredPermissions: definition.required_permissions,
    sourceModules: definition.source_modules,
    status: definition.status,
    supportedExports: definition.supported_exports,
    unavailableReason: definition.unavailable_reason ?? null,
  };
}

function mapBackendContract(contract?: ApiBackendContract): AdminReportBackendContract {
  if (!contract) {
    return adminReportBackendContract;
  }
  return {
    asyncJobsSupported: contract.async_jobs_supported,
    definitionsEndpoint: contract.definitions_endpoint,
    exportEndpoint: contract.export_endpoint,
    generationHistorySupported: contract.generation_history_supported,
    previewEndpoint: contract.preview_endpoint,
    savedConfigurationsSupported: contract.saved_configurations_supported,
    supportedExportFormats: contract.supported_export_formats ?? [],
  };
}

function mapRelatedLink(link: ApiRelatedLink): AdminReportRelatedLink {
  return {
    canOpen: link.can_open,
    documentId: link.document_id ?? null,
    documentType: link.document_type ?? null,
    label: link.label,
    module: link.module,
    reference: link.reference ?? null,
    routeHint: link.route_hint ?? null,
  };
}

function mapRow(row: ApiRow): AdminReportRow {
  return {
    cells: row.cells,
    id: row.id,
    sourceDocumentLinks: (row.source_document_links ?? []).map(mapRelatedLink),
  };
}

function mapPreview(response: ApiPreviewResponse): AdminReportPreview {
  return {
    columns: response.columns.map((column) => ({
      key: column.key,
      kind: column.kind,
      label: column.label,
    })),
    filtersApplied: response.filters_applied,
    generatedAt: response.generated_at,
    relatedLinks: response.related_links.map(mapRelatedLink),
    reportCode: response.report_code,
    reportName: response.report_name,
    rows: response.rows.map(mapRow),
    summaryCards: response.summary_cards.map((card) => ({
      helperText: card.helper_text ?? null,
      label: card.label,
      tone: card.tone,
      value: card.value,
    })),
    warnings: response.warnings ?? [],
  };
}

function mapDefinitionsResponse(response: ApiDefinitionsResponse): AdminReportDefinitionsResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    definitions: response.definitions.map(mapDefinition),
    filterOptions: {
      categories: response.filter_options.categories.map(mapOption),
      exportFormats: response.filter_options.export_formats.map(mapOption),
      sensitivities: response.filter_options.sensitivities.map(mapOption),
      sourceModules: response.filter_options.source_modules.map(mapOption),
      statuses: response.filter_options.statuses.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    metrics: {
      availableReports: String(response.metrics.available_reports),
      categoryCount: String(response.metrics.category_count),
      exportableReports: String(response.metrics.exportable_reports),
      pendingBackendReports: String(response.metrics.pending_backend_reports),
      recentlyGeneratedReports:
        response.metrics.recently_generated_reports === null ||
        response.metrics.recently_generated_reports === undefined
          ? null
          : String(response.metrics.recently_generated_reports),
      sensitiveReports: String(response.metrics.sensitive_reports),
    },
    total: response.total,
  };
}

function buildReportSearchParams(filters: AdminReportCatalogFilters): URLSearchParams {
  const params = new URLSearchParams();
  appendOptionalParam(params, "category", filters.category);
  appendOptionalParam(params, "export_support", filters.exportSupport);
  appendOptionalParam(params, "search", filters.search);
  appendOptionalParam(params, "sensitivity", filters.sensitivity);
  appendOptionalParam(params, "source_module", filters.sourceModule);
  appendOptionalParam(params, "status", filters.status);
  return params;
}

export async function fetchAdminReports(
  accessToken: string,
  filters: AdminReportCatalogFilters,
): Promise<AdminReportDefinitionsResponse> {
  const params = buildReportSearchParams(filters);
  const suffix = params.toString();
  const response = await requestJson<ApiDefinitionsResponse>({
    accessToken,
    path: `/v1/admin/reports${suffix ? `?${suffix}` : ""}`,
  });
  return mapDefinitionsResponse(response);
}

export async function previewAdminReport(
  accessToken: string,
  reportCode: string,
  filters: Record<string, string>,
): Promise<AdminReportPreview> {
  const response = await requestJson<ApiPreviewResponse>({
    accessToken,
    body: { filters },
    method: "POST",
    path: `/v1/admin/reports/${reportCode}/preview`,
  });
  return mapPreview(response);
}

export async function exportAdminReport(
  accessToken: string,
  reportCode: string,
  filters: Record<string, string>,
  format = "json",
): Promise<AdminReportExportResponse> {
  const response = await requestJson<ApiExportResponse>({
    accessToken,
    body: { filters, format },
    method: "POST",
    path: `/v1/admin/reports/${reportCode}/export`,
  });
  return {
    filtersApplied: response.filters_applied,
    format: response.format,
    generatedAt: response.generated_at,
    reportCode: response.report_code,
    reportName: response.report_name,
    rows: response.rows.map(mapRow),
    totalRows: response.total_rows,
    warnings: response.warnings ?? [],
  };
}
