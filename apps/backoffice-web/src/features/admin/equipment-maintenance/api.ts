import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminEquipmentBackendContract,
  AdminEquipmentCreatePayload,
  AdminEquipmentDetail,
  AdminEquipmentFilterOption,
  AdminEquipmentListFilters,
  AdminEquipmentListItem,
  AdminEquipmentListResponse,
  AdminEquipmentStatusPayload,
  AdminMaintenanceCompletePayload,
  AdminMaintenanceCreatePayload,
  AdminMaintenanceRecordListItem,
} from "./types";

type ApiBackendContract = components["schemas"]["AdminEquipmentBackendContractView"];
type ApiCreateEquipment = components["schemas"]["AdminEquipmentCreateRequest"];
type ApiDetail = components["schemas"]["AdminEquipmentDetailView"];
type ApiFilterOption = components["schemas"]["AdminEquipmentFilterOptionView"];
type ApiListItem = components["schemas"]["AdminEquipmentListItemView"];
type ApiListResponse = components["schemas"]["AdminEquipmentListResponse"];
type ApiMaintenance = components["schemas"]["AdminMaintenanceRecordListItemView"];
type ApiMaintenanceComplete = components["schemas"]["AdminMaintenanceCompleteRequest"];
type ApiMaintenanceCreate = components["schemas"]["AdminMaintenanceCreateRequest"];

export const adminEquipmentBackendContract: AdminEquipmentBackendContract = {
  cancelMaintenanceEndpoint:
    "POST /v1/admin/equipment-maintenance/maintenance/{maintenance_id}/cancel",
  completeMaintenanceEndpoint:
    "POST /v1/admin/equipment-maintenance/maintenance/{maintenance_id}/complete",
  createEquipmentEndpoint: "POST /v1/admin/equipment-maintenance/equipment",
  createMaintenanceEndpoint: "POST /v1/admin/equipment-maintenance/maintenance",
  detailEndpoint: "GET /v1/admin/equipment-maintenance/equipment/{equipment_id}",
  evidenceContract:
    "Evidence files are not supported yet; evidence is captured as evidence_note.",
  incidentContract:
    "Incident backend is not available yet; incident links are stored as references.",
  listEndpoint: "GET /v1/admin/equipment-maintenance/equipment",
  startMaintenanceEndpoint:
    "POST /v1/admin/equipment-maintenance/maintenance/{maintenance_id}/start",
  statusEndpoint: "POST /v1/admin/equipment-maintenance/equipment/{equipment_id}/status",
  updateEquipmentEndpoint: "PATCH /v1/admin/equipment-maintenance/equipment/{equipment_id}",
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

function toMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined) {
    return "$0.00";
  }
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return String(value);
  }
  return new Intl.NumberFormat("es-MX", {
    currency: "MXN",
    style: "currency",
  }).format(parsed);
}

export { toMoney as formatEquipmentMoney };

function mapOption(option: ApiFilterOption): AdminEquipmentFilterOption {
  return { id: option.id, label: option.label };
}

function mapBackendContract(
  contract: ApiBackendContract | undefined,
): AdminEquipmentBackendContract {
  if (!contract) {
    return adminEquipmentBackendContract;
  }
  return {
    cancelMaintenanceEndpoint: contract.cancel_maintenance_endpoint,
    completeMaintenanceEndpoint: contract.complete_maintenance_endpoint,
    createEquipmentEndpoint: contract.create_equipment_endpoint,
    createMaintenanceEndpoint: contract.create_maintenance_endpoint,
    detailEndpoint: contract.detail_endpoint,
    evidenceContract: contract.evidence_contract,
    incidentContract: contract.incident_contract,
    listEndpoint: contract.list_endpoint,
    startMaintenanceEndpoint: contract.start_maintenance_endpoint,
    statusEndpoint: contract.status_endpoint,
    updateEquipmentEndpoint: contract.update_equipment_endpoint,
  };
}

