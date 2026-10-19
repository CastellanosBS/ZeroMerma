export function formatOrderPaymentType(value: string): string {
  const labels: Record<string, string> = {
    ADVANCE: "Anticipo",
    SETTLEMENT: "Liquidación",
    REFUND: "Reembolso",
    TECHNICAL_REVERSAL: "Compensación técnica",
  };
  return labels[value] ?? value;
}

export const recordedCardExplanation =
  "Tarjeta registrada externamente: no afecta el efectivo de caja ni confirma una captura del proveedor.";
