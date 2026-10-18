import type { components } from "@zeromerma/api-client";
import { useState, type FormEvent } from "react";
import { queryClient } from "../../../../lib/query-client";
import { requestJson } from "../../../../lib/api";
import { AdminActionButton } from "../../components/AdminActionButton";
import type { AdminUserDetail } from "../types";

type SessionList = components["schemas"]["AuthSessionsResponse"];
type ResetCredential = components["schemas"]["PasswordResetCredentialView"];
export function AdminUserSecurityActions({ detail }: { detail: AdminUserDetail }) {
  const [sessions, setSessions] = useState<SessionList | null>(null);
  const [credential, setCredential] = useState<ResetCredential | null>(null);
  const [reason, setReason] = useState("");
  const [showReset, setShowReset] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const prefix = `/v1/admin/users/${encodeURIComponent(detail.overview.id)}`;
  async function loadSessions(page = 1) {
    setBusy(true); setMessage(null);
    try { setSessions(await requestJson<SessionList>({ path: `${prefix}/sessions?page=${page}&page_size=10` })); }
    catch { setMessage("No fue posible consultar las sesiones."); }
    finally { setBusy(false); }
  }
  async function revoke(id: string) {
    setBusy(true); setMessage(null);
    try {
      await requestJson<void>({ path: `${prefix}/sessions/${encodeURIComponent(id)}`, method: "DELETE" });
      await loadSessions(sessions?.page ?? 1);
    } catch { setMessage("No fue posible revocar la sesión."); }
    finally { setBusy(false); }
  }
  async function issueReset(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage(null); setCredential(null);
    const body: components["schemas"]["PasswordResetIssueRequest"] = { reason: reason.trim() };
    try {
      const result = await requestJson<ResetCredential>({ path: `${prefix}/password-reset`, method: "POST", body });
      setCredential(result); setReason(""); setShowReset(false);
      await queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    } catch { setMessage("No fue posible emitir el código. Verifica tus permisos y el estado de la cuenta."); }
    finally { setBusy(false); }
  }
  return <div className="mt-3 grid gap-3 text-sm">
    <div className="flex flex-wrap gap-3">
      <AdminActionButton capability="users.manage" type="button" disabled={busy || !detail.securityActions.canRevokeSessions} onClick={() => void loadSessions()}>Ver sesiones</AdminActionButton>
      <AdminActionButton capability="users.manage" type="button" disabled={busy || !detail.securityActions.canSendPasswordReset} onClick={() => { setShowReset(!showReset); setCredential(null); }}>Restablecer contraseña</AdminActionButton>
    </div>
    {detail.securityActions.passwordResetRequiresApproval ? <p>Esta cuenta requiere aprobación privilegiada para restablecer la contraseña.</p> : null}
    {message ? <p role="alert">{message}</p> : null}
    {showReset ? <form className="grid gap-2" onSubmit={issueReset}>
      <label>Motivo del restablecimiento<input className="block w-full rounded border p-2" required minLength={8} maxLength={1000} value={reason} onChange={event => setReason(event.target.value)} /></label>
      <p>Se emitirá un código de un solo uso para entregar al usuario. No se envía por correo.</p>
      <button type="submit" disabled={busy} className="rounded border p-2">Emitir código</button>
    </form> : null}
    {credential ? <div className="grid gap-2 rounded border p-3">
      <p>Entrega este código al usuario. Vence: {new Date(credential.expires_at).toLocaleString()}.</p>
      <label>Código de un solo uso<input className="block w-full rounded border p-2" autoComplete="off" readOnly type="password" value={credential.reset_token} /></label>
      <button type="button" onClick={() => void navigator.clipboard.writeText(credential.reset_token).catch(() => setMessage("No se pudo copiar el código."))}>Copiar código</button>
      <button type="button" onClick={() => setCredential(null)}>Ocultar y descartar código</button>
    </div> : null}
    {sessions ? <div className="grid gap-2">
      <p>{sessions.total} sesiones · Página {sessions.page}</p>
      {sessions.items.map(session => <div className="rounded border p-2" key={session.id}>
        <p>{session.audience} · {session.status} · {new Date(session.last_activity_at).toLocaleString()}</p>
        <button disabled={busy || !["ACTIVE", "LOCKED"].includes(session.status)} type="button" onClick={() => void revoke(session.id)}>Revocar sesión</button>
      </div>)}
      <div className="flex gap-3"><button disabled={busy || sessions.page === 1} onClick={() => void loadSessions(sessions.page - 1)}>Anterior</button><button disabled={busy || sessions.page * sessions.page_size >= sessions.total} onClick={() => void loadSessions(sessions.page + 1)}>Siguiente</button><button onClick={() => setSessions(null)}>Cerrar lista</button></div>
    </div> : null}
  </div>;
}
