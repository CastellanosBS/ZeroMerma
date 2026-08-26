import { useEffect, useMemo, useState } from "react";

import type {
  AdminInputSupplyDetail,
  AdminInputSupplyFilterOption,
  AdminInputSupplyKind,
  AdminInputSupplyPayload,
  AdminInputSupplySupplierRelationPayload,
} from "../types";

interface AdminInputSupplyFormPanelProps {
  classOptions: AdminInputSupplyFilterOption[];
  errorMessage?: string | null;
  initialInput?: AdminInputSupplyDetail | null;
  isSubmitting: boolean;
  supplierOptions: AdminInputSupplyFilterOption[];
  usageTypeOptions: AdminInputSupplyFilterOption[];
  onClose: () => void;
  onSubmit: (payload: AdminInputSupplyPayload) => void;
}

interface SupplierRelationDraft extends AdminInputSupplySupplierRelationPayload {
  localId: string;
}

const inputClassName =
  "rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-950 outline-none transition focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:bg-slate-100 disabled:text-slate-500";

const uomOptions = ["PCS", "KG", "G", "L", "ML"];

function relationDraftFromDetail(
  initialInput?: AdminInputSupplyDetail | null,
): SupplierRelationDraft[] {
  return (
    initialInput?.suppliers.map((relation) => ({
      conversionFactor: relation.conversionFactor,
      currency: relation.currency,
      isActive: relation.isActive,
      lastKnownPrice: relation.lastKnownPrice,
      leadTimeDays: relation.leadTimeDays,
      localId: relation.id,
      minimumOrderQty: relation.minimumOrderQty,
      notes: relation.notes,
      purchaseUom: relation.purchaseUom,
      supplierId: relation.supplierId,
      supplierSku: relation.supplierSku,
    })) ?? []
  );
}

function isNegative(value: string | null | undefined): boolean {
  if (!value?.trim()) {
    return false;
  }
  return Number(value) < 0;
}

function isNonPositive(value: string | null | undefined): boolean {
  if (!value?.trim()) {
    return false;
  }
  return Number(value) <= 0;
}

