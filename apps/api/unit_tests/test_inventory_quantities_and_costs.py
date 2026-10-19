from decimal import Decimal, localcontext

import pytest

from zeromerma_api.modules.inventory.domain.costs import value_effect
from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.domain.quantities import convert_quantity, exact_decimal


def test_conversion_is_exact_and_independent_of_ambient_decimal_context() -> None:
    with localcontext() as context:
        context.prec = 3
        snapshot = convert_quantity(Decimal("12.345"), "BOX", "PIECE", Decimal("12"))
    assert snapshot.quantity_base == Decimal("148.140")
    assert snapshot.source_quantity == Decimal("12.345")
    assert snapshot.conversion_factor == Decimal("12.000000")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "0.0001", "1000000000"])
def test_quantity_does_not_silently_lose_precision(value: str) -> None:
    with pytest.raises(InventoryValidationError):
        exact_decimal(Decimal(value))


def test_distinct_uom_requires_explicit_conversion_and_same_uom_requires_identity() -> None:
    with pytest.raises(InventoryValidationError):
        convert_quantity(Decimal("1"), "BOX", "PIECE")
    with pytest.raises(InventoryValidationError):
        convert_quantity(Decimal("1"), "KG", "KG", Decimal("1000"))
    with pytest.raises(InventoryValidationError):
        convert_quantity(Decimal("0.001"), "BOX", "PIECE", Decimal("0.5"))


def test_weighted_average_outflow_uses_stock_value_not_catalog_cost() -> None:
    first = value_effect(
        quantity_before=Decimal(0),
        value_before=Decimal(0),
        delta=Decimal(10),
        unit_cost=Decimal(2),
        total_cost=None,
    )
    second = value_effect(
        quantity_before=Decimal(10),
        value_before=first.balance_value,
        delta=Decimal(10),
        unit_cost=Decimal(4),
        total_cost=None,
    )
    with localcontext() as context:
        context.prec = 2
        consumed = value_effect(
            quantity_before=Decimal(20),
            value_before=second.balance_value,
            delta=Decimal(-5),
            unit_cost=None,
            total_cost=None,
        )
    assert consumed.unit_cost == Decimal("3.00000000")
    assert consumed.total_cost == Decimal("15.00000000")
    assert consumed.balance_value == Decimal("45.00000000")


def test_unknown_valuation_propagates_until_stock_is_empty() -> None:
    unknown = value_effect(
        quantity_before=Decimal(10),
        value_before=None,
        delta=Decimal(2),
        unit_cost=Decimal(4),
        total_cost=None,
    )
    assert unknown.balance_value is None
    cleared = value_effect(
        quantity_before=Decimal(12),
        value_before=None,
        delta=Decimal(-12),
        unit_cost=None,
        total_cost=None,
    )
    assert cleared.total_cost is None and cleared.balance_value == Decimal(0)


def test_full_outflow_consumes_rounding_residual_and_invalid_reversal_rejects() -> None:
    effect = value_effect(
        quantity_before=Decimal(3),
        value_before=Decimal(1),
        delta=Decimal(-3),
        unit_cost=None,
        total_cost=None,
    )
    assert effect.total_cost == Decimal(1) and effect.balance_value == Decimal(0)
    with pytest.raises(InventoryValidationError, match="remaining stock"):
        value_effect(
            quantity_before=Decimal(1),
            value_before=Decimal(1),
            delta=Decimal(-1),
            unit_cost=Decimal(2),
            total_cost=None,
            use_documented_outflow=True,
        )
