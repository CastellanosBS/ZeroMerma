export function getOrderDeliveryActionLabel({
  isPending,
  requiresSettlement,
}: {
  isPending: boolean;
  requiresSettlement: boolean;
}) {
  if (isPending) {
    return requiresSettlement ? "Cobrando..." : "Entregando...";
  }

  return requiresSettlement ? "Cobrar" : "Entregar pedido";
}
