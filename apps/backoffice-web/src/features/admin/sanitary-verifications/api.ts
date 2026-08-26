import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminSanitaryBackendContract,
  AdminSanitaryCancelPayload,
  AdminSanitaryChecklistPayload,
  AdminSanitaryCompletePayload,
  AdminSanitaryCreatePayload,
  AdminSanitaryFilterOption,
  AdminSanitaryListFilters,
  AdminSanitaryTemplate,
  AdminSanitaryTemplateItem,
  AdminSanitaryVerificationDetail,
  AdminSanitaryVerificationListItem,
  AdminSanitaryVerificationListResponse,
} from "./types";

type ApiBackendContract = components["schemas"]["AdminSanitaryBackendContractView"];
type ApiChecklistInput = components["schemas"]["AdminSanitaryChecklistItemInput"];
type ApiChecklistItem = components["schemas"]["AdminSanitaryChecklistItemView"];
type ApiCompleteRequest = components["schemas"]["AdminSanitaryVerificationCompleteRequest"];
type ApiCreateRequest = components["schemas"]["AdminSanitaryVerificationCreateRequest"];
type ApiDetail = components["schemas"]["AdminSanitaryVerificationDetailView"];
type ApiFilterOption = components["schemas"]["AdminSanitaryFilterOptionView"];
type ApiListItem = components["schemas"]["AdminSanitaryVerificationListItemView"];
type ApiListResponse = components["schemas"]["AdminSanitaryVerificationListResponse"];
type ApiTemplate = components["schemas"]["AdminSanitaryTemplateView"];
type ApiTemplateItem = components["schemas"]["AdminSanitaryTemplateItemView"];

