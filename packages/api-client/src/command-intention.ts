import { ApiError } from "./transport";
import { createIdempotencyKey } from "./uuid-v7";

export type CommandIntentionStatus = "PENDING" | "UNKNOWN" | "CONFLICT" | "CONFIRMED" | "REJECTED";
export type CommandIntentionMetadata<C> = C & {
  key: string;
  payloadDigest: string;
  status: CommandIntentionStatus;
};

const pendingStatuses = new Set<string>(["PENDING", "UNKNOWN", "CONFLICT"]);
const running = new Set<string>();

export function isCommandIntentionPending(value: { status: string } | null): boolean {
  return value !== null && pendingStatuses.has(value.status);
}

/** Coordinates one durable identity per scope; economic bodies live only in memory. */
export function createCommandIntentionCoordinator<C extends object, P, R>(options: {
  storagePrefix: string;
  eventName: string;
  contextFields: readonly (keyof C & string)[];
  nullableFields?: readonly (keyof C & string)[];
  scope: (context: C) => string;
  validateContext?: (context: C) => boolean;
  send: (context: C, payload: P, key: string) => Promise<R>;
  recover: (metadata: CommandIntentionMetadata<C>) => Promise<R>;
  isRecoveredRejection?: (metadata: CommandIntentionMetadata<C>, error: unknown) => boolean;
}) {
  type Metadata = CommandIntentionMetadata<C>;
  const bodies = new Map<string, P>();
  const fields = [...options.contextFields, "key", "payloadDigest", "status"];
  const storageKey = (scope: string) => `${options.storagePrefix}${scope}`;

  function read(scope: string): Metadata | null {
    const raw = localStorage.getItem(storageKey(scope));
    if (raw === null) return null;
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== "object" || Array.isArray(value)) throw invalidMetadata();
    const record = value as Record<string, unknown>;
    if (
      Object.keys(record).length !== fields.length ||
      !fields.every((field) => {
        const item = record[field];
        return (
          (typeof item === "string" && item.length > 0) ||
          (item === null && options.nullableFields?.includes(field as keyof C & string))
        );
      })
    )
      throw invalidMetadata();
    const metadata = value as Metadata;
    if (
      options.scope(metadata) !== scope ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(metadata.key) ||
      !/^[0-9a-f]{64}$/.test(metadata.payloadDigest) ||
      ![...pendingStatuses, "CONFIRMED", "REJECTED"].includes(metadata.status) ||
      options.validateContext?.(metadata) === false
    )
      throw invalidMetadata();
    return metadata;
  }

  function invalidMetadata() {
    return new Error(
      "Los datos de recuperación no son válidos. Conserva la referencia y solicita revisión.",
    );
  }

  function write(metadata: Metadata) {
    // Persist only the explicit metadata allowlist, never payloads or responses.
    const record = Object.fromEntries(
      fields.map((field) => [field, (metadata as Record<string, unknown>)[field]]),
    );
    localStorage.setItem(storageKey(options.scope(metadata)), JSON.stringify(record));
    window.dispatchEvent(new Event(options.eventName));
  }

  async function claim<T>(scope: string, action: () => Promise<T>): Promise<T> {
    const key = storageKey(scope);
    if (running.has(key)) throw new Error("La operación ya se está procesando.");
    if (!navigator.locks)
      throw new Error(
        "Este navegador no permite coordinar operaciones entre pestañas. Usa un navegador compatible en una conexión segura.",
      );
    running.add(key);
    try {
      return await navigator.locks.request(key, { ifAvailable: true }, async (lock) => {
        if (!lock)
          throw new Error(
            "Otra pestaña está resolviendo la operación. Recupera el resultado antes de continuar.",
          );
        return action();
      });
    } finally {
      running.delete(key);
    }
  }

  async function digest(payload: P): Promise<string> {
    const hash = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(JSON.stringify(payload)),
    );
    return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  function recordError(
    metadata: Metadata,
    error: unknown,
    firstKnownSend: boolean,
    recoveredRejection = false,
  ) {
    const code = error instanceof ApiError ? error.error?.code : null;
    const rejected =
      recoveredRejection ||
      (firstKnownSend &&
        error instanceof ApiError &&
        error.error !== null &&
        [400, 404, 409, 422].includes(error.statusCode) &&
        !code?.startsWith("IDEMPOTENCY_"));
    write({
      ...metadata,
      status: code === "IDEMPOTENCY_KEY_REUSED" ? "CONFLICT" : rejected ? "REJECTED" : "UNKNOWN",
    });
    if (rejected) bodies.delete(metadata.key);
  }

  async function send(metadata: Metadata, payload: P, firstKnownSend: boolean): Promise<R> {
    try {
      const result = await options.send(metadata, payload, metadata.key);
      write({ ...metadata, status: "CONFIRMED" });
      bodies.delete(metadata.key);
      return result;
    } catch (error) {
      recordError(metadata, error, firstKnownSend);
      throw error;
    }
  }

  function requirePending(context: C): Metadata {
    const metadata = read(options.scope(context));
    if (
      !metadata ||
      !isCommandIntentionPending(metadata) ||
      !options.contextFields.every((field) => metadata[field] === context[field])
    ) {
      throw new Error(
        "La recuperación requiere el operador, la estación y la caja originales y el mismo comando.",
      );
    }
    return metadata;
  }

  return {
    read,
    hasBody: (key: string) => bodies.has(key),
    forgetBodies: () => bodies.clear(),
    subscribe(scope: string, update: () => void) {
      const onStorage = (event: StorageEvent) => {
        if (event.key === null || event.key === storageKey(scope)) update();
      };
      window.addEventListener(options.eventName, update);
      window.addEventListener("storage", onStorage);
      return () => {
        window.removeEventListener(options.eventName, update);
        window.removeEventListener("storage", onStorage);
      };
    },
    begin(context: C, payload: P, observedKey: string | null): Promise<R> {
      return claim(options.scope(context), async () => {
        const existing = read(options.scope(context));
        if (isCommandIntentionPending(existing) || (existing?.key ?? null) !== observedKey) {
          throw new Error(
            "Hay una intención de otra pestaña. Recupera su resultado antes de continuar.",
          );
        }
        const frozen = JSON.parse(JSON.stringify(payload)) as P;
        const metadata = {
          ...context,
          key: createIdempotencyKey(),
          payloadDigest: await digest(frozen),
          status: "PENDING" as const,
        };
        bodies.set(metadata.key, frozen);
        write(metadata);
        return send(metadata, frozen, true);
      });
    },
    retry(context: C): Promise<R> {
      return claim(options.scope(context), async () => {
        const metadata = requirePending(context);
        if (metadata.status === "CONFLICT")
          throw new Error(
            "La clave está en conflicto. Conserva la referencia y solicita revisión.",
          );
        const payload = bodies.get(metadata.key);
        if (!payload || (await digest(payload)) !== metadata.payloadDigest) {
          throw new Error(
            "El contenido original ya no está disponible. Consulta el resultado; no vuelvas a cobrar.",
          );
        }
        write({ ...metadata, status: "PENDING" });
        return send(metadata, payload, false);
      });
    },
    recover(context: C): Promise<R> {
      return claim(options.scope(context), async () => {
        const metadata = requirePending(context);
        try {
          const result = await options.recover(metadata);
          write({ ...metadata, status: "CONFIRMED" });
          bodies.delete(metadata.key);
          return result;
        } catch (error) {
          recordError(
            metadata,
            error,
            false,
            options.isRecoveredRejection?.(metadata, error) === true,
          );
          throw error;
        }
      });
    },
  };
}