function normalizeOptional(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

export function AdminInputSupplyFormPanel({
  classOptions,
  errorMessage,
  initialInput,
  isSubmitting,
  supplierOptions,
  usageTypeOptions,
  onClose,
  onSubmit,
}: AdminInputSupplyFormPanelProps) {
  const initialRelations = useMemo(() => relationDraftFromDetail(initialInput), [initialInput]);
  const firstClassId = classOptions[0]?.id ?? "";
  const [code, setCode] = useState(initialInput?.overview.code ?? "");
  const [isActive, setIsActive] = useState(initialInput?.overview.isActive ?? true);
  const [isInventoryTracked, setIsInventoryTracked] = useState(
    initialInput?.overview.isInventoryTracked ?? true,
  );
  const [isPurchasable, setIsPurchasable] = useState(initialInput?.overview.isPurchasable ?? true);
  const [minimumStock, setMinimumStock] = useState(
    initialInput?.inventoryStatus.minimumStock ?? "",
  );
  const [name, setName] = useState(initialInput?.overview.name ?? "");
  const [preferredOrderQuantity, setPreferredOrderQuantity] = useState(
    initialInput?.inventoryStatus.preferredOrderQuantity ?? "",
  );
  const [procurementNotes, setProcurementNotes] = useState(
    initialInput?.classification.notes ?? "",
  );
  const [productClassId, setProductClassId] = useState(
    initialInput?.overview.categoryId ?? firstClassId,
  );
  const [productKind, setProductKind] = useState<AdminInputSupplyKind>(
    initialInput?.overview.productKind ?? "RAW_MATERIAL",
  );
  const [purchaseConversionFactor, setPurchaseConversionFactor] = useState(
    initialInput?.unitsConversion.conversionFactor ?? "",
  );
  const [purchaseUom, setPurchaseUom] = useState(initialInput?.overview.purchaseUom ?? "");
  const [reorderPoint, setReorderPoint] = useState(
    initialInput?.inventoryStatus.reorderPoint ?? "",
  );
  const [standardCost, setStandardCost] = useState(initialInput?.overview.standardCost ?? "");
  const [supplierRelations, setSupplierRelations] =
    useState<SupplierRelationDraft[]>(initialRelations);
  const [unitOfMeasure, setUnitOfMeasure] = useState(initialInput?.overview.baseUom ?? "KG");
  const [usageType, setUsageType] = useState(initialInput?.classification.usageType ?? "");
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  useEffect(() => {
    const nextRelations = relationDraftFromDetail(initialInput);
    setCode(initialInput?.overview.code ?? "");
    setIsActive(initialInput?.overview.isActive ?? true);
    setIsInventoryTracked(initialInput?.overview.isInventoryTracked ?? true);
    setIsPurchasable(initialInput?.overview.isPurchasable ?? true);
    setMinimumStock(initialInput?.inventoryStatus.minimumStock ?? "");
    setName(initialInput?.overview.name ?? "");
    setPreferredOrderQuantity(initialInput?.inventoryStatus.preferredOrderQuantity ?? "");
    setProcurementNotes(initialInput?.classification.notes ?? "");
    setProductClassId(initialInput?.overview.categoryId ?? firstClassId);
    setProductKind(initialInput?.overview.productKind ?? "RAW_MATERIAL");
    setPurchaseConversionFactor(initialInput?.unitsConversion.conversionFactor ?? "");
    setPurchaseUom(initialInput?.overview.purchaseUom ?? "");
    setReorderPoint(initialInput?.inventoryStatus.reorderPoint ?? "");
    setStandardCost(initialInput?.overview.standardCost ?? "");
    setSupplierRelations(nextRelations);
    setUnitOfMeasure(initialInput?.overview.baseUom ?? "KG");
    setUsageType(initialInput?.classification.usageType ?? "");
    setValidationMessage(null);
  }, [firstClassId, initialInput]);

  function updateRelation(localId: string, patch: Partial<SupplierRelationDraft>) {
    setSupplierRelations((current) =>
      current.map((relation) =>
        relation.localId === localId ? { ...relation, ...patch } : relation,
      ),
    );
  }

  function addRelation() {
    const supplierId = supplierOptions.find(
      (option) =>
        !supplierRelations.some(
          (relation) => relation.supplierId === option.id && relation.isActive !== false,
        ),
    )?.id;
    if (!supplierId) {
      setValidationMessage("No hay proveedores disponibles para agregar o ya estan asociados.");
      return;
    }
    setSupplierRelations((current) => [
      ...current,
      {
        currency: "MXN",
        isActive: true,
        leadTimeDays: 0,
        localId: `new-${Date.now()}`,
        purchaseUom: purchaseUom || unitOfMeasure,
        supplierId,
      },
    ]);
  }

  function removeRelation(localId: string) {
    setSupplierRelations((current) =>
      current.map((relation) =>
        relation.localId === localId ? { ...relation, isActive: false } : relation,
      ),
    );
  }

  function validate(): string | null {
    if (!name.trim()) {
      return "El nombre del insumo es requerido.";
    }
    if (!code.trim()) {
      return "El codigo/SKU es requerido.";
    }
    if (!productClassId) {
      return "Selecciona una categoria o familia.";
    }
    if (!unitOfMeasure.trim()) {
      return "La unidad base es requerida.";
    }
    if (
      purchaseUom.trim() &&
      purchaseUom.trim().toUpperCase() !== unitOfMeasure.trim().toUpperCase()
    ) {
      if (!purchaseConversionFactor.trim()) {
        return "El factor de conversion es requerido cuando la unidad de compra difiere de la base.";
      }
      if (isNonPositive(purchaseConversionFactor)) {
        return "El factor de conversion debe ser mayor a cero.";
      }
    }
    if (
      isNegative(standardCost) ||
      isNegative(minimumStock) ||
      isNegative(reorderPoint) ||
      isNegative(preferredOrderQuantity)
    ) {
      return "Costos y cantidades de reorden no pueden ser negativos.";
    }
    const activeSupplierIds = supplierRelations
      .filter((relation) => relation.isActive !== false)
      .map((relation) => relation.supplierId);
    if (new Set(activeSupplierIds).size !== activeSupplierIds.length) {
      return "No se permiten relaciones activas duplicadas para el mismo proveedor.";
    }
    for (const relation of supplierRelations) {
      if (!relation.supplierId) {
        return "Cada relacion con proveedor debe tener proveedor.";
      }
      if (isNegative(relation.lastKnownPrice) || isNegative(relation.minimumOrderQty)) {
        return "Precio y cantidad minima de proveedor no pueden ser negativos.";
      }
      if (relation.leadTimeDays != null && Number(relation.leadTimeDays) < 0) {
        return "El lead time de proveedor no puede ser negativo.";
      }
      if (
        relation.purchaseUom &&
        relation.purchaseUom !== unitOfMeasure &&
        isNonPositive(relation.conversionFactor)
      ) {
        return "La relacion con proveedor requiere factor de conversion mayor a cero cuando cambia la unidad.";
      }
    }
    return null;
  }

  function handleSubmit() {
    const message = validate();
    if (message) {
      setValidationMessage(message);
      return;
    }
    setValidationMessage(null);
    onSubmit({
      code: code.trim().toUpperCase(),
      isActive,
      isInventoryTracked,
      isPurchasable,
      minimumStock: normalizeOptional(minimumStock),
      name: name.trim(),
      preferredOrderQuantity: normalizeOptional(preferredOrderQuantity),
      procurementNotes: normalizeOptional(procurementNotes),
      productClassId,
      productKind,
      purchaseConversionFactor: normalizeOptional(purchaseConversionFactor),
      purchaseUom: normalizeOptional(purchaseUom.toUpperCase()),
      reorderPoint: normalizeOptional(reorderPoint),
      standardCost: normalizeOptional(standardCost),
      supplierRelations: supplierRelations.map((relation) => ({
        conversionFactor: relation.conversionFactor ?? null,
        currency: relation.currency || "MXN",
        isActive: relation.isActive !== false,
        lastKnownPrice: relation.lastKnownPrice ?? null,
        leadTimeDays: Number(relation.leadTimeDays ?? 0),
        minimumOrderQty: relation.minimumOrderQty ?? null,
        notes: relation.notes ?? null,
        purchaseUom: relation.purchaseUom ? relation.purchaseUom.toUpperCase() : null,
        supplierId: relation.supplierId,
        supplierSku: relation.supplierSku ?? null,
      })),
      unitOfMeasure: unitOfMeasure.trim().toUpperCase(),
      usageType: normalizeOptional(usageType),
    });
  }

  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-4 shadow-[var(--ui-shadow-subtle)]">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            {initialInput ? "Editar insumo" : "Nuevo insumo"}
          </p>
          <h2 className="text-lg font-semibold text-slate-950">
            Catalogo comprable e inventariable
          </h2>
          <p className="text-sm text-slate-600">
            Configura identidad, unidades, costo, proveedores y reorden sin modificar stock
            directamente.
          </p>
        </div>
        <button
          className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700"
          type="button"
          onClick={onClose}
        >
          Cerrar
        </button>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <label className="flex flex-col gap-1 xl:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Nombre
          </span>
          <input
            className={inputClassName}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Codigo / SKU
          </span>
          <input
            className={inputClassName}
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Tipo
          </span>
          <select
            className={inputClassName}
            value={productKind}
            onChange={(event) => setProductKind(event.target.value as AdminInputSupplyKind)}
          >
            <option value="RAW_MATERIAL">Materia prima</option>
            <option value="CONSUMABLE">Consumible</option>
            <option value="DISPOSABLE">Desechable / empaque</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 xl:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Categoria / familia
          </span>
          <select
            className={inputClassName}
            value={productClassId}
            onChange={(event) => setProductClassId(event.target.value)}
          >
            <option value="">Selecciona categoria</option>
            {classOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700">
          <input
            checked={isActive}
            type="checkbox"
            onChange={(event) => setIsActive(event.target.checked)}
          />
          Activo
        </label>
        <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700">
          <input
            checked={isInventoryTracked}
            type="checkbox"
            onChange={(event) => setIsInventoryTracked(event.target.checked)}
          />
          Inventariable
        </label>
        <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700">
          <input
            checked={isPurchasable}
            type="checkbox"
            onChange={(event) => setIsPurchasable(event.target.checked)}
          />
          Comprable
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Unidad base
          </span>
          <select
            className={inputClassName}
            value={unitOfMeasure}
            onChange={(event) => setUnitOfMeasure(event.target.value)}
          >
            {uomOptions.map((uom) => (
              <option key={uom} value={uom}>
                {uom}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Unidad compra
          </span>
          <select
            className={inputClassName}
            value={purchaseUom}
            onChange={(event) => setPurchaseUom(event.target.value)}
          >
            <option value="">Sin unidad compra</option>
            {uomOptions.map((uom) => (
              <option key={uom} value={uom}>
                {uom}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Factor compra
          </span>
          <input
            className={inputClassName}
            min="0"
            step="0.001"
            type="number"
            value={purchaseConversionFactor}
            onChange={(event) => setPurchaseConversionFactor(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Uso
          </span>
          <select
            className={inputClassName}
            value={usageType}
            onChange={(event) => setUsageType(event.target.value)}
          >
            <option value="">No definido</option>
            {usageTypeOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Costo estandar
          </span>
          <input
            className={inputClassName}
            min="0"
            step="0.01"
            type="number"
            value={standardCost}
            onChange={(event) => setStandardCost(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Stock minimo
          </span>
          <input
            className={inputClassName}
            min="0"
            step="0.001"
            type="number"
            value={minimumStock}
            onChange={(event) => setMinimumStock(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Punto reorden
          </span>
          <input
            className={inputClassName}
            min="0"
            step="0.001"
            type="number"
            value={reorderPoint}
            onChange={(event) => setReorderPoint(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Pedido preferido
          </span>
          <input
            className={inputClassName}
            min="0"
            step="0.001"
            type="number"
            value={preferredOrderQuantity}
            onChange={(event) => setPreferredOrderQuantity(event.target.value)}
          />
        </label>

        <label className="flex flex-col gap-1 xl:col-span-6">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Notas de compras
          </span>
          <input
            className={inputClassName}
            value={procurementNotes}
            onChange={(event) => setProcurementNotes(event.target.value)}
          />
        </label>
      </div>

      <section className="mt-4 rounded-[18px] border border-slate-200 bg-slate-50 p-3">
        <div className="mb-2 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-950">Proveedores asociados</h3>
            <p className="text-xs text-slate-500">
              Relaciones persistidas con proveedor; no edita datos maestros.
            </p>
          </div>
          <button
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700"
            type="button"
            onClick={addRelation}
          >
            Agregar proveedor
          </button>
        </div>
        {supplierRelations.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-500">
            Este insumo no tiene proveedores asociados.
          </p>
        ) : (
          <div className="grid gap-2">
            {supplierRelations.map((relation) => (
              <div
                className={`grid gap-2 rounded-xl border bg-white p-2 md:grid-cols-4 ${
                  relation.isActive === false ? "border-slate-200 opacity-70" : "border-slate-200"
                }`}
                key={relation.localId}
              >
                <label className="flex flex-col gap-1 md:col-span-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                    Proveedor
                  </span>
                  <select
                    className={inputClassName}
                    value={relation.supplierId}
                    onChange={(event) =>
                      updateRelation(relation.localId, { supplierId: event.target.value })
                    }
                  >
                    {supplierOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                    SKU proveedor
                  </span>
                  <input
                    className={inputClassName}
                    value={relation.supplierSku ?? ""}
                    onChange={(event) =>
                      updateRelation(relation.localId, { supplierSku: event.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                    Unidad compra
                  </span>
                  <select
                    className={inputClassName}
                    value={relation.purchaseUom ?? ""}
                    onChange={(event) =>
                      updateRelation(relation.localId, { purchaseUom: event.target.value || null })
                    }
                  >
                    <option value="">Sin unidad</option>
                    {uomOptions.map((uom) => (
                      <option key={uom} value={uom}>
                        {uom}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                    Factor
                  </span>
                  <input
                    className={inputClassName}
                    min="0"
                    step="0.001"
                    type="number"
                    value={relation.conversionFactor ?? ""}
                    onChange={(event) =>
                      updateRelation(relation.localId, { conversionFactor: event.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                    Precio proveedor
                  </span>
                  <input
                    className={inputClassName}
                    min="0"
                    step="0.01"
                    type="number"
                    value={relation.lastKnownPrice ?? ""}
                    onChange={(event) =>
                      updateRelation(relation.localId, { lastKnownPrice: event.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                    Minimo compra
                  </span>
                  <input
                    className={inputClassName}
                    min="0"
                    step="0.001"
                    type="number"
                    value={relation.minimumOrderQty ?? ""}
                    onChange={(event) =>
                      updateRelation(relation.localId, { minimumOrderQty: event.target.value })
                    }
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                    Lead time dias
                  </span>
                  <input
                    className={inputClassName}
                    min="0"
                    type="number"
                    value={relation.leadTimeDays ?? 0}
                    onChange={(event) =>
                      updateRelation(relation.localId, { leadTimeDays: Number(event.target.value) })
                    }
                  />
                </label>
                <div className="flex items-end gap-2">
                  <label className="flex flex-1 items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700">
                    <input
                      checked={relation.isActive !== false}
                      type="checkbox"
                      onChange={(event) =>
                        updateRelation(relation.localId, { isActive: event.target.checked })
                      }
                    />
                    Activa
                  </label>
                  <button
                    className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700"
                    type="button"
                    onClick={() => removeRelation(relation.localId)}
                  >
                    Quitar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {validationMessage || errorMessage ? (
        <p className="mt-3 rounded-xl border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-danger)]">
          {validationMessage ?? errorMessage}
        </p>
      ) : null}

      <div className="mt-4 flex justify-end gap-2">
        <button
          className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700"
          disabled={isSubmitting}
          type="button"
          onClick={onClose}
        >
          Cancelar
        </button>
        <button
          className="rounded-xl bg-[var(--ui-color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          disabled={isSubmitting}
          type="button"
          onClick={handleSubmit}
        >
          Guardar insumo
        </button>
      </div>
    </section>
  );
}
