export type PosOperationType =
  | "cashClose"
  | "cashSession"
  | "correction"
  | "discount"
  | "order"
  | "payment"
  | "return"
  | "sale"
  | "shipmentDispatch"
  | "shipmentReceipt"
  | "ticket"
  | "waste";

export type PosToastActionKind =
  | "continuePos"
  | "newOperation"
  | "print"
  | "viewHistory";

export interface PosMessageAction {
  key: string;
  kind: PosToastActionKind;
  label: string;
}

export interface PosFieldValidationMessage {
  field: string;
  message: string;
  tone?: "error" | "info" | "warning";
}

export interface PosBlockerMessage {
  key: string;
  message: string;
  tone?: "blocked" | "error" | "warning";
}

export interface PosConfirmationCopy {
  cancelLabel: string;
  confirmLabel: string;
  description: string;
  eyebrow?: string;
  tone?: "danger" | "warning";
  title: string;
}

export interface PosOperationResultMessage {
  description?: string;
  nextActions?: PosMessageAction[];
  operationType: PosOperationType;
  referenceId?: string | null;
  referenceLabel?: string;
  successTitle: string;
}

function getDefaultOperationSuccessTitle(operationType: PosOperationType): string {
  switch (operationType) {
    case "sale":
      return "Venta registrada";
    case "shipmentDispatch":
      return "Envio registrado";
    case "shipmentReceipt":
      return "Recepcion registrada";
    case "waste":
      return "Merma registrada";
    case "correction":
      return "Correccion registrada";
    case "return":
      return "Devolucion registrada";
    case "order":
      return "Pedido registrado";
    case "payment":
      return "Pago registrado";
    case "discount":
      return "Descuento registrado";
    case "cashClose":
      return "Turno cerrado";
    case "cashSession":
      return "Caja abierta";
    case "ticket":
      return "Ticket procesado";
    default:
      return "Operacion registrada";
  }
}

function getDefaultReferenceLabel(operationType: PosOperationType): string {
  switch (operationType) {
    case "cashClose":
      return "Cierre";
    case "cashSession":
      return "Caja";
    case "ticket":
      return "Ticket";
    default:
      return "Folio";
  }
}

function getDefaultActionLabel(kind: PosToastActionKind): string {
  switch (kind) {
    case "continuePos":
      return "Continuar POS";
    case "newOperation":
      return "Nueva operacion";
    case "print":
      return "Imprimir";
    case "viewHistory":
      return "Ver historial";
    default:
      return "Continuar";
  }
}

export function createToastAction(kind: PosToastActionKind, key?: string): PosMessageAction {
  return {
    key: key ?? kind,
    kind,
    label: getDefaultActionLabel(kind),
  };
}

export function createOperationResultMessage(
  input: Omit<PosOperationResultMessage, "referenceLabel" | "successTitle"> & {
    referenceLabel?: string;
    successTitle?: string;
  },
): PosOperationResultMessage {
  return {
    ...input,
    referenceLabel: input.referenceLabel ?? getDefaultReferenceLabel(input.operationType),
    successTitle: input.successTitle ?? getDefaultOperationSuccessTitle(input.operationType),
  };
}

export const posMessageCatalog = {
  confirmation: {
    destructiveOperation: (
      title: string,
      description: string,
      confirmLabel: string,
    ): PosConfirmationCopy => ({
      cancelLabel: "Cancelar",
      confirmLabel,
      description,
      eyebrow: "Confirmacion",
      title,
      tone: "danger",
    }),
    warningOperation: (
      title: string,
      description: string,
      confirmLabel: string,
    ): PosConfirmationCopy => ({
      cancelLabel: "Cancelar",
      confirmLabel,
      description,
      eyebrow: "Revision final",
      title,
      tone: "warning",
    }),
  },
  validation: {
    amountShortfall: (amount: string) => `Faltan ${amount}. Captura un monto suficiente.`,
    minimumOneLine: () => "Agrega al menos una linea para continuar.",
    selectMethod: (operationLabel: string) =>
      `Selecciona el metodo del ${operationLabel} para continuar.`,
    selectOriginAndReason: () => "Selecciona origen y motivo para habilitar productos.",
  },
};
