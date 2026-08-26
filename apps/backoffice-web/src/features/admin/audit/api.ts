import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminAuditBackendContract,
  AdminAuditEventDetail,
  AdminAuditEventListItem,
  AdminAuditExportResponse,
  AdminAuditFilterOption,
  AdminAuditListFilters,
  AdminAuditListResponse,
} from "./types";

type ApiBackendContract = components["schemas"]["AdminAuditBackendContractView"];
type ApiDetail = components["schemas"]["AdminAuditEventDetailView"];
type ApiExport = components["schemas"]["AdminAuditExportResponse"];
type ApiListItem = components["schemas"]["AdminAuditEventListItemView"];
type ApiListResponse = components["schemas"]["AdminAuditEventsListResponse"];
type ApiOption = components["schemas"]["AdminAuditFilterOptionView"];

export const adminAuditBackendContract: AdminAuditBackendContract = {
  exportSupported: true,
  immutableEvents: true,
  mutationSupported: false,
  relatedTimelineSupported: true,
  requestContextSupported: true,
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

function mapOption(option: ApiOption): AdminAuditFilterOption {
  return { id: option.code, label: option.label };
}

function mapBackendContract(contract?: ApiBackendContract): AdminAuditBackendContract {
  if (!contract) {
    return adminAuditBackendContract;
  }
  return {
    exportSupported: contract.export_supported,
    immutableEvents: contract.immutable_events,
    mutationSupported: contract.mutation_supported,
    relatedTimelineSupported: contract.related_timeline_supported,
    requestContextSupported: contract.request_context_supported,
  };
}

export function mapAdminAuditListItemFromApi(item: ApiListItem): AdminAuditEventListItem {
  return {
    action: item.action,
    actionLabel: item.action_label,
    actorEmail: item.actor_email ?? null,
    actorName: item.actor_name,
    actorType: item.actor_type,
    actorUserId: item.actor_user_id ?? null,
    branchId: item.branch_id ?? null,
    branchName: item.branch_name ?? null,
    entityId: item.entity_id ?? null,
    entityReference: item.entity_reference ?? null,
    entityType: item.entity_type,
    id: item.id,
    isSensitive: item.is_sensitive,
    module: item.module,
    moduleLabel: item.module_label,
    occurredAt: item.occurred_at,
    result: item.result,
    severity: item.severity,
    sourceApp: item.source_app,
    warningState: item.warning_state,
    workstationId: item.workstation_id ?? null,
    workstationName: item.workstation_name ?? null,
  };
}

function mapListFromApi(response: ApiListResponse): AdminAuditListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      actions: response.filter_options.actions.map(mapOption),
      branches: response.filter_options.branches.map(mapOption),
      entityTypes: response.filter_options.entity_types.map(mapOption),
      modules: response.filter_options.modules.map(mapOption),
      results: response.filter_options.results.map(mapOption),
      sensitivities: response.filter_options.sensitivities.map(mapOption),
      severities: response.filter_options.severities.map(mapOption),
      sourceApps: response.filter_options.source_apps.map(mapOption),
      users: response.filter_options.users.map(mapOption),
      warningStates: response.filter_options.warning_states.map(mapOption),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminAuditListItemFromApi),
    metrics: {
      accessEvents: String(response.metrics.access_events),
      activeActors: String(response.metrics.active_actors),
      failedEvents: String(response.metrics.failed_events),
      financialEvents: String(response.metrics.financial_events),
      inventoryEvents: String(response.metrics.inventory_events),
      sensitiveEvents: String(response.metrics.sensitive_events),
      systemEvents: String(response.metrics.system_events),
      totalEvents: String(response.metrics.total_events),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function mapDetailFromApi(response: ApiDetail): AdminAuditEventDetail {
  return {
    actorContext: {
      branchAssignmentsSummary: response.actor_context.branch_assignments_summary ?? null,
      canOpenUser: response.actor_context.can_open_user,
      email: response.actor_context.email ?? null,
      fullName: response.actor_context.full_name,
      rolesSummary: response.actor_context.roles_summary ?? null,
      userId: response.actor_context.user_id ?? null,
      userStatus: response.actor_context.user_status ?? null,
    },
    availableActions: {
      canCopyCorrelationId: response.available_actions.can_copy_correlation_id,
      canCopyEventId: response.available_actions.can_copy_event_id,
      canExportEvent: response.available_actions.can_export_event,
      canOpenRelatedDocument: response.available_actions.can_open_related_document,
      canOpenUser: response.available_actions.can_open_user,
      canSearchRelatedEvents: response.available_actions.can_search_related_events,
    },
    changeSummary: response.change_summary.map((item) => ({
      changeType: item.change_type,
      field: item.field,
      newValueMasked: item.new_value_masked ?? null,
      oldValueMasked: item.old_value_masked ?? null,
    })),
    entityContext: {
      branchId: response.entity_context.branch_id ?? null,
      branchName: response.entity_context.branch_name ?? null,
      canOpenRelatedDocument: response.entity_context.can_open_related_document,
      cashSessionId: response.entity_context.cash_session_id ?? null,
      entityId: response.entity_context.entity_id ?? null,
      entityReference: response.entity_context.entity_reference ?? null,
      entityType: response.entity_context.entity_type,
      relatedModule: response.entity_context.related_module,
      workstationId: response.entity_context.workstation_id ?? null,
      workstationName: response.entity_context.workstation_name ?? null,
    },
    overview: {
      ...mapAdminAuditListItemFromApi(response.overview),
      requestId: response.overview.request_id ?? null,
    },
    relatedDocuments: response.related_documents.map((item) => ({
      canOpen: item.can_open,
      documentId: item.document_id ?? null,
      documentType: item.document_type,
      label: item.label,
      module: item.module,
      reference: item.reference ?? null,
    })),
    requestContext: response.request_context
      ? {
          correlationId: response.request_context.correlation_id ?? null,
          durationMs: response.request_context.duration_ms ?? null,
          endpoint: response.request_context.endpoint ?? null,
          errorCode: response.request_context.error_code ?? null,
          ipAddress: response.request_context.ip_address ?? null,
          method: response.request_context.method ?? null,
          requestId: response.request_context.request_id ?? null,
          statusCode: response.request_context.status_code ?? null,
          userAgent: response.request_context.user_agent ?? null,
        }
      : null,
    timelineRelatedEvents: response.timeline_related_events.map((item) => ({
      action: item.action,
      actionLabel: item.action_label,
      actorName: item.actor_name,
      id: item.id,
      isSensitive: item.is_sensitive,
      occurredAt: item.occurred_at,
      result: item.result,
    })),
  };
}

function buildAuditSearchParams(filters: AdminAuditListFilters): URLSearchParams {
  const params = new URLSearchParams();
  appendOptionalParam(params, "action", filters.action);
  appendOptionalParam(params, "actor_email", filters.actorEmail);
  appendOptionalParam(params, "actor_user_id", filters.actorUserId);
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "date_from", filters.dateFrom);
  appendOptionalParam(params, "date_to", filters.dateTo);
  appendOptionalParam(params, "entity_id", filters.entityId);
  appendOptionalParam(params, "entity_type", filters.entityType);
  appendOptionalParam(params, "module", filters.module);
  appendOptionalParam(params, "related_reference", filters.relatedReference);
  appendOptionalParam(params, "result", filters.result);
  appendOptionalParam(params, "search", filters.search);
  appendOptionalParam(params, "sensitive", filters.sensitive);
  appendOptionalParam(params, "severity", filters.severity);
  appendOptionalParam(params, "source_app", filters.sourceApp);
  appendOptionalParam(params, "warning_state", filters.warningState);
  appendOptionalParam(params, "workstation", filters.workstation);
  return params;
}

