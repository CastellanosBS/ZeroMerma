import type { components } from "@zeromerma/api-client";

import { requestJson } from "../../../lib/api";
import type {
  AdminSupplierBackendContract,
  AdminSupplierContactPayload,
  AdminSupplierDetail,
  AdminSupplierFilterOption,
  AdminSupplierListFilters,
  AdminSupplierListItem,
  AdminSupplierListResponse,
  AdminSupplierPayload,
  AdminSupplierProductPayload,
  AdminSupplierStatusPayload,
  AdminSupplierWarning,
} from "./types";

export const adminSupplierBackendContract: AdminSupplierBackendContract = {
  contactEndpoint: "POST /v1/admin/suppliers/{supplier_id}/contacts",
  createEndpoint: "POST /v1/admin/suppliers",
  detailEndpoint: "GET /v1/admin/suppliers/{supplier_id}",
  listEndpoint: "GET /v1/admin/suppliers",
  productEndpoint: "POST /v1/admin/suppliers/{supplier_id}/products",
  statusEndpoint: "POST /v1/admin/suppliers/{supplier_id}/status",
  updateEndpoint: "PATCH /v1/admin/suppliers/{supplier_id}",
};

type ApiSupplierBackendContract = components["schemas"]["AdminSupplierBackendContractView"];
type ApiSupplierContactPayload = components["schemas"]["AdminSupplierContactRequest"];
type ApiSupplierCreatePayload = components["schemas"]["AdminSupplierCreateRequest"];
type ApiSupplierDetail = components["schemas"]["AdminSupplierDetailView"];
type ApiSupplierFilterOption = components["schemas"]["AdminSupplierFilterOptionView"];
type ApiSupplierListItem = components["schemas"]["AdminSupplierListItemView"];
type ApiSupplierListResponse = components["schemas"]["AdminSupplierListResponse"];
type ApiSupplierProductPayload = components["schemas"]["AdminSupplierProductRequest"];
type ApiSupplierStatusPayload = components["schemas"]["AdminSupplierStatusRequest"];
type ApiSupplierWarning = components["schemas"]["AdminSupplierWarningView"];

function appendOptionalParam(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (!value || value === "all") {
    return;
  }
  params.set(key, value);
}

function mapMetric(value: number | string | null | undefined): string {
  if (value === null || value === undefined) {
    return "No disponible";
  }
  return String(value);
}

function mapFilterOptions(options: ApiSupplierFilterOption[]): AdminSupplierFilterOption[] {
  return options.map((option) => ({ id: String(option.id), label: option.label }));
}

function mapWarning(warning: ApiSupplierWarning): AdminSupplierWarning {
  return {
    code: warning.code,
    message: warning.message,
    severity: warning.severity,
  };
}

function mapBackendContract(contract?: ApiSupplierBackendContract): AdminSupplierBackendContract {
  if (!contract) {
    return adminSupplierBackendContract;
  }
  return {
    contactEndpoint: contract.contact_endpoint,
    createEndpoint: contract.create_endpoint,
    detailEndpoint: contract.detail_endpoint,
    listEndpoint: contract.list_endpoint,
    productEndpoint: contract.product_endpoint,
    statusEndpoint: contract.status_endpoint,
    updateEndpoint: contract.update_endpoint,
  };
}

export function mapAdminSupplierListItemFromApi(item: ApiSupplierListItem): AdminSupplierListItem {
  return {
    branchCount: item.branch_count,
    category: item.category,
    code: item.code,
    commercialName: item.commercial_name ?? null,
    id: item.id,
    legalName: item.legal_name,
    primaryContactEmail: item.primary_contact_email ?? null,
    primaryContactName: item.primary_contact_name ?? null,
    primaryContactPhone: item.primary_contact_phone ?? null,
    productCount: item.product_count,
    status: item.status,
    taxId: item.tax_id ?? null,
    termsSummary: item.terms_summary,
    updatedAt: item.updated_at,
    warningState: item.warning_state ?? null,
    warnings: item.warnings.map(mapWarning),
  };
}

