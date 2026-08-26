import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminCleaningBackendContract,
  AdminCleaningCancelPayload,
  AdminCleaningChecklistItem,
  AdminCleaningChecklistPayload,
  AdminCleaningCompletePayload,
  AdminCleaningCreatePayload,
  AdminCleaningFilterOption,
  AdminCleaningListFilters,
  AdminCleaningLogDetail,
  AdminCleaningLogListItem,
  AdminCleaningLogListResponse,
  AdminCleaningTemplate,
  AdminCleaningTemplateItem,
} from "./types";

type ApiBackendContract = components["schemas"]["AdminCleaningBackendContractView"];
type ApiChecklistInput = components["schemas"]["AdminCleaningChecklistItemInput"];
type ApiChecklistItem = components["schemas"]["AdminCleaningChecklistItemView"];
type ApiCompleteRequest = components["schemas"]["AdminCleaningLogCompleteRequest"];
type ApiCreateRequest = components["schemas"]["AdminCleaningLogCreateRequest"];
type ApiDetail = components["schemas"]["AdminCleaningLogDetailView"];
type ApiFilterOption = components["schemas"]["AdminCleaningFilterOptionView"];
type ApiListItem = components["schemas"]["AdminCleaningLogListItemView"];
type ApiListResponse = components["schemas"]["AdminCleaningLogListResponse"];
type ApiTemplate = components["schemas"]["AdminCleaningTemplateView"];
type ApiTemplateItem = components["schemas"]["AdminCleaningTemplateItemView"];

