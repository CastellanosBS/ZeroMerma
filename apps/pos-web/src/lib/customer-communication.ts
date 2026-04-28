export type CustomerCommunicationIntent = "orderReady" | "returnReceipt" | "saleTicket";
export type CustomerCommunicationChannel = "email" | "sms";

export interface CustomerCommunicationActionState {
  disabled: boolean;
  disabledReason: string;
  helperText: string;
  label: string;
}

const CUSTOMER_COMMUNICATION_PROVIDER_READY = false;
const CUSTOMER_COMMUNICATION_WORKER_READY = false;

function getChannelLabel(channel: CustomerCommunicationChannel): string {
  return channel === "email" ? "correo" : "SMS";
}

function getDocumentLabel(intent: Exclude<CustomerCommunicationIntent, "orderReady">): string {
  return intent === "saleTicket" ? "ticket" : "comprobante de devolucion";
}

function getProviderGapReason(channel: CustomerCommunicationChannel | null): string {
  if (channel === null) {
    return "La notificacion al cliente requiere un proveedor de email/SMS y un worker de entrega canonico, aun no implementados.";
  }

  return `El envio por ${getChannelLabel(channel)} requiere un proveedor configurado y un worker de entrega canonico, aun no implementados.`;
}

function getContactGapReason(
  intent: CustomerCommunicationIntent,
  channel: CustomerCommunicationChannel | null,
): string {
  if (intent === "orderReady") {
    return "Captura telefono o correo del cliente para habilitar el aviso de pedido listo.";
  }

  if (channel === "email") {
    return `El ${getDocumentLabel(intent)} no conserva correo del cliente en el contrato actual.`;
  }

  return `El ${getDocumentLabel(intent)} no conserva telefono del cliente en el contrato actual.`;
}

export function getCustomerCommunicationReadinessNote(
  intent: CustomerCommunicationIntent,
): string {
  switch (intent) {
    case "orderReady":
      return "Avisos al cliente pendientes: no hay proveedor de email/SMS ni worker de entrega canonico.";
    case "saleTicket":
      return "Envio de tickets pendiente: falta proveedor de entrega y el contrato no conserva contacto del cliente.";
    case "returnReceipt":
      return "Envio de comprobantes pendiente: falta proveedor de entrega y el contrato no conserva contacto del cliente.";
    default:
      return "La comunicacion con clientes sigue pendiente de integracion canonica.";
  }
}

export function getCustomerCommunicationActionState({
  customerEmail,
  customerPhone,
  intent,
  channel = null,
}: {
  customerEmail?: string | null;
  customerPhone?: string | null;
  intent: CustomerCommunicationIntent;
  channel?: CustomerCommunicationChannel | null;
}): CustomerCommunicationActionState {
  const normalizedEmail = customerEmail?.trim() ?? "";
  const normalizedPhone = customerPhone?.trim() ?? "";
  const label =
    intent === "orderReady"
      ? "Notificar pedido listo"
      : channel === "email"
        ? `Enviar ${getDocumentLabel(intent)} por correo`
        : `Enviar ${getDocumentLabel(intent)} por SMS`;

  const hasRequiredContact =
    intent === "orderReady"
      ? normalizedEmail.length > 0 || normalizedPhone.length > 0
      : channel === "email"
        ? normalizedEmail.length > 0
        : normalizedPhone.length > 0;

  const disabledReason = !hasRequiredContact
    ? getContactGapReason(intent, channel)
    : !CUSTOMER_COMMUNICATION_PROVIDER_READY || !CUSTOMER_COMMUNICATION_WORKER_READY
      ? getProviderGapReason(channel)
      : "";

  return {
    disabled: disabledReason.length > 0,
    disabledReason,
    helperText: getCustomerCommunicationReadinessNote(intent),
    label,
  };
}
