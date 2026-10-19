import { isCommandIntentionPending, type components } from "@zeromerma/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import type { TransferDetailResponse } from "../../lib/api-contracts";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import { useOperationsBootstrapQuery } from "../operations/queries";
import { parseQuantityToMilliUnits, sanitizeQuantityInput } from "../pos-terminal/model";
import { transferIntentions } from "./transfer-command-intent";
import { TransferRecoveryPanel } from "./transfer-recovery-panel";
import { useTransferDraftIdentity, useTransferIntention } from "./use-transfer-intention";

type ResolutionKind = components["schemas"]["TransferResolveRequest"]["kind"];

export function TransitResolutionPanel({ detail }: { detail: TransferDetailResponse }) {
  const user = usePosAuthStore((state) => state.user);
  const context = useOperationsBootstrapQuery().data;
  const cash = useCurrentCashSessionQuery().data;
  const queryClient = useQueryClient();
  const intention = useTransferIntention(context?.workstation.id ?? "");
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
  const observed = useTransferDraftIdentity(intention.metadata, Boolean(context), clear);
  const atOrigin = context?.branch.id === detail.shipment.source_branch_id;
  const kind: ResolutionKind = atOrigin ? "RETURN_TO_ORIGIN" : "SEND_TO_WASTE";
  const branches = [detail.shipment.source_branch_id, detail.shipment.destination_branch_id];
  const allowed = ["transfers.execute", atOrigin ? "transfers.cancel" : "waste.manage"].every(
    (capability) =>
      branches.every(
        (branch) =>
          branch &&
          user?.effective_grants?.some(
            (grant) =>
              grant.capability === capability &&
              (grant.scope_type === "GLOBAL" || grant.branch_ids.includes(branch)),
          ),
      ),
  );
  const mutation = useMutation({
    mutationFn: async () => {
      if (!user || !context || !cash || !allowed || intention.error)
        throw new Error("Se requiere caja abierta y permiso para resolver el tránsito.");
      const lines = detail.receipt_progress.flatMap((line) => {
        const value = quantities[line.shipment_line_id]?.trim();
        if (!value) return [];
        const amount = parseQuantityToMilliUnits(value);
        const pending = parseQuantityToMilliUnits(line.pending_quantity);
        if (amount === null || amount <= 0 || pending === null || amount > pending)
          throw new Error("La cantidad debe ser positiva y no superar el pendiente.");
        const lotAllocations = (line.lots ?? []).flatMap((lot) => {
          const quantity = lotQuantities[`${line.shipment_line_id}:${lot.lot_id}`]?.trim();
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
            shipment_line_id: line.shipment_line_id,
            quantity: value,
            ...(lotAllocations.length ? { lot_allocations: lotAllocations } : {}),
          },
        ];
      });
      if (!lines.length || !reason.trim())
        throw new Error("Captura cantidad y motivo de la disposición física.");
      return transferIntentions.begin(
        {
          userId: user.id,
          branchId: context.branch.id,
          workstationId: context.workstation.id,
          workstationCode: context.workstation.code,
          cashSessionId: cash.id,
          transferId: detail.shipment.id,
          commandCode: kind === "RETURN_TO_ORIGIN" ? "resolve_return" : "resolve_waste",
        },
        {
          kind,
          destination_location: quarantine ? "QUARANTINE" : "BACKROOM",
          reason: reason.trim(),
          lines,
          cash_session_id: cash.id,
          workstation_code: context.workstation.code,
        },
        observed.current ?? null,
      );
    },
    onSuccess: () => {
      setMessage("Disposición física confirmada.");
      clear();
      void queryClient.invalidateQueries();
    },
    onError: (error) =>
      setMessage(error instanceof Error ? error.message : "No se pudo confirmar."),
  });
  return (
    <section
      aria-label="Estado físico del envío"
      className="grid gap-3 rounded-xl border p-3 text-sm"
    >
      <h3 className="font-semibold">Cantidades del envío</h3>
      {detail.receipt_progress.map((line) => (
        <div key={line.shipment_line_id}>
          <p className="font-medium">
            {
              detail.shipment.lines.find((item) => item.id === line.shipment_line_id)
                ?.product_name_snapshot
            }
          </p>
          <p>
            Recibido {line.received_quantity} · Retornado {line.returned_quantity ?? "0"} · Merma{" "}
            {line.waste_quantity ?? "0"} · En tránsito {line.pending_quantity}
          </p>
        </div>
      ))}
      {detail.receipt_progress.flatMap((line) =>
        (line.lots ?? []).map((lot) => (
          <p key={`${line.shipment_line_id}:${lot.lot_id}`}>
            Lote {lot.lot_code} · vence {lot.expires_at ?? "sin fecha"}: recibido{" "}
            {lot.received_quantity}, retornado {lot.returned_quantity}, merma {lot.waste_quantity},
            pendiente {lot.pending_quantity}.
          </p>
        )),
      )}
      {(detail.resolutions ?? []).map((item) => (
        <p key={item.id}>
          {item.kind === "RETURN_TO_ORIGIN" ? "Retorno al origen" : "Ingreso a merma"}:{" "}
          {item.reason} / {item.destination_location}
          {" · "}
          {item.lines.map((line) => `${line.quantity} ${line.unit_of_measure}`).join(", ")}
        </p>
      ))}
      {detail.shipment.status === "IN_TRANSIT" && allowed ? (
        <details>
          <summary className="cursor-pointer font-semibold">
            {atOrigin
              ? "Confirmar producto retornado al origen"
              : "Registrar daño recibido en merma"}
          </summary>
          <p className="my-2">
            {atOrigin
              ? "Confirma sólo la mercancía que ya regresó físicamente a esta sucursal."
              : "Confirma sólo producto dañado bajo custodia en esta sucursal. Un faltante sin localizar sigue en tránsito."}
          </p>
          {atOrigin ? (
            <label className="flex gap-2">
              <input
                type="checkbox"
                checked={quarantine}
                onChange={(event) => setQuarantine(event.target.checked)}
              />{" "}
              Retornar a cuarentena (producto pendiente de inspeccion)
            </label>
          ) : null}
          {detail.receipt_progress
            .filter((line) => Number(line.pending_quantity) > 0)
            .map((line) => (
              <label className="grid gap-1 my-2" key={line.shipment_line_id}>
                Cantidad a resolver:{" "}
                {
                  detail.shipment.lines.find((item) => item.id === line.shipment_line_id)
                    ?.product_name_snapshot
                }
                <input
                  className="min-h-11 rounded-lg border px-3"
                  inputMode="decimal"
                  value={quantities[line.shipment_line_id] ?? ""}
                  onChange={(event) =>
                    setQuantities((state) => ({
                      ...state,
                      [line.shipment_line_id]: sanitizeQuantityInput(event.target.value),
                    }))
                  }
                />
              </label>
            ))}
          {detail.receipt_progress.flatMap((line) =>
            (line.lots ?? [])
              .filter((lot) => Number(lot.pending_quantity) > 0)
              .map((lot) => (
                <label className="grid gap-1 my-2" key={`${line.shipment_line_id}:${lot.lot_id}`}>
                  Lote {lot.lot_code} · vence {lot.expires_at ?? "sin fecha"} · pendiente{" "}
                  {lot.pending_quantity}
                  <input
                    className="min-h-10 rounded border px-2"
                    inputMode="decimal"
                    aria-label={`Cantidad a resolver del lote ${lot.lot_code}`}
                    value={lotQuantities[`${line.shipment_line_id}:${lot.lot_id}`] ?? ""}
                    onChange={(event) =>
                      setLotQuantities((state) => ({
                        ...state,
                        [`${line.shipment_line_id}:${lot.lot_id}`]: event.target.value,
                      }))
                    }
                  />
                </label>
              )),
          )}
          <label className="grid gap-1 my-2">
            Motivo de la disposición
            <textarea
              className="rounded-lg border p-2"
              maxLength={500}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </label>
          <button
            className="min-h-11 rounded-lg bg-slate-900 text-white px-3 disabled:opacity-50"
            type="button"
            disabled={
              mutation.isPending ||
              Boolean(intention.error) ||
              isCommandIntentionPending(intention.metadata)
            }
            onClick={() => mutation.mutate()}
          >
            {atOrigin ? "Confirmar retorno físico" : "Confirmar ingreso a merma"}
          </button>
        </details>
      ) : null}
      {message ? <p role="status">{message}</p> : null}
      {context ? <TransferRecoveryPanel workstationId={context.workstation.id} /> : null}
    </section>
  );
}
