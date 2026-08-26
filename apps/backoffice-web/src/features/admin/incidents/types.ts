export type AdminIncidentStatus =
  | "OPEN"
  | "IN_REVIEW"
  | "IN_PROGRESS"
  | "WAITING_ACTION"
  | "RESOLVED"
  | "CLOSED"
  | "CANCELLED";

export type AdminIncidentSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type AdminIncidentType =
  | "SANITATION_ISSUE"
  | "CLEANING_NON_COMPLIANCE"
  | "EQUIPMENT_FAILURE"
  | "PRODUCTION_ISSUE"
  | "INVENTORY_ISSUE"
  | "TRANSFER_ISSUE"
  | "WASTE_ISSUE"
  | "SAFETY_ISSUE"
  | "CUSTOMER_COMPLAINT"
  | "PROCESS_DEVIATION"
  | "OTHER";

export type AdminIncidentSourceType =
  | "MANUAL"
  | "CLEANING_LOG"
  | "SANITARY_VERIFICATION"
  | "EQUIPMENT"
  | "PRODUCTION"
  | "INVENTORY"
  | "TRANSFER"
  | "WASTE_MERMA"
  | "CUSTOMER_REPORT"
  | "CORRECTION";

export interface AdminIncidentBackendContract {
  addFollowUpEndpoint: string;
  changeStatusEndpoint: string;
  createEndpoint: string;
  detailEndpoint: string;
  evidenceContract: string;
  listEndpoint: string;
  reopenEndpoint: string;
  resolveEndpoint: string;
  updateEndpoint: string;
}

export interface AdminIncidentFilterOption {
  id: string;
  label: string;
}

export interface AdminIncidentFilterOptions {
  areas: AdminIncidentFilterOption[];
  branches: AdminIncidentFilterOption[];
  dueStates: AdminIncidentFilterOption[];
  evidenceStates: AdminIncidentFilterOption[];
  incidentTypes: AdminIncidentFilterOption[];
  relatedDocumentStates: AdminIncidentFilterOption[];
  reportedByUsers: AdminIncidentFilterOption[];
  responsibleUsers: AdminIncidentFilterOption[];
  severities: AdminIncidentFilterOption[];
  sourceTypes: AdminIncidentFilterOption[];
  statuses: AdminIncidentFilterOption[];
}

export interface AdminIncidentMetrics {
  highRiskCount: string;
  inProgressCount: string;
  openCount: string;
  overdueCount: string;
  resolvedCount: string;
  sanitaryGeneratedCount: string;
  totalCount: string;
  withEvidenceCount: string;
}

export interface AdminIncidentWarning {
  code: string;
  message: string;
  severity: "info" | "warning" | "critical";
}

export interface AdminIncidentListFilters {
  areaName: string;
  branchId: string;
  dateFrom: string | null;
  dateTo: string | null;
  dueState: string;
  evidenceState: string;
  incidentType: string;
  page: number;
  pageSize: number;
  relatedDocumentState: string;
  reportedByUserId: string;
  responsibleUserId: string;
  search: string;
  severity: string;
  sourceType: string;
  status: string;
  warningState: string;
}

export interface AdminIncidentListItem {
  areaName: string | null;
  branchId: string;
  branchName: string;
  createdAt: string;
  dueAt: string | null;
  folio: string;
  hasEvidence: boolean;
  id: string;
  incidentType: AdminIncidentType;
  relatedDocumentCount: number;
  reportedByUserId: string;
  reportedByUserName: string;
  responsibleUserId: string | null;
  responsibleUserName: string | null;
  severity: AdminIncidentSeverity;
  sourceReference: string | null;
  sourceType: AdminIncidentSourceType;
  status: AdminIncidentStatus;
  title: string;
  updatedAt: string;
  warningState: string;
  warnings: AdminIncidentWarning[];
}

export interface AdminIncidentListResponse {
  backendContract: AdminIncidentBackendContract;
  filterOptions: AdminIncidentFilterOptions;
  isBackendConnected: boolean;
  items: AdminIncidentListItem[];
  metrics: AdminIncidentMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminIncidentDetail {
  availableActions: {
    canAddEvidence: boolean;
    canAddFollowUp: boolean;
    canAssign: boolean;
    canCancel: boolean;
    canCreateCorrectiveAction: boolean;
    canCreateMaintenance: boolean;
    canExport: boolean;
    canMarkInProgress: boolean;
    canPrint: boolean;
    canReopen: boolean;
    canResolve: boolean;
    note: string | null;
  };
  correctiveAction: {
    correctiveAction: string | null;
    currentProgress: string;
    dueAt: string | null;
    responsibleUserId: string | null;
    responsibleUserName: string | null;
    resolutionNote: string | null;
    resolutionResult: string | null;
    resolvedAt: string | null;
  };
  descriptionClassification: {
    description: string;
    foodSafetyImpact: boolean;
    incidentType: AdminIncidentType;
    notes: string | null;
    operationalImpact: string | null;
    riskLevel: AdminIncidentSeverity;
    severity: AdminIncidentSeverity;
  };
  evidence: {
    emptyState: string;
    evidenceNote: string | null;
    files: Record<string, string>[];
    hasEvidence: boolean;
    isSupported: boolean;
    uploadSupported: boolean;
  };
  followUps: {
    createdAt: string;
    createdByUserId: string;
    createdByUserName: string;
    id: string;
    note: string;
    statusChange: string | null;
  }[];
  locationScope: {
    areaName: string | null;
    branchCode: string;
    branchId: string;
    branchName: string;
    equipmentName: string | null;
    processName: string | null;
    productReference: string | null;
    productionReference: string | null;
  };
  overview: AdminIncidentListItem & {
    resolvedAt: string | null;
  };
  relatedDocuments: {
    documentId: string;
    documentType: string;
    folio: string;
    routeHint: string | null;
    status: string;
  }[];
  sourceDocument: {
    emptyState: string;
    routeHint: string | null;
    sourceDocumentId: string | null;
    sourceReference: string | null;
    sourceSummary: string | null;
    sourceType: AdminIncidentSourceType;
  };
  timeline: {
    label: string;
    note: string | null;
    occurredAt: string;
    userName: string | null;
  }[];
  warnings: AdminIncidentWarning[];
}

export interface AdminIncidentCreatePayload {
  areaName: string | null;
  branchId: string;
  correctiveAction: string | null;
  description: string;
  dueAt: string | null;
  equipmentName: string | null;
  evidenceNote: string | null;
  foodSafetyImpact: boolean;
  incidentType: AdminIncidentType;
  notes: string | null;
  operationalImpact: string | null;
  processName: string | null;
  productReference: string | null;
  productionReference: string | null;
  responsibleUserId: string | null;
  severity: AdminIncidentSeverity;
  sourceDocumentId: string | null;
  sourceReference: string | null;
  sourceSummary: string | null;
  sourceType: AdminIncidentSourceType;
  title: string;
}

export interface AdminIncidentFollowUpPayload {
  note: string;
  statusChange: AdminIncidentStatus | null;
}

export interface AdminIncidentStatusPayload {
  cancellationReason: string | null;
  note: string | null;
  status: AdminIncidentStatus;
}

export interface AdminIncidentResolvePayload {
  evidenceNote: string | null;
  resolutionNote: string;
  result: string;
  resolvedAt: string | null;
}
