const RESERVED_SCANNER_TOKENS = new Set([
  "APP",
  "COM",
  "EMAIL",
  "ENVIO",
  "FOLIO",
  "HTTP",
  "HTTPS",
  "LOCAL",
  "MODE",
  "PRODUCT",
  "PRODUCTO",
  "QR",
  "RECEIPCION",
  "RECEIPT",
  "RETURN",
  "RETURNS",
  "SCAN",
  "SCANNER",
  "SHIPMENT",
  "SHIPMENTS",
  "SMS",
  "STATION",
  "TICKET",
  "TICKETS",
  "URL",
  "WWW",
]);

export function normalizeScannerText(rawValue: string): string {
  return rawValue.replace(/[\r\n\t]+/g, " ").trim().toUpperCase();
}

export function extractScannerTokens(rawValue: string): string[] {
  const normalizedValue = normalizeScannerText(rawValue);
  return normalizedValue.match(/[A-Z0-9]+(?:-[A-Z0-9]+)*/g) ?? [];
}

function findScannerToken(
  rawValue: string,
  predicate: (token: string) => boolean,
): string | null {
  const matchingToken = extractScannerTokens(rawValue).find(predicate);
  return matchingToken ?? null;
}

export function parseTicketScannerValue(rawValue: string): string | null {
  return findScannerToken(rawValue, (token) => /^TCK-[A-Z0-9-]+$/.test(token));
}

export function parseShipmentScannerValue(rawValue: string): string | null {
  return findScannerToken(rawValue, (token) => /^(ENV|REC)-[A-Z0-9-]+$/.test(token));
}

export function parseProductScannerValue(rawValue: string): string | null {
  const tokens = extractScannerTokens(rawValue).filter((token) => !RESERVED_SCANNER_TOKENS.has(token));
  return tokens.at(-1) ?? null;
}

export function matchesScannerValue(candidateValue: string, scannedValue: string): boolean {
  return normalizeScannerText(candidateValue) === normalizeScannerText(scannedValue);
}