export const adminCleaningBackendContract: AdminCleaningBackendContract = {
  cancelEndpoint: "POST /v1/admin/cleaning-logs/{cleaning_log_id}/cancel",
  completeEndpoint: "POST /v1/admin/cleaning-logs/{cleaning_log_id}/complete",
  createEndpoint: "POST /v1/admin/cleaning-logs",
  detailEndpoint: "GET /v1/admin/cleaning-logs/{cleaning_log_id}",
  evidenceContract: "Evidence files are not supported yet; evidence is captured as evidence_note.",
  listEndpoint: "GET /v1/admin/cleaning-logs",
  templatesEndpoint: "GET /v1/admin/cleaning-logs/templates",
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

function mapOption(option: ApiFilterOption): AdminCleaningFilterOption {
  return { id: option.id, label: option.label };
}

function mapBackendContract(
  contract: ApiBackendContract | undefined,
): AdminCleaningBackendContract {
  if (!contract) {
    return adminCleaningBackendContract;
  }
  return {
    cancelEndpoint: contract.cancel_endpoint,
    completeEndpoint: contract.complete_endpoint,
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    evidenceContract: contract.evidence_contract,
    listEndpoint: contract.list_endpoint,
    templatesEndpoint: contract.templates_endpoint,
  };
}

function mapChecklistPayload(item: AdminCleaningChecklistPayload): ApiChecklistInput {
  return {
    id: item.id,
    is_completed: item.isCompleted,
    is_required: item.isRequired,
    label: item.label,
    notes: item.notes,
  };
}

function mapChecklistItem(item: ApiChecklistItem): AdminCleaningChecklistItem {
  return {
    displayOrder: item.display_order,
    id: item.id,
    isCompleted: item.is_completed,
    isRequired: item.is_required,
    label: item.label,
    notes: item.notes ?? null,
  };
}

function mapTemplateItem(item: ApiTemplateItem): AdminCleaningTemplateItem {
  return {
    description: item.description ?? null,
    displayOrder: item.display_order,
    id: item.id,
    isRequired: item.is_required,
    label: item.label,
  };
}

export function mapAdminCleaningTemplateFromApi(template: ApiTemplate): AdminCleaningTemplate {
  return {
    areaType: template.area_type,
    cleaningType: template.cleaning_type,
    description: template.description ?? null,
    estimatedDurationMinutes: template.estimated_duration_minutes ?? null,
    frequency: template.frequency,
    id: template.id,
    isActive: template.is_active,
    items: template.items.map(mapTemplateItem),
    methodSummary: template.method_summary ?? null,
    name: template.name,
    requiresEvidence: template.requires_evidence,
    requiredTools: template.required_tools ?? null,
    riskLevel: template.risk_level,
  };
}

export function mapAdminCleaningListItemFromApi(item: ApiListItem): AdminCleaningLogListItem {
  return {
    areaId: item.area_id ?? null,
    areaName: item.area_name,
    branchId: item.branch_id,
    branchName: item.branch_name,
    checklistCompletedCount: item.checklist_completed_count,
    checklistTotalCount: item.checklist_total_count,
    cleaningType: item.cleaning_type,
    completedAt: item.completed_at ?? null,
    equipmentId: item.equipment_id ?? null,
    equipmentName: item.equipment_name ?? null,
    folio: item.folio,
    hasEvidence: item.has_evidence,
    hasObservations: item.has_observations,
    id: item.id,
    responsibleUserId: item.responsible_user_id,
    responsibleUserName: item.responsible_user_name,
    riskLevel: item.risk_level,
    scheduledAt: item.scheduled_at,
    shiftCode: item.shift_code,
    status: item.status,
    taskName: item.task_name,
    updatedAt: item.updated_at,
    warningState: item.warning_state,
    warnings: item.warnings,
  };
}

function mapDetailFromApi(response: ApiDetail): AdminCleaningLogDetail {
  return {
    availableActions: {
      canAddEvidence: response.available_actions.can_add_evidence,
      canCancel: response.available_actions.can_cancel,
      canComplete: response.available_actions.can_complete,
      canCreateIncident: response.available_actions.can_create_incident,
      canEdit: response.available_actions.can_edit,
      canExport: response.available_actions.can_export,
      canPrint: response.available_actions.can_print,
      note: response.available_actions.note ?? null,
    },
    checklist: response.checklist.map(mapChecklistItem),
    evidence: {
      emptyState: response.evidence.empty_state,
      evidenceNote: response.evidence.evidence_note ?? null,
      files: response.evidence.files ?? [],
      hasEvidence: response.evidence.has_evidence,
      isSupported: response.evidence.is_supported,
      uploadSupported: response.evidence.upload_supported,
    },
    locationArea: {
      areaName: response.location_area.area_name,
      areaType: response.location_area.area_type,
      branchCode: response.location_area.branch_code,
      branchId: response.location_area.branch_id,
      branchName: response.location_area.branch_name,
      equipmentName: response.location_area.equipment_name ?? null,
    },
    observationsIssues: {
      cancellationReason: response.observations_issues.cancellation_reason ?? null,
      correctiveNote: response.observations_issues.corrective_note ?? null,
      incompleteRequiredCount: response.observations_issues.incomplete_required_count,
      issueNotes: response.observations_issues.issue_notes ?? null,
      notes: response.observations_issues.notes ?? null,
    },
    overview: {
      ...mapAdminCleaningListItemFromApi({
        area_id: null,
        area_name: response.overview.area_name,
        branch_id: response.overview.branch_id,
        branch_name: response.overview.branch_name,
        checklist_completed_count: response.checklist.filter((item) => item.is_completed).length,
        checklist_total_count: response.checklist.length,
        cleaning_type: response.overview.cleaning_type,
        completed_at: response.overview.completed_at ?? null,
        equipment_id: null,
        equipment_name: response.overview.equipment_name ?? null,
        folio: response.overview.folio,
        has_evidence: response.evidence.has_evidence,
        has_observations: Boolean(
          response.observations_issues.notes ||
          response.observations_issues.issue_notes ||
          response.observations_issues.cancellation_reason,
        ),
        id: response.overview.id,
        responsible_user_id: response.overview.responsible_user_id,
        responsible_user_name: response.overview.responsible_user_name,
        risk_level: response.overview.risk_level,
        scheduled_at: response.overview.scheduled_at,
        shift_code: response.overview.shift_code,
        status: response.overview.status,
        task_name: response.overview.task_name,
        updated_at: response.overview.created_at,
        warning_state: response.overview.warning_state,
        warnings: response.warnings,
      }),
      createdAt: response.overview.created_at,
      createdByUserId: response.overview.created_by_user_id,
      createdByUserName: response.overview.created_by_user_name,
      startedAt: response.overview.started_at ?? null,
    },
    relatedDocuments: response.related_documents.map((document) => ({
      documentId: document.document_id,
      documentType: document.document_type,
      folio: document.folio,
      routeHint: document.route_hint ?? null,
      status: document.status,
    })),
    taskTemplate: {
      cleaningType: response.task_template.cleaning_type,
      estimatedDurationMinutes: response.task_template.estimated_duration_minutes ?? null,
      frequency: response.task_template.frequency ?? null,
      methodSummary: response.task_template.method_summary ?? null,
      requiredTools: response.task_template.required_tools ?? null,
      riskLevel: response.task_template.risk_level,
      taskName: response.task_template.task_name,
      taskTemplateId: response.task_template.task_template_id ?? null,
      taskTemplateName: response.task_template.task_template_name ?? null,
    },
    warnings: response.warnings,
  };
}

function mapListFromApi(response: ApiListResponse): AdminCleaningLogListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      areaTypes: response.filter_options.area_types.map(mapOption),
      areas: response.filter_options.areas.map(mapOption),
      branches: response.filter_options.branches.map(mapOption),
      cleaningTypes: response.filter_options.cleaning_types.map(mapOption),
      evidenceStates: response.filter_options.evidence_states.map(mapOption),
      observationStates: response.filter_options.observation_states.map(mapOption),
      responsibleUsers: response.filter_options.responsible_users.map(mapOption),
      riskLevels: response.filter_options.risk_levels.map(mapOption),
      shifts: response.filter_options.shifts.map(mapOption),
      statuses: response.filter_options.statuses.map(mapOption),
      templates: response.filter_options.templates.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminCleaningListItemFromApi),
    metrics: {
      completedCount: String(response.metrics.completed_count),
      highRiskCount: String(response.metrics.high_risk_count),
      overdueCount: String(response.metrics.overdue_count),
      pendingCount: String(response.metrics.pending_count),
      requiresReviewCount: String(response.metrics.requires_review_count),
      totalCount: String(response.metrics.total_count),
      withEvidenceCount: String(response.metrics.with_evidence_count),
      withObservationsCount: String(response.metrics.with_observations_count),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

export function buildAdminCleaningLogsListPath(filters: AdminCleaningListFilters): string {
  const params = new URLSearchParams();

  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "area_name", filters.areaName);
  appendOptionalParam(params, "area_type", filters.areaType);
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "cleaning_type", filters.cleaningType);
  appendOptionalParam(params, "date_from", toDateTimeParam(filters.dateFrom, "start"));
  appendOptionalParam(params, "date_to", toDateTimeParam(filters.dateTo, "end"));
  appendOptionalParam(params, "evidence_state", filters.evidenceState);
  appendOptionalParam(params, "observation_state", filters.observationState);
  appendOptionalParam(params, "responsible_user_id", filters.responsibleUserId);
  appendOptionalParam(params, "risk_level", filters.riskLevel);
  appendOptionalParam(params, "search", filters.search.trim());
  appendOptionalParam(params, "shift_code", filters.shiftCode);
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "template_id", filters.templateId);
  appendOptionalParam(params, "warning_state", filters.warningState);

  return `/v1/admin/cleaning-logs?${params.toString()}`;
}

