import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { PosConfirmationCopy } from "../lib/pos-messages";
import {
  PosBlockerPanel,
  PosConfirmationDialog,
  PosEmptyState,
  PosErrorState,
  PosInlineValidationMessage,
  PosLoadingState,
  PosOperationResultPanel,
  PosOperationResultToast,
} from "./pos-feedback";

describe("POS feedback primitives", () => {
  it("renders loading, empty, and error states with explicit markers", () => {
    const loadingMarkup = renderToStaticMarkup(
      <PosLoadingState description="Consultando datos del turno." title="Cargando modulo" />,
    );
    const emptyMarkup = renderToStaticMarkup(
      <PosEmptyState description="No hay registros para el filtro." title="Sin resultados" />,
    );
    const errorMarkup = renderToStaticMarkup(
      <PosErrorState description="No fue posible consultar la API." title="Error operativo" />,
    );

    expect(loadingMarkup).toContain('data-pos-state-panel="true"');
    expect(loadingMarkup).toContain("Cargando");
    expect(emptyMarkup).toContain("Sin datos");
    expect(errorMarkup).toContain("Atencion");
  });

  it("renders inline validation and blocker panel in a compact shared format", () => {
    const inlineMarkup = renderToStaticMarkup(
      <PosInlineValidationMessage tone="warning">
        Agrega al menos una linea para continuar.
      </PosInlineValidationMessage>,
    );
    const blockerMarkup = renderToStaticMarkup(
      <PosBlockerPanel
        blockers={[
          { key: "branch", message: "Selecciona origen y motivo para habilitar productos." },
          { key: "amount", message: "Faltan $50.00. Captura un monto suficiente.", tone: "error" },
        ]}
      />,
    );

    expect(inlineMarkup).toContain('data-pos-inline-validation="true"');
    expect(blockerMarkup).toContain('data-pos-blocker-panel="true"');
    expect(blockerMarkup).toContain("Bloqueado");
  });

  it("renders operation result toast with folio and next actions", () => {
    const markup = renderToStaticMarkup(
      <PosOperationResultToast
        message={{
          nextActions: [
            { key: "print", kind: "print", label: "Imprimir" },
            { key: "continue", kind: "continuePos", label: "Continuar POS" },
          ],
          operationType: "sale",
          referenceId: "VTA-001",
          successTitle: "Venta registrada",
        }}
      />,
    );

    expect(markup).toContain("Venta registrada");
    expect(markup).toContain("VTA-001");
    expect(markup).toContain("Imprimir");
  });

  it("renders operation result panel with explicit action hierarchy", () => {
    const markup = renderToStaticMarkup(
      <PosOperationResultPanel
        message={{
          nextActions: [
            { key: "print", kind: "print", label: "Imprimir" },
            { key: "view-ticket", kind: "viewHistory", label: "Ver ticket" },
            { key: "new-client", kind: "newOperation", label: "Nuevo cliente" },
          ],
          operationType: "sale",
          referenceId: "TCK-001",
          successTitle: "Venta registrada",
        }}
      />,
    );

    expect(markup).toContain('data-pos-operation-result-panel="true"');
    expect(markup).toContain("TCK-001");
    expect(markup).toContain("Nuevo cliente");
  });

  it("renders confirmation dialog actions and copy", () => {
    const confirmation: PosConfirmationCopy = {
      cancelLabel: "Cancelar",
      confirmLabel: "Confirmar cierre",
      description: "Esta operacion no se puede deshacer.",
      eyebrow: "Revision final",
      title: "Confirmar cierre de turno",
      tone: "danger",
    };

    const markup = renderToStaticMarkup(
      <PosConfirmationDialog
        confirmation={confirmation}
        isOpen
        onCancel={() => {}}
        onConfirm={() => {}}
      />,
    );

    expect(markup).toContain("Confirmar cierre de turno");
    expect(markup).toContain("Operacion sensible");
    expect(markup).toContain("Confirmar cierre");
  });
});
