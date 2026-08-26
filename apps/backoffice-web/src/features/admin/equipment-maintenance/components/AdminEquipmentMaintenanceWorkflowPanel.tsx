import { useState } from "react";

import type {
  AdminEquipmentCreatePayload,
  AdminEquipmentFilterOptions,
  AdminEquipmentListItem,
  AdminEquipmentOperationalStatus,
  AdminEquipmentRiskLevel,
  AdminMaintenanceCompletePayload,
  AdminMaintenanceCreatePayload,
  AdminMaintenanceRecordListItem,
  AdminMaintenanceResult,
  AdminMaintenanceStatus,
  AdminMaintenanceType,
} from "../types";

const fieldClassName =
  "h-10 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]";

const textareaClassName =
  "min-h-20 w-full min-w-0 resize-y rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]";

function nowLocalInputValue() {
  const value = new Date();
  value.setMinutes(value.getMinutes() - value.getTimezoneOffset());
  return value.toISOString().slice(0, 16);
}

function localInputToIso(value: string | null) {
  return value ? new Date(value).toISOString() : null;
}

function optionNodes(options: { id: string; label: string }[], label = "Selecciona") {
  return (
    <>
      <option value="">{label}</option>
      {options.map((option) => (
        <option key={option.id} value={option.id}>
          {option.label}
        </option>
      ))}
    </>
  );
}

interface AdminEquipmentMaintenanceWorkflowPanelProps {
  equipment: AdminEquipmentListItem[];
  errorMessage?: string | null;
  isSubmitting?: boolean;
  maintenanceRecord: AdminMaintenanceRecordListItem | null;
  mode: "equipment" | "maintenance" | "complete";
  options: AdminEquipmentFilterOptions;
  selectedEquipment: AdminEquipmentListItem | null;
  onCancel: () => void;
  onCompleteMaintenance: (payload: AdminMaintenanceCompletePayload) => void;
  onCreateEquipment: (payload: AdminEquipmentCreatePayload) => void;
  onCreateMaintenance: (payload: AdminMaintenanceCreatePayload) => void;
}

