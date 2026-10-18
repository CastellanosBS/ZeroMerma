import { useState, type FormEvent } from "react";
import type { components } from "@zeromerma/api-client";
import { requestJson } from "../../lib/http";

export function PasswordResetForm() {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); setMessage(null);
    if (password !== confirmation) { setMessage("Las contraseñas nuevas no coinciden."); return; }
    setBusy(true);
    const body: components["schemas"]["PasswordResetRequest"] = { reset_token: code, new_password: password };
    try {
      await requestJson<void>({ path: "/v1/auth/password/reset", method: "POST", body });
      setCode(""); setPassword(""); setConfirmation(""); setOpen(false);
      setMessage("Contraseña restablecida. Inicia sesión con la nueva contraseña.");
    } catch { setMessage("No se pudo restablecer la contraseña. Revisa el código o solicita uno nuevo."); }
    finally { setBusy(false); }
  }
  return <div className="grid gap-3 px-6 pb-5 text-sm">
    <button type="button" className="underline" onClick={() => { setOpen(!open); setCode(""); setPassword(""); setConfirmation(""); setMessage(null); }}>Restablecer contraseña</button>
    {message ? <p role="status">{message}</p> : null}
    {open ? <form className="grid gap-3" onSubmit={submit}>
      <p>Solicita un código de un solo uso al administrador e ingrésalo aquí.</p>
      <label>Código de restablecimiento<input className="block w-full rounded border p-3" autoComplete="off" required type="password" value={code} onChange={event => setCode(event.target.value)} /></label>
      <label>Nueva contraseña<input className="block w-full rounded border p-3" autoComplete="new-password" required minLength={12} maxLength={128} type="password" value={password} onChange={event => setPassword(event.target.value)} /></label>
      <label>Confirma la nueva contraseña<input className="block w-full rounded border p-3" autoComplete="new-password" required minLength={12} maxLength={128} type="password" value={confirmation} onChange={event => setConfirmation(event.target.value)} /></label>
      <button className="rounded bg-blue-700 p-3 text-white" type="submit" disabled={busy}>Guardar nueva contraseña</button>
    </form> : null}
  </div>;
}