export const adminSanitaryBackendContract: AdminSanitaryBackendContract = {
  cancelEndpoint: "POST /v1/admin/sanitary-verifications/{verification_id}/cancel",
  completeEndpoint: "POST /v1/admin/sanitary-verifications/{verification_id}/complete",
  createEndpoint: "POST /v1/admin/sanitary-verifications",
  detailEndpoint: "GET /v1/admin/sanitary-verifications/{verification_id}",
  evidenceContract:
    "Evidence files are not supported yet; evidence is captured as evidence_note.",
  incidentContract:
    "Incident creation is not supported yet; failed verifications expose action metadata.",
  listEndpoint: "GET /v1/admin/sanitary-verifications",
  startEndpoint: "POST /v1/admin/sanitary-verifications/{verification_id}/start",
  templatesEndpoint: "GET /v1/admin/sanitary-verifications/templates",
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

function toDateTimeParam(value: string | null | undefined, boundary: "start" | "end") {
  if (!value) {
    return null;
  }
  const suffix = boundary === "start" ? "T00:00:00.000Z" : "T23:59:59.999Z";
  return `${value}${suffix}`;
}

function mapOption(option: ApiFilterOption): AdminSanitaryFilterOption {
  return { id: option.id, label: option.label };
}

function mapBackendContract(
  contract: ApiBackendContract | undefined,
): AdminSanitaryBackendContract {
  if (!contract) {
    return adminSanitaryBackendContract;
  }
  return {
    cancelEndpoint: contract.cancel_endpoint,
    completeEndpoint: contract.complete_endpoint,
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    evidenceContract: contract.evidence_contract,
    incidentContract: contract.incident_contract,
    listEndpoint: contract.list_endpoint,
    startEndpoint: contract.start_endpoint,
    templatesEndpoint: contract.templates_endpoint,
  };
}

function mapChecklistPayload(item: AdminSanitaryChecklistPayload): ApiChecklistInput {
  return {
    evidence_required_on_failure: item.evidenceRequiredOnFailure,
    expected_standard: item.expectedStandard,
    id: item.id,
    is_required: item.isRequired,
    label: item.label,
    notes: item.notes,
    result: item.result,
    risk_level: item.riskLevel,
  };
}

function mapChecklistItem(item: ApiChecklistItem): AdminSanitaryChecklistPayload {
  return {
    displayOrder: item.display_order,
    evidenceRequiredOnFailure: item.evidence_required_on_failure,
    expectedStandard: item.expected_standard ?? null,
    id: item.id,
    isRequired: item.is_required,
    label: item.label,
    notes: item.notes ?? null,
    result: item.result,
    riskLevel: item.risk_level,
  };
}

function mapTemplateItem(item: ApiTemplateItem): AdminSanitaryTemplateItem {
  return {
    description: item.description ?? null,
    displayOrder: item.display_order,
    evidenceRequiredOnFailure: item.evidence_required_on_failure,
    expectedStandard: item.expected_standard ?? null,
    id: item.id,
    isRequired: item.is_required,
    label: item.label,
    riskLevel: item.risk_level,
  };
}

export function mapAdminSanitaryTemplateFromApi(template: ApiTemplate): AdminSanitaryTemplate {
  return {
    areaType: template.area_type,
    description: template.description ?? null,
    frequency: template.frequency,
    id: template.id,
    isActive: template.is_active,
    items: template.items.map(mapTemplateItem),
    name: template.name,
    passThresholdPercent: template.pass_threshold_percent,
    processType: template.process_type,
    requiresEvidenceOnFailure: template.requires_evidence_on_failure,
    riskLevel: template.risk_level,
  };
}

export function mapAdminSanitaryListItemFromApi(
  item: ApiListItem,
): AdminSanitaryVerificationListItem {
  return {
    areaId: item.area_id ?? null,
    areaName: item.area_name,
    branchId: item.branch_id,
    branchName: item.branch_name,
    checklistTotalCount: item.checklist_total_count,
    completedAt: item.completed_at ?? null,
    equipmentId: item.equipment_id ?? null,
    equipmentName: item.equipment_name ?? null,
    failedCount: item.failed_count,
    folio: item.folio,
    hasEvidence: item.has_evidence,
    hasIncident: item.has_incident,
    id: item.id,
    inspectorUserId: item.inspector_user_id,
    inspectorUserName: item.inspector_user_name,
    passedCount: item.passed_count,
    processName: item.process_name ?? null,
    result: item.result,
    riskLevel: item.risk_level,
    scheduledAt: item.scheduled_at,
    status: item.status,
    templateName: item.template_name,
    updatedAt: item.updated_at,
    warningState: item.warning_state,
    warnings: item.warnings,
  };
}

function mapDetailFromApi(response: ApiDetail): AdminSanitaryVerificationDetail {
  return {
    availableActions: {
      canAddEvidence: response.available_actions.can_add_evidence,
      canCancel: response.available_actions.can_cancel,
      canComplete: response.available_actions.can_complete,
      canCreateIncident: response.available_actions.can_create_incident,
      canEdit: response.available_actions.can_edit,
      canExport: response.available_actions.can_export,
      canPrint: response.available_actions.can_print,
      canStart: response.available_actions.can_start,
      note: response.available_actions.note ?? null,
    },
    checklistResults: response.checklist_results.map(mapChecklistItem),
    checklistTemplate: {
      areaType: response.checklist_template.area_type,
      description: response.checklist_template.description ?? null,
      failedItems: response.checklist_template.failed_items,
      frequency: response.checklist_template.frequency ?? null,
      passedItems: response.checklist_template.passed_items,
      passThresholdPercent: response.checklist_template.pass_threshold_percent,
      processType: response.checklist_template.process_type,
      riskLevel: response.checklist_template.risk_level,
      templateId: response.checklist_template.template_id ?? null,
      templateName: response.checklist_template.template_name,
      totalItems: response.checklist_template.total_items,
    },
    evidence: {
      emptyState: response.evidence.empty_state,
      evidenceNote: response.evidence.evidence_note ?? null,
      files: response.evidence.files ?? [],
      hasEvidence: response.evidence.has_evidence,
      isSupported: response.evidence.is_supported,
      uploadSupported: response.evidence.upload_supported,
    },
    findingsObservations: {
      cancellationReason: response.findings_observations.cancellation_reason ?? null,
      failedRequiredCount: response.findings_observations.failed_required_count,
      findingsNotes: response.findings_observations.findings_notes ?? null,
      followUpDueAt: response.findings_observations.follow_up_due_at ?? null,
      followUpRequired: response.findings_observations.follow_up_required,
      notes: response.findings_observations.notes ?? null,
    },
    overview: {
      ...mapAdminSanitaryListItemFromApi({
        area_id: null,
        area_name: response.overview.area_name,
        branch_id: response.overview.branch_id,
        branch_name: response.overview.branch_name,
        checklist_total_count: response.checklist_results.length,
        completed_at: response.overview.completed_at ?? null,
        equipment_id: null,
        equipment_name: response.overview.equipment_name ?? null,
        failed_count: response.checklist_results.filter((item) => item.result === "FAILED").length,
        folio: response.overview.folio,
        has_evidence: response.evidence.has_evidence,
        has_incident: false,
        id: response.overview.id,
        inspector_user_id: response.overview.inspector_user_id,
        inspector_user_name: response.overview.inspector_user_name,
        passed_count: response.checklist_results.filter((item) => item.result === "PASSED").length,
        process_name: response.overview.process_name ?? null,
        result: response.overview.result,
        risk_level: response.overview.risk_level,
        scheduled_at: response.overview.scheduled_at,
        status: response.overview.status,
        template_name: response.checklist_template.template_name,
        updated_at: response.overview.created_at,
        warning_state: response.overview.warning_state,
        warnings: response.warnings,
      }),
      createdAt: response.overview.created_at,
      createdByUserId: response.overview.created_by_user_id,
      createdByUserName: response.overview.created_by_user_name,
      startedAt: response.overview.started_at ?? null,
    },
    relatedCleaningLogs: response.related_cleaning_logs.map((log) => ({
      completedAt: log.completed_at ?? null,
      folio: log.folio,
      id: log.id,
      responsibleUserName: log.responsible_user_name,
      routeHint: log.route_hint ?? null,
      status: log.status,
    })),
    relatedDocuments: response.related_documents.map((document) => ({
      documentId: document.document_id,
      documentType: document.document_type,
      folio: document.folio,
      routeHint: document.route_hint ?? null,
      status: document.status,
    })),
    scope: {
      areaName: response.scope.area_name,
      areaType: response.scope.area_type,
      branchCode: response.scope.branch_code,
      branchId: response.scope.branch_id,
      branchName: response.scope.branch_name,
      equipmentName: response.scope.equipment_name ?? null,
      processName: response.scope.process_name ?? null,
      processType: response.scope.process_type,
    },
    scoreResult: {
      maxScore: response.score_result.max_score ?? null,
      percentage: response.score_result.percentage ?? null,
      result: response.score_result.result,
      score: response.score_result.score ?? null,
      thresholdPercent: response.score_result.threshold_percent,
    },
    warnings: response.warnings,
  };
}

function mapListFromApi(response: ApiListResponse): AdminSanitaryVerificationListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      areaTypes: response.filter_options.area_types.map(mapOption),
      areas: response.filter_options.areas.map(mapOption),
      branches: response.filter_options.branches.map(mapOption),
      evidenceStates: response.filter_options.evidence_states.map(mapOption),
      incidentStates: response.filter_options.incident_states.map(mapOption),
      inspectors: response.filter_options.inspectors.map(mapOption),
      processTypes: response.filter_options.process_types.map(mapOption),
      processes: response.filter_options.processes.map(mapOption),
      results: response.filter_options.results.map(mapOption),
      riskLevels: response.filter_options.risk_levels.map(mapOption),
      statuses: response.filter_options.statuses.map(mapOption),
      templates: response.filter_options.templates.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminSanitaryListItemFromApi),
    metrics: {
      failedCount: String(response.metrics.failed_count),
      highRiskCount: String(response.metrics.high_risk_count),
      pendingCount: String(response.metrics.pending_count),
      passedCount: String(response.metrics.passed_count),
      requiresFollowUpCount: String(response.metrics.requires_follow_up_count),
      totalCount: String(response.metrics.total_count),
      withEvidenceCount: String(response.metrics.with_evidence_count),
      withIncidentCount: String(response.metrics.with_incident_count),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

export function buildAdminSanitaryVerificationsListPath(
  filters: AdminSanitaryListFilters,
): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "area_name", filters.areaName);
  appendOptionalParam(params, "area_type", filters.areaType);
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "date_from", toDateTimeParam(filters.dateFrom, "start"));
  appendOptionalParam(params, "date_to", toDateTimeParam(filters.dateTo, "end"));
  appendOptionalParam(params, "evidence_state", filters.evidenceState);
  appendOptionalParam(params, "incident_state", filters.incidentState);
  appendOptionalParam(params, "inspector_user_id", filters.inspectorUserId);
  appendOptionalParam(params, "process_name", filters.processName);
  appendOptionalParam(params, "process_type", filters.processType);
  appendOptionalParam(params, "result", filters.result);
  appendOptionalParam(params, "risk_level", filters.riskLevel);
  appendOptionalParam(params, "search", filters.search.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "template_id", filters.templateId);
  appendOptionalParam(params, "warning_state", filters.warningState);

  return `/v1/admin/sanitary-verifications?${params.toString()}`;
}

