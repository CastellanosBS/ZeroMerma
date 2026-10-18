import { createPortal } from "react-dom";
import { useState, type FormEvent } from "react";
import type { AuthSessionView } from "@zeromerma/api-client";
import { useBackofficeAuthStore } from "./backoffice-auth-store";
import { changePassword, listOwnSessions, revokeOtherSessions, revokeSession } from "./session-api";

export function OwnSessionsPanel() {
  const currentId = useBackofficeAuthStore(state => state.session?.id);
  const [open, setOpen] = useState(false);
  const [sessions, setSessions] = useState<AuthSessionView[]>([]);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  async function refresh(requestedPage = 1) {
    setError(null); setBusy(true);
    try { const result = await listOwnSessions(requestedPage); setSessions(result.items); setPage(result.page); setHasNext(result.page * result.page_size < result.total); }
    catch { setError("No fue posible consultar tus sesiones."); }
    finally { setBusy(false); }
  }
  async function revoke(id?: string) {
    setBusy(true); setError(null);
    try {
      if (id) await revokeSession(id); else await revokeOtherSessions();
      if (id === currentId) useBackofficeAuthStore.getState().clearSession();
      else await refresh(page);
    } catch { setError("No se pudo revocar la sesión. Reintenta."); }
    finally { setBusy(false); }
  }
  async function submitPassword(event: FormEvent) {
    event.preventDefault();
    if (newPassword !== confirmation) { setError("Las contraseñas nuevas no coinciden."); return; }
    setBusy(true); setError(null);
    try { await changePassword({ current_password: password, new_password: newPassword }); }
    catch { setError("No se pudo cambiar la contraseña. Revisa los datos e intenta de nuevo."); }
    finally { setBusy(false); setPassword(""); setNewPassword(""); setConfirmation(""); }
  }
  return <>
    <button className="rounded-full border px-3 py-2" type="button" onClick={() => { setOpen(true); void refresh(); }}>Mis sesiones</button>
    {open ? createPortal(<div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4">
      <section role="dialog" aria-modal="true" aria-labelledby="own-sessions-heading" className="max-h-[90vh] w-full max-w-xl overflow-auto rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex justify-between gap-4"><h2 id="own-sessions-heading" className="text-xl font-semibold">Mis sesiones</h2><button type="button" onClick={() => { setOpen(false); setPassword(""); setNewPassword(""); setConfirmation(""); }}>Cerrar</button></div>
        {error ? <p role="alert" className="my-3 text-red-700">{error}</p> : null}
        {sessions.map(session => <div className="my-3 rounded border p-3" key={session.id}>
          <p>{session.audience === "POS" ? "Punto de venta" : "Administración"} · {session.id === currentId ? "Esta sesión" : "Otra sesión"}</p>
          <p>Estado: {session.status}. Última actividad: {new Date(session.last_activity_at).toLocaleString()}</p>
          <button className="mt-2 underline" disabled={busy || !["ACTIVE", "LOCKED"].includes(session.status)} type="button" onClick={() => void revoke(session.id)}>Revocar sesión</button>
        </div>)}
        <div className="flex gap-3"><button disabled={busy || page === 1} onClick={() => void refresh(page - 1)}>Anterior</button><span>Página {page}</span><button disabled={busy || !hasNext} onClick={() => void refresh(page + 1)}>Siguiente</button></div>
        <button disabled={busy} type="button" className="my-3 rounded border p-2" onClick={() => void revoke()}>Cerrar las demás sesiones</button>
        <form className="grid gap-3 border-t pt-4" onSubmit={submitPassword}>
          <h3 className="font-semibold">Cambiar contraseña</h3><p>Al cambiarla se cerrarán todas tus sesiones.</p>
          <label>Contraseña actual<input className="block w-full rounded border p-2" autoComplete="current-password" required type="password" value={password} onChange={event => setPassword(event.target.value)} /></label>
          <label>Nueva contraseña<input className="block w-full rounded border p-2" autoComplete="new-password" required minLength={12} maxLength={128} type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} /></label>
          <label>Confirma la nueva contraseña<input className="block w-full rounded border p-2" autoComplete="new-password" required minLength={12} maxLength={128} type="password" value={confirmation} onChange={event => setConfirmation(event.target.value)} /></label>
          <button disabled={busy} type="submit" className="rounded bg-blue-700 p-3 text-white">Cambiar contraseña</button>
        </form>
      </section>
    </div>, document.body) : null}
  </>;
}
