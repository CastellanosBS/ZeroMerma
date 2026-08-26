export type AdminWasteStatus = "COMMITTED" | "CANCELLED";
export type AdminWasteImpactLevel = "normal" | "high";
export type AdminWasteEvidenceState = "all" | "with_evidence" | "without_evidence";
export type AdminWasteWarningSeverity = "info" | "warning" | "critical";
export type AdminWasteLocationCode = "BACKROOM" | "COUNTER" | "IN_TRANSIT";

export interface AdminWasteFilterOption {
  id: string;
  label: string;
}

export interface AdminWasteReason {
  code: string;
  displayOrder: number;
  highImpactDefault: boolean;
  label: string;
  requiresEvidence: boolean;
  requiresNote: boolean;
}

export interface AdminWasteBackendContract {
  createEndpoint: string;
  detailEndpoint: string;
  inventoryMovementContract: string;
  listEndpoint: string;
  reasonsEndpoint: string;
}

export interface AdminWasteFilterOptions {
  branches: AdminWasteFilterOption[];
  classes: AdminWasteFilterOption[];
  evidenceStates: AdminWasteFilterOption[];
  impactLevels: AdminWasteFilterOption[];
  locations: AdminWasteFilterOption[];
  operators: AdminWasteFilterOption[];
  productKinds: AdminWasteFilterOption[];
  products: AdminWasteFilterOption[];
  reasons: AdminWasteReason[];
  statuses: AdminWasteFilterOption[];
}

export interface AdminWasteMetrics {
  contaminatedOrDamaged: string;
  evidenceRecords: string;
  estimatedValue: string;
  expiredRecords: string;
  highImpactRecords: string;
  totalQuantity: string;
  totalRecords: string;
}

export interface AdminWasteWarning {
  code: string;
  message: string;
  severity: AdminWasteWarningSeverity;
}

export interface AdminWasteListFilters {
  branchId?: string | null;
  classId?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
  evidenceState?: AdminWasteEvidenceState;
  impactLevel?: AdminWasteImpactLevel | "all";
  locationCode?: AdminWasteLocationCode | "all";
  operatorUserId?: string | null;
  page: number;
  pageSize: number;
  productId?: string | null;
  productKind?: string | "all";
  reasonCode?: string | "all";
  search?: string;
  status?: AdminWasteStatus | "all";
  warningState?: AdminWasteWarningSeverity | "all";
}

export interface AdminWasteListItem {
  branchId: string;
  branchName: string;
  createdAt: string;
  estimatedValue?: string | null;
  folio: string;
  hasEvidence: boolean;
  id: string;
  impactLevel: AdminWasteImpactLevel;
  lineCount: number;
  locationCode: AdminWasteLocationCode;
  locationName: string;
  operatorName: string;
  productCode: string;
  productId: string;
  productKind: string;
  productName: string;
  quantity: string;
  reasonCode: string;
  reasonLabel: string;
  status: AdminWasteStatus;
  uom: string;
  warningState?: AdminWasteWarningSeverity | null;
  warnings: AdminWasteWarning[];
}

export interface AdminWasteListResponse {
  backendContract: AdminWasteBackendContract;
  filterOptions: AdminWasteFilterOptions;
  isBackendConnected: boolean;
  items: AdminWasteListItem[];
  metrics: AdminWasteMetrics;
  page: number;
  pageSize: number;
  total: number;
}

export interface AdminWasteOverview {
  branchId: string;
  branchName: string;
  confirmedAt?: string | null;
  createdAt: string;
  folio: string;
  hasEvidence: boolean;
  id: string;
  impactLevel: AdminWasteImpactLevel;
  locationCode: AdminWasteLocationCode;
  locationName: string;
  notes?: string | null;
  operatorId: string;
  operatorName: string;
  quantity: string;
  reasonCode: string;
  reasonLabel: string;
  status: AdminWasteStatus;
  uom: string;
  warningState?: AdminWasteWarningSeverity | null;
  workstationCode?: string | null;
  workstationName?: string | null;
}

export interface AdminWasteProductInventoryContext {
  branchId: string;
  branchName: string;
  classId: string;
  className: string;
  currentStock?: string | null;
  productCode: string;
  productId: string;
  productIsActive: boolean;
  productKind: string;
  productName: string;
  stockAfter?: string | null;
  stockBefore?: string | null;
  uom: string;
}

export interface AdminWasteLine {
  estimatedValue?: string | null;
  lineNumber: number;
  productCode: string;
  productId: string;
  productKind: string;
  productName: string;
  quantity: string;
  uom: string;
}

export interface AdminWasteReasonClassification {
  category: string;
  description?: string | null;
  label: string;
  requiresEvidence: boolean;
  requiresNote: boolean;
}

export interface AdminWasteEvidence {
  attachmentSupported: boolean;
  evidenceItems: Array<Record<string, string>>;
  notes?: string | null;
}

export interface AdminWasteInventoryMovement {
  balanceAfter?: string | null;
  direction: string;
  id: string;
  locationCode: string;
  movementType: string;
  productId: string;
  quantity: string;
  sourceDocumentId?: string | null;
  sourceDocumentType?: string | null;
  unitOfMeasure: string;
}

export interface AdminWasteInventoryImpact {
  integrationAvailable: boolean;
  movements: AdminWasteInventoryMovement[];
  notes?: string | null;
}

export interface AdminWasteRelatedDocument {
  documentId: string;
  documentType: string;
  folio: string;
  status: string;
}

export interface AdminWasteAvailableActions {
  canCreateCorrection: boolean;
  canEdit: boolean;
  canOpenInventoryMovement: boolean;
  canPrint: boolean;
}

export interface AdminWasteDetail {
  availableActions: AdminWasteAvailableActions;
  evidence: AdminWasteEvidence;
  inventoryImpact: AdminWasteInventoryImpact;
  lines: AdminWasteLine[];
  overview: AdminWasteOverview;
  productInventoryContext: AdminWasteProductInventoryContext;
  reasonClassification: AdminWasteReasonClassification;
  relatedDocuments: AdminWasteRelatedDocument[];
  warnings: AdminWasteWarning[];
}

export interface AdminWasteCreatePayload {
  branchId: string;
  locationCode: AdminWasteLocationCode;
  notes?: string | null;
  productId: string;
  quantity: string;
  reasonCode: string;
}
