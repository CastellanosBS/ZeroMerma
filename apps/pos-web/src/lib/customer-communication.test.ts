import { describe, expect, it } from "vitest";

import {
  getCustomerCommunicationActionState,
  getCustomerCommunicationReadinessNote,
} from "./customer-communication";

describe("customer communication readiness", () => {
  it("requires customer contact before enabling order-ready notifications", () => {
    const actionState = getCustomerCommunicationActionState({
      customerPhone: "",
      intent: "orderReady",
    });

    expect(actionState.disabled).toBe(true);
    expect(actionState.label).toBe("Notificar pedido listo");
    expect(actionState.disabledReason).toContain("Captura telefono o correo del cliente");
  });

  it("keeps order-ready notifications disabled when provider infrastructure is missing", () => {
    const actionState = getCustomerCommunicationActionState({
      customerPhone: "6621001000",
      intent: "orderReady",
    });

    expect(actionState.disabled).toBe(true);
    expect(actionState.disabledReason).toContain("proveedor de email/SMS");
    expect(actionState.disabledReason).toContain("worker de entrega");
  });

  it("documents that sale tickets do not preserve customer email", () => {
    const actionState = getCustomerCommunicationActionState({
      channel: "email",
      intent: "saleTicket",
    });

    expect(actionState.disabled).toBe(true);
    expect(actionState.label).toBe("Enviar ticket por correo");
    expect(actionState.disabledReason).toContain("ticket no conserva correo del cliente");
  });

  it("documents that return receipts do not preserve customer phone", () => {
    const actionState = getCustomerCommunicationActionState({
      channel: "sms",
      intent: "returnReceipt",
    });

    expect(actionState.disabled).toBe(true);
    expect(actionState.label).toBe("Enviar comprobante de devolucion por SMS");
    expect(actionState.disabledReason).toContain(
      "comprobante de devolucion no conserva telefono del cliente",
    );
  });

  it("provides a shared readiness note for tickets", () => {
    expect(getCustomerCommunicationReadinessNote("saleTicket")).toContain(
      "contrato no conserva contacto del cliente",
    );
  });
});
