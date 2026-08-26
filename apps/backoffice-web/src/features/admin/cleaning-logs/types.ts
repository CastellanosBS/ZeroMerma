export interface AdminCleaningBackendContract {
  cancelEndpoint: string;
  completeEndpoint: string;
  createEndpoint: string;
  detailEndpoint: string;
  evidenceContract: string;
  listEndpoint: string;
  templatesEndpoint: string;
}

export interface AdminCleaningFilterOption {
  id: string;
  label: string;
}

export interface AdminCleaningFilterOptions {
  areaTypes: AdminCleaningFilterOption[];
  areas: AdminCleaningFilterOption[];
  branches: AdminCleaningFilterOption[];
  cleaningTypes: AdminCleaningFilterOption[];
  evidenceStates: AdminCleaningFilterOption[];
  observationStates: AdminCleaningFilterOption[];
  responsibleUsers: AdminCleaningFilterOption[];
  riskLevels: AdminCleaningFilterOption[];
  shifts: AdminCleaningFilterOption[];
  statuses: AdminCleaningFilterOption[];
  templates: AdminCleaningFilterOption[];
}

export interface AdminCleaningMetrics {
  completedCount: string;
  highRiskCount: string;
  overdueCount: string;
  pendingCount: string;
  requiresReviewCount: string;
  totalCount: string;
  withEvidenceCount: string;
  withObservationsCount: string;
}

export interface AdminCleaningWarning {
  code: string;
  message: string;
  severity: "info" | "warning" | "critical";
}

export interface AdminCleaningListFilters {
  areaName: string;
  areaType: string;
  branchId: string;
  cleaningType: string;
  dateFrom: string | null;
  dateTo: string | null;
  evidenceState: string;
  observationState: string;
  page: number;
  pageSize: number;
  responsibleUserId: string;
  riskLevel: string;
  search: string;
  shiftCode: string;
  status: string;
  templateId: string;
  warningState: string;
}

export interface AdminCleaningLogListItem {
  areaId: string | null;
  areaName: string;
  branchId: string;
  branchName: string;
  checklistCompletedCount: number;
  checklistTotalCount: number;
  cleaningType: string;
  completedAt: string | null;
  equipmentId: string | null;
  equipmentName: string | null;
  folio: string;
  hasEvidence: boolean;
  hasObservations: boolean;
  id: string;
  responsibleUserId: string;
  responsibleUserName: string;
  riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  scheduledAt: string;
  shiftCode: string;
  status:
    | "SCHEDULED"
    | "PENDING"
    | "IN_PROGRESS"
    | "COMPLETED"
    | "MISSED"
    | "CANCELLED"
    | "REQUIRES_REVIEW";
  taskName: string;
  updatedAt: string;
  warningState: string;
  warnings: AdminCleaningWarning[];
}

export interface AdminCleaningLogListResponse {
  backendContract: AdminCleaningBackendContract;
  filterOptions: AdminCleaningFilterOptions;
  isBackendConnected: boolean;
  items: AdminCleaningLogListItem[];
  metrics: AdminCleaningMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminCleaningChecklistItem {
  displayOrder: number;
  id: string;
  isCompleted: boolean;
  isRequired: boolean;
  label: string;
  notes: string | null;
}

export interface AdminCleaningTemplateItem {
  description: string | null;
  displayOrder: number;
  id: string;
  isRequired: boolean;
  label: string;
}

export interface AdminCleaningTemplate {
  areaType: string;
  cleaningType: string;
  description: string | null;
  estimatedDurationMinutes: number | null;
  frequency: string;
  id: string;
  isActive: boolean;
  items: AdminCleaningTemplateItem[];
  methodSummary: string | null;
  name: string;
  requiresEvidence: boolean;
  requiredTools: string | null;
  riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export interface AdminCleaningRelatedDocument {
  documentId: string;
  documentType: string;
  folio: string;
  routeHint: string | null;
  status: string;
}

export interface AdminCleaningLogDetail {
  availableActions: {
    canAddEvidence: boolean;
    canCancel: boolean;
    canComplete: boolean;
    canCreateIncident: boolean;
    canEdit: boolean;
    canExport: boolean;
    canPrint: boolean;
    note: string | null;
  };
  checklist: AdminCleaningChecklistItem[];
  evidence: {
    emptyState: string;
    evidenceNote: string | null;
    files: Record<string, string>[];
    hasEvidence: boolean;
    isSupported: boolean;
    uploadSupported: boolean;
  };
  locationArea: {
    areaName: string;
    areaType: string;
    branchCode: string;
    branchId: string;
    branchName: string;
    equipmentName: string | null;
  };
  observationsIssues: {
    cancellationReason: string | null;
    correctiveNote: string | null;
    incompleteRequiredCount: number;
    issueNotes: string | null;
    notes: string | null;
  };
  overview: AdminCleaningLogListItem & {
    createdAt: string;
    createdByUserId: string;
    createdByUserName: string;
    startedAt: string | null;
  };
  relatedDocuments: AdminCleaningRelatedDocument[];
  taskTemplate: {
    cleaningType: string;
    estimatedDurationMinutes: number | null;
    frequency: string | null;
    methodSummary: string | null;
    requiredTools: string | null;
    riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    taskName: string;
    taskTemplateId: string | null;
    taskTemplateName: string | null;
  };
  warnings: AdminCleaningWarning[];
}

export interface AdminCleaningChecklistPayload {
  id: string | null;
  isCompleted: boolean;
  isRequired: boolean;
  label: string;
  notes: string | null;
}

export interface AdminCleaningCreatePayload {
  areaName: string;
  areaType: string;
  branchId: string;
  checklistItems: AdminCleaningChecklistPayload[];
  cleaningType: string;
  completeImmediately: boolean;
  completedAt: string | null;
  equipmentName: string | null;
  evidenceNote: string | null;
  issueNotes: string | null;
  notes: string | null;
  responsibleUserId: string;
  riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  scheduledAt: string;
  shiftCode: string;
  taskName: string | null;
  taskTemplateId: string | null;
}

export interface AdminCleaningCompletePayload {
  checklistItems: AdminCleaningChecklistPayload[];
  completedAt: string | null;
  evidenceNote: string | null;
  issueNotes: string | null;
  notes: string | null;
}

export interface AdminCleaningCancelPayload {
  reason: string;
}
