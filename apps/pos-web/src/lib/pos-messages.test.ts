import { describe, expect, it } from "vitest";

import {
  createOperationResultMessage,
  createToastAction,
  posMessageCatalog,
} from "./pos-messages";

describe("POS message catalog", () => {
  it("builds operation result messages with canonical defaults", () => {
    const message = createOperationResultMessage({
      nextActions: [createToastAction("print")],
      operationType: "sale",
      referenceId: "VTA-001",
    });

    expect(message.successTitle).toBe("Venta registrada");
    expect(message.referenceLabel).toBe("Folio");
    expect(message.nextActions?.[0]?.label).toBe("Imprimir");
  });

  it("provides compact validation copy helpers", () => {
    expect(posMessageCatalog.validation.minimumOneLine()).toBe(
      "Agrega al menos una linea para continuar.",
    );
    expect(posMessageCatalog.validation.selectOriginAndReason()).toBe(
      "Selecciona origen y motivo para habilitar productos.",
    );
    expect(posMessageCatalog.validation.amountShortfall("$45.00")).toBe(
      "Faltan $45.00. Captura un monto suficiente.",
    );
  });
});