export async function fetchAdminAuditEvents(
  accessToken: string,
  filters: AdminAuditListFilters,
): Promise<AdminAuditListResponse> {
  const params = buildAuditSearchParams(filters);
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));

  const suffix = params.toString();
  const response = await requestJson<ApiListResponse>({
    accessToken,
    path: `/v1/admin/audit${suffix ? `?${suffix}` : ""}`,
  });
  return mapListFromApi(response);
}

export async function fetchAdminAuditEventDetail(
  accessToken: string,
  eventId: string,
): Promise<AdminAuditEventDetail> {
  const response = await requestJson<ApiDetail>({
    accessToken,
    path: `/v1/admin/audit/${eventId}`,
  });
  return mapDetailFromApi(response);
}

export async function exportAdminAuditEvents(
  accessToken: string,
  filters: AdminAuditListFilters,
): Promise<AdminAuditExportResponse> {
  const params = buildAuditSearchParams(filters);
  const suffix = params.toString();
  const response = await requestJson<ApiExport>({
    accessToken,
    path: `/v1/admin/audit/export${suffix ? `?${suffix}` : ""}`,
  });
  return {
    format: response.format,
    generatedAt: response.generated_at,
    rows: response.rows.map((item) => ({
      action: item.action,
      actor: item.actor,
      actorEmail: item.actor_email ?? null,
      branchName: item.branch_name ?? null,
      entityId: item.entity_id ?? null,
      entityReference: item.entity_reference ?? null,
      entityType: item.entity_type,
      isSensitive: item.is_sensitive,
      module: item.module,
      occurredAt: item.occurred_at,
      result: item.result,
      sourceApp: item.source_app,
      workstationName: item.workstation_name ?? null,
    })),
    total: response.total,
  };
}