function mapMaintenance(record: ApiMaintenance): AdminMaintenanceRecordListItem {
  return {
    completedAt: record.completed_at ?? null,
    cost: record.cost ?? null,
    evidenceNote: record.evidence_note ?? null,
    folio: record.folio,
    hasEvidence: record.has_evidence,
    id: record.id,
    maintenanceType: record.maintenance_type,
    notes: record.notes ?? null,
    providerName: record.provider_name ?? null,
    relatedIncidentReference: record.related_incident_reference ?? null,
    result: record.result,
    scheduledAt: record.scheduled_at ?? null,
    startedAt: record.started_at ?? null,
    status: record.status,
    technicianName: record.technician_name ?? null,
    warningState: record.warning_state,
  };
}

export function mapAdminEquipmentListItemFromApi(item: ApiListItem): AdminEquipmentListItem {
  return {
    areaId: item.area_id ?? null,
    areaName: item.area_name ?? null,
    branchId: item.branch_id,
    branchName: item.branch_name,
    code: item.code,
    equipmentType: item.equipment_type,
    id: item.id,
    lastMaintenanceAt: item.last_maintenance_at ?? null,
    maintenanceStatus: item.maintenance_status,
    name: item.name,
    nextMaintenanceAt: item.next_maintenance_at ?? null,
    openIncidentCount: item.open_incident_count,
    operationalStatus: item.operational_status,
    periodCost: item.period_cost,
    riskLevel: item.risk_level,
    updatedAt: item.updated_at,
    warningState: item.warning_state,
    warnings: item.warnings,
  };
}

function mapDetailFromApi(response: ApiDetail): AdminEquipmentDetail {
  const warningState = response.overview.warning_state;
  return {
    availableActions: {
      canCancelMaintenance: response.available_actions.can_cancel_maintenance,
      canCompleteMaintenance: response.available_actions.can_complete_maintenance,
      canCreateCorrective: response.available_actions.can_create_corrective,
      canCreatePreventive: response.available_actions.can_create_preventive,
      canEditEquipment: response.available_actions.can_edit_equipment,
      canExport: response.available_actions.can_export,
      canMarkOperational: response.available_actions.can_mark_operational,
      canMarkOutOfService: response.available_actions.can_mark_out_of_service,
      canPrint: response.available_actions.can_print,
      canStartMaintenance: response.available_actions.can_start_maintenance,
      note: response.available_actions.note ?? null,
    },
    costContext: {
      lastServiceCost: response.cost_context.last_service_cost ?? null,
      periodCost: response.cost_context.period_cost,
      totalLifetimeCost: response.cost_context.total_lifetime_cost,
      warrantyNote: response.cost_context.warranty_note ?? null,
    },
    currentMaintenanceStatus: {
      currentLinkedIncident: response.current_maintenance_status.current_linked_incident ?? null,
      currentOpenMaintenance: response.current_maintenance_status.current_open_maintenance
        ? mapMaintenance(response.current_maintenance_status.current_open_maintenance)
        : null,
      downtimeState: response.current_maintenance_status.downtime_state,
      lastMaintenanceAt: response.current_maintenance_status.last_maintenance_at ?? null,
      lastMaintenanceResult: response.current_maintenance_status.last_maintenance_result ?? null,
      lastMaintenanceType: response.current_maintenance_status.last_maintenance_type ?? null,
      nextScheduledMaintenanceAt:
        response.current_maintenance_status.next_scheduled_maintenance_at ?? null,
      overdue: response.current_maintenance_status.overdue,
    },
    evidence: {
      emptyState: response.evidence.empty_state,
      files: response.evidence.files ?? [],
      hasEvidence: response.evidence.has_evidence,
      isSupported: response.evidence.is_supported,
      latestEvidenceNote: response.evidence.latest_evidence_note ?? null,
      uploadSupported: response.evidence.upload_supported,
    },
    incidentsRelated: response.incidents_related.map((incident) => ({
      folio: incident.folio,
      routeHint: incident.route_hint ?? null,
      severity: incident.severity,
      status: incident.status,
    })),
    locationContext: {
      areaName: response.location_context.area_name ?? null,
      areaType: response.location_context.area_type,
      branchCode: response.location_context.branch_code,
      branchId: response.location_context.branch_id,
      branchName: response.location_context.branch_name,
      foodSafetyCritical: response.location_context.food_safety_critical,
      isCritical: response.location_context.is_critical,
    },
    maintenanceHistory: response.maintenance_history.map(mapMaintenance),
    metadata: {
      brand: response.metadata.brand ?? null,
      maintenanceFrequencyDays: response.metadata.maintenance_frequency_days ?? null,
      model: response.metadata.model ?? null,
      notes: response.metadata.notes ?? null,
      providerName: response.metadata.provider_name ?? null,
      purchaseDate: response.metadata.purchase_date ?? null,
      serialNumber: response.metadata.serial_number ?? null,
      warrantyExpiresAt: response.metadata.warranty_expires_at ?? null,
    },
    overview: {
      ...mapAdminEquipmentListItemFromApi({
        area_id: null,
        area_name: response.location_context.area_name ?? null,
        branch_id: response.overview.branch_id,
        branch_name: response.overview.branch_name,
        code: response.overview.code,
        equipment_type: response.overview.equipment_type,
        id: response.overview.id,
        last_maintenance_at: response.current_maintenance_status.last_maintenance_at ?? null,
        maintenance_status: response.current_maintenance_status.current_open_maintenance
          ? response.current_maintenance_status.current_open_maintenance.status
          : response.current_maintenance_status.overdue
            ? "OVERDUE"
            : "OK",
        name: response.overview.name,
        next_maintenance_at:
          response.current_maintenance_status.next_scheduled_maintenance_at ?? null,
        open_incident_count: response.incidents_related.length,
        operational_status: response.overview.operational_status,
        period_cost: response.cost_context.period_cost,
        risk_level: response.overview.risk_level,
        updated_at: response.overview.updated_at,
        warning_state: warningState,
        warnings: response.warnings,
      }),
      createdAt: response.overview.created_at,
    },
    relatedDocuments: response.related_documents.map((document) => ({
      documentId: document.document_id,
      documentType: document.document_type,
      folio: document.folio,
      routeHint: document.route_hint ?? null,
      status: document.status,
    })),
    warnings: response.warnings,
  };
}