export function fetchAdminSanitaryVerifications(
  accessToken: string,
  filters: AdminSanitaryListFilters,
): Promise<AdminSanitaryVerificationListResponse> {
  return requestJson<ApiListResponse>({
    accessToken,
    path: buildAdminSanitaryVerificationsListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminSanitaryTemplates(
  accessToken: string,
): Promise<AdminSanitaryTemplate[]> {
  return requestJson<ApiTemplate[]>({
    accessToken,
    path: "/v1/admin/sanitary-verifications/templates",
  }).then((response) => response.map(mapAdminSanitaryTemplateFromApi));
}

export function fetchAdminSanitaryVerificationDetail(
  accessToken: string,
  verificationId: string,
): Promise<AdminSanitaryVerificationDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/sanitary-verifications/${verificationId}`,
  }).then(mapDetailFromApi);
}

export function createAdminSanitaryVerification(
  accessToken: string,
  payload: AdminSanitaryCreatePayload,
): Promise<AdminSanitaryVerificationDetail> {
  const body: ApiCreateRequest = {
    area_name: payload.areaName,
    area_type: payload.areaType,
    branch_id: payload.branchId,
    checklist_results: payload.checklistResults.map(mapChecklistPayload),
    complete_immediately: payload.completeImmediately,
    completed_at: payload.completedAt,
    equipment_name: payload.equipmentName,
    evidence_note: payload.evidenceNote,
    findings_notes: payload.findingsNotes,
    inspector_user_id: payload.inspectorUserId,
    notes: payload.notes,
    process_name: payload.processName,
    process_type: payload.processType,
    risk_level: payload.riskLevel,
    scheduled_at: payload.scheduledAt,
    template_id: payload.templateId,
    template_name: payload.templateName,
  };

  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: "/v1/admin/sanitary-verifications",
  }).then(mapDetailFromApi);
}

export function startAdminSanitaryVerification(
  accessToken: string,
  verificationId: string,
): Promise<AdminSanitaryVerificationDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    method: "POST",
    path: `/v1/admin/sanitary-verifications/${verificationId}/start`,
  }).then(mapDetailFromApi);
}

export function completeAdminSanitaryVerification(
  accessToken: string,
  verificationId: string,
  payload: AdminSanitaryCompletePayload,
): Promise<AdminSanitaryVerificationDetail> {
  const body: ApiCompleteRequest = {
    checklist_results: payload.checklistResults.map(mapChecklistPayload),
    completed_at: payload.completedAt,
    evidence_note: payload.evidenceNote,
    findings_notes: payload.findingsNotes,
    notes: payload.notes,
  };

  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/sanitary-verifications/${verificationId}/complete`,
  }).then(mapDetailFromApi);
}

export function cancelAdminSanitaryVerification(
  accessToken: string,
  verificationId: string,
  payload: AdminSanitaryCancelPayload,
): Promise<AdminSanitaryVerificationDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    body: { reason: payload.reason },
    method: "POST",
    path: `/v1/admin/sanitary-verifications/${verificationId}/cancel`,
  }).then(mapDetailFromApi);
}
