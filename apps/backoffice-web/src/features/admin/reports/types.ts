export interface AdminReportFilterOption {
  id: string;
  label: string;
}

export interface AdminReportFilterDefinition {
  defaultValue: string | null;
  key: string;
  label: string;
  options: AdminReportFilterOption[];
  optionsSource: string | null;
  required: boolean;
  type: string;
}

export interface AdminReportDefinition {
  availableFilters: AdminReportFilterDefinition[];
  backendEndpoint: string | null;
  category: string;
  categoryLabel: string;
  code: string;
  description: string;
  isSensitive: boolean;
  name: string;
  previewKind: string;
  requiredPermissions: string[];
  sourceModules: string[];
  status: string;
  supportedExports: string[];
  unavailableReason: string | null;
}

export interface AdminReportCatalogFilters {
  category: string;
  exportSupport: string;
  search: string;
  sensitivity: string;
  sourceModule: string;
  status: string;
}

export interface AdminReportCatalogFilterOptions {
  categories: AdminReportFilterOption[];
  exportFormats: AdminReportFilterOption[];
  sensitivities: AdminReportFilterOption[];
  sourceModules: AdminReportFilterOption[];
  statuses: AdminReportFilterOption[];
}

export interface AdminReportCatalogMetrics {
  availableReports: string;
  categoryCount: string;
  exportableReports: string;
  pendingBackendReports: string;
  recentlyGeneratedReports: string | null;
  sensitiveReports: string;
}

export interface AdminReportBackendContract {
  asyncJobsSupported: boolean;
  definitionsEndpoint: string;
  exportEndpoint: string;
  generationHistorySupported: boolean;
  previewEndpoint: string;
  savedConfigurationsSupported: boolean;
  supportedExportFormats: string[];
}

export interface AdminReportDefinitionsResponse {
  backendContract: AdminReportBackendContract;
  definitions: AdminReportDefinition[];
  filterOptions: AdminReportCatalogFilterOptions;
  isBackendConnected: boolean;
  metrics: AdminReportCatalogMetrics;
  total: number;
}

export interface AdminReportSummaryCard {
  helperText: string | null;
  label: string;
  tone: string;
  value: string;
}

export interface AdminReportColumn {
  key: string;
  kind: string;
  label: string;
}

export interface AdminReportRelatedLink {
  canOpen: boolean;
  documentId: string | null;
  documentType: string | null;
  label: string;
  module: string;
  reference: string | null;
  routeHint: string | null;
}

export interface AdminReportRow {
  cells: Record<string, string | null>;
  id: string;
  sourceDocumentLinks: AdminReportRelatedLink[];
}

export interface AdminReportPreview {
  columns: AdminReportColumn[];
  filtersApplied: Record<string, string | null>;
  generatedAt: string;
  relatedLinks: AdminReportRelatedLink[];
  reportCode: string;
  reportName: string;
  rows: AdminReportRow[];
  summaryCards: AdminReportSummaryCard[];
  warnings: string[];
}

export interface AdminReportExportResponse {
  filtersApplied: Record<string, string | null>;
  format: string;
  generatedAt: string;
  reportCode: string;
  reportName: string;
  rows: AdminReportRow[];
  totalRows: number;
  warnings: string[];
}
