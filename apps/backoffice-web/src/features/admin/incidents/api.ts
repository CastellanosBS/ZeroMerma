import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminIncidentBackendContract,
  AdminIncidentCreatePayload,
  AdminIncidentDetail,
  AdminIncidentFilterOption,
  AdminIncidentFollowUpPayload,
  AdminIncidentListFilters,
  AdminIncidentListItem,
  AdminIncidentListResponse,
  AdminIncidentResolvePayload,
  AdminIncidentStatusPayload,
} from "./types";

type ApiBackendContract = components["schemas"]["AdminIncidentBackendContractView"];
type ApiCreate = components["schemas"]["AdminIncidentCreateRequest"];
type ApiDetail = components["schemas"]["AdminIncidentDetailView"];
type ApiFilterOption = components["schemas"]["AdminIncidentFilterOptionView"];
type ApiFollowUp = components["schemas"]["AdminIncidentFollowUpCreateRequest"];
type ApiListItem = components["schemas"]["AdminIncidentListItemView"];
type ApiListResponse = components["schemas"]["AdminIncidentListResponse"];
type ApiResolve = components["schemas"]["AdminIncidentResolveRequest"];
type ApiStatus = components["schemas"]["AdminIncidentStatusRequest"];

export const adminIncidentBackendContract: AdminIncidentBackendContract = {
  addFollowUpEndpoint: "POST /v1/admin/incidents/{incident_id}/follow-ups",
  changeStatusEndpoint: "POST /v1/admin/incidents/{incident_id}/status",
  createEndpoint: "POST /v1/admin/incidents",
  detailEndpoint: "GET /v1/admin/incidents/{incident_id}",
  evidenceContract:
    "Evidence files are not supported yet; evidence is captured as evidence_note.",
  listEndpoint: "GET /v1/admin/incidents",
  reopenEndpoint: "POST /v1/admin/incidents/{incident_id}/reopen",
  resolveEndpoint: "POST /v1/admin/incidents/{incident_id}/resolve",
  updateEndpoint: "PATCH /v1/admin/incidents/{incident_id}",
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

function mapOption(option: ApiFilterOption): AdminIncidentFilterOption {
  return { id: option.id, label: option.label };
}

function mapBackendContract(contract?: ApiBackendContract): AdminIncidentBackendContract {
  if (!contract) {
    return adminIncidentBackendContract;
  }
  return {
    addFollowUpEndpoint: contract.add_follow_up_endpoint,
    changeStatusEndpoint: contract.change_status_endpoint,
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    evidenceContract: contract.evidence_contract,
    listEndpoint: contract.list_endpoint,
    reopenEndpoint: contract.reopen_endpoint,
    resolveEndpoint: contract.resolve_endpoint,
    updateEndpoint: contract.update_endpoint,
  };
}

export function mapAdminIncidentListItemFromApi(item: ApiListItem): AdminIncidentListItem {
  return {
    areaName: item.area_name ?? null,
    branchId: item.branch_id,
    branchName: item.branch_name,
    createdAt: item.created_at,
    dueAt: item.due_at ?? null,
    folio: item.folio,
    hasEvidence: item.has_evidence,
    id: item.id,
    incidentType: item.incident_type,
    relatedDocumentCount: item.related_document_count,
    reportedByUserId: item.reported_by_user_id,
    reportedByUserName: item.reported_by_user_name,
    responsibleUserId: item.responsible_user_id ?? null,
    responsibleUserName: item.responsible_user_name ?? null,
    severity: item.severity,
    sourceReference: item.source_reference ?? null,
    sourceType: item.source_type,
    status: item.status,
    title: item.title,
    updatedAt: item.updated_at,
    warningState: item.warning_state,
    warnings: item.warnings,
  };
}

function mapDetailFromApi(response: ApiDetail): AdminIncidentDetail {
  return {
    availableActions: {
      canAddEvidence: response.available_actions.can_add_evidence,
      canAddFollowUp: response.available_actions.can_add_follow_up,
      canAssign: response.available_actions.can_assign,
      canCancel: response.available_actions.can_cancel,
      canCreateCorrectiveAction: response.available_actions.can_create_corrective_action,
      canCreateMaintenance: response.available_actions.can_create_maintenance,
      canExport: response.available_actions.can_export,
      canMarkInProgress: response.available_actions.can_mark_in_progress,
      canPrint: response.available_actions.can_print,
      canReopen: response.available_actions.can_reopen,
      canResolve: response.available_actions.can_resolve,
      note: response.available_actions.note ?? null,
    },
    correctiveAction: {
      correctiveAction: response.corrective_action.corrective_action ?? null,
      currentProgress: response.corrective_action.current_progress,
      dueAt: response.corrective_action.due_at ?? null,
      responsibleUserId: response.corrective_action.responsible_user_id ?? null,
      responsibleUserName: response.corrective_action.responsible_user_name ?? null,
      resolutionNote: response.corrective_action.resolution_note ?? null,
      resolutionResult: response.corrective_action.resolution_result ?? null,
      resolvedAt: response.corrective_action.resolved_at ?? null,
    },
    descriptionClassification: {
      description: response.description_classification.description,
      foodSafetyImpact: response.description_classification.food_safety_impact,
      incidentType: response.description_classification.incident_type,
      notes: response.description_classification.notes ?? null,
      operationalImpact: response.description_classification.operational_impact ?? null,
      riskLevel: response.description_classification.risk_level,
      severity: response.description_classification.severity,
    },
    evidence: {
      emptyState: response.evidence.empty_state,
      evidenceNote: response.evidence.evidence_note ?? null,
      files: response.evidence.files ?? [],
      hasEvidence: response.evidence.has_evidence,
      isSupported: response.evidence.is_supported,
      uploadSupported: response.evidence.upload_supported,
    },
    followUps: response.follow_ups.map((item) => ({
      createdAt: item.created_at,
      createdByUserId: item.created_by_user_id,
      createdByUserName: item.created_by_user_name,
      id: item.id,
      note: item.note,
      statusChange: item.status_change ?? null,
    })),
    locationScope: {
      areaName: response.location_scope.area_name ?? null,
      branchCode: response.location_scope.branch_code,
      branchId: response.location_scope.branch_id,
      branchName: response.location_scope.branch_name,
      equipmentName: response.location_scope.equipment_name ?? null,
      processName: response.location_scope.process_name ?? null,
      productReference: response.location_scope.product_reference ?? null,
      productionReference: response.location_scope.production_reference ?? null,
    },
    overview: {
      ...mapAdminIncidentListItemFromApi(response.overview),
      resolvedAt: response.overview.resolved_at ?? null,
    },
    relatedDocuments: response.related_documents.map((document) => ({
      documentId: document.document_id,
      documentType: document.document_type,
      folio: document.folio,
      routeHint: document.route_hint ?? null,
      status: document.status,
    })),
    sourceDocument: {
      emptyState: response.source_document.empty_state,
      routeHint: response.source_document.route_hint ?? null,
      sourceDocumentId: response.source_document.source_document_id ?? null,
      sourceReference: response.source_document.source_reference ?? null,
      sourceSummary: response.source_document.source_summary ?? null,
      sourceType: response.source_document.source_type,
    },
    timeline: response.timeline.map((item) => ({
      label: item.label,
      note: item.note ?? null,
      occurredAt: item.occurred_at,
      userName: item.user_name ?? null,
    })),
    warnings: response.warnings,
  };
}

function mapListFromApi(response: ApiListResponse): AdminIncidentListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      areas: response.filter_options.areas.map(mapOption),
      branches: response.filter_options.branches.map(mapOption),
      dueStates: response.filter_options.due_states.map(mapOption),
      evidenceStates: response.filter_options.evidence_states.map(mapOption),
      incidentTypes: response.filter_options.incident_types.map(mapOption),
      relatedDocumentStates: response.filter_options.related_document_states.map(mapOption),
      reportedByUsers: response.filter_options.reported_by_users.map(mapOption),
      responsibleUsers: response.filter_options.responsible_users.map(mapOption),
      severities: response.filter_options.severities.map(mapOption),
      sourceTypes: response.filter_options.source_types.map(mapOption),
      statuses: response.filter_options.statuses.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminIncidentListItemFromApi),
    metrics: {
      highRiskCount: String(response.metrics.high_risk_count),
      inProgressCount: String(response.metrics.in_progress_count),
      openCount: String(response.metrics.open_count),
      overdueCount: String(response.metrics.overdue_count),
      resolvedCount: String(response.metrics.resolved_count),
      sanitaryGeneratedCount: String(response.metrics.sanitary_generated_count),
      totalCount: String(response.metrics.total_count),
      withEvidenceCount: String(response.metrics.with_evidence_count),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

export function buildAdminIncidentsListPath(filters: AdminIncidentListFilters): string {
  const params = new URLSearchParams();
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "area_name", filters.areaName);
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "date_from", toDateTimeParam(filters.dateFrom, "start"));
  appendOptionalParam(params, "date_to", toDateTimeParam(filters.dateTo, "end"));
  appendOptionalParam(params, "due_state", filters.dueState);
  appendOptionalParam(params, "evidence_state", filters.evidenceState);
  appendOptionalParam(params, "incident_type", filters.incidentType);
  appendOptionalParam(params, "related_document_state", filters.relatedDocumentState);
  appendOptionalParam(params, "reported_by_user_id", filters.reportedByUserId);
  appendOptionalParam(params, "responsible_user_id", filters.responsibleUserId);
  appendOptionalParam(params, "search", filters.search.trim());
  appendOptionalParam(params, "severity", filters.severity);
  appendOptionalParam(params, "source_type", filters.sourceType);
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "warning_state", filters.warningState);
  return `/v1/admin/incidents?${params.toString()}`;
}

