import { isCommandIntentionPending } from "@zeromerma/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { hasEffectiveCapability } from "../../../auth/authorization";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { transferIntentions } from "../transfer-command-intent";
import { useTransferDraftIdentity, useTransferIntention } from "../use-transfer-intention";
import type { AdminTransferDetail, AdminTransferResolvePayload } from "../types";

export function AdminTransferResolutionPanel({ detail }: { detail: AdminTransferDetail }) {
  const user = useBackofficeAuthStore((state) => state.user);
  const queryClient = useQueryClient();
  const intention = useTransferIntention();
  const [kind, setKind] = useState<AdminTransferResolvePayload["kind"]>("RETURN_TO_ORIGIN");
  const [quantities, setQuantities] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");
  const [lotQuantities, setLotQuantities] = useState<Record<string, string>>({});
  const [quarantine, setQuarantine] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const clear = useCallback(() => {
    setQuantities({});
    setLotQuantities({});
    setReason("");
  }, []);
  const observed = useTransferDraftIdentity(intention.metadata, true, clear);
  const branchIds = [detail.origin.branchId, detail.destination.branchId];
  const allowed =
    hasEffectiveCapability(user, "transfers.execute", branchIds) &&
    hasEffectiveCapability(
      user,
      kind === "RETURN_TO_ORIGIN" ? "transfers.cancel" : "waste.manage",
      branchIds,
    );
  const mutation = useMutation({
    mutationFn: async () => {
      if (!user || !allowed || intention.error)
        throw new Error("Se requiere autorización para resolver el tránsito.");
      const lines = detail.lines.flatMap((line) => {
        const value = quantities[line.shipmentLineId]?.trim();
        if (!value) return [];
        if (
          !/^\d+(\.\d{1,3})?$/.test(value) ||
          Number(value) <= 0 ||
          Number(value) > Number(line.pendingQuantity)
        )
          throw new Error("La cantidad debe ser positiva y no superar el pendiente.");
        const lotAllocations = (line.lots ?? []).flatMap((lot) => {
          const quantity = lotQuantities[`${line.shipmentLineId}:${lot.lot_id}`]?.trim();
          if (!quantity) return [];
          if (
            !/^\d+(\.\d{1,3})?$/.test(quantity) ||
            Number(quantity) <= 0 ||
            Number(quantity) > Number(lot.pending_quantity)
          )
            throw new Error("Revisa la cantidad de cada lote.");
          return [{ lot_id: lot.lot_id, quantity }];
        });
        return [
          {
            shipment_line_id: line.shipmentLineId,
            quantity: value,
            ...(lotAllocations.length ? { lot_allocations: lotAllocations } : {}),
          },
        ];
      });
      if (!lines.length || !reason.trim())
        throw new Error("Captura cantidad y motivo de la disposición física.");
      const commandCode = kind === "RETURN_TO_ORIGIN" ? "resolve_return" : "resolve_waste";
      return transferIntentions.begin(
        {
          userId: user.id,
          branchId: detail.origin.branchId,
          transferId: detail.overview.id,
          commandCode,
        },
        {
          commandCode,
          body: {
            kind,
            lines,
            reason: reason.trim(),
            destination_location: quarantine ? "QUARANTINE" : "BACKROOM",
          },
        },
        observed.current ?? null,
      );
    },
    onSuccess: () => {
      clear();
      setMessage("Disposición física confirmada.");
      void queryClient.invalidateQueries({ queryKey: ["admin", "transfers"] });
    },
    onError: (error) =>
      setMessage(error instanceof Error ? error.message : "No se pudo confirmar."),
  });
  return (
    <section
      aria-label="Resoluciones del tránsito"
      className="grid gap-2 rounded-xl border bg-white p-3 text-xs"
    >
      <h4 className="font-semibold">Estado físico por producto</h4>
      {detail.lines.map((line) => (
        <p key={line.shipmentLineId}>
          {line.productName}: recibido {line.receivedQuantity ?? "0"}, retornado{" "}
          {line.returnedQuantity ?? "0"}, merma {line.wasteQuantity ?? "0"}, en tránsito{" "}
          {line.pendingQuantity}.
        </p>
      ))}
      {detail.lines.flatMap((line) =>
        (line.lots ?? []).map((lot) => (
          <p key={`${line.shipmentLineId}:${lot.lot_id}`}>
            Lote {lot.lot_code} · vence {lot.expires_at ?? "sin fecha"}: recibido{" "}
            {lot.received_quantity}, retornado {lot.returned_quantity}, merma {lot.waste_quantity},
            pendiente {lot.pending_quantity}.
          </p>
        )),
      )}
      {(detail.resolutions ?? []).map((item) => (
        <p key={item.id}>
          {item.kind === "RETURN_TO_ORIGIN" ? "Retorno al origen" : "Ingreso a merma"}:{" "}
          {item.reason} / {item.destination_location} ·{" "}
          {item.lines.map((line) => `${line.quantity} ${line.unit_of_measure}`).join(", ")}
        </p>
      ))}
      {detail.overview.status === "IN_TRANSIT" ? (
        <details>
          <summary className="cursor-pointer font-semibold">Resolver mercancía en tránsito</summary>
          <label className="grid gap-1 my-2">
            Disposición física
            <select
              aria-label="Disposición física"
              className="min-h-10 rounded border px-2"
              value={kind}
              onChange={(event) =>
                setKind(event.target.value as AdminTransferResolvePayload["kind"])
              }
            >
              <option value="RETURN_TO_ORIGIN">Producto ya retornado al origen</option>
              <option value="SEND_TO_WASTE">Producto dañado bajo custodia en destino</option>
            </select>
          </label>
          <p>Confirma la ubicación física. Los faltantes sin localizar permanecen en tránsito.</p>
          {kind === "RETURN_TO_ORIGIN" ? (
            <label className="flex gap-2">
              <input
                type="checkbox"
                checked={quarantine}
                onChange={(event) => setQuarantine(event.target.checked)}
              />
              Retornar a cuarentena (producto pendiente de inspección)
            </label>
          ) : null}
          {detail.lines
            .filter((line) => Number(line.pendingQuantity) > 0)
            .map((line) => (
              <label className="grid gap-1 my-2" key={line.shipmentLineId}>
                Cantidad a resolver: {line.productName}
                <input
                  className="min-h-10 rounded border px-2"
                  inputMode="decimal"
                  value={quantities[line.shipmentLineId] ?? ""}
                  onChange={(event) =>
                    setQuantities((state) => ({
                      ...state,
                      [line.shipmentLineId]: event.target.value,
                    }))
                  }
                />
              </label>
            ))}
          {detail.lines.flatMap((line) =>
            (line.lots ?? [])
              .filter((lot) => Number(lot.pending_quantity) > 0)
              .map((lot) => (
                <label className="grid gap-1 my-2" key={`${line.shipmentLineId}:${lot.lot_id}`}>
                  Lote {lot.lot_code} · vence {lot.expires_at ?? "sin fecha"} · pendiente{" "}
                  {lot.pending_quantity}
                  <input
                    className="min-h-10 rounded border px-2"
                    inputMode="decimal"
                    aria-label={`Cantidad a resolver del lote ${lot.lot_code}`}
                    value={lotQuantities[`${line.shipmentLineId}:${lot.lot_id}`] ?? ""}
                    onChange={(event) =>
                      setLotQuantities((state) => ({
                        ...state,
                        [`${line.shipmentLineId}:${lot.lot_id}`]: event.target.value,
                      }))
                    }
                  />
                </label>
              )),
          )}
          <label className="grid gap-1 my-2">
            Motivo de la disposición
            <textarea
              className="rounded border p-2"
              maxLength={500}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </label>
          <button
            className="min-h-10 rounded bg-slate-900 px-3 text-white disabled:opacity-50"
            type="button"
            disabled={
              !allowed ||
              mutation.isPending ||
              Boolean(intention.error) ||
              isCommandIntentionPending(intention.metadata)
            }
            onClick={() => mutation.mutate()}
          >
            Confirmar disposición física
          </button>
        </details>
      ) : null}
      {message ? <p role="status">{message}</p> : null}
    </section>
  );
}
