export interface AdminAuditFilterOption {
  id: string;
  label: string;
}

export interface AdminAuditBackendContract {
  exportSupported: boolean;
  immutableEvents: boolean;
  mutationSupported: boolean;
  relatedTimelineSupported: boolean;
  requestContextSupported: boolean;
}

export interface AdminAuditFilterOptions {
  actions: AdminAuditFilterOption[];
  branches: AdminAuditFilterOption[];
  entityTypes: AdminAuditFilterOption[];
  modules: AdminAuditFilterOption[];
  results: AdminAuditFilterOption[];
  sensitivities: AdminAuditFilterOption[];
  severities: AdminAuditFilterOption[];
  sourceApps: AdminAuditFilterOption[];
  users: AdminAuditFilterOption[];
  warningStates: AdminAuditFilterOption[];
}

export interface AdminAuditListFilters {
  action: string;
  actorEmail: string;
  actorUserId: string;
  branchId: string;
  dateFrom: string;
  dateTo: string;
  entityId: string;
  entityType: string;
  module: string;
  page: number;
  pageSize: number;
  relatedReference: string;
  result: string;
  search: string;
  sensitive: string;
  severity: string;
  sourceApp: string;
  warningState: string;
  workstation: string;
}

export interface AdminAuditMetrics {
  accessEvents: string;
  activeActors: string;
  failedEvents: string;
  financialEvents: string;
  inventoryEvents: string;
  sensitiveEvents: string;
  systemEvents: string;
  totalEvents: string;
}

export interface AdminAuditEventListItem {
  action: string;
  actionLabel: string;
  actorEmail: string | null;
  actorName: string;
  actorType: string;
  actorUserId: string | null;
  branchId: string | null;
  branchName: string | null;
  entityId: string | null;
  entityReference: string | null;
  entityType: string;
  id: string;
  isSensitive: boolean;
  module: string;
  moduleLabel: string;
  occurredAt: string;
  result: string;
  severity: string;
  sourceApp: string;
  warningState: string;
  workstationId: string | null;
  workstationName: string | null;
}

export interface AdminAuditListResponse {
  backendContract: AdminAuditBackendContract;
  filterOptions: AdminAuditFilterOptions;
  isBackendConnected: boolean;
  items: AdminAuditEventListItem[];
  metrics: AdminAuditMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminAuditChangeItem {
  changeType: string;
  field: string;
  newValueMasked: string | null;
  oldValueMasked: string | null;
}

export interface AdminAuditRequestContext {
  correlationId: string | null;
  durationMs: number | null;
  endpoint: string | null;
  errorCode: string | null;
  ipAddress: string | null;
  method: string | null;
  requestId: string | null;
  statusCode: number | null;
  userAgent: string | null;
}

export interface AdminAuditRelatedDocument {
  canOpen: boolean;
  documentId: string | null;
  documentType: string;
  label: string;
  module: string;
  reference: string | null;
}

export interface AdminAuditTimelineEvent {
  action: string;
  actionLabel: string;
  actorName: string;
  id: string;
  isSensitive: boolean;
  occurredAt: string;
  result: string;
}

export interface AdminAuditEventDetail {
  actorContext: {
    branchAssignmentsSummary: string | null;
    canOpenUser: boolean;
    email: string | null;
    fullName: string;
    rolesSummary: string | null;
    userId: string | null;
    userStatus: string | null;
  };
  availableActions: {
    canCopyCorrelationId: boolean;
    canCopyEventId: boolean;
    canExportEvent: boolean;
    canOpenRelatedDocument: boolean;
    canOpenUser: boolean;
    canSearchRelatedEvents: boolean;
  };
  changeSummary: AdminAuditChangeItem[];
  entityContext: {
    branchId: string | null;
    branchName: string | null;
    canOpenRelatedDocument: boolean;
    cashSessionId: string | null;
    entityId: string | null;
    entityReference: string | null;
    entityType: string;
    relatedModule: string;
    workstationId: string | null;
    workstationName: string | null;
  };
  overview: AdminAuditEventListItem & { requestId: string | null };
  relatedDocuments: AdminAuditRelatedDocument[];
  requestContext: AdminAuditRequestContext | null;
  timelineRelatedEvents: AdminAuditTimelineEvent[];
}

export interface AdminAuditExportResponse {
  format: string;
  generatedAt: string;
  rows: Array<{
    action: string;
    actor: string;
    actorEmail: string | null;
    branchName: string | null;
    entityId: string | null;
    entityReference: string | null;
    entityType: string;
    isSensitive: boolean;
    module: string;
    occurredAt: string;
    result: string;
    sourceApp: string;
    workstationName: string | null;
  }>;
  total: number;
}
