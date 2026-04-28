import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PosAuditSummary } from "./pos-audit-summary";

describe("PosAuditSummary", () => {
  it("renders safe audit actors, notification status, reason, and notes", () => {
    const markup = renderToStaticMarkup(
      <PosAuditSummary
        auditSummary={{
          acknowledged_at_utc: "2026-04-22T20:05:00Z",
          acknowledged_by: {
            email: "cashier@zeromerma.local",
            full_name: "Main Branch Cashier",
            user_id: "user-1",
          },
          acknowledgement_label: "Validado por",
          backoffice_notification: {
            label: "Revision de backoffice",
            occurred_at_utc: "2026-04-22T20:06:00Z",
            processed_at_utc: null,
            status: "PENDING",
          },
          confirmed_at_utc: "2026-04-22T20:04:00Z",
          confirmed_by: {
            email: "cashier@zeromerma.local",
            full_name: "Main Branch Cashier",
            user_id: "user-1",
          },
          created_at_utc: "2026-04-22T20:03:00Z",
          created_by: {
            email: "cashier@zeromerma.local",
            full_name: "Main Branch Cashier",
            user_id: "user-1",
          },
          notes: "Cliente devolvio producto dañado.",
          reason_label: "Problema de calidad",
        }}
        timeZone="America/Hermosillo"
      />,
    );

    expect(markup).toContain('data-pos-audit-summary="true"');
    expect(markup).toContain("Creado por");
    expect(markup).toContain("Confirmado por");
    expect(markup).toContain("Validado por");
    expect(markup).toContain("Revision de backoffice");
    expect(markup).toContain("Pendiente");
    expect(markup).toContain("Problema de calidad");
    expect(markup).toContain("Cliente devolvio producto dañado.");
  });
});
