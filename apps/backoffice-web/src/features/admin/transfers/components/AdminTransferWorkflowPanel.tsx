import { AdminActionButton } from "../../components/AdminActionButton";
import { hasEffectiveCapability, type PermissionCode } from "../../../auth/authorization";
import { useBackofficeAuthorization } from "../../../auth/authorization-context";
import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import type {
  AdminTransferCreatePayload,
  AdminTransferDetail,
  AdminTransferFilterOption,
  AdminTransferLinePayload,
  AdminTransferReceivePayload,
  AdminTransferUpdatePayload,
} from "../types";

const inputClassName =
  "h-10 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

type WorkflowMode = "cancel" | "create" | "dispatch" | "edit" | "receive";

interface DraftLineState {
  id: string;
  notes: string;
  productId: string;
  quantity: string;
}

interface ReceiveLineState {
  notes: string;
  receivedQuantity: string;
  shipmentLineId: string;
  varianceReason: string;
}

interface AdminTransferWorkflowPanelProps {
  branchOptions: AdminTransferFilterOption[];
  errorMessage?: string | null;
  isSubmitting?: boolean;
  mode: WorkflowMode;
  onCancelTransfer: (reason: string | null) => void;
  onClose: () => void;
  onCreate: (payload: AdminTransferCreatePayload, dispatchNow: boolean) => void;
  onDispatch: (notes: string | null) => void;
  onReceive: (payload: AdminTransferReceivePayload) => void;
  onUpdate: (payload: AdminTransferUpdatePayload) => void;
  productOptions: AdminTransferFilterOption[];
  transfer?: AdminTransferDetail | null;
}

function getTitle(mode: WorkflowMode): string {
  const labels: Record<WorkflowMode, string> = {
    cancel: "Cancelar transferencia",
    create: "Nueva transferencia",
    dispatch: "Enviar transferencia",
    edit: "Editar borrador",
    receive: "Recibir transferencia",
  };

  return labels[mode];
}

function getDescription(mode: WorkflowMode, transfer?: AdminTransferDetail | null): string {
  if (mode === "create") {
    return "Crea un documento persistido antes de afectar inventario.";
  }
  if (mode === "edit") {
    return transfer
      ? `${transfer.overview.folio} - solo disponible en borrador.`
      : "Solo disponible en borrador.";
  }
  if (mode === "dispatch") {
    return transfer
      ? `${transfer.overview.folio} saldra de la sucursal origen.`
      : "Confirma salida de origen.";
  }
  if (mode === "receive") {
    return transfer
      ? `${transfer.overview.folio} se recibe en destino.`
      : "Captura cantidades recibidas.";
  }
  return transfer
    ? `${transfer.overview.folio} quedara cancelada si backend lo permite.`
    : "Cancelacion controlada.";
}

function buildInitialDraftLines(transfer?: AdminTransferDetail | null): DraftLineState[] {
  if (transfer?.lines.length) {
    return transfer.lines.map((line) => ({
      id: line.shipmentLineId,
      notes: line.notes ?? "",
      productId: line.productId,
      quantity: line.requestedQuantity,
    }));
  }

  return [{ id: crypto.randomUUID(), notes: "", productId: "", quantity: "" }];
}

function toDraftPayload(lines: DraftLineState[]): AdminTransferLinePayload[] {
  return lines.map((line) => ({
    notes: line.notes.trim() || null,
    productId: line.productId,
    quantity: line.quantity,
  }));
}

