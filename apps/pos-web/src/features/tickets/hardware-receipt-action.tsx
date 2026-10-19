import { isCommandIntentionPending, type CommandIntentionMetadata, type components } from "@zeromerma/api-client";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { requestJson } from "../../lib/http";
import { requestLocalHardware } from "../../lib/local-hardware-transport";
import { usePosAuthStore } from "../auth/auth-store";
import { hardwareIntentions, printScope, recoverHardwareCommand, type PrintContext } from "./print-command-intent";

type Receipt = components["schemas"]["OperationalReceiptView"];
type Bootstrap = components["schemas"]["HardwareBootstrapView"];
const labels: Record<string, string> = {
  QUEUED: "Trabajo en cola. Puedes reanudar el mismo trabajo.",
  PROCESSING: "La impresora está procesando el trabajo.",
  ACKNOWLEDGED: "El adaptador recibió el trabajo; salida física sin confirmar.",
  PRINTED: "El adaptador confirmó la impresión.",
  UNAVAILABLE: "Impresora no disponible; la operación original sigue registrada.",
  UNKNOWN: "Resultado de impresión incierto. Verifica el papel antes de otra copia.",
};

export function HardwareReceiptAction({ receipt, workstationCode }: {
  receipt: Receipt | null | undefined; workstationCode?: string;
}) {
  const auth = usePosAuthStore();
  const scope = auth.session?.workstation_id && receipt
    ? `${auth.session.workstation_id}:${receipt.source_kind}:${receipt.source_id}` : "";
  const bootstrap = useQuery({
    queryKey: ["hardware", workstationCode, auth.generation],
    queryFn: () => requestJson<Bootstrap>({ path: `/v1/hardware/bootstrap?workstation_code=${encodeURIComponent(workstationCode!)}` }),
    enabled: Boolean(receipt && workstationCode && auth.isAuthenticated), retry: false, staleTime: 30_000,
  });
  const busy = useRef(false);
  const receiptEpoch = useRef(0);
  const [metadata, setMetadata] = useState<CommandIntentionMetadata<PrintContext> | null>(null);
  const [invalidMetadata, setInvalidMetadata] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [deviceState, setDeviceState] = useState("");
  const [deviceStateKey, setDeviceStateKey] = useState("");
  useEffect(() => {
    receiptEpoch.current += 1;
    setMessage(""); setDeviceState(""); setPending(false);
    const update = () => {
      try { setMetadata(scope ? hardwareIntentions.read(scope) : null); setInvalidMetadata(false); }
      catch { setMetadata(null); setInvalidMetadata(true); }
    };
    update();
    const unsubscribe = scope ? hardwareIntentions.subscribe(scope, update) : undefined;
    return () => { receiptEpoch.current += 1; unsubscribe?.(); };
  }, [scope, auth.generation]);
  const printer = bootstrap.data?.devices.find((device) => device.kind === "PRINTER" && device.enabled);
  const owned = !metadata || (metadata.userId === auth.user?.id && metadata.workstationId === auth.session?.workstation_id);

  async function operate(mode: "start" | "consult" | "resume") {
    if (!receipt || !workstationCode || !printer || busy.current || !auth.user || !auth.session?.workstation_id
      || !auth.isAuthenticated || !owned || invalidMetadata) return;
    if ((mode === "start" && !canStart) || (mode === "resume" && (deviceState !== "QUEUED" || deviceStateKey !== metadata?.key))) return;
    busy.current = true; setPending(true);
    const generation = auth.generation;
    const epoch = receiptEpoch.current;
    const isCurrent = () => usePosAuthStore.getState().generation === generation && receiptEpoch.current === epoch;
    const context: PrintContext = { userId: auth.user.id, workstationId: auth.session.workstation_id,
      workstationCode, sourceKind: receipt.source_kind, sourceId: receipt.source_id };
    try {
      const current = hardwareIntentions.read(printScope(context));
      const acknowledgement = mode === "start"
        ? await hardwareIntentions.begin(context, { workstation_code: workstationCode, binding_id: printer.id,
          kind: "PRINT", receipt_source_kind: receipt.source_kind, receipt_source_id: receipt.source_id }, current?.key ?? null)
        : current ? isCommandIntentionPending(current)
          ? await hardwareIntentions.recover(context) : await recoverHardwareCommand(current)
          : null;
      if (!acknowledgement || !isCurrent()) return;
      const admittedKey = hardwareIntentions.read(printScope(context))?.key ?? "";
      // A fresh grant changes expiry, never the device command identity or content.
      const body = await requestLocalHardware(acknowledgement.grant, mode === "consult");
      if (!isCurrent()) return;
      if (body.command_id !== acknowledgement.command_id || !Object.hasOwn(labels, body.state)) throw new Error("Unknown device response");
      setDeviceStateKey(admittedKey); setDeviceState(body.state); setMessage(labels[body.state]!);
    } catch {
      if (isCurrent()) {
        setDeviceState("UNKNOWN");
        setMessage("No se pudo confirmar el resultado. Consulta el trabajo antes de otra copia.");
      }
    } finally { busy.current = false; if (isCurrent()) setPending(false); }
  }
  const canStart = !metadata || metadata.status === "REJECTED"
    || (deviceStateKey === metadata.key && ["PRINTED", "UNAVAILABLE"].includes(deviceState));
  const blocked = pending || !owned || invalidMetadata;
  return <div className="mt-2 text-xs text-slate-600">
    <p>{printer ? "Impresora vinculada a esta caja." : bootstrap.isError
      ? "No se pudo consultar el estado del dispositivo."
      : "Impresora local pendiente de instalación y validación."}</p>
    {printer ? <div className="flex flex-wrap gap-2">
      <button type="button" className="min-h-12 rounded-lg border px-3" disabled={blocked || !canStart}
        onClick={() => void operate("start")}>{metadata ? "Solicitar otra copia local" : "Imprimir con dispositivo local"}</button>
      <button type="button" className="min-h-12 rounded-lg border px-3" disabled={blocked || !metadata}
        onClick={() => void operate("consult")}>Consultar impresión</button>
      {deviceState === "QUEUED" && deviceStateKey === metadata?.key ? <button type="button" className="min-h-12 rounded-lg border px-3" disabled={blocked}
        onClick={() => void operate("resume")}>Reanudar el mismo trabajo</button> : null}
    </div> : null}
    <p role="status">{invalidMetadata ? "Referencia local inválida; solicita revisión antes de otra copia."
      : !owned ? "La impresión pendiente pertenece a otro operador."
      : message || (metadata ? "Hay una referencia guardada. Consulta su resultado antes de imprimir." : "")}</p>
  </div>;
}
