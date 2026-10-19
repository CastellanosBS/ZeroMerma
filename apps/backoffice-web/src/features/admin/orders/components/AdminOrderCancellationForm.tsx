import { useEffect, useRef, useState, type FormEvent } from "react";
import type { AdminOrderCancelRequest } from "../api";

export function AdminOrderCancellationForm({ folio, busy, onCancel, onConfirm }: {
  folio: string;
  busy: boolean;
  onCancel: () => void;
  onConfirm: (payload: AdminOrderCancelRequest) => void;
}) {
  const [reason, setReason] = useState("");
  const [responsibility, setResponsibility] = useState<AdminOrderCancelRequest["cancellation_responsibility"] | "">("");
  const reasonInput = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { reasonInput.current?.focus(); }, []);
  function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !responsibility || reason.trim().length < 4) return;
    onConfirm({ cancellation_reason: reason.trim(), cancellation_responsibility: responsibility });
  }
  return <section aria-label="Cancelar pedido" className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
    <h2 className="font-semibold">Cancelar {folio}</h2>
    <p className="mt-1 text-sm">Indica la causa real. El servidor calcula la política aplicable; si corresponde un reembolso, completa la cancelación desde el POS con caja abierta.</p>
    <form className="mt-3 grid gap-3" onSubmit={submit}>
      <label className="grid gap-1">Motivo de cancelación
        <textarea ref={reasonInput} required minLength={4} maxLength={240} disabled={busy}
          value={reason} onChange={event => setReason(event.target.value)} className="rounded border p-2" />
      </label>
      <label className="grid gap-1">Responsabilidad
        <select required disabled={busy} value={responsibility}
          onChange={event => setResponsibility(event.target.value as typeof responsibility)} className="rounded border p-2">
          <option value="">Selecciona la responsabilidad</option>
          <option value="CUSTOMER">Solicitud o incumplimiento del cliente</option>
          <option value="MERCHANT">Incumplimiento del negocio</option>
        </select>
      </label>
      <div className="flex flex-wrap gap-3">
        <button type="button" disabled={busy} onClick={onCancel} className="rounded border bg-white px-4 py-3">Volver sin cancelar</button>
        <button type="submit" disabled={busy || !responsibility || reason.trim().length < 4} className="rounded bg-rose-700 px-4 py-3 text-white disabled:opacity-50">
          {busy ? "Confirmando…" : "Confirmar cancelación"}
        </button>
      </div>
    </form>
  </section>;
}