export function AdminTransferWorkflowPanel({
  branchOptions: allBranchOptions,
  errorMessage,
  isSubmitting = false,
  mode,
  onCancelTransfer,
  onClose,
  onCreate,
  onDispatch,
  onReceive,
  onUpdate,
  productOptions,
  transfer,
}: AdminTransferWorkflowPanelProps) {
  const actor = useBackofficeAuthorization();
  const actionCapability: PermissionCode =
    mode === "cancel"
      ? "transfers.cancel"
      : mode === "dispatch" || mode === "receive"
        ? "transfers.execute"
        : "transfers.manage";
  const branchOptions = useMemo(
    () =>
      allBranchOptions.filter((option) =>
        hasEffectiveCapability(actor, actionCapability, [option.id]),
      ),
    [actor, actionCapability, allBranchOptions],
  );
  const [destinationBranchId, setDestinationBranchId] = useState(
    transfer?.destination.branchId || branchOptions[1]?.id || branchOptions[0]?.id || "",
  );
  const [draftLines, setDraftLines] = useState<DraftLineState[]>(() =>
    buildInitialDraftLines(transfer),
  );
  const [localError, setLocalError] = useState<string | null>(null);
  const [notes, setNotes] = useState(transfer?.overview.notes ?? "");
  const [originBranchId, setOriginBranchId] = useState(
    transfer?.origin.branchId || branchOptions[0]?.id || "",
  );
  const [receiveLines, setReceiveLines] = useState<ReceiveLineState[]>(() =>
    (transfer?.lines ?? []).map((line) => ({
      notes: "",
      receivedQuantity: line.sentQuantity,
      shipmentLineId: line.shipmentLineId,
      varianceReason: line.varianceReason ?? "",
    })),
  );
  const [reason, setReason] = useState("");

  const selectedOriginLabel = useMemo(
    () =>
      branchOptions.find((option) => option.id === originBranchId)?.label ??
      "Origen no seleccionado",
    [branchOptions, originBranchId],
  );
  const selectedDestinationLabel = useMemo(
    () =>
      branchOptions.find((option) => option.id === destinationBranchId)?.label ??
      "Destino no seleccionado",
    [branchOptions, destinationBranchId],
  );

  function updateDraftLine(id: string, patch: Partial<DraftLineState>) {
    setDraftLines((current) =>
      current.map((line) => (line.id === id ? { ...line, ...patch } : line)),
    );
  }

  function removeDraftLine(id: string) {
    setDraftLines((current) =>
      current.length > 1 ? current.filter((line) => line.id !== id) : current,
    );
  }

  function addDraftLine() {
    setDraftLines((current) => [
      ...current,
      { id: crypto.randomUUID(), notes: "", productId: productOptions[0]?.id ?? "", quantity: "" },
    ]);
  }

  function updateReceiveLine(shipmentLineId: string, patch: Partial<ReceiveLineState>) {
    setReceiveLines((current) =>
      current.map((line) =>
        line.shipmentLineId === shipmentLineId ? { ...line, ...patch } : line,
      ),
    );
  }

  function validateDraft(): boolean {
    if (!originBranchId) {
      setLocalError("Selecciona una sucursal origen.");
      return false;
    }
    if (!destinationBranchId) {
      setLocalError("Selecciona una sucursal destino.");
      return false;
    }
    if (originBranchId === destinationBranchId) {
      setLocalError("Origen y destino no pueden ser la misma sucursal.");
      return false;
    }
    if (
      draftLines.length === 0 ||
      draftLines.some((line) => !line.productId || !line.quantity || Number(line.quantity) <= 0)
    ) {
      setLocalError("Agrega al menos una linea con producto y cantidad mayor que cero.");
      return false;
    }
    return true;
  }

  function validateReceipt(): boolean {
    if (!transfer) {
      setLocalError("Selecciona una transferencia para recibir.");
      return false;
    }
    for (const receiveLine of receiveLines) {
      const sourceLine = transfer.lines.find(
        (line) => line.shipmentLineId === receiveLine.shipmentLineId,
      );
      if (
        !sourceLine ||
        receiveLine.receivedQuantity === "" ||
        Number(receiveLine.receivedQuantity) < 0
      ) {
        setLocalError("Las cantidades recibidas deben ser cero o mayores.");
        return false;
      }
      if (
        Number(receiveLine.receivedQuantity) !== Number(sourceLine.sentQuantity) &&
        !receiveLine.varianceReason.trim()
      ) {
        setLocalError("Captura una razon para cada discrepancia entre enviado y recibido.");
        return false;
      }
    }
    return true;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!hasEffectiveCapability(actor, actionCapability, [originBranchId, destinationBranchId]))
      return;
    setLocalError(null);

    if (mode === "create" || mode === "edit") {
      if (!validateDraft()) {
        return;
      }
      const lines = toDraftPayload(draftLines);
      if (mode === "edit") {
        onUpdate({
          destinationBranchId,
          lines,
          notes: notes.trim() || null,
          originBranchId,
        });
        return;
      }
      onCreate(
        {
          destinationBranchId,
          lines,
          notes: notes.trim() || null,
          originBranchId,
        },
        false,
      );
      return;
    }

    if (mode === "dispatch") {
      onDispatch(notes.trim() || null);
      return;
    }

    if (mode === "receive") {
      if (!validateReceipt()) {
        return;
      }
      onReceive({
        lines: receiveLines.map((line) => ({
          notes: line.notes.trim() || null,
          receivedQuantity: line.receivedQuantity,
          shipmentLineId: line.shipmentLineId,
          varianceReason: line.varianceReason.trim() || null,
        })),
        notes: notes.trim() || null,
      });
      return;
    }

    onCancelTransfer(reason.trim() || null);
  }

  function handleCreateAndDispatch() {
    if (
      !hasEffectiveCapability(actor, "transfers.manage", [originBranchId, destinationBranchId]) ||
      !hasEffectiveCapability(actor, "transfers.execute", [originBranchId, destinationBranchId])
    )
      return;
    setLocalError(null);
    if (!validateDraft()) {
      return;
    }
    onCreate(
      {
        destinationBranchId,
        lines: toDraftPayload(draftLines),
        notes: notes.trim() || null,
        originBranchId,
      },
      true,
    );
  }

  return (
    <form
      className="grid min-w-0 gap-3 rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3"
      onSubmit={handleSubmit}
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">{getTitle(mode)}</h3>
          <p className="truncate text-xs text-slate-500" title={getDescription(mode, transfer)}>
            {getDescription(mode, transfer)}
          </p>
        </div>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cerrar
        </button>
      </div>

      {(localError || errorMessage) && (
        <p className="rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {localError ?? errorMessage}
        </p>
      )}

      {mode === "create" || mode === "edit" ? (
        <>
          <div className="grid min-w-0 gap-2 lg:grid-cols-2">
            <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
              Origen
              <select
                className={`${inputClassName} truncate`}
                disabled={branchOptions.length === 0 || mode === "edit"}
                title={selectedOriginLabel}
                value={originBranchId}
                onChange={(event) => setOriginBranchId(event.target.value)}
              >
                {branchOptions.length === 0 ? (
                  <option value="">Sucursales pendientes de API</option>
                ) : null}
                {branchOptions.map((option) => (
                  <option key={option.id} title={option.label} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
              Destino
              <select
                className={`${inputClassName} truncate`}
                disabled={branchOptions.length === 0 || mode === "edit"}
                title={selectedDestinationLabel}
                value={destinationBranchId}
                onChange={(event) => setDestinationBranchId(event.target.value)}
              >
                {branchOptions.length === 0 ? (
                  <option value="">Sucursales pendientes de API</option>
                ) : null}
                {branchOptions.map((option) => (
                  <option key={option.id} title={option.label} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 p-2.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                Lineas
              </span>
              <button
                className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                type="button"
                onClick={addDraftLine}
              >
                Agregar producto
              </button>
            </div>
            {draftLines.map((line, index) => (
              <div
                className="grid min-w-0 gap-2 rounded-[16px] border border-[var(--ui-color-border)] bg-white p-2 md:grid-cols-[minmax(12rem,1fr)_7rem_minmax(10rem,0.85fr)_auto]"
                key={line.id}
              >
                <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  Producto {index + 1}
                  <select
                    className={`${inputClassName} truncate`}
                    disabled={productOptions.length === 0}
                    value={line.productId}
                    onChange={(event) =>
                      updateDraftLine(line.id, { productId: event.target.value })
                    }
                  >
                    <option value="">Selecciona producto</option>
                    {productOptions.map((option) => (
                      <option key={option.id} title={option.label} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  Cantidad
                  <input
                    className={inputClassName}
                    min="0.001"
                    placeholder="0.000"
                    step="0.001"
                    type="number"
                    value={line.quantity}
                    onChange={(event) => updateDraftLine(line.id, { quantity: event.target.value })}
                  />
                </label>
                <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  Notas linea
                  <input
                    className={inputClassName}
                    maxLength={180}
                    placeholder="Opcional"
                    value={line.notes}
                    onChange={(event) => updateDraftLine(line.id, { notes: event.target.value })}
                  />
                </label>
                <div className="flex items-end">
                  <button
                    className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                    disabled={draftLines.length === 1}
                    type="button"
                    onClick={() => removeDraftLine(line.id)}
                  >
                    Quitar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}

      {mode === "receive" && transfer ? (
        <div className="grid gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 p-2.5">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Recepcion
          </span>
          {transfer.lines.map((line) => {
            const receiveLine = receiveLines.find(
              (item) => item.shipmentLineId === line.shipmentLineId,
            );
            const hasDifference =
              Number(receiveLine?.receivedQuantity ?? "0") !== Number(line.sentQuantity);

            return (
              <div
                className="grid min-w-0 gap-2 rounded-[16px] border border-[var(--ui-color-border)] bg-white p-2 lg:grid-cols-[minmax(12rem,1fr)_7rem_minmax(11rem,0.9fr)_minmax(10rem,0.8fr)]"
                key={line.shipmentLineId}
              >
                <div className="min-w-0">
                  <p
                    className="truncate text-sm font-semibold text-slate-950"
                    title={line.productName}
                  >
                    {line.productName}
                  </p>
                  <p className="truncate font-mono text-xs text-slate-500" title={line.productCode}>
                    {line.productCode} - enviado {line.sentQuantity} {line.unitOfMeasure}
                  </p>
                </div>
                <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  Recibido
                  <input
                    className={inputClassName}
                    min="0"
                    step="0.001"
                    type="number"
                    value={receiveLine?.receivedQuantity ?? ""}
                    onChange={(event) =>
                      updateReceiveLine(line.shipmentLineId, {
                        receivedQuantity: event.target.value,
                      })
                    }
                  />
                </label>
                <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  Razon si difiere
                  <input
                    className={inputClassName}
                    disabled={!hasDifference}
                    maxLength={180}
                    placeholder={hasDifference ? "Obligatoria" : "Sin diferencia"}
                    value={receiveLine?.varianceReason ?? ""}
                    onChange={(event) =>
                      updateReceiveLine(line.shipmentLineId, { varianceReason: event.target.value })
                    }
                  />
                </label>
                <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  Notas
                  <input
                    className={inputClassName}
                    maxLength={180}
                    placeholder="Opcional"
                    value={receiveLine?.notes ?? ""}
                    onChange={(event) =>
                      updateReceiveLine(line.shipmentLineId, { notes: event.target.value })
                    }
                  />
                </label>
              </div>
            );
          })}
        </div>
      ) : null}

      {mode === "cancel" ? (
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Motivo / notas
          <textarea
            className="min-h-20 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-medium normal-case tracking-normal text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            maxLength={500}
            placeholder="Contexto de cancelacion si aplica."
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
      ) : null}

      {mode !== "cancel" ? (
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Notas
          <textarea
            className="min-h-20 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-medium normal-case tracking-normal text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            maxLength={500}
            placeholder="Contexto operativo, empaque, responsable o evidencia disponible."
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>
      ) : null}

      <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
        Las transferencias son documentos auditados. El inventario se afecta solo al enviar o
        recibir mediante backend.
      </p>

      <div className="flex min-w-0 flex-wrap justify-end gap-2 border-t border-[var(--ui-color-border)] pt-3">
        <button
          className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onClose}
        >
          Cerrar
        </button>
        {mode === "create" ? (
          <AdminActionButton
            capability="transfers.manage"
            additionalCapabilities={["transfers.execute"]}
            branchIds={[originBranchId, destinationBranchId]}
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-4 py-2 text-sm font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={isSubmitting}
            type="button"
            onClick={handleCreateAndDispatch}
          >
            Guardar y enviar
          </AdminActionButton>
        ) : null}
        <AdminActionButton
          capability={actionCapability}
          branchIds={[originBranchId, destinationBranchId]}
          className="rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--ui-color-primary-strong)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting
            ? "Guardando"
            : mode === "create"
              ? "Guardar borrador"
              : mode === "edit"
                ? "Guardar cambios"
                : mode === "receive"
                  ? "Confirmar recepcion"
                  : mode === "dispatch"
                    ? "Confirmar envio"
                    : "Cancelar transferencia"}
        </AdminActionButton>
      </div>
    </form>
  );
}
