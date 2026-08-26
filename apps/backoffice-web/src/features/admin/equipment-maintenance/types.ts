export type AdminEquipmentRiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type AdminEquipmentOperationalStatus =
  | "OPERATIONAL"
  | "OUT_OF_SERVICE"
  | "UNDER_MAINTENANCE"
  | "RETIRED"
  | "INACTIVE";

export type AdminMaintenanceStatus =
  | "SCHEDULED"
  | "PENDING"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "OVERDUE"
  | "CANCELLED";

export type AdminMaintenanceType =
  | "PREVENTIVE"
  | "CORRECTIVE"
  | "INSPECTION"
  | "CALIBRATION"
  | "CLEANING_TECHNICAL";

export type AdminMaintenanceResult =
  | "NOT_COMPLETED"
  | "COMPLETED_SUCCESSFULLY"
  | "COMPLETED_WITH_OBSERVATIONS"
  | "FAILED"
  | "REQUIRES_FOLLOW_UP"
  | "CANCELLED";

export interface AdminEquipmentBackendContract {
  cancelMaintenanceEndpoint: string;
  completeMaintenanceEndpoint: string;
  createEquipmentEndpoint: string;
  createMaintenanceEndpoint: string;
  detailEndpoint: string;
  evidenceContract: string;
  incidentContract: string;
  listEndpoint: string;
  startMaintenanceEndpoint: string;
  statusEndpoint: string;
  updateEquipmentEndpoint: string;
}

export interface AdminEquipmentFilterOption {
  id: string;
  label: string;
}

export interface AdminEquipmentFilterOptions {
  areaTypes: AdminEquipmentFilterOption[];
  areas: AdminEquipmentFilterOption[];
  branches: AdminEquipmentFilterOption[];
  equipmentTypes: AdminEquipmentFilterOption[];
  incidentStates: AdminEquipmentFilterOption[];
  maintenanceStatuses: AdminEquipmentFilterOption[];
  maintenanceTypes: AdminEquipmentFilterOption[];
  operationalStatuses: AdminEquipmentFilterOption[];
  providers: AdminEquipmentFilterOption[];
  riskLevels: AdminEquipmentFilterOption[];
  technicians: AdminEquipmentFilterOption[];
}

export interface AdminEquipmentMetrics {
  correctiveOpenCount: string;
  highRiskCount: string;
  operationalCount: string;
  outOfServiceCount: string;
  overdueCount: string;
  pendingMaintenanceCount: string;
  periodCost: string;
  totalEquipmentCount: string;
}

export interface AdminEquipmentWarning {
  code: string;
  message: string;
  severity: "info" | "warning" | "critical";
}

export interface AdminEquipmentListFilters {
  areaName: string;
  areaType: string;
  branchId: string;
  dateFrom: string | null;
  dateTo: string | null;
  equipmentType: string;
  incidentState: string;
  maintenanceStatus: string;
  maintenanceType: string;
  operationalStatus: string;
  overdueState: string;
  page: number;
  pageSize: number;
  providerName: string;
  riskLevel: string;
  search: string;
  technicianName: string;
}

export interface AdminMaintenanceRecordListItem {
  completedAt: string | null;
  cost: string | number | null;
  evidenceNote: string | null;
  folio: string;
  hasEvidence: boolean;
  id: string;
  maintenanceType: AdminMaintenanceType;
  notes: string | null;
  providerName: string | null;
  relatedIncidentReference: string | null;
  result: AdminMaintenanceResult;
  scheduledAt: string | null;
  startedAt: string | null;
  status: AdminMaintenanceStatus;
  technicianName: string | null;
  warningState: string;
}

export interface AdminEquipmentListItem {
  areaId: string | null;
  areaName: string | null;
  branchId: string;
  branchName: string;
  code: string;
  equipmentType: string;
  id: string;
  lastMaintenanceAt: string | null;
  maintenanceStatus: string;
  name: string;
  nextMaintenanceAt: string | null;
  openIncidentCount: number;
  operationalStatus: AdminEquipmentOperationalStatus;
  periodCost: string | number;
  riskLevel: AdminEquipmentRiskLevel;
  updatedAt: string;
  warningState: string;
  warnings: AdminEquipmentWarning[];
}