export function fetchAdminIncidents(
  accessToken: string,
  filters: AdminIncidentListFilters,
): Promise<AdminIncidentListResponse> {
  return requestJson<ApiListResponse>({
    accessToken,
    path: buildAdminIncidentsListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminIncidentDetail(
  accessToken: string,
  incidentId: string,
): Promise<AdminIncidentDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/incidents/${incidentId}`,
  }).then(mapDetailFromApi);
}

function mapCreatePayload(payload: AdminIncidentCreatePayload): ApiCreate {
  return {
    area_name: payload.areaName,
    branch_id: payload.branchId,
    corrective_action: payload.correctiveAction,
    description: payload.description,
    due_at: payload.dueAt,
    equipment_name: payload.equipmentName,
    evidence_note: payload.evidenceNote,
    food_safety_impact: payload.foodSafetyImpact,
    incident_type: payload.incidentType,
    notes: payload.notes,
    operational_impact: payload.operationalImpact,
    process_name: payload.processName,
    product_reference: payload.productReference,
    production_reference: payload.productionReference,
    responsible_user_id: payload.responsibleUserId,
    severity: payload.severity,
    source_document_id: payload.sourceDocumentId,
    source_reference: payload.sourceReference,
    source_summary: payload.sourceSummary,
    source_type: payload.sourceType,
    title: payload.title,
  };
}

export function createAdminIncident(
  accessToken: string,
  payload: AdminIncidentCreatePayload,
): Promise<AdminIncidentDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    body: mapCreatePayload(payload),
    method: "POST",
    path: "/v1/admin/incidents",
  }).then(mapDetailFromApi);
}

export function addAdminIncidentFollowUp(
  accessToken: string,
  incidentId: string,
  payload: AdminIncidentFollowUpPayload,
): Promise<AdminIncidentDetail> {
  const body: ApiFollowUp = {
    note: payload.note,
    status_change: payload.statusChange,
  };
  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/incidents/${incidentId}/follow-ups`,
  }).then(mapDetailFromApi);
}

export function changeAdminIncidentStatus(
  accessToken: string,
  incidentId: string,
  payload: AdminIncidentStatusPayload,
): Promise<AdminIncidentDetail> {
  const body: ApiStatus = {
    cancellation_reason: payload.cancellationReason,
    note: payload.note,
    status: payload.status,
  };
  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/incidents/${incidentId}/status`,
  }).then(mapDetailFromApi);
}

export function resolveAdminIncident(
  accessToken: string,
  incidentId: string,
  payload: AdminIncidentResolvePayload,
): Promise<AdminIncidentDetail> {
  const body: ApiResolve = {
    evidence_note: payload.evidenceNote,
    resolution_note: payload.resolutionNote,
    resolved_at: payload.resolvedAt,
    result: payload.result,
  };
  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/incidents/${incidentId}/resolve`,
  }).then(mapDetailFromApi);
}

export function reopenAdminIncident(
  accessToken: string,
  incidentId: string,
  note: string,
): Promise<AdminIncidentDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    body: { note },
    method: "POST",
    path: `/v1/admin/incidents/${incidentId}/reopen`,
  }).then(mapDetailFromApi);
}
