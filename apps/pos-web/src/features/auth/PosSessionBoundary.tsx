import { observeOperatorActivity, ApiError } from "@zeromerma/api-client";
import { useCallback, useEffect, useRef, useState, type FormEvent, type PropsWithChildren } from "react";
import { usePosAuthStore } from "./auth-store";
import { changePassword, logoutSession, recordActivity, restoreSession, reauthenticate } from "./session-api";

export function PosSessionBoundary({ children }: PropsWithChildren) {
  const phase = usePosAuthStore((state) => state.phase);
  const session = usePosAuthStore((state) => state.session);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const passwordInput = useRef<HTMLInputElement>(null);
  const refresh = useCallback(async (requireVerification = false) => {
    setError(null);
    if (requireVerification) usePosAuthStore.getState().requireVerification();
    try { await restoreSession(); }
    catch (failure) {
      if (!(failure instanceof ApiError && failure.statusCode === 401)) {
        setError("No fue posible verificar la sesión. Revisa la conexión y vuelve a intentar.");
      }
    }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    setPassword(""); setNewPassword(""); setConfirmation("");
    if (phase !== "restoring") setError(null);
    passwordInput.current?.focus();
  }, [phase]);
  useEffect(() => {
    if (phase !== "ready") return;
    return observeOperatorActivity(window, () => { void recordActivity().catch(() => undefined); });
  }, [phase]);
  useEffect(() => {
    if (!session || phase !== "ready") return;
    // A status read observes the server deadline; it never extends operator activity.
    const deadline = Math.min(Date.parse(session.idle_expires_at), Date.parse(session.absolute_expires_at));
    // A backwards workstation clock cannot keep cached business data visible indefinitely.
    const delay = Math.min(30 * 60_000, Math.max(100, deadline - Date.now() + 100));
    const timer = window.setTimeout(() => void refresh(true), delay);
    return () => window.clearTimeout(timer);
  }, [phase, refresh, session]);
  useEffect(() => {
    const onFocus = () => { if (usePosAuthStore.getState().phase !== "signedOut") void refresh(); };
    const onVisibility = () => { if (document.visibilityState === "visible") onFocus(); };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [refresh]);
  async function signOut() {
    setBusy(true); setError(null);
    try { await logoutSession(); }
    catch { setError("No se pudo cerrar la sesión en el servidor. Reintenta."); }
    finally { setBusy(false); }
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError(null);
    if (phase === "passwordChange" && newPassword !== confirmation) {
      setError("Las contraseñas nuevas no coinciden."); return;
    }
    setBusy(true);
    try {
      if (phase === "locked") await reauthenticate({ password });
      else {
        await changePassword({ current_password: password, new_password: newPassword });
        setNotice("Contraseña actualizada. Inicia sesión de nuevo.");
      }
      setPassword(""); setNewPassword(""); setConfirmation("");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "No fue posible completar la operación.");
    } finally { setBusy(false); }
  }
  if (phase === "restoring") {
    return <main className="grid min-h-screen place-content-center gap-4 p-6">
      <h1>Verificando sesión</h1>
      {error ? <p role="alert">{error}</p> : <p>Espera un momento...</p>}
      <button onClick={() => void refresh()}>Reintentar</button>
    </main>;
  }
  if (phase === "locked" || phase === "passwordChange") {
    return <main className="grid min-h-screen place-content-center gap-4 bg-slate-50 p-6 text-slate-950">
      <form className="grid w-full max-w-md gap-4 rounded-2xl bg-white p-6 shadow" onSubmit={submit}>
        <h1 className="text-2xl font-semibold">{phase === "locked" ? "Sesión bloqueada" : "Cambia tu contraseña"}</h1>
        <p>{phase === "locked" ? "Confirma tu contraseña para continuar. El turno de caja permanece abierto." : "La contraseña temporal debe cambiarse antes de operar."}</p>
        <label>Contraseña actual<input ref={passwordInput} className="block w-full rounded border p-3" autoComplete="current-password" type="password" required value={password} onChange={event => setPassword(event.target.value)} /></label>
        {phase === "passwordChange" ? <>
          <label>Nueva contraseña<input className="block w-full rounded border p-3" autoComplete="new-password" type="password" minLength={12} maxLength={128} required value={newPassword} onChange={event => setNewPassword(event.target.value)} /></label>
          <label>Confirma la nueva contraseña<input className="block w-full rounded border p-3" autoComplete="new-password" type="password" minLength={12} maxLength={128} required value={confirmation} onChange={event => setConfirmation(event.target.value)} /></label>
        </> : null}
        {error ? <p role="alert">{error}</p> : null}
        <button className="rounded bg-blue-700 p-3 text-white" disabled={busy} type="submit">{busy ? "Validando..." : phase === "locked" ? "Desbloquear" : "Cambiar contraseña"}</button>
        <button disabled={busy} onClick={() => void signOut()} type="button">Cerrar sesión</button>
      </form>
    </main>;
  }
  return <>{notice ? <p role="status" className="bg-emerald-50 p-3 text-emerald-900">{notice}</p> : null}{children}</>;
}