function mapListFromApi(response: ApiListResponse): AdminEquipmentListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      areaTypes: response.filter_options.area_types.map(mapOption),
      areas: response.filter_options.areas.map(mapOption),
      branches: response.filter_options.branches.map(mapOption),
      equipmentTypes: response.filter_options.equipment_types.map(mapOption),
      incidentStates: response.filter_options.incident_states.map(mapOption),
      maintenanceStatuses: response.filter_options.maintenance_statuses.map(mapOption),
      maintenanceTypes: response.filter_options.maintenance_types.map(mapOption),
      operationalStatuses: response.filter_options.operational_statuses.map(mapOption),
      providers: response.filter_options.providers.map(mapOption),
      riskLevels: response.filter_options.risk_levels.map(mapOption),
      technicians: response.filter_options.technicians.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminEquipmentListItemFromApi),
    metrics: {
      correctiveOpenCount: String(response.metrics.corrective_open_count),
      highRiskCount: String(response.metrics.high_risk_count),
      operationalCount: String(response.metrics.operational_count),
      outOfServiceCount: String(response.metrics.out_of_service_count),
      overdueCount: String(response.metrics.overdue_count),
      pendingMaintenanceCount: String(response.metrics.pending_maintenance_count),
      periodCost: toMoney(response.metrics.period_cost),
      totalEquipmentCount: String(response.metrics.total_equipment_count),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

export function buildAdminEquipmentListPath(filters: AdminEquipmentListFilters): string {
  const params = new URLSearchParams();
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "area_name", filters.areaName);
  appendOptionalParam(params, "area_type", filters.areaType);
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "date_from", toDateTimeParam(filters.dateFrom, "start"));
  appendOptionalParam(params, "date_to", toDateTimeParam(filters.dateTo, "end"));
  appendOptionalParam(params, "equipment_type", filters.equipmentType);
  appendOptionalParam(params, "incident_state", filters.incidentState);
  appendOptionalParam(params, "maintenance_status", filters.maintenanceStatus);
  appendOptionalParam(params, "maintenance_type", filters.maintenanceType);
  appendOptionalParam(params, "operational_status", filters.operationalStatus);
  appendOptionalParam(params, "overdue_state", filters.overdueState);
  appendOptionalParam(params, "provider_name", filters.providerName);
  appendOptionalParam(params, "risk_level", filters.riskLevel);
  appendOptionalParam(params, "search", filters.search.trim());
  appendOptionalParam(params, "technician_name", filters.technicianName);
  return `/v1/admin/equipment-maintenance/equipment?${params.toString()}`;
}