export function mapAdminSupplierDetailFromApi(item: ApiSupplierDetail): AdminSupplierDetail {
  return {
    availableActions: {
      canAddContact: item.available_actions.can_add_contact,
      canAddProduct: item.available_actions.can_add_product,
      canBlock: item.available_actions.can_block,
      canDeactivate: item.available_actions.can_deactivate,
      canEdit: item.available_actions.can_edit,
    },
    branchApplicability: item.branch_applicability.map((branch) => ({
      branchCode: branch.branch_code,
      branchId: branch.branch_id,
      branchName: branch.branch_name,
      branchStatus: branch.branch_status,
      deliveryNotes: branch.delivery_notes ?? null,
      isActive: branch.is_active,
    })),
    commercialTerms: {
      creditDays: item.commercial_terms.credit_days,
      defaultCurrency: item.commercial_terms.default_currency,
      deliveryNotes: item.commercial_terms.delivery_notes ?? null,
      leadTimeDays: item.commercial_terms.lead_time_days,
      minimumOrderAmount: item.commercial_terms.minimum_order_amount ?? null,
      paymentTermsType: item.commercial_terms.payment_terms_type,
      purchaseNotes: item.commercial_terms.purchase_notes ?? null,
      summary: item.commercial_terms.summary,
    },
    contacts: item.contacts.map((contact) => ({
      email: contact.email ?? null,
      id: contact.id,
      isActive: contact.is_active,
      isPrimary: contact.is_primary,
      name: contact.name,
      notes: contact.notes ?? null,
      phone: contact.phone ?? null,
      role: contact.role ?? null,
      whatsapp: contact.whatsapp ?? null,
    })),
    fiscalLegal: {
      fiscalAddress: item.fiscal_legal.fiscal_address ?? null,
      fiscalRegime: item.fiscal_legal.fiscal_regime ?? null,
      legalName: item.fiscal_legal.legal_name,
      notes: item.fiscal_legal.notes ?? null,
      paymentFiscalEmail: item.fiscal_legal.payment_fiscal_email ?? null,
      taxId: item.fiscal_legal.tax_id ?? null,
    },
    operationalActivity: {
      integrationAvailable: item.operational_activity.integration_available,
      notes: item.operational_activity.notes,
      openPurchaseOrders: item.operational_activity.open_purchase_orders ?? null,
      recentPurchaseOrders: item.operational_activity.recent_purchase_orders ?? null,
    },
    overview: {
      category: item.overview.category,
      code: item.overview.code,
      commercialName: item.overview.commercial_name ?? null,
      createdAt: item.overview.created_at,
      id: item.overview.id,
      legalName: item.overview.legal_name,
      readinessState: item.overview.readiness_state ?? null,
      status: item.overview.status,
      taxId: item.overview.tax_id ?? null,
      updatedAt: item.overview.updated_at,
    },
    productAssociations: item.product_associations.map((relation) => ({
      currency: relation.currency,
      id: relation.id,
      isActive: relation.is_active,
      lastKnownPrice: relation.last_known_price ?? null,
      leadTimeDays: relation.lead_time_days,
      minimumOrderQty: relation.minimum_order_qty ?? null,
      notes: relation.notes ?? null,
      productCode: relation.product_code,
      productId: relation.product_id,
      productKind: relation.product_kind,
      productName: relation.product_name,
      purchaseUom: relation.purchase_uom,
      supplierSku: relation.supplier_sku ?? null,
    })),
    relatedDocuments: item.related_documents.map((document) => ({
      documentId: document.document_id,
      documentType: document.document_type,
      folio: document.folio,
      status: document.status,
    })),
    warnings: item.warnings.map(mapWarning),
  };
}

function mapSupplierListFromApi(response: ApiSupplierListResponse): AdminSupplierListResponse {
  return {
    backendContract: mapBackendContract(response.backend_contract),
    filterOptions: {
      branches: mapFilterOptions(response.filter_options.branches),
      categories: mapFilterOptions(response.filter_options.categories),
      productKinds: mapFilterOptions(response.filter_options.product_kinds),
      products: mapFilterOptions(response.filter_options.products),
      statuses: mapFilterOptions(response.filter_options.statuses),
      warningStates: mapFilterOptions(response.filter_options.warning_states),
    },
    isBackendConnected: response.is_backend_connected,
    items: response.items.map(mapAdminSupplierListItemFromApi),
    metrics: {
      activeSuppliers: mapMetric(response.metrics.active_suppliers),
      blockedSuppliers: mapMetric(response.metrics.blocked_suppliers),
      inactiveSuppliers: mapMetric(response.metrics.inactive_suppliers),
      suppliersWithRecentActivity: mapMetric(response.metrics.suppliers_with_recent_activity),
      suppliersWithWarnings: mapMetric(response.metrics.suppliers_with_warnings),
      suppliersWithoutProducts: mapMetric(response.metrics.suppliers_without_products),
      totalSuppliers: mapMetric(response.metrics.total_suppliers),
    },
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
  };
}

function toContactApiPayload(payload: AdminSupplierContactPayload): ApiSupplierContactPayload {
  return {
    email: payload.email ?? null,
    is_primary: payload.isPrimary ?? false,
    name: payload.name,
    notes: payload.notes ?? null,
    phone: payload.phone ?? null,
    role: payload.role ?? null,
    whatsapp: payload.whatsapp ?? null,
  };
}

