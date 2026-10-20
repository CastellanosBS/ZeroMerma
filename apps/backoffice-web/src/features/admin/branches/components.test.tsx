// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AdminBranchDetailPanel } from "./components/AdminBranchDetailPanel";
import { AdminBranchFormPanel } from "./components/AdminBranchFormPanel";
import type { AdminBranchDetail } from "./types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const detail: AdminBranchDetail = {
  overview: {
    id: "branch-1", brandId: "brand-1", brandName: "Synthetic Brand", code: "NEW-BRANCH",
    name: "Sucursal nueva", status: "active", readiness: "warning", timezone: "America/Hermosillo",
  },
  locationContact: {
    receiptCommercialName: "Merenna", receiptBusinessDescriptor: "Panadería y repostería",
    addressLine: "Plaza Distrito H, Boulevard Juan Navarrete 492K", city: "Hermosillo",
    state: "Sonora", postalCode: "83249", country: "Mexico",
  },
  operationalConfig: {
    inventoryScopeReady: false, isActive: true, posReady: false,
    productionScopeReady: false, timezone: "America/Hermosillo",
  },
  availableActions: {
    canActivate: false, canDeactivate: true, canEdit: true, canOpenUsers: true, canOpenWorkstations: true,
  },
  relatedOperationsSummary: { openCashSessions: 0 },
  userAssignmentsSummary: { active: 0, inactive: 0, items: [], total: 0 },
  workstationsSummary: { active: 0, inactive: 0, items: [], total: 0 },
  warnings: [],
};

function inputByLabel(container: HTMLElement, text: string): HTMLInputElement {
  const label = [...container.querySelectorAll("label")].find((node) => node.textContent?.trim() === text);
  const input = label?.querySelector("input");
  if (!input) throw new Error(`Missing input: ${text}`);
  return input;
}

describe("branch commercial receipt settings", () => {
  it("leaves the commercial identity blank for a new branch", () => {
    const container = document.createElement("div");
    container.innerHTML = renderToStaticMarkup(<AdminBranchFormPanel
      brandOptions={[{ id: "brand-1", label: "Synthetic Brand" }]}
      onClose={vi.fn()} onSubmit={vi.fn()}
    />);
    expect(inputByLabel(container, "Nombre comercial").value).toBe("");
    expect(inputByLabel(container, "Descripción del negocio").value).toBe("");
    expect(container.textContent).not.toContain("Merenna");
    expect(container.textContent).toContain("Los ya emitidos conservan su encabezado original");
  });

  it("loads, edits and clears commercial identity independently of the branch name", () => {
    const container = document.createElement("div"); document.body.append(container);
    const root = createRoot(container);
    const submit = vi.fn();
    try {
      act(() => root.render(<AdminBranchFormPanel branchDetail={detail}
        brandOptions={[{ id: "brand-1", label: "Synthetic Brand" }]}
        onClose={vi.fn()} onSubmit={submit}
      />));
      const commercial = inputByLabel(container, "Nombre comercial");
      const descriptor = inputByLabel(container, "Descripción del negocio");
      expect(commercial.value).toBe("Merenna");
      expect(descriptor.value).toBe("Panadería y repostería");
      expect(commercial.maxLength).toBe(160);
      act(() => {
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
        setter.call(commercial, "  Merenna  ");
        commercial.dispatchEvent(new Event("input", { bubbles: true }));
        setter.call(descriptor, "   ");
        descriptor.dispatchEvent(new Event("input", { bubbles: true }));
      });
      act(() => container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
      expect(submit).toHaveBeenCalledWith(expect.objectContaining({
        name: "Sucursal nueva", receiptCommercialName: "Merenna", receiptBusinessDescriptor: null,
        addressLine: "Plaza Distrito H, Boulevard Juan Navarrete 492K", postalCode: "83249",
      }));
    } finally { act(() => root.unmount()); container.remove(); }
  });

  it("shows the configured commercial identity and postal code separately from fiscal identity", () => {
    const markup = renderToStaticMarkup(<AdminBranchDetailPanel
      branchDetail={detail} onEdit={vi.fn()} onToggleStatus={vi.fn()}
    />);
    const container = document.createElement("div"); container.innerHTML = markup;
    expect(container.textContent).toContain("Merenna");
    expect(container.textContent).toContain("Panadería y repostería");
    expect(container.textContent).toContain("83249");
    expect(container.textContent).toContain("La identidad fiscal se configura por separado");
  });
});
