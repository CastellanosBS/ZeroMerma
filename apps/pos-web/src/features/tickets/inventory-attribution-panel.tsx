import { isCommandIntentionPending, type components } from "@zeromerma/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import { parseQuantityToMilliUnits, sanitizeQuantityInput } from "../pos-terminal/model";
import { attributionIntentions } from "./attribution-command-intent";
import { useTicketsBootstrapQuery } from "./queries";
import { useAttributionDraftIdentity, useAttributionIntention } from "./use-attribution-intention";

type Ticket = Pick<components["schemas"]["TicketDetailResponse"], "id" | "branch" | "lines">;
type Line = Ticket["lines"][number];
export function InventoryAttributionPanel({ ticket }: { ticket: Ticket }) {
  const lines = ticket.lines.filter((line) => line.capture_mode === "CLASS_CAPTURE");
  if (!lines.length) return null;
  return (
    <section
      aria-label="Atribucion fisica del ticket"
      className="grid gap-3 rounded-xl border p-3 text-sm"
    >
      <h3 className="font-semibold">Producto entregado por clase</h3>
      <p>
        Identifica el producto y lote entregados. Puedes atribuir una parte y conservar el resto
        pendiente; el importe cobrado no cambia.
      </p>
      {lines.map((line) => (
        <AttributionLineForm key={line.id} ticket={ticket} line={line} />
      ))}
    </section>
  );
}
function AttributionLineForm({ ticket, line }: { ticket: Ticket; line: Line }) {
  const user = usePosAuthStore((state) => state.user);
  const context = useTicketsBootstrapQuery().data;
  const cash = useCurrentCashSessionQuery().data;
  const queries = useQueryClient();
  const intention = useAttributionIntention(context?.workstation.id ?? "");
  const [selected, setSelected] = useState("");
  const [quantity, setQuantity] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const clear = useCallback(() => {
    setSelected("");
    setQuantity("");
  }, []);
  const observed = useAttributionDraftIdentity(intention.metadata, clear);
  const allowed =
    context?.branch.id === ticket.branch.id &&
    user?.effective_grants?.some(
      (grant) =>
        grant.capability === "pos.operate" &&
        (grant.scope_type === "GLOBAL" || grant.branch_ids.includes(ticket.branch.id)),
    );
  const options = line.attribution_options ?? [];
  const mutation = useMutation({
    mutationFn: async () => {
      if (!user || !context || !cash || cash.status !== "OPEN" || !allowed || intention.error)
        throw new Error("Se requiere caja abierta y autorizacion en esta sucursal.");
      const option = options.find((item) => `${item.product_id}:${item.lot_id ?? ""}` === selected);
      const amount = parseQuantityToMilliUnits(quantity);
      const remaining = parseQuantityToMilliUnits(line.remaining_attribution_quantity);
      if (!option || amount === null || amount <= 0 || remaining === null || amount > remaining)
        throw new Error("Selecciona producto y lote y una cantidad dentro del pendiente.");
      if (
        option.available_quantity !== null &&
        amount > (parseQuantityToMilliUnits(option.available_quantity) ?? 0)
      )
        throw new Error("La cantidad supera la existencia disponible de esta opcion.");
      return attributionIntentions.begin(
        {
          userId: user.id,
          branchId: context.branch.id,
          workstationId: context.workstation.id,
          workstationCode: context.workstation.code,
          cashSessionId: cash.id,
          saleId: ticket.id,
        },
        {
          workstation_code: context.workstation.code,
          cash_session_id: cash.id,
          lines: [
            {
              sale_line_id: line.id,
              product_id: option.product_id,
              lot_id: option.lot_id,
              quantity,
            },
          ],
        },
        observed.current ?? null,
      );
    },
    onSuccess: () => {
      clear();
      setMessage("Atribucion confirmada; consulta la cantidad pendiente actualizada.");
      void queries.invalidateQueries();
    },
    onError: (error) =>
      setMessage(error instanceof Error ? error.message : "No fue posible atribuir."),
  });
  const pending = isCommandIntentionPending(intention.metadata);
  return (
    <fieldset
      className="grid gap-2 rounded-lg border p-2"
      aria-label={`Atribucion de ${line.name}`}
    >
      <legend className="font-semibold">{line.name}</legend>
      <p>Pendiente de atribuir: {line.remaining_attribution_quantity}</p>
      {line.physical_attributions.length ? (
        <details>
          <summary>Atribuciones registradas ({line.physical_attributions.length})</summary>
          {line.physical_attributions.map((entry) => (
            <p key={entry.id}>
              {entry.quantity} unidades ·{" "}
              {new Date(entry.occurred_at).toLocaleString("es-MX", {
                timeZone: ticket.branch.timezone,
              })}
            </p>
          ))}
        </details>
      ) : null}
      {Number(line.remaining_attribution_quantity) > 0 ? (
        <>
          <label className="grid gap-1">
            Producto y lote entregados
            <select
              aria-label="Producto y lote entregados"
              className="min-h-10 rounded border px-2"
              value={selected}
              disabled={pending || mutation.isPending}
              onChange={(event) => setSelected(event.target.value)}
            >
              <option value="">Selecciona producto y lote</option>
              {options.map((option) => (
                <option
                  key={`${option.product_id}:${option.lot_id ?? ""}`}
                  value={`${option.product_id}:${option.lot_id ?? ""}`}
                >
                  {option.product_name} · {option.product_code}
                  {option.lot_id
                    ? ` · lote ${option.lot_code} · vence ${option.expires_at ?? "sin fecha"}`
                    : ""}{" "}
                  · disponible {option.available_quantity ?? "no inventariable"}
                </option>
              ))}
            </select>
          </label>
          {!options.length ? (
            <p>No hay opciones elegibles con existencia para esta venta.</p>
          ) : null}
          <label className="grid gap-1">
            Cantidad a atribuir
            <input
              className="min-h-10 rounded border px-2"
              inputMode="decimal"
              value={quantity}
              disabled={pending || mutation.isPending}
              onChange={(event) => setQuantity(sanitizeQuantityInput(event.target.value))}
            />
          </label>
          <button
            type="button"
            className="rounded bg-slate-900 p-2 text-white disabled:opacity-50"
            disabled={
              !allowed || !cash || pending || mutation.isPending || Boolean(intention.error)
            }
            onClick={() => mutation.mutate()}
          >
            Confirmar producto entregado
          </button>
          {!cash ? <p>Abre caja para registrar la atribucion.</p> : null}
        </>
      ) : (
        <p>La obligacion fisica de esta linea esta resuelta.</p>
      )}
      {message ? <p role="status">{message}</p> : null}
    </fieldset>
  );
}
