"""Weighted average valuation; absent evidence never becomes a zero-cost fact."""

from dataclasses import dataclass
from decimal import Decimal

from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.domain.quantities import exact_decimal, inventory_calculation

COST_QUANTUM = Decimal("0.00000001")


@dataclass(frozen=True)
class InventoryCostEffect:
    unit_cost: Decimal | None
    total_cost: Decimal | None
    balance_value: Decimal | None


@inventory_calculation
def value_effect(
    *,
    quantity_before: Decimal,
    value_before: Decimal | None,
    delta: Decimal,
    unit_cost: Decimal | None,
    total_cost: Decimal | None,
    use_documented_outflow: bool = False,
) -> InventoryCostEffect:
    quantity = abs(delta)
    if unit_cost is not None:
        unit_cost = exact_decimal(unit_cost, scale=8, precision=18)
        if unit_cost < 0:
            raise InventoryValidationError("Inventory unit cost cannot be negative.")
    if total_cost is not None:
        total_cost = exact_decimal(total_cost, scale=8, precision=24)
        if total_cost < 0:
            raise InventoryValidationError("Inventory value cannot be negative.")
        derived_unit = (total_cost / quantity).quantize(COST_QUANTUM)
        if unit_cost is not None and unit_cost != derived_unit:
            raise InventoryValidationError("Inventory unit cost and total value disagree.")
        unit_cost = exact_decimal(derived_unit, scale=8, precision=18)
    elif unit_cost is not None:
        total_cost = (quantity * unit_cost).quantize(COST_QUANTUM)
    if delta < 0 and not use_documented_outflow:
        if unit_cost is not None or total_cost is not None:
            raise InventoryValidationError("Ordinary stock outflow uses its locked weighted cost.")
        if value_before is not None and quantity_before > 0 and quantity <= quantity_before:
            total_cost = (
                value_before
                if quantity == quantity_before
                else (value_before * quantity / quantity_before).quantize(COST_QUANTUM)
            )
            unit_cost = (total_cost / quantity).quantize(COST_QUANTUM)
    quantity_after = quantity_before + delta
    if quantity_after < 0 or quantity_before < 0 or value_before is None or total_cost is None:
        value_after = None
    else:
        value_after = value_before + (total_cost if delta > 0 else -total_cost)
        if value_after < 0 or (quantity_after == 0 and value_after != 0):
            raise InventoryValidationError(
                "The documented cost cannot reconcile the remaining stock."
            )
        value_after = exact_decimal(value_after, scale=8, precision=24)
    if quantity_after == 0:
        value_after = Decimal("0.00000000")
    return InventoryCostEffect(unit_cost, total_cost, value_after)