export function fetchAdminEquipment(
  accessToken: string,
  filters: AdminEquipmentListFilters,
): Promise<AdminEquipmentListResponse> {
  return requestJson<ApiListResponse>({
    accessToken,
    path: buildAdminEquipmentListPath(filters),
  }).then(mapListFromApi);
}

export function fetchAdminEquipmentDetail(
  accessToken: string,
  equipmentId: string,
): Promise<AdminEquipmentDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/equipment-maintenance/equipment/${equipmentId}`,
  }).then(mapDetailFromApi);
}

function mapEquipmentPayload(payload: AdminEquipmentCreatePayload): ApiCreateEquipment {
  return {
    area_name: payload.areaName,
    area_type: payload.areaType,
    branch_id: payload.branchId,
    brand: payload.brand,
    code: payload.code,
    equipment_type: payload.equipmentType,
    food_safety_critical: payload.foodSafetyCritical,
    is_critical: payload.isCritical,
    maintenance_frequency_days: payload.maintenanceFrequencyDays,
    model: payload.model,
    name: payload.name,
    notes: payload.notes,
    operational_status: payload.operationalStatus,
    provider_name: payload.providerName,
    purchase_date: payload.purchaseDate,
    risk_level: payload.riskLevel,
    serial_number: payload.serialNumber,
    warranty_expires_at: payload.warrantyExpiresAt,
  };
}

export function createAdminEquipment(
  accessToken: string,
  payload: AdminEquipmentCreatePayload,
): Promise<AdminEquipmentDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    body: mapEquipmentPayload(payload),
    method: "POST",
    path: "/v1/admin/equipment-maintenance/equipment",
  }).then(mapDetailFromApi);
}

export function updateAdminEquipmentStatus(
  accessToken: string,
  equipmentId: string,
  payload: AdminEquipmentStatusPayload,
): Promise<AdminEquipmentDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    body: {
      operational_status: payload.operationalStatus,
      reason: payload.reason,
    },
    method: "POST",
    path: `/v1/admin/equipment-maintenance/equipment/${equipmentId}/status`,
  }).then(mapDetailFromApi);
}

export function createAdminMaintenance(
  accessToken: string,
  payload: AdminMaintenanceCreatePayload,
): Promise<AdminEquipmentDetail> {
  const body: ApiMaintenanceCreate = {
    description: payload.description,
    equipment_id: payload.equipmentId,
    expected_cost: payload.expectedCost,
    maintenance_type: payload.maintenanceType,
    provider_name: payload.providerName,
    related_incident_reference: payload.relatedIncidentReference,
    scheduled_at: payload.scheduledAt,
    source_document_reference: payload.sourceDocumentReference,
    source_document_type: payload.sourceDocumentType,
    start_immediately: payload.startImmediately,
    status: payload.status,
    technician_name: payload.technicianName,
  };
  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: "/v1/admin/equipment-maintenance/maintenance",
  }).then(mapDetailFromApi);
}

export function startAdminMaintenance(
  accessToken: string,
  maintenanceId: string,
): Promise<AdminEquipmentDetail> {
  return requestJson<ApiDetail>({
    accessToken,
    method: "POST",
    path: `/v1/admin/equipment-maintenance/maintenance/${maintenanceId}/start`,
  }).then(mapDetailFromApi);
}

export function completeAdminMaintenance(
  accessToken: string,
  maintenanceId: string,
  payload: AdminMaintenanceCompletePayload,
): Promise<AdminEquipmentDetail> {
  const body: ApiMaintenanceComplete = {
    completed_at: payload.completedAt,
    cost: payload.cost,
    equipment_status_after_service: payload.equipmentStatusAfterService,
    evidence_note: payload.evidenceNote,
    notes: payload.notes,
    result: payload.result,
    technician_name: payload.technicianName,
  };
  return requestJson<ApiDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/equipment-maintenance/maintenance/${maintenanceId}/complete`,
  }).then(mapDetailFromApi);
}
