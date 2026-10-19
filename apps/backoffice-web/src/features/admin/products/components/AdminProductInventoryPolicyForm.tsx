import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AdminActionButton } from "../../components/AdminActionButton";
import { toBackofficeErrorMessage } from "../../../../lib/api";
import { updateAdminProduct } from "../api";
import type { AdminProduct } from "../types";
import { hasEffectiveCapability } from "../../../auth/authorization";
import { useBackofficeAuthorization } from "../../../auth/authorization-context";

export function AdminProductInventoryPolicyForm({ product }: { product: AdminProduct }) {
  const actor = useBackofficeAuthorization();
  const allowed = hasEffectiveCapability(actor, "catalog.manage", [], true);
  const queryClient = useQueryClient();
  const [sellable, setSellable] = useState(product.isSellable ?? true);
  const [usable, setUsable] = useState(product.isUsableAsInput ?? false);
  const [tracked, setTracked] = useState(product.lotTrackingEnabled ?? false);
  const [expiry, setExpiry] = useState(product.expiryRequired ?? false);
  const mutation = useMutation({
    mutationFn: () =>
      updateAdminProduct(product.id, {
        isSellable: sellable,
        isUsableAsInput: usable,
        lotTrackingEnabled: tracked,
        expiryRequired: expiry,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "products"] }),
  });
  return (
    <form
      className="grid gap-2 rounded-xl border bg-white p-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (allowed && !mutation.isPending) mutation.mutate();
      }}
    >
      <h4>Uso y trazabilidad</h4>
      <label>
        <input
          type="checkbox"
          checked={sellable}
          onChange={(event) => setSellable(event.target.checked)}
        />{" "}
        Vendible
      </label>
      <label>
        <input
          type="checkbox"
          checked={usable}
          onChange={(event) => setUsable(event.target.checked)}
        />{" "}
        Usable como insumo
      </label>
      <label>
        <input
          type="checkbox"
          checked={tracked}
          onChange={(event) => {
            setTracked(event.target.checked);
            if (!event.target.checked) setExpiry(false);
          }}
        />{" "}
        Control por lote (FEFO)
      </label>
      <label>
        <input
          type="checkbox"
          checked={expiry}
          disabled={!tracked}
          onChange={(event) => setExpiry(event.target.checked)}
        />{" "}
        Caducidad obligatoria
      </label>
      <p>Activar lotes no identifica ni certifica existencias anteriores.</p>
      {mutation.isError ? (
        <p role="alert">
          {toBackofficeErrorMessage(mutation.error, "No se pudo guardar la política.")}
        </p>
      ) : null}
      {mutation.isSuccess ? <p role="status">Política guardada.</p> : null}
      <AdminActionButton
        capability="catalog.manage"
        globalOnly
        type="submit"
        disabled={mutation.isPending}
      >
        Guardar uso y trazabilidad
      </AdminActionButton>
    </form>
  );
}