function toProductApiPayload(payload: AdminSupplierProductPayload): ApiSupplierProductPayload {
  return {
    currency: payload.currency ?? "MXN",
    is_active: payload.isActive ?? true,
    last_known_price: payload.lastKnownPrice ?? null,
    lead_time_days: payload.leadTimeDays ?? 0,
    minimum_order_qty: payload.minimumOrderQty ?? null,
    notes: payload.notes ?? null,
    product_id: payload.productId,
    purchase_uom: payload.purchaseUom ?? null,
    supplier_sku: payload.supplierSku ?? null,
  };
}

function toSupplierApiPayload(payload: AdminSupplierPayload): ApiSupplierCreatePayload {
  return {
    branch_ids: payload.branchIds,
    category: payload.category,
    code: payload.code ?? null,
    commercial_name: payload.commercialName ?? null,
    contacts: payload.contacts.map(toContactApiPayload),
    credit_days: payload.creditDays,
    default_currency: payload.defaultCurrency,
    delivery_notes: payload.deliveryNotes ?? null,
    fiscal_address: payload.fiscalAddress ?? null,
    fiscal_regime: payload.fiscalRegime ?? null,
    lead_time_days: payload.leadTimeDays,
    legal_name: payload.legalName,
    minimum_order_amount: payload.minimumOrderAmount ?? null,
    notes: payload.notes ?? null,
    payment_fiscal_email: payload.paymentFiscalEmail ?? null,
    payment_terms_type: payload.paymentTermsType,
    product_relations: payload.productRelations.map(toProductApiPayload),
    purchase_notes: payload.purchaseNotes ?? null,
    status: payload.status,
    tax_id: payload.taxId ?? null,
  };
}

export function buildAdminSuppliersListPath(filters: AdminSupplierListFilters): string {
  const params = new URLSearchParams();
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  appendOptionalParam(params, "branch_id", filters.branchId);
  appendOptionalParam(params, "category", filters.category);
  appendOptionalParam(params, "product_kind", filters.productKind);
  appendOptionalParam(params, "search", filters.search?.trim());
  appendOptionalParam(params, "status", filters.status);
  appendOptionalParam(params, "warning_state", filters.warningState);
  return `/v1/admin/suppliers?${params.toString()}`;
}

export function fetchAdminSuppliers(accessToken: string, filters: AdminSupplierListFilters): Promise<AdminSupplierListResponse> {
  return requestJson<ApiSupplierListResponse>({
    accessToken,
    path: buildAdminSuppliersListPath(filters),
  }).then(mapSupplierListFromApi);
}

export function fetchAdminSupplierDetail(accessToken: string, supplierId: string): Promise<AdminSupplierDetail> {
  return requestJson<ApiSupplierDetail>({
    accessToken,
    path: `/v1/admin/suppliers/${supplierId}`,
  }).then(mapAdminSupplierDetailFromApi);
}

export function createAdminSupplier(accessToken: string, payload: AdminSupplierPayload): Promise<AdminSupplierDetail> {
  return requestJson<ApiSupplierDetail>({
    accessToken,
    body: toSupplierApiPayload(payload),
    method: "POST",
    path: "/v1/admin/suppliers",
  }).then(mapAdminSupplierDetailFromApi);
}

export function updateAdminSupplier(accessToken: string, supplierId: string, payload: AdminSupplierPayload): Promise<AdminSupplierDetail> {
  return requestJson<ApiSupplierDetail>({
    accessToken,
    body: toSupplierApiPayload(payload),
    method: "PATCH",
    path: `/v1/admin/suppliers/${supplierId}`,
  }).then(mapAdminSupplierDetailFromApi);
}

export function changeAdminSupplierStatus(
  accessToken: string,
  supplierId: string,
  payload: AdminSupplierStatusPayload,
): Promise<AdminSupplierDetail> {
  const body: ApiSupplierStatusPayload = {
    notes: payload.notes ?? null,
    status: payload.status,
  };
  return requestJson<ApiSupplierDetail>({
    accessToken,
    body,
    method: "POST",
    path: `/v1/admin/suppliers/${supplierId}/status`,
  }).then(mapAdminSupplierDetailFromApi);
}

export function addAdminSupplierContact(
  accessToken: string,
  supplierId: string,
  payload: AdminSupplierContactPayload,
): Promise<AdminSupplierDetail> {
  return requestJson<ApiSupplierDetail>({
    accessToken,
    body: toContactApiPayload(payload),
    method: "POST",
    path: `/v1/admin/suppliers/${supplierId}/contacts`,
  }).then(mapAdminSupplierDetailFromApi);
}

export function addAdminSupplierProduct(
  accessToken: string,
  supplierId: string,
  payload: AdminSupplierProductPayload,
): Promise<AdminSupplierDetail> {
  return requestJson<ApiSupplierDetail>({
    accessToken,
    body: toProductApiPayload(payload),
    method: "POST",
    path: `/v1/admin/suppliers/${supplierId}/products`,
  }).then(mapAdminSupplierDetailFromApi);
}
