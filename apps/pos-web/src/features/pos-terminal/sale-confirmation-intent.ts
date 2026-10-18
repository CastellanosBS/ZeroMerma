import { ApiError, createIdempotencyKey } from "@zeromerma/api-client";
import type { ConfirmSaleRequest, SaleConfirmationView } from "../../lib/api-contracts";
import { confirmPosSale, getSaleConfirmation } from "./pos-terminal-api";

export interface SaleIntentionContext {
  userId: string;
  branchId: string;
  workstationId: string;
  workstationCode: string;
  cashSessionId: string;
}

export interface SaleIntentionMetadata extends SaleIntentionContext {
  key: string;
  payloadDigest: string;
  status: "PENDING" | "UNKNOWN" | "CONFLICT" | "CONFIRMED" | "REJECTED";
}

export const SALE_INTENTION_EVENT = "zeromerma-sale-intention";
export const SALE_INTENTION_STORAGE_PREFIX = "zeromerma-sale-intention:";
const bodies = new Map<string, ConfirmSaleRequest>();
const running = new Set<string>();
const pendingStatuses = new Set(["PENDING", "UNKNOWN", "CONFLICT"]);
const fields = [
  "userId",
  "branchId",
  "workstationId",
  "workstationCode",
  "cashSessionId",
  "key",
  "payloadDigest",
  "status",
] as const;

function storageKey(workstationId: string): string {
  return `${SALE_INTENTION_STORAGE_PREFIX}${workstationId}`;
}

export function readSaleIntention(workstationId: string): SaleIntentionMetadata | null {
  const raw = localStorage.getItem(storageKey(workstationId));
  if (raw === null) return null;
  const value: unknown = JSON.parse(raw);
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.keys(value).length !== fields.length ||
    !fields.every(
      (field) => field in value && typeof (value as Record<string, unknown>)[field] === "string",
    ) ||
    !("status" in value) ||
    ![...pendingStatuses, "CONFIRMED", "REJECTED"].includes(String(value.status))
  ) {
    throw new Error(
      "Los datos de recuperación no son válidos. No inicies otro cobro en esta estación.",
    );
  }
  const metadata = value as SaleIntentionMetadata;
  if (
    metadata.workstationId !== workstationId ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(metadata.key) ||
    !/^[0-9a-f]{64}$/.test(metadata.payloadDigest) ||
    !fields.every((field) => metadata[field].length > 0)
  ) {
    throw new Error(
      "Los datos de recuperación no son válidos. Conserva la referencia y solicita revisión.",
    );
  }
  return metadata;
}

export function isSaleIntentionPending(value: SaleIntentionMetadata | null): boolean {
  return value !== null && pendingStatuses.has(value.status);
}

export function hasSaleIntentionBody(key: string): boolean {
  return bodies.has(key);
}

export function forgetSaleIntentionBodies(): void {
  bodies.clear();
}

function writeMetadata(value: SaleIntentionMetadata): void {
  // Economic payloads, API responses, credentials and personal details never enter storage.
  localStorage.setItem(storageKey(value.workstationId), JSON.stringify(value));
  window.dispatchEvent(new Event(SALE_INTENTION_EVENT));
}

function sameContext(left: SaleIntentionContext, right: SaleIntentionContext): boolean {
  return (
    left.userId === right.userId &&
    left.branchId === right.branchId &&
    left.workstationId === right.workstationId &&
    left.workstationCode === right.workstationCode &&
    left.cashSessionId === right.cashSessionId
  );
}

async function withClaim<T>(workstationId: string, action: () => Promise<T>): Promise<T> {
  if (running.has(workstationId)) throw new Error("La venta ya se está procesando.");
  if (!navigator.locks)
    throw new Error(
      "Este navegador no permite coordinar el cobro entre pestañas. Usa un navegador compatible en una conexión segura.",
    );
  running.add(workstationId);
  try {
    return await navigator.locks.request(
      storageKey(workstationId),
      { ifAvailable: true },
      async (lock) => {
        if (!lock)
          throw new Error(
            "Otra pestaña está resolviendo la venta. Recupera el resultado antes de cobrar.",
          );
        return action();
      },
    );
  } finally {
    running.delete(workstationId);
  }
}

