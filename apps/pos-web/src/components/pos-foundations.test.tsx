import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  PosButton,
  PosCard,
  PosFieldLabel,
  PosPanel,
  PosSectionTitle,
  PosStatusBadge,
} from "./pos-foundations";
import { CheckCircleIcon } from "./pos-icons";

describe("POS foundations", () => {
  it("renders PosButton with explicit POS button marker and icon-label structure", () => {
    const markup = renderToStaticMarkup(
      <PosButton leadingIcon={<CheckCircleIcon className="h-4 w-4" />} variant="primary">
        Confirmar
      </PosButton>,
    );

    expect(markup).toContain('data-pos-button="true"');
    expect(markup).toContain("Confirmar");
    expect(markup).toContain("pos-button-icon-label");
  });

  it("renders PosStatusBadge with explicit status semantics", () => {
    const markup = renderToStaticMarkup(
      <PosStatusBadge status="pending">Pendiente</PosStatusBadge>,
    );

    expect(markup).toContain('data-pos-status-badge="true"');
    expect(markup).toContain('data-status="pending"');
    expect(markup).toContain("pos-status-badge--pending");
  });

  it("renders PosPanel and PosCard with POS foundation surface classes", () => {
    const panelMarkup = renderToStaticMarkup(<PosPanel tone="muted">Panel</PosPanel>);
    const cardMarkup = renderToStaticMarkup(<PosCard tone="success">Card</PosCard>);

    expect(panelMarkup).toContain("pos-foundation-panel");
    expect(panelMarkup).toContain('data-tone="muted"');
    expect(cardMarkup).toContain("pos-foundation-card");
    expect(cardMarkup).toContain('data-tone="success"');
  });

  it("renders PosSectionTitle and PosFieldLabel with compact hierarchy metadata", () => {
    const titleMarkup = renderToStaticMarkup(
      <PosSectionTitle
        description="Captura compacta y operativa."
        eyebrow="Cobro"
        title="Registrar pago"
      />,
    );
    const labelMarkup = renderToStaticMarkup(
      <PosFieldLabel helper="Solo monto confirmado." required>
        Monto
      </PosFieldLabel>,
    );

    expect(titleMarkup).toContain("pos-section-title__headline");
    expect(titleMarkup).toContain("Captura compacta y operativa.");
    expect(labelMarkup).toContain("pos-field-label__required");
    expect(labelMarkup).toContain("Solo monto confirmado.");
  });
});
