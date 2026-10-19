import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { components } from "@zeromerma/api-client";
import { Button } from "../../components/ui/button";
import { formatCurrency, formatLocalDateTime } from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import { formatMoneyFromCents, parseMoneyToCents } from "../pos-terminal/model";
import { getOrdersCatalog, getOrdersClassProducts, quoteOrder } from "./orders-api";
import type { OrderCommandPayload } from "./order-command-intent";
import { orderDateTimeInput, orderDateTimeToUtc } from "./order-date-time";

type Order = components["schemas"]["CustomerOrderDetailResponse"];
type Quote = components["schemas"]["OrderQuoteView"];

export function OrderLifecyclePanel({
  order,
  workstationCode,
  cashSessionId,
  pending,
  onCommand,
  onChanged,
}: {
  order: Order;
  workstationCode: string;
  cashSessionId: string;
  pending: boolean;
  onCommand: (code: "pay" | "amend", payload: OrderCommandPayload) => Promise<unknown>;
  onChanged: () => void;
}) {
  const [cash, setCash] = useState("");
  const [card, setCard] = useState("");
  const [editing, setEditing] = useState(false);
  const [reason, setReason] = useState("");
  const [requested, setRequested] = useState(
    order.requested_for_at ? orderDateTimeInput(order.requested_for_at, order.branch.timezone) : "",
  );
  const [items, setItems] = useState(
    order.items.map((item) => ({
      product_id: item.product_id,
      quantity: item.quantity,
      name: item.product_name_snapshot,
    })),
  );
  const [classId, setClassId] = useState("");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const classes = useQuery({
    queryKey: ["order-amend-classes", workstationCode],
    queryFn: () => getOrdersCatalog({ workstationCode }),
    enabled: editing,
  });
  const products = useQuery({
    queryKey: ["order-amend-products", workstationCode, classId],
    queryFn: () => getOrdersClassProducts({ workstationCode, classId }),
    enabled: editing && !!classId,
  });

  function payments() {
    const values = [
      { payment_method_code: "CASH", value: cash },
      { payment_method_code: "CARD", value: card },
    ];
    return values.flatMap(({ payment_method_code, value }) => {
      if (!value.trim()) return [];
      const cents = parseMoneyToCents(value);
      if (cents === null || cents <= 0)
        throw new Error("Captura importes positivos con dos decimales.");
      return [{ payment_method_code, amount: formatMoneyFromCents(cents) }];
    });
  }

  async function execute(action: "pay" | "quote" | "amend") {
    if (busy || pending) return;
    setBusy(true);
    setError(null);
    setFeedback(null);
    try {
      const base = { workstation_code: workstationCode, cash_session_id: cashSessionId };
      if (action === "quote") {
        setQuote(
          await quoteOrder({
            workstation_code: workstationCode,
            requested_for_at: orderDateTimeToUtc(requested, order.branch.timezone),
            items: items.map(({ product_id, quantity }) => ({ product_id, quantity })),
          }),
        );
        return;
      }
      const payload =
        action === "pay"
          ? { ...base, payments: payments() }
          : {
              ...base,
              expected_version: order.version,
              requested_for_at: orderDateTimeToUtc(requested, order.branch.timezone),
              quote_fingerprint: quote?.quote_fingerprint ?? "",
              reason: reason.trim(),
              additional_payments: payments(),
              items: items.map(({ product_id, quantity }) => ({ product_id, quantity })),
            };
      await onCommand(action, payload);
      setCash("");
      setCard("");
      setQuote(null);
      setEditing(false);
      setFeedback(action === "pay" ? "Abono confirmado." : "Nueva versión confirmada.");
      onChanged();
    } catch (failure) {
      setError(
        toOperationalErrorMessage(
          failure,
          "No se confirmó la operación. Consulta la recuperación si el resultado es incierto.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      aria-label="Seguimiento financiero y cambios del pedido"
      className="grid gap-3 rounded-xl border bg-white p-4"
    >
      <h2 className="text-lg font-semibold">Seguimiento del pedido</h2>
      {order.production_commit_at ? (
        <p>
          Compromiso productivo:{" "}
          {formatLocalDateTime(order.production_commit_at, order.branch.timezone)} · versión{" "}
          {order.version}
        </p>
      ) : (
        <p role="alert">
          Falta evidencia de la política original. Este pedido requiere revisión administrativa.
        </p>
      )}
      <p>
        Pago por aplicar: {formatCurrency(order.unapplied_amount ?? "0")} · Ingreso por entrega:{" "}
        {formatCurrency(order.recognized_revenue_amount ?? "0")} · Retenido:{" "}
        {formatCurrency(order.retained_amount ?? "0")}
      </p>
      {feedback ? <p role="status">{feedback}</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {order.can_pay || (editing && order.can_amend) ? (
        <fieldset disabled={busy || pending} className="flex flex-wrap gap-3">
          <legend>{editing ? "Abono adicional para esta modificación" : "Registrar abono"}</legend>
          <label>
            Efectivo
            <input
              aria-label="Abono en efectivo"
              inputMode="decimal"
              value={cash}
              onChange={(event) => setCash(event.target.value)}
            />
          </label>
          <label>
            Tarjeta cobrada por separado
            <input
              aria-label="Abono en tarjeta"
              inputMode="decimal"
              value={card}
              onChange={(event) => setCard(event.target.value)}
            />
          </label>
          <p>
            Registra únicamente el importe aplicado. Un pago con tarjeta aquí es un registro
            contable del cobro externo.
          </p>
          {!editing ? <Button onClick={() => void execute("pay")}>Confirmar abono</Button> : null}
        </fieldset>
      ) : null}
      {order.can_amend ? (
        <Button
          disabled={busy || pending}
          onClick={() => {
            setEditing(!editing);
            setQuote(null);
          }}
        >
          {" "}
          {editing ? "Cerrar modificación" : "Modificar pedido"}
        </Button>
      ) : null}
      {editing ? (
        <fieldset disabled={busy || pending} className="grid gap-3">
          <legend>Nueva versión del pedido</legend>
          <label>
            Fecha de entrega ({order.branch.timezone})
            <input
              aria-label="Nueva fecha de entrega"
              type="datetime-local"
              value={requested}
              onChange={(event) => {
                setRequested(event.target.value);
                setQuote(null);
              }}
            />
          </label>
          {items.map((item) => (
            <div key={item.product_id} className="flex gap-2">
              <label>
                {item.name}
                <input
                  aria-label={`Cantidad de ${item.name}`}
                  inputMode="decimal"
                  value={item.quantity}
                  onChange={(event) => {
                    const value = event.target.value;
                    setItems((current) =>
                      current.map((row) =>
                        row.product_id === item.product_id ? { ...row, quantity: value } : row,
                      ),
                    );
                    setQuote(null);
                  }}
                />
              </label>
              <Button
                onClick={() => {
                  setItems((current) =>
                    current.filter((row) => row.product_id !== item.product_id),
                  );
                  setQuote(null);
                }}
              >
                Quitar {item.name}
              </Button>
            </div>
          ))}
          <label>
            Clase
            <select
              aria-label="Clase para modificación"
              value={classId}
              onChange={(event) => setClassId(event.target.value)}
            >
              <option value="">Selecciona</option>
              {classes.data?.classes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Agregar producto
            <select
              aria-label="Agregar producto al pedido"
              value=""
              onChange={(event) => {
                const product = products.data?.products.find(
                  (item) => item.id === event.target.value,
                );
                if (product)
                  setItems((current) =>
                    current.some((item) => item.product_id === product.id)
                      ? current
                      : [...current, { product_id: product.id, quantity: "1", name: product.name }],
                  );
                setQuote(null);
              }}
            >
              <option value="">Selecciona</option>
              {products.data?.products.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Motivo
            <textarea
              aria-label="Motivo de modificación"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              maxLength={240}
            />
          </label>
          <Button
            disabled={reason.trim().length < 4 || items.length === 0}
            onClick={() => void execute("quote")}
          >
            Cotizar modificación
          </Button>
          {quote ? (
            <div>
              <p>
                Nuevo total: {formatCurrency(quote.total_amount)}. Mínimo pagado:{" "}
                {formatCurrency(quote.minimum_advance_amount)}.
              </p>
              <p>
                Nuevo compromiso:{" "}
                {formatLocalDateTime(quote.production_commit_at, quote.branch_timezone)}
              </p>
              <Button onClick={() => void execute("amend")}>Confirmar nueva versión</Button>
            </div>
          ) : null}
        </fieldset>
      ) : null}
    </section>
  );
}