export function AdminEquipmentMaintenanceWorkflowPanel({
  equipment,
  errorMessage,
  isSubmitting = false,
  maintenanceRecord,
  mode,
  onCancel,
  onCompleteMaintenance,
  onCreateEquipment,
  onCreateMaintenance,
  options,
  selectedEquipment,
}: AdminEquipmentMaintenanceWorkflowPanelProps) {
  const [branchId, setBranchId] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [equipmentType, setEquipmentType] = useState("OVEN");
  const [areaName, setAreaName] = useState("");
  const [areaType, setAreaType] = useState("PRODUCTION");
  const [operationalStatus, setOperationalStatus] =
    useState<AdminEquipmentOperationalStatus>("OPERATIONAL");
  const [riskLevel, setRiskLevel] = useState<AdminEquipmentRiskLevel>("MEDIUM");
  const [brand, setBrand] = useState("");
  const [model, setModel] = useState("");
  const [serialNumber, setSerialNumber] = useState("");
  const [purchaseDate, setPurchaseDate] = useState("");
  const [warrantyExpiresAt, setWarrantyExpiresAt] = useState("");
  const [providerName, setProviderName] = useState("");
  const [frequencyDays, setFrequencyDays] = useState("");
  const [isCritical, setIsCritical] = useState(false);
  const [foodSafetyCritical, setFoodSafetyCritical] = useState(false);
  const [equipmentNotes, setEquipmentNotes] = useState("");

  const [maintenanceEquipmentId, setMaintenanceEquipmentId] = useState(
    selectedEquipment?.id ?? "",
  );
  const [maintenanceType, setMaintenanceType] = useState<AdminMaintenanceType>("PREVENTIVE");
  const [maintenanceStatus, setMaintenanceStatus] = useState<AdminMaintenanceStatus>("PENDING");
  const [scheduledAt, setScheduledAt] = useState(nowLocalInputValue());
  const [maintenanceProvider, setMaintenanceProvider] = useState("");
  const [technicianName, setTechnicianName] = useState("");
  const [expectedCost, setExpectedCost] = useState("");
  const [description, setDescription] = useState("");
  const [relatedIncidentReference, setRelatedIncidentReference] = useState("");
  const [sourceDocumentReference, setSourceDocumentReference] = useState("");
  const [sourceDocumentType, setSourceDocumentType] = useState("");
  const [startImmediately, setStartImmediately] = useState(false);

  const [completedAt, setCompletedAt] = useState(nowLocalInputValue());
  const [result, setResult] = useState<AdminMaintenanceResult>("COMPLETED_SUCCESSFULLY");
  const [cost, setCost] = useState("");
  const [completionNotes, setCompletionNotes] = useState("");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [statusAfterService, setStatusAfterService] =
    useState<AdminEquipmentOperationalStatus>("OPERATIONAL");
  const [localError, setLocalError] = useState<string | null>(null);

  function handleEquipmentSubmit() {
    setLocalError(null);
    if (!name.trim()) {
      setLocalError("Captura el nombre del equipo.");
      return;
    }
    if (!code.trim()) {
      setLocalError("Captura el codigo o activo del equipo.");
      return;
    }
    if (!branchId) {
      setLocalError("Selecciona una sucursal.");
      return;
    }
    const frequency = frequencyDays ? Number(frequencyDays) : null;
    if (frequency !== null && (!Number.isFinite(frequency) || frequency <= 0)) {
      setLocalError("La frecuencia debe ser mayor a cero.");
      return;
    }
    if (purchaseDate && warrantyExpiresAt && warrantyExpiresAt < purchaseDate) {
      setLocalError("La garantia debe vencer despues de la fecha de compra.");
      return;
    }
    onCreateEquipment({
      areaName: areaName.trim() || null,
      areaType,
      branchId,
      brand: brand.trim() || null,
      code: code.trim(),
      equipmentType,
      foodSafetyCritical,
      isCritical,
      maintenanceFrequencyDays: frequency,
      model: model.trim() || null,
      name: name.trim(),
      notes: equipmentNotes.trim() || null,
      operationalStatus,
      providerName: providerName.trim() || null,
      purchaseDate: purchaseDate || null,
      riskLevel,
      serialNumber: serialNumber.trim() || null,
      warrantyExpiresAt: warrantyExpiresAt || null,
    });
  }

  function handleMaintenanceSubmit() {
    setLocalError(null);
    if (!maintenanceEquipmentId) {
      setLocalError("Selecciona un equipo.");
      return;
    }
    if (!description.trim()) {
      setLocalError("Captura la descripcion del mantenimiento.");
      return;
    }
    if (maintenanceStatus === "SCHEDULED" && !scheduledAt) {
      setLocalError("El mantenimiento programado requiere fecha.");
      return;
    }
    if (expectedCost && Number(expectedCost) < 0) {
      setLocalError("El costo esperado no puede ser negativo.");
      return;
    }
    onCreateMaintenance({
      description: description.trim(),
      equipmentId: maintenanceEquipmentId,
      expectedCost: expectedCost.trim() || null,
      maintenanceType,
      providerName: maintenanceProvider.trim() || null,
      relatedIncidentReference: relatedIncidentReference.trim() || null,
      scheduledAt: scheduledAt ? localInputToIso(scheduledAt) : null,
      sourceDocumentReference: sourceDocumentReference.trim() || null,
      sourceDocumentType: sourceDocumentType.trim() || null,
      startImmediately,
      status: maintenanceStatus,
      technicianName: technicianName.trim() || null,
    });
  }

  function handleCompleteSubmit() {
    setLocalError(null);
    if (!maintenanceRecord) {
      setLocalError("Selecciona un mantenimiento abierto.");
      return;
    }
    if (cost && Number(cost) < 0) {
      setLocalError("El costo no puede ser negativo.");
      return;
    }
    if (
      (result === "FAILED" ||
        result === "REQUIRES_FOLLOW_UP" ||
        result === "COMPLETED_WITH_OBSERVATIONS") &&
      !completionNotes.trim()
    ) {
      setLocalError("El resultado fallido o parcial requiere notas.");
      return;
    }
    onCompleteMaintenance({
      completedAt: localInputToIso(completedAt),
      cost: cost.trim() || null,
      equipmentStatusAfterService: statusAfterService,
      evidenceNote: evidenceNote.trim() || null,
      notes: completionNotes.trim() || null,
      result,
      technicianName: technicianName.trim() || null,
    });
  }

  const title =
    mode === "equipment"
      ? "Nuevo equipo"
      : mode === "maintenance"
        ? "Nuevo mantenimiento"
        : `Completar ${maintenanceRecord?.folio ?? "mantenimiento"}`;

  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80 p-4">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Control de mantenimiento auditado
          </p>
          <h3 className="mt-1 text-base font-semibold text-slate-950">{title}</h3>
          <p className="mt-1 text-sm leading-5 text-slate-600">
            Registra equipos y mantenimientos con sucursal, costo, proveedor, evidencia y estado
            operativo persistidos por backend.
          </p>
        </div>
        <button
          className="shrink-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={onCancel}
        >
          Cerrar
        </button>
      </div>

      {mode === "equipment" ? (
        <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Sucursal
            <select className={fieldClassName} value={branchId} onChange={(event) => setBranchId(event.target.value)}>
              {optionNodes(options.branches)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Codigo / activo
            <input className={fieldClassName} value={code} onChange={(event) => setCode(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Equipo
            <input className={fieldClassName} value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tipo
            <select className={fieldClassName} value={equipmentType} onChange={(event) => setEquipmentType(event.target.value)}>
              {optionNodes(options.equipmentTypes)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Area
            <input className={fieldClassName} value={areaName} onChange={(event) => setAreaName(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tipo area
            <select className={fieldClassName} value={areaType} onChange={(event) => setAreaType(event.target.value)}>
              {optionNodes(options.areaTypes)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Estado
            <select
              className={fieldClassName}
              value={operationalStatus}
              onChange={(event) =>
                setOperationalStatus(event.target.value as AdminEquipmentOperationalStatus)
              }
            >
              {optionNodes(options.operationalStatuses)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Riesgo
            <select
              className={fieldClassName}
              value={riskLevel}
              onChange={(event) => setRiskLevel(event.target.value as AdminEquipmentRiskLevel)}
            >
              {optionNodes(options.riskLevels)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Marca
            <input className={fieldClassName} value={brand} onChange={(event) => setBrand(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Modelo
            <input className={fieldClassName} value={model} onChange={(event) => setModel(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Serie
            <input className={fieldClassName} value={serialNumber} onChange={(event) => setSerialNumber(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Proveedor
            <input className={fieldClassName} value={providerName} onChange={(event) => setProviderName(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Compra
            <input className={fieldClassName} type="date" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Garantia
            <input className={fieldClassName} type="date" value={warrantyExpiresAt} onChange={(event) => setWarrantyExpiresAt(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Frecuencia dias
            <input className={fieldClassName} min="1" type="number" value={frequencyDays} onChange={(event) => setFrequencyDays(event.target.value)} />
          </label>
          <div className="flex items-center gap-4 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2">
            <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
              <input checked={isCritical} type="checkbox" onChange={(event) => setIsCritical(event.target.checked)} />
              Critico
            </label>
            <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
              <input checked={foodSafetyCritical} type="checkbox" onChange={(event) => setFoodSafetyCritical(event.target.checked)} />
              Inocuidad
            </label>
          </div>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 md:col-span-2 xl:col-span-4">
            Notas
            <textarea className={textareaClassName} value={equipmentNotes} onChange={(event) => setEquipmentNotes(event.target.value)} />
          </label>
        </div>
      ) : null}

      {mode === "maintenance" ? (
        <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Equipo
            <select
              className={fieldClassName}
              value={maintenanceEquipmentId}
              onChange={(event) => setMaintenanceEquipmentId(event.target.value)}
            >
              {optionNodes(equipment.map((item) => ({ id: item.id, label: `${item.code} ${item.name}` })))}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tipo
            <select
              className={fieldClassName}
              value={maintenanceType}
              onChange={(event) => setMaintenanceType(event.target.value as AdminMaintenanceType)}
            >
              {optionNodes(options.maintenanceTypes)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Estado
            <select
              className={fieldClassName}
              value={maintenanceStatus}
              onChange={(event) => setMaintenanceStatus(event.target.value as AdminMaintenanceStatus)}
            >
              <option value="PENDING">Pendiente</option>
              <option value="SCHEDULED">Programado</option>
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Programado
            <input className={fieldClassName} type="datetime-local" value={scheduledAt} onChange={(event) => setScheduledAt(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Proveedor
            <input className={fieldClassName} value={maintenanceProvider} onChange={(event) => setMaintenanceProvider(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tecnico
            <input className={fieldClassName} value={technicianName} onChange={(event) => setTechnicianName(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Costo esperado
            <input className={fieldClassName} min="0" type="number" value={expectedCost} onChange={(event) => setExpectedCost(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Incidencia ref.
            <input className={fieldClassName} value={relatedIncidentReference} onChange={(event) => setRelatedIncidentReference(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tipo origen
            <input className={fieldClassName} value={sourceDocumentType} onChange={(event) => setSourceDocumentType(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Origen ref.
            <input className={fieldClassName} value={sourceDocumentReference} onChange={(event) => setSourceDocumentReference(event.target.value)} />
          </label>
          <label className="flex items-center gap-2 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700">
            <input checked={startImmediately} type="checkbox" onChange={(event) => setStartImmediately(event.target.checked)} />
            Iniciar ahora
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 md:col-span-2 xl:col-span-4">
            Descripcion
            <textarea className={textareaClassName} value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
        </div>
      ) : null}

      {mode === "complete" ? (
        <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Resultado
            <select
              className={fieldClassName}
              value={result}
              onChange={(event) => setResult(event.target.value as AdminMaintenanceResult)}
            >
              <option value="COMPLETED_SUCCESSFULLY">Completado correctamente</option>
              <option value="COMPLETED_WITH_OBSERVATIONS">Con observaciones</option>
              <option value="FAILED">Fallido</option>
              <option value="REQUIRES_FOLLOW_UP">Requiere seguimiento</option>
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Completado
            <input className={fieldClassName} type="datetime-local" value={completedAt} onChange={(event) => setCompletedAt(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Costo
            <input className={fieldClassName} min="0" type="number" value={cost} onChange={(event) => setCost(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Estado posterior
            <select
              className={fieldClassName}
              value={statusAfterService}
              onChange={(event) =>
                setStatusAfterService(event.target.value as AdminEquipmentOperationalStatus)
              }
            >
              <option value="OPERATIONAL">Operativo</option>
              <option value="OUT_OF_SERVICE">Fuera de servicio</option>
              <option value="UNDER_MAINTENANCE">En mantenimiento</option>
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Tecnico
            <input className={fieldClassName} value={technicianName} onChange={(event) => setTechnicianName(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 md:col-span-2">
            Evidencia
            <textarea className={textareaClassName} value={evidenceNote} onChange={(event) => setEvidenceNote(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 md:col-span-2">
            Notas
            <textarea className={textareaClassName} value={completionNotes} onChange={(event) => setCompletionNotes(event.target.value)} />
          </label>
        </div>
      ) : null}

      {localError || errorMessage ? (
        <p className="mt-3 rounded-[16px] border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {localError ?? errorMessage}
        </p>
      ) : null}

      <div className="mt-4 flex min-w-0 flex-wrap items-center justify-between gap-3 border-t border-[var(--ui-color-border)] pt-3">
        <p className="min-w-0 text-sm leading-5 text-slate-600">
          No se editan cortes, inventario ni incidencias desde aqui; solo se registra control de
          equipos y mantenimientos auditados.
        </p>
        <button
          className="shrink-0 rounded-2xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--ui-color-primary-strong)] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-600"
          disabled={isSubmitting}
          type="button"
          onClick={
            mode === "equipment"
              ? handleEquipmentSubmit
              : mode === "maintenance"
                ? handleMaintenanceSubmit
                : handleCompleteSubmit
          }
        >
          {mode === "equipment"
            ? "Guardar equipo"
            : mode === "maintenance"
              ? "Guardar mantenimiento"
              : "Completar mantenimiento"}
        </button>
      </div>
    </section>
  );
}