export interface AdminEquipmentListResponse {
  backendContract: AdminEquipmentBackendContract;
  filterOptions: AdminEquipmentFilterOptions;
  isBackendConnected: boolean;
  items: AdminEquipmentListItem[];
  metrics: AdminEquipmentMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminEquipmentDetail {
  availableActions: {
    canCancelMaintenance: boolean;
    canCompleteMaintenance: boolean;
    canCreateCorrective: boolean;
    canCreatePreventive: boolean;
    canEditEquipment: boolean;
    canExport: boolean;
    canMarkOperational: boolean;
    canMarkOutOfService: boolean;
    canPrint: boolean;
    canStartMaintenance: boolean;
    note: string | null;
  };
  costContext: {
    lastServiceCost: string | number | null;
    periodCost: string | number;
    totalLifetimeCost: string | number;
    warrantyNote: string | null;
  };
  currentMaintenanceStatus: {
    currentOpenMaintenance: AdminMaintenanceRecordListItem | null;
    currentLinkedIncident: string | null;
    downtimeState: string;
    lastMaintenanceAt: string | null;
    lastMaintenanceResult: AdminMaintenanceResult | null;
    lastMaintenanceType: AdminMaintenanceType | null;
    nextScheduledMaintenanceAt: string | null;
    overdue: boolean;
  };
  evidence: {
    emptyState: string;
    files: Record<string, string>[];
    hasEvidence: boolean;
    isSupported: boolean;
    latestEvidenceNote: string | null;
    uploadSupported: boolean;
  };
  incidentsRelated: {
    folio: string;
    routeHint: string | null;
    severity: string;
    status: string;
  }[];
  locationContext: {
    areaName: string | null;
    areaType: string;
    branchCode: string;
    branchId: string;
    branchName: string;
    foodSafetyCritical: boolean;
    isCritical: boolean;
  };
  maintenanceHistory: AdminMaintenanceRecordListItem[];
  metadata: {
    brand: string | null;
    maintenanceFrequencyDays: number | null;
    model: string | null;
    notes: string | null;
    providerName: string | null;
    purchaseDate: string | null;
    serialNumber: string | null;
    warrantyExpiresAt: string | null;
  };
  overview: AdminEquipmentListItem & {
    createdAt: string;
  };
  relatedDocuments: {
    documentId: string;
    documentType: string;
    folio: string;
    routeHint: string | null;
    status: string;
  }[];
  warnings: AdminEquipmentWarning[];
}

export interface AdminEquipmentCreatePayload {
  areaName: string | null;
  areaType: string;
  branchId: string;
  brand: string | null;
  code: string;
  equipmentType: string;
  foodSafetyCritical: boolean;
  isCritical: boolean;
  maintenanceFrequencyDays: number | null;
  model: string | null;
  name: string;
  notes: string | null;
  operationalStatus: AdminEquipmentOperationalStatus;
  providerName: string | null;
  purchaseDate: string | null;
  riskLevel: AdminEquipmentRiskLevel;
  serialNumber: string | null;
  warrantyExpiresAt: string | null;
}

export interface AdminEquipmentStatusPayload {
  operationalStatus: AdminEquipmentOperationalStatus;
  reason: string | null;
}

export interface AdminMaintenanceCreatePayload {
  description: string;
  equipmentId: string;
  expectedCost: string | null;
  maintenanceType: AdminMaintenanceType;
  providerName: string | null;
  relatedIncidentReference: string | null;
  scheduledAt: string | null;
  sourceDocumentReference: string | null;
  sourceDocumentType: string | null;
  startImmediately: boolean;
  status: AdminMaintenanceStatus;
  technicianName: string | null;
}

export interface AdminMaintenanceCompletePayload {
  completedAt: string | null;
  cost: string | null;
  equipmentStatusAfterService: AdminEquipmentOperationalStatus | null;
  evidenceNote: string | null;
  notes: string | null;
  result: AdminMaintenanceResult;
  technicianName: string | null;
}