export function fetchAdminCleaningLogs(
  accessToken: string,
  filters: AdminCleaningListFilters,
): Promise<AdminCleaningLogListResponse> {
  return requestJson<ApiListResponse>({
    accessToken,
    path: buildAdminCleaningLogsListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminCleaningTemplates(accessToken: string): Promise<AdminCleaningTemplate[]> {
  return requestJson<ApiTemplate[]>({
    accessToken,
    path: "/v1/admin/cleaning-logs/templates",
  }).then((response) => response.map(mapAdminCleaningTemplateFromApi));
}

export function fetchAdminCleaningLogDetail(
  accessToken: string,
  cleaningLogId: string,
): Promise<AdminCleaningLogDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/cleaning-logs/${cleaningLogId}`,
  }).then(mapDetailFromApi);
}

export function createAdminCleaningLog(
  accessToken: string,
  payload: AdminCleaningCreatePayload,
): Promise<AdminCleaningLogDetail> {
  const body: ApiCreateRequest = {
    area_name: payload.areaName,
    area_type: payload.areaType,
    branch_id: payload.branchId,
    checklist_items: payload.checklistItems.map(mapChecklistPayload),
    cleaning_type: payload.cleaningType,
    complete_immediately: payload.completeImmediately,
    completed_at: payload.completedAt,
    equipment_name: payload.equipmentName,
    evidence_note: payload.evidenceNote,
    issue_notes: payload.issueNotes,
    notes: payload.notes,
    responsible_user_id: payload.responsibleUserId,
    risk_level: payload.riskLevel,
    scheduled_at: payload.scheduledAt,
    shift_code: payload.shiftCode,
    task_name: payload.taskName,
    task_template_id: payload.taskTemplateId,
  };

  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: "/v1/admin/cleaning-logs",
  }).then(mapDetailFromApi);
}

export function completeAdminCleaningLog(
  accessToken: string,
  cleaningLogId: string,
  payload: AdminCleaningCompletePayload,
): Promise<AdminCleaningLogDetail> {
  const body: ApiCompleteRequest = {
    checklist_items: payload.checklistItems.map(mapChecklistPayload),
    completed_at: payload.completedAt,
    evidence_note: payload.evidenceNote,
    issue_notes: payload.issueNotes,
    notes: payload.notes,
  };

  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/cleaning-logs/${cleaningLogId}/complete`,
  }).then(mapDetailFromApi);
}

export function cancelAdminCleaningLog(
  accessToken: string,
  cleaningLogId: string,
  payload: AdminCleaningCancelPayload,
): Promise<AdminCleaningLogDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    body: { reason: payload.reason },
    method: "POST",
    path: `/v1/admin/cleaning-logs/${cleaningLogId}/cancel`,
  }).then(mapDetailFromApi);
}
