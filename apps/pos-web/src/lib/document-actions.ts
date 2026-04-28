export type PrintableDocumentKind =
  | "branchReceiptDocument"
  | "branchShipmentDocument"
  | "cashCloseReport"
  | "correctionDocument"
  | "counterTransferReceipt"
  | "returnReceipt"
  | "saleTicket"
  | "wasteDocument";

type DocumentActionAvailability = {
  copyFolio: {
    isAvailable: boolean;
    label: string;
    unavailableReason?: string;
  };
  exportPdf: {
    isAvailable: boolean;
    label: string;
    unavailableReason?: string;
  };
  print: {
    isAvailable: boolean;
    label: string;
    unavailableReason?: string;
  };
};

export const DOCUMENT_ACTION_AVAILABILITY: Record<
  PrintableDocumentKind,
  DocumentActionAvailability
> = {
  saleTicket: {
    copyFolio: {
      isAvailable: true,
      label: "Copiar folio",
    },
    exportPdf: {
      isAvailable: false,
      label: "Exportar PDF",
      unavailableReason: "La exportacion PDF del ticket sigue pendiente de un contrato backend.",
    },
    print: {
      isAvailable: true,
      label: "Imprimir ticket",
    },
  },
  returnReceipt: {
    copyFolio: {
      isAvailable: true,
      label: "Copiar folio",
    },
    exportPdf: {
      isAvailable: false,
      label: "Exportar PDF",
      unavailableReason:
        "La exportacion PDF del comprobante de devolucion sigue pendiente de un contrato backend.",
    },
    print: {
      isAvailable: true,
      label: "Imprimir comprobante",
    },
  },
  counterTransferReceipt: {
    copyFolio: {
      isAvailable: true,
      label: "Copiar folio",
    },
    exportPdf: {
      isAvailable: false,
      label: "Exportar PDF",
      unavailableReason:
        "La exportacion PDF del comprobante de traspaso sigue pendiente de un contrato backend.",
    },
    print: {
      isAvailable: false,
      label: "Imprimir comprobante",
      unavailableReason:
        "El comprobante de traspaso sigue pendiente de implementacion en esta etapa.",
    },
  },
  branchShipmentDocument: {
    copyFolio: {
      isAvailable: true,
      label: "Copiar folio",
    },
    exportPdf: {
      isAvailable: false,
      label: "Exportar PDF",
      unavailableReason:
        "La exportacion PDF del envio sigue pendiente de un contrato backend.",
    },
    print: {
      isAvailable: false,
      label: "Imprimir comprobante",
      unavailableReason:
        "El comprobante de envio sigue pendiente de implementacion en esta etapa.",
    },
  },
  branchReceiptDocument: {
    copyFolio: {
      isAvailable: true,
      label: "Copiar folio",
    },
    exportPdf: {
      isAvailable: false,
      label: "Exportar PDF",
      unavailableReason:
        "La exportacion PDF de la recepcion sigue pendiente de un contrato backend.",
    },
    print: {
      isAvailable: false,
      label: "Imprimir comprobante",
      unavailableReason:
        "El comprobante de recepcion sigue pendiente de implementacion en esta etapa.",
    },
  },
  wasteDocument: {
    copyFolio: {
      isAvailable: true,
      label: "Copiar folio",
    },
    exportPdf: {
      isAvailable: false,
      label: "Exportar PDF",
      unavailableReason:
        "La exportacion PDF de la merma sigue pendiente de un contrato backend.",
    },
    print: {
      isAvailable: false,
      label: "Imprimir comprobante",
      unavailableReason:
        "El comprobante de merma sigue pendiente de implementacion en esta etapa.",
    },
  },
  correctionDocument: {
    copyFolio: {
      isAvailable: true,
      label: "Copiar folio",
    },
    exportPdf: {
      isAvailable: false,
      label: "Exportar PDF",
      unavailableReason:
        "La exportacion PDF del ajuste sigue pendiente de un contrato backend.",
    },
    print: {
      isAvailable: false,
      label: "Imprimir comprobante",
      unavailableReason:
        "El comprobante del ajuste sigue pendiente de implementacion en esta etapa.",
    },
  },
  cashCloseReport: {
    copyFolio: {
      isAvailable: true,
      label: "Copiar referencia",
    },
    exportPdf: {
      isAvailable: false,
      label: "Exportar PDF",
      unavailableReason:
        "La exportacion PDF del cierre sigue pendiente de un contrato backend.",
    },
    print: {
      isAvailable: false,
      label: "Imprimir reporte",
      unavailableReason:
        "El reporte imprimible del cierre sigue pendiente de un contrato backend.",
    },
  },
};

export function getDocumentActionAvailability(
  kind: PrintableDocumentKind,
): DocumentActionAvailability {
  return DOCUMENT_ACTION_AVAILABILITY[kind];
}

export async function copyDocumentReferenceToClipboard(referenceValue: string): Promise<void> {
  if (!navigator.clipboard) {
    throw new Error("clipboard-unavailable");
  }

  await navigator.clipboard.writeText(referenceValue);
}
