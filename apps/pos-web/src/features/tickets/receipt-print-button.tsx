import { isCommandIntentionPending, type components } from "@zeromerma/api-client";
import { useEffect, useRef, useState } from "react";

import { openBrowserPrintWindow, writePrintableDocument } from "../../lib/browser-print";
import { usePosAuthStore } from "../auth/auth-store";
import { buildOperationalReceiptPrintDocument } from "./print";
import { HardwareReceiptAction } from "./hardware-receipt-action";
import { browserPrintIntentions, printScope, type PrintContext } from "./print-command-intent";

type Receipt = components["schemas"]["OperationalReceiptView"];

export function ReceiptPrintButton({
  receipt,
  workstationCode,
}: {
  receipt: Receipt | null | undefined;
  workstationCode?: string;
}) {
  const busy = useRef(false);
  const [pending, setPending] = useState(false);
  const [feedback, setFeedback] = useState("");
  const auth = usePosAuthStore();
  const receiptEpoch = useRef(0);
  useEffect(() => {
    receiptEpoch.current += 1;
    setFeedback(""); setPending(false);
    return () => { receiptEpoch.current += 1; };
  }, [receipt?.source_id, workstationCode, auth.generation]);

  async function requestPrint() {
    if (!receipt || !workstationCode || busy.current || !auth.user || !auth.session?.workstation_id
      || !auth.isAuthenticated) return;
    const printWindow = openBrowserPrintWindow();
    if (!printWindow) {
      setFeedback("Permite ventanas emergentes para abrir el comprobante.");
      return;
    }
    busy.current = true;
    setPending(true);
    setFeedback("");
    const generation = usePosAuthStore.getState().generation;
    const epoch = receiptEpoch.current;
    const isCurrent = () => usePosAuthStore.getState().generation === generation && receiptEpoch.current === epoch;
    try {
      const context: PrintContext = { userId: auth.user.id, workstationId: auth.session.workstation_id,
        workstationCode, sourceKind: receipt.source_kind, sourceId: receipt.source_id };
      const previous = browserPrintIntentions.read(printScope(context));
      const result = isCommandIntentionPending(previous)
        ? await browserPrintIntentions.recover(context)
        : await browserPrintIntentions.begin(context,
          { workstation_code: workstationCode, reason: "Copia solicitada desde el comprobante" }, previous?.key ?? null);
      if (!isCurrent()) {
        printWindow.close();
        return;
      }
      writePrintableDocument(printWindow, buildOperationalReceiptPrintDocument(result.receipt));
      setFeedback("Diálogo abierto; verifica la salida en la impresora.");
    } catch {
      printWindow.close();
      if (isCurrent()) setFeedback("No se pudo abrir el comprobante. Consulta la misma intención antes de otra copia.");
    } finally {
      busy.current = false;
      if (isCurrent()) setPending(false);
    }
  }

  return (
    <div className="mt-2">
      {receipt && workstationCode ? (
        <HardwareReceiptAction key={receipt.source_id} receipt={receipt} workstationCode={workstationCode} />
      ) : null}
      <button type="button" className="min-h-12 rounded-lg border border-slate-300 px-3 py-2"
        disabled={!receipt || !workstationCode || pending || !auth.isAuthenticated} onClick={() => void requestPrint()}>
        {pending ? "Preparando comprobante…" : "Imprimir comprobante"}
      </button>
      <p className="text-xs text-slate-600" role="status">{feedback || (!receipt
        ? "El documento histórico no conserva un comprobante inmutable."
        : "Impresión de navegador; salida física sin verificar.")}</p>
    </div>
  );
}
