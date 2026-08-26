export type AdminSanitaryRiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type AdminSanitaryStatus =
  | "SCHEDULED"
  | "PENDING"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
  | "REQUIRES_FOLLOW_UP";

export type AdminSanitaryResult = "NOT_EVALUATED" | "PASSED" | "FAILED" | "PARTIAL";

export type AdminSanitaryItemResult = "PENDING" | "PASSED" | "FAILED" | "NOT_APPLICABLE";

export interface AdminSanitaryBackendContract {
  cancelEndpoint: string;
  completeEndpoint: string;
  createEndpoint: string;
  detailEndpoint: string;
  evidenceContract: string;
  incidentContract: string;
  listEndpoint: string;
  startEndpoint: string;
  templatesEndpoint: string;
}

export interface AdminSanitaryFilterOption {
  id: string;
  label: string;
}

export interface AdminSanitaryFilterOptions {
  areaTypes: AdminSanitaryFilterOption[];
  areas: AdminSanitaryFilterOption[];
  branches: AdminSanitaryFilterOption[];
  evidenceStates: AdminSanitaryFilterOption[];
  incidentStates: AdminSanitaryFilterOption[];
  inspectors: AdminSanitaryFilterOption[];
  processTypes: AdminSanitaryFilterOption[];
  processes: AdminSanitaryFilterOption[];
  results: AdminSanitaryFilterOption[];
  riskLevels: AdminSanitaryFilterOption[];
  statuses: AdminSanitaryFilterOption[];
  templates: AdminSanitaryFilterOption[];
}

export interface AdminSanitaryMetrics {
  failedCount: string;
  highRiskCount: string;
  pendingCount: string;
  passedCount: string;
  requiresFollowUpCount: string;
  totalCount: string;
  withEvidenceCount: string;
  withIncidentCount: string;
}

export interface AdminSanitaryWarning {
  code: string;
  message: string;
  severity: "info" | "warning" | "critical";
}

export interface AdminSanitaryListFilters {
  areaName: string;
  areaType: string;
  branchId: string;
  dateFrom: string | null;
  dateTo: string | null;
  evidenceState: string;
  incidentState: string;
  inspectorUserId: string;
  page: number;
  pageSize: number;
  processName: string;
  processType: string;
  result: string;
  riskLevel: string;
  search: string;
  status: string;
  templateId: string;
  warningState: string;
}

export interface AdminSanitaryVerificationListItem {
  areaId: string | null;
  areaName: string;
  branchId: string;
  branchName: string;
  checklistTotalCount: number;
  completedAt: string | null;
  equipmentId: string | null;
  equipmentName: string | null;
  failedCount: number;
  folio: string;
  hasEvidence: boolean;
  hasIncident: boolean;
  id: string;
  inspectorUserId: string;
  inspectorUserName: string;
  passedCount: number;
  processName: string | null;
  result: AdminSanitaryResult;
  riskLevel: AdminSanitaryRiskLevel;
  scheduledAt: string;
  status: AdminSanitaryStatus;
  templateName: string;
  updatedAt: string;
  warningState: string;
  warnings: AdminSanitaryWarning[];
}

export interface AdminSanitaryVerificationListResponse {
  backendContract: AdminSanitaryBackendContract;
  filterOptions: AdminSanitaryFilterOptions;
  isBackendConnected: boolean;
  items: AdminSanitaryVerificationListItem[];
  metrics: AdminSanitaryMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminSanitaryChecklistPayload {
  displayOrder?: number;
  evidenceRequiredOnFailure: boolean;
  expectedStandard: string | null;
  id: string | null;
  isRequired: boolean;
  label: string;
  notes: string | null;
  result: AdminSanitaryItemResult;
  riskLevel: AdminSanitaryRiskLevel;
}

export interface AdminSanitaryTemplateItem {
  description: string | null;
  displayOrder: number;
  evidenceRequiredOnFailure: boolean;
  expectedStandard: string | null;
  id: string;
  isRequired: boolean;
  label: string;
  riskLevel: AdminSanitaryRiskLevel;
}

export interface AdminSanitaryTemplate {
  areaType: string;
  description: string | null;
  frequency: string;
  id: string;
  isActive: boolean;
  items: AdminSanitaryTemplateItem[];
  name: string;
  passThresholdPercent: number;
  processType: string;
  requiresEvidenceOnFailure: boolean;
  riskLevel: AdminSanitaryRiskLevel;
}

export interface AdminSanitaryRelatedCleaningLog {
  completedAt: string | null;
  folio: string;
  id: string;
  responsibleUserName: string;
  routeHint: string | null;
  status: string;
}

export interface AdminSanitaryRelatedDocument {
  documentId: string;
  documentType: string;
  folio: string;
  routeHint: string | null;
  status: string;
}

export interface AdminSanitaryVerificationDetail {
  availableActions: {
    canAddEvidence: boolean;
    canCancel: boolean;
    canComplete: boolean;
    canCreateIncident: boolean;
    canEdit: boolean;
    canExport: boolean;
    canPrint: boolean;
    canStart: boolean;
    note: string | null;
  };
  checklistResults: AdminSanitaryChecklistPayload[];
  checklistTemplate: {
    areaType: string;
    description: string | null;
    failedItems: number;
    frequency: string | null;
    passedItems: number;
    passThresholdPercent: number;
    processType: string;
    riskLevel: AdminSanitaryRiskLevel;
    templateId: string | null;
    templateName: string;
    totalItems: number;
  };
  evidence: {
    emptyState: string;
    evidenceNote: string | null;
    files: Record<string, string>[];
    hasEvidence: boolean;
    isSupported: boolean;
    uploadSupported: boolean;
  };
  findingsObservations: {
    cancellationReason: string | null;
    failedRequiredCount: number;
    findingsNotes: string | null;
    followUpDueAt: string | null;
    followUpRequired: boolean;
    notes: string | null;
  };
  overview: AdminSanitaryVerificationListItem & {
    createdAt: string;
    createdByUserId: string;
    createdByUserName: string;
    startedAt: string | null;
  };
  relatedCleaningLogs: AdminSanitaryRelatedCleaningLog[];
  relatedDocuments: AdminSanitaryRelatedDocument[];
  scope: {
    areaName: string;
    areaType: string;
    branchCode: string;
    branchId: string;
    branchName: string;
    equipmentName: string | null;
    processName: string | null;
    processType: string;
  };
  scoreResult: {
    maxScore: number | null;
    percentage: number | null;
    result: AdminSanitaryResult;
    score: number | null;
    thresholdPercent: number;
  };
  warnings: AdminSanitaryWarning[];
}

export interface AdminSanitaryCreatePayload {
  areaName: string;
  areaType: string;
  branchId: string;
  checklistResults: AdminSanitaryChecklistPayload[];
  completeImmediately: boolean;
  completedAt: string | null;
  equipmentName: string | null;
  evidenceNote: string | null;
  findingsNotes: string | null;
  inspectorUserId: string;
  notes: string | null;
  processName: string | null;
  processType: string;
  riskLevel: AdminSanitaryRiskLevel;
  scheduledAt: string;
  templateId: string | null;
  templateName: string | null;
}

export interface AdminSanitaryCompletePayload {
  checklistResults: AdminSanitaryChecklistPayload[];
  completedAt: string | null;
  evidenceNote: string | null;
  findingsNotes: string | null;
  notes: string | null;
}

export interface AdminSanitaryCancelPayload {
  reason: string;
}
