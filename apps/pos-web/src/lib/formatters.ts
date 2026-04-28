export function formatCurrency(amount: number | string): string {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    currencyDisplay: "narrowSymbol",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(amount));
}

export function formatLocalDateTime(dateTime: string, timeZone: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone,
  }).format(new Date(dateTime));
}

export function formatCompactLocalDateTime(dateTime: string, timeZone: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    month: "short",
    timeZone,
  }).format(new Date(dateTime));
}

export function formatRecordReference(reference: string | null | undefined, fallback = "Sin folio"): string {
  const normalizedReference = reference?.trim();
  return normalizedReference && normalizedReference.length > 0 ? normalizedReference : fallback;
}

export function formatRecordStatus(status: string | null | undefined, fallback = "Sin estado"): string {
  const normalizedStatus = status?.trim();
  if (!normalizedStatus) {
    return fallback;
  }

  return normalizedStatus
    .toLowerCase()
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}
