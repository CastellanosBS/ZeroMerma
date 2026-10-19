import { isCommandIntentionPending } from "@zeromerma/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminActionButton } from "../../components/AdminActionButton";
import { ORDER_POLICY_SCOPE, orderPolicyIntentions, readOrderPolicy, type OrderPolicyRequest } from "../order-policy-intent";
import type { AdminOrderFilterOption } from "../types";

function intentionSnapshot() {
  try { return { metadata: orderPolicyIntentions.read(ORDER_POLICY_SCOPE), error: null }; }
  catch { return { metadata: null, error: "No se puede leer la referencia de política. No repitas el cambio; solicita revisión." }; }
}

export function OrderCommitmentPolicyPanel({ branches }: { branches: AdminOrderFilterOption[] }) {
  const user = useBackofficeAuthStore(state => state.user);
  const [intention, setIntention] = useState(intentionSnapshot);
  const [branchId, setBranchId] = useState(() => intention.metadata?.branchId ?? "");
  const [leadMinutes, setLeadMinutes] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const client = useQueryClient();
  useEffect(() => orderPolicyIntentions.subscribe(ORDER_POLICY_SCOPE, () => setIntention(intentionSnapshot())), []);
  const pending = isCommandIntentionPending(intention.metadata);
  const policy = useQuery({
    queryKey: ["admin", "orders", "policy", branchId], queryFn: () => readOrderPolicy(branchId),
    enabled: Boolean(user && branchId), networkMode: "always", retry: false,
  });
  const mutation = useMutation({
    networkMode: "always", retry: false,
    mutationFn: async ({ payload, recovery }: { payload?: OrderPolicyRequest; recovery?: "read" | "retry" }) => {
      if (!user) throw new Error("Inicia sesión antes de configurar la política.");
      if (recovery) {
        const metadata = intention.metadata;
        if (!metadata || metadata.userId !== user.id) throw new Error("Se requiere el operador original.");
        return recovery === "read" ? orderPolicyIntentions.recover(metadata) : orderPolicyIntentions.retry(metadata);
      }
      if (!payload || !branchId || pending || intention.error) throw new Error("Resuelve la referencia pendiente antes de continuar.");
      return orderPolicyIntentions.begin({ userId: user.id, branchId }, payload, intention.metadata?.key ?? null);
    },
    onSuccess: result => {
      setMessage(`Política versión ${result.version} confirmada: ${result.lead_time_minutes} minutos antes de la entrega.`);
      setLeadMinutes(""); setReason("");
      void client.invalidateQueries({ queryKey: ["admin", "orders", "policy"] });
    },
    onError: error => setMessage(toBackofficeErrorMessage(error, "No fue posible confirmar la política. Consulta la referencia antes de repetirla.")),
  });
  const validMinutes = /^\d+$/.test(leadMinutes) && Number(leadMinutes) <= 525600;
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!validMinutes || reason.trim().length < 4 || mutation.isPending || pending || intention.error) return;
    setMessage(null);
    mutation.mutate({ payload: { lead_time_minutes: Number(leadMinutes), reason: reason.trim() } });
  }
  return <details className="shrink-0 rounded-2xl border border-slate-200 bg-white p-3">
    <summary className="cursor-pointer font-semibold">Política de compromiso de producción</summary>
    <p className="mt-2 text-sm">Define explícitamente cuántos minutos antes de la entrega se compromete el pedido. No hay un plazo predeterminado. Los pedidos existentes conservan su política confirmada.</p>
    {intention.error || pending ? <div role="alert" className="my-3 rounded border border-amber-300 bg-amber-50 p-3">
      <p>{intention.error ?? "Cambio de política pendiente. Consulta el resultado antes de guardar otra versión."}</p>
      {intention.metadata ? <>
        <p>Referencia: {intention.metadata.key}</p>
        <button type="button" disabled={mutation.isPending || intention.metadata.userId !== user?.id} onClick={() => mutation.mutate({ recovery: "read" })}>Consultar resultado de política</button>
        {orderPolicyIntentions.hasBody(intention.metadata.key) && intention.metadata.status !== "CONFLICT" ? <button type="button" disabled={mutation.isPending || intention.metadata.userId !== user?.id} onClick={() => mutation.mutate({ recovery: "retry" })}>Reintentar la misma política</button> : null}
      </> : null}
    </div> : null}
    <form className="mt-3 grid gap-3 md:grid-cols-2" onSubmit={submit}>
      <label className="grid gap-1">Sucursal de la política
        <select value={branchId} disabled={pending || mutation.isPending} required onChange={event => { setBranchId(event.target.value); setLeadMinutes(""); setReason(""); setMessage(null); }} className="rounded border p-2">
          <option value="">Selecciona la sucursal</option>
          {branches.map(branch => <option key={branch.id} value={branch.id}>{branch.label}</option>)}
        </select>
      </label>
      <label className="grid gap-1">Anticipación de producción en minutos
        <input type="number" inputMode="numeric" required min={0} max={525600} step={1} value={leadMinutes} disabled={pending || mutation.isPending} onChange={event => setLeadMinutes(event.target.value)} className="rounded border p-2" />
      </label>
      <label className="grid gap-1 md:col-span-2">Motivo de la configuración
        <input required minLength={4} maxLength={240} value={reason} disabled={pending || mutation.isPending} onChange={event => setReason(event.target.value)} className="rounded border p-2" />
      </label>
      {branchId ? <p className="text-sm md:col-span-2">{policy.isPending ? "Consultando política…" : policy.error ? "No se pudo consultar la política actual." : policy.data ? `Versión actual ${policy.data.version}: ${policy.data.lead_time_minutes} minutos.` : "Esta sucursal todavía no tiene una política de pedidos."}</p> : null}
      <AdminActionButton capability="orders.manage" branchIds={branchId ? [branchId] : []} type="submit" disabled={!branchId || !validMinutes || reason.trim().length < 4 || pending || mutation.isPending || Boolean(intention.error) || policy.isPending || Boolean(policy.error)} className="rounded bg-blue-800 p-3 text-white disabled:opacity-50">
        {mutation.isPending ? "Confirmando…" : "Guardar nueva versión de política"}
      </AdminActionButton>
    </form>
    {message ? <p role="status" className="mt-3">{message}</p> : null}
  </details>;
}
