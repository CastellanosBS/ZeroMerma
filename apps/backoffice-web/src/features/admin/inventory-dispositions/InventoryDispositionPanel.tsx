import { isCommandIntentionPending, type components } from "@zeromerma/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { hasEffectiveCapability } from "../../auth/authorization";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
import {
  dispositionIntentions,
  type InventoryDispositionRequest,
} from "./disposition-command-intent";
import { useDispositionDraftIdentity, useDispositionIntention } from "./use-disposition-intention";

export function InventoryDispositionPanel({
  branchId,
  productId,
  kind,
  returnAllocationId = null,
  lots = [],
  availableQuantity,
  originalDisposition,
}: {
  branchId: string;
  productId: string;
  kind: InventoryDispositionRequest["kind"];
  returnAllocationId?: string | null;
  lots?: components["schemas"]["AdminInventoryLotView"][];
  availableQuantity: string;
  originalDisposition?: components["schemas"]["ReturnDispositionAllocationView"]["disposition_code"];
}) {
  const user = useBackofficeAuthStore((state) => state.user);
  const queries = useQueryClient();
  const intention = useDispositionIntention();
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState("");
  const [destination, setDestination] = useState<InventoryDispositionRequest["destination"]>(
    kind === "RETURN_CORRECTION"
      ? originalDisposition === "QUARANTINE"
        ? "WASTE"
        : "QUARANTINE"
      : "BACKROOM",
  );
  const [lotId, setLotId] = useState("");
  const [inspected, setInspected] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const clear = useCallback(() => {
    setQuantity("");
    setReason("");
    setLotId("");
    setInspected(false);
  }, []);
  const observed = useDispositionDraftIdentity(intention.metadata, clear);
  const canExecute = hasEffectiveCapability(
    user,
    kind === "RETURN_CORRECTION" ? "returns_corrections.manage" : "inventory.adjust",
    [branchId],
  );
  const requiresInspection = kind === "QUARANTINE_RELEASE" && destination !== "WASTE";
  const mutation = useMutation({
    mutationFn: async () => {
      if (!user || !canExecute || intention.error)
        throw new Error("Se requiere autorizacion sobre esta sucursal.");
      if (
        !/^\d+(\.\d{1,3})?$/.test(quantity) ||
        Number(quantity) <= 0 ||
        Number(quantity) > Number(availableQuantity)
      )
        throw new Error("Captura una cantidad positiva dentro del saldo disponible.");
      if (reason.trim().length < 3) throw new Error("Escribe el motivo de la disposicion.");
      if (requiresInspection && !inspected)
        throw new Error("Confirma la inspeccion antes de liberar el producto.");
      if (kind === "QUARANTINE_RELEASE" && lots.length && !lotId)
        throw new Error("Selecciona el lote fisico.");
      return dispositionIntentions.begin(
        {
          userId: user.id,
          branchId,
          productId,
          kind,
          returnAllocationId,
          lotId: kind === "QUARANTINE_RELEASE" ? lotId || null : null,
        },
        {
          branch_id: branchId,
          product_id: productId,
          kind,
          quantity,
          destination,
          return_allocation_id: returnAllocationId,
          lot_id: kind === "QUARANTINE_RELEASE" ? lotId || null : null,
          inspection_passed: requiresInspection && inspected,
          reason: reason.trim(),
          notes: null,
        },
        observed.current ?? null,
      );
    },
    onSuccess: (result) => {
      setMessage(`Disposicion confirmada: ${result.quantity} a ${result.destination}.`);
      clear();
      void queries.invalidateQueries();
    },
    onError: (error) =>
      setMessage(error instanceof Error ? error.message : "No se pudo confirmar."),
  });
  if (!canExecute) return null;
  return (
    <details className="my-2 rounded-lg border p-2 text-xs">
      <summary className="cursor-pointer font-semibold">
        {kind === "RETURN_CORRECTION"
          ? "Corregir destino fisico de esta devolucion"
          : "Resolver producto en cuarentena"}
      </summary>
      <p>Registra el destino real del producto. Esta accion no modifica el reembolso.</p>
      <label className="grid gap-1 my-2">
        Cantidad a disponer
        <input
          className="rounded border p-2"
          inputMode="decimal"
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
        />
      </label>
      <label className="grid gap-1 my-2">
        Destino fisico
        <select
          aria-label="Destino fisico"
          className="rounded border p-2"
          value={destination}
          onChange={(event) => {
            setDestination(event.target.value as InventoryDispositionRequest["destination"]);
            setInspected(false);
          }}
        >
          {kind === "RETURN_CORRECTION" ? (
            originalDisposition !== "QUARANTINE" ? (
              <option value="QUARANTINE">Cuarentena</option>
            ) : null
          ) : (
            <>
              <option value="BACKROOM">Almacen</option>
              <option value="COUNTER">Mostrador</option>
            </>
          )}
          <option value="WASTE">Merma</option>
        </select>
      </label>
      {kind === "QUARANTINE_RELEASE" && lots.length ? (
        <label className="grid gap-1 my-2">
          Lote fisico
          <select
            aria-label="Lote fisico"
            className="rounded border p-2"
            value={lotId}
            onChange={(event) => {
              setLotId(event.target.value);
              setInspected(false);
            }}
          >
            <option value="">Selecciona lote</option>
            {lots.map((lot) => (
              <option value={lot.id} key={lot.id}>
                {lot.lot_code} · vence {lot.expires_at ?? "sin fecha"} · disponible{" "}
                {lot.available_quantity}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {requiresInspection ? (
        <label className="flex gap-2 my-2">
          <input
            type="checkbox"
            checked={inspected}
            onChange={(event) => setInspected(event.target.checked)}
          />
          Inspeccione el producto y es apto para venta.
        </label>
      ) : null}
      <label className="grid gap-1 my-2">
        Motivo de disposicion
        <input
          className="rounded border p-2"
          maxLength={160}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </label>
      <button
        type="button"
        className="rounded bg-slate-900 px-3 py-2 text-white disabled:opacity-50"
        disabled={
          mutation.isPending ||
          Boolean(intention.error) ||
          isCommandIntentionPending(intention.metadata)
        }
        onClick={() => mutation.mutate()}
      >
        Confirmar disposicion fisica
      </button>
      {message ? <p role="status">{message}</p> : null}
    </details>
  );
}