async function digest(payload: ConfirmSaleRequest): Promise<string> {
  const hash = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(JSON.stringify(payload)),
  );
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function recordError(
  metadata: SaleIntentionMetadata,
  error: unknown,
  firstKnownSend: boolean,
): void {
  const code = error instanceof ApiError ? error.error?.code : null;
  const rejected =
    firstKnownSend &&
    error instanceof ApiError &&
    error.error !== null &&
    [400, 404, 409, 422].includes(error.statusCode) &&
    !code?.startsWith("IDEMPOTENCY_");
  writeMetadata({
    ...metadata,
    status: code === "IDEMPOTENCY_KEY_REUSED" ? "CONFLICT" : rejected ? "REJECTED" : "UNKNOWN",
  });
  if (rejected) bodies.delete(metadata.key);
}

async function send(
  metadata: SaleIntentionMetadata,
  payload: ConfirmSaleRequest,
  firstKnownSend: boolean,
): Promise<SaleConfirmationView> {
  try {
    const sale = await confirmPosSale(payload, metadata.key);
    writeMetadata({ ...metadata, status: "CONFIRMED" });
    bodies.delete(metadata.key);
    return sale;
  } catch (error) {
    recordError(metadata, error, firstKnownSend);
    throw error;
  }
}

export function beginSaleConfirmation(
  context: SaleIntentionContext,
  payload: ConfirmSaleRequest,
  observedKey: string | null,
): Promise<SaleConfirmationView> {
  return withClaim(context.workstationId, async () => {
    const existing = readSaleIntention(context.workstationId);
    if (isSaleIntentionPending(existing) || (existing?.key ?? null) !== observedKey) {
      throw new Error(
        "Hay una intención de venta de otra pestaña. Recupera su resultado antes de cobrar.",
      );
    }
    const frozen = JSON.parse(JSON.stringify(payload)) as ConfirmSaleRequest;
    const metadata: SaleIntentionMetadata = {
      ...context,
      key: createIdempotencyKey(),
      payloadDigest: await digest(frozen),
      status: "PENDING",
    };
    bodies.set(metadata.key, frozen);
    writeMetadata(metadata);
    return send(metadata, frozen, true);
  });
}

function requirePending(context: SaleIntentionContext): SaleIntentionMetadata {
  const metadata = readSaleIntention(context.workstationId);
  if (!metadata || !isSaleIntentionPending(metadata) || !sameContext(context, metadata)) {
    throw new Error("La recuperación requiere el operador, la estación y la caja originales.");
  }
  return metadata;
}

export function retrySaleConfirmation(
  context: SaleIntentionContext,
): Promise<SaleConfirmationView> {
  return withClaim(context.workstationId, async () => {
    const metadata = requirePending(context);
    if (metadata.status === "CONFLICT")
      throw new Error("La clave está en conflicto. Conserva la referencia y solicita revisión.");
    const payload = bodies.get(metadata.key);
    if (!payload || (await digest(payload)) !== metadata.payloadDigest) {
      throw new Error(
        "El contenido original ya no está disponible. Consulta el resultado; no vuelvas a cobrar.",
      );
    }
    writeMetadata({ ...metadata, status: "PENDING" });
    return send(metadata, payload, false);
  });
}

export function recoverSaleConfirmation(
  context: SaleIntentionContext,
): Promise<SaleConfirmationView> {
  return withClaim(context.workstationId, async () => {
    const metadata = requirePending(context);
    try {
      const sale = await getSaleConfirmation(
        metadata.key,
        metadata.workstationCode,
        metadata.cashSessionId,
      );
      writeMetadata({ ...metadata, status: "CONFIRMED" });
      bodies.delete(metadata.key);
      return sale;
    } catch (error) {
      recordError(metadata, error, false);
      throw error;
    }
  });
}
