import { withCapabilities } from "../../../test-support/authorization";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminSupplierDetailPanel } from "./components/AdminSupplierDetailPanel";
import { AdminSupplierFormPanel } from "./components/AdminSupplierFormPanel";
import { AdminSuppliersFilters } from "./components/AdminSuppliersFilters";
import { AdminSuppliersTable } from "./components/AdminSuppliersTable";
import { AdminSuppliersPage } from "./pages/AdminSuppliersPage";
import type {
  AdminSupplierDetail,
  AdminSupplierFilterOptions,
  AdminSupplierListFilters,
  AdminSupplierListItem,
} from "./types";

const filterOptions: AdminSupplierFilterOptions = {
  branches: [{ id: "branch-1", label: "Centro - MAIN" }],
  categories: [{ id: "RAW_MATERIALS", label: "Materia prima" }],
  productKinds: [{ id: "RAW_MATERIAL", label: "Materia prima" }],
  products: [{ id: "product-1", label: "Harina 1 kg - HARINA-1KG" }],
  statuses: [
    { id: "ACTIVE", label: "Activo" },
    { id: "BLOCKED", label: "Bloqueado" },
  ],
  warningStates: [{ id: "with_warnings", label: "Con advertencias" }],
};

const filters: AdminSupplierListFilters = {
  category: "all",
  page: 1,
  pageSize: 25,
  productKind: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const supplier: AdminSupplierListItem = {
  branchCount: 1,
  category: "RAW_MATERIALS",
  code: "SUP-HARINA",
  commercialName: "Harinas del Centro",
  id: "supplier-1",
  legalName: "Harinas del Centro SA de CV",
  primaryContactEmail: "compras@harinas.example",
  primaryContactName: "Ana Lopez",
  primaryContactPhone: "555-0101",
  productCount: 1,
  status: "ACTIVE",
  taxId: "HCE010101AA1",
  termsSummary: "Credito 15 dias",
  updatedAt: "2026-05-20T10:00:00Z",
  warningState: "warning",
  warnings: [
    { code: "missing_branch", message: "Proveedor sin sucursales asociadas.", severity: "warning" },
  ],
};

const supplierDetail: AdminSupplierDetail = {
  availableActions: {
    canAddContact: true,
    canAddProduct: true,
    canBlock: true,
    canDeactivate: true,
    canEdit: true,
  },
  branchApplicability: [
    {
      branchCode: "MAIN",
      branchId: "branch-1",
      branchName: "Centro",
      branchStatus: "ACTIVE",
      deliveryNotes: "Lunes",
      isActive: true,
    },
  ],
  commercialTerms: {
    creditDays: 15,
    defaultCurrency: "MXN",
    deliveryNotes: "Entrega matutina",
    leadTimeDays: 2,
    minimumOrderAmount: "500.00",
    paymentTermsType: "CREDIT",
    purchaseNotes: "Confirmar un dia antes",
    summary: "Credito 15 dias",
  },
  contacts: [
    {
      email: "compras@harinas.example",
      id: "contact-1",
      isActive: true,
      isPrimary: true,
      name: "Ana Lopez",
      notes: null,
      phone: "555-0101",
      role: "Ventas",
      whatsapp: null,
    },
  ],
  fiscalLegal: {
    fiscalAddress: "Calle Central 123",
    fiscalRegime: null,
    legalName: "Harinas del Centro SA de CV",
    notes: "Proveedor prioritario",
    paymentFiscalEmail: "facturas@harinas.example",
    taxId: "HCE010101AA1",
  },
  operationalActivity: {
    integrationAvailable: false,
    notes:
      "Purchase orders, receipts, invoices and supplier payments are pending canonical backend modules.",
    openPurchaseOrders: null,
    recentPurchaseOrders: null,
  },
  overview: {
    category: "RAW_MATERIALS",
    code: "SUP-HARINA",
    commercialName: "Harinas del Centro",
    createdAt: "2026-05-20T09:00:00Z",
    id: "supplier-1",
    legalName: "Harinas del Centro SA de CV",
    readinessState: "warning",
    status: "ACTIVE",
    taxId: "HCE010101AA1",
    updatedAt: "2026-05-20T10:00:00Z",
  },
  productAssociations: [
    {
      currency: "MXN",
      id: "supplier-product-1",
      isActive: true,
      lastKnownPrice: "18.50",
      leadTimeDays: 2,
      minimumOrderQty: "25.000",
      notes: null,
      productCode: "HARINA-1KG",
      productId: "product-1",
      productKind: "RAW_MATERIAL",
      productName: "Harina 1 kg",
      purchaseUom: "KG",
      supplierSku: "H-1KG",
    },
  ],
  relatedDocuments: [],
  warnings: [
    { code: "missing_branch", message: "Proveedor sin sucursales asociadas.", severity: "warning" },
  ],
};

function render(element: ReactElement) {
  return renderToString(withCapabilities(element, ["suppliers.manage"]));
}

describe("admin suppliers UI components", () => {
  it("renders the supplier page shell", () => {
    const queryClient = new QueryClient();

    const html = render(
      <QueryClientProvider client={queryClient}>
        <AdminSuppliersPage />
      </QueryClientProvider>,
    );

    expect(html).toContain("Proveedores");
    expect(html).toContain("Nuevo proveedor");
    expect(html).toContain(
      "Selecciona un proveedor para revisar contactos, condiciones comerciales y productos asociados.",
    );
  });

  it("renders compact supplier filter toolbar", () => {
    const html = render(
      <AdminSuppliersFilters
        filters={filters}
        isBackendConnected={true}
        options={filterOptions}
        onChange={() => undefined}
      />,
    );

    expect(html).toContain("Proveedor, comercial, RFC, contacto, producto");
    expect(html).toContain("Filtros");
    expect(html).toContain("API conectada");
    expect(html).not.toContain("Tipo surtido");
  });

  it("renders empty and populated supplier table states with status actions", () => {
    const emptyHtml = render(
      <AdminSuppliersTable
        backendContract={{
          contactEndpoint: "POST /v1/admin/suppliers/{supplier_id}/contacts",
          createEndpoint: "POST /v1/admin/suppliers",
          detailEndpoint: "GET /v1/admin/suppliers/{supplier_id}",
          listEndpoint: "GET /v1/admin/suppliers",
          productEndpoint: "POST /v1/admin/suppliers/{supplier_id}/products",
          statusEndpoint: "POST /v1/admin/suppliers/{supplier_id}/status",
          updateEndpoint: "PATCH /v1/admin/suppliers/{supplier_id}",
        }}
        isLoading={false}
        page={1}
        pageSize={25}
        suppliers={[]}
        total={0}
        onChangeStatus={() => undefined}
        onOpenProducts={() => undefined}
        onPageChange={() => undefined}
        onSelectSupplier={() => undefined}
      />,
    );
    expect(emptyHtml).toContain(
      "No hay proveedores registrados. Crea el primer proveedor para iniciar la gestion de compras.",
    );

    const tableHtml = render(
      <AdminSuppliersTable
        backendContract={{
          contactEndpoint: "POST /v1/admin/suppliers/{supplier_id}/contacts",
          createEndpoint: "POST /v1/admin/suppliers",
          detailEndpoint: "GET /v1/admin/suppliers/{supplier_id}",
          listEndpoint: "GET /v1/admin/suppliers",
          productEndpoint: "POST /v1/admin/suppliers/{supplier_id}/products",
          statusEndpoint: "POST /v1/admin/suppliers/{supplier_id}/status",
          updateEndpoint: "PATCH /v1/admin/suppliers/{supplier_id}",
        }}
        isLoading={false}
        page={1}
        pageSize={25}
        suppliers={[supplier]}
        total={1}
        onChangeStatus={() => undefined}
        onOpenProducts={() => undefined}
        onPageChange={() => undefined}
        onSelectSupplier={() => undefined}
      />,
    );

    expect(tableHtml).toContain("Nombre / razon social");
    expect(tableHtml).toContain("Harinas del Centro SA de CV");
    expect(tableHtml).toContain("Desactivar");
    expect(tableHtml).toContain("Bloquear");
  });

  it("renders detail sections, warnings and related empty state", () => {
    const detailHtml = render(
      <AdminSupplierDetailPanel
        isLoading={false}
        supplierDetail={supplierDetail}
        supplierPreview={supplier}
        onOpenBranch={() => undefined}
        onOpenProduct={() => undefined}
      />,
    );

    expect(detailHtml).toContain("Fiscal / legal");
    expect(detailHtml).toContain("Contactos");
    expect(detailHtml).toContain("Condiciones comerciales");
    expect(detailHtml).toContain("Productos surtidos");
    expect(detailHtml).toContain("Sucursales aplicables");
    expect(detailHtml).toContain("Advertencias");
    expect(detailHtml).toContain("Este proveedor no tiene documentos relacionados.");
  });

  it("renders create and edit supplier forms with validation surface and associations", () => {
    const createHtml = render(
      <AdminSupplierFormPanel
        branchOptions={filterOptions.branches}
        categoryOptions={filterOptions.categories}
        errorMessage="El nombre o razon social es requerido."
        isSubmitting={false}
        productOptions={filterOptions.products}
        statusOptions={filterOptions.statuses}
        onClose={() => undefined}
        onSubmit={() => undefined}
      />,
    );

    expect(createHtml).toContain("Nuevo proveedor");
    expect(createHtml).toContain("Datos maestros y preparacion de compras");
    expect(createHtml).toContain("Productos surtidos");
    expect(createHtml).toContain("Sucursales aplicables");
    expect(createHtml).toContain("El nombre o razon social es requerido.");

    const editHtml = render(
      <AdminSupplierFormPanel
        branchOptions={filterOptions.branches}
        categoryOptions={filterOptions.categories}
        initialSupplier={supplierDetail}
        isSubmitting={false}
        productOptions={filterOptions.products}
        statusOptions={filterOptions.statuses}
        onClose={() => undefined}
        onSubmit={() => undefined}
      />,
    );

    expect(editHtml).toContain("Editar proveedor");
    expect(editHtml).toContain("Harinas del Centro SA de CV");
    expect(editHtml).toContain("Ana Lopez");
  });
});
