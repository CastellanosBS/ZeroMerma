"""Exact inventory quantities and immutable conversion evidence."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from functools import wraps
from uuid import UUID

from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError

ZERO = Decimal("0.000")


def inventory_calculation[**P, T](function: Callable[P, T]) -> Callable[P, T]:
    @wraps(function)
    def calculate(*args: P.args, **kwargs: P.kwargs) -> T:
        with localcontext(Context(prec=40, rounding=ROUND_HALF_UP)):
            return function(*args, **kwargs)

    return calculate


@inventory_calculation
def exact_decimal(value: Decimal, *, scale: int = 3, precision: int = 12) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise InventoryValidationError("Inventory requires a finite Decimal.")
    if abs(value) >= Decimal(10) ** (precision - scale):
        raise InventoryValidationError("Inventory quantity exceeds its numeric precision.")
    result = value.quantize(Decimal(1).scaleb(-scale))
    if result != value:
        raise InventoryValidationError("Inventory precision cannot be discarded by rounding.")
    return result


def normalize_uom(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 32:
        raise InventoryValidationError("An explicit inventory unit is required.")
    return result


@dataclass(frozen=True)
class InventoryQuantitySnapshot:
    source_quantity: Decimal
    source_uom: str
    conversion_factor: Decimal
    quantity_base: Decimal
    base_uom: str


@dataclass(frozen=True)
class InventoryLotQuantity:
    lot_id: UUID
    quantity: Decimal


@inventory_calculation
def convert_quantity(
    source_quantity: Decimal,
    source_uom: str,
    base_uom: str,
    conversion_factor: Decimal | None = None,
) -> InventoryQuantitySnapshot:
    quantity = exact_decimal(source_quantity)
    if quantity <= ZERO:
        raise InventoryValidationError("Source inventory quantity must be positive.")
    source, base = normalize_uom(source_uom), normalize_uom(base_uom)
    if conversion_factor is None:
        if source != base:
            raise InventoryValidationError("Different units require an explicit conversion.")
        conversion_factor = Decimal("1")
    factor = exact_decimal(conversion_factor, scale=6)
    if factor <= 0 or (source == base and factor != 1):
        raise InventoryValidationError("The inventory conversion factor is invalid.")
    converted = exact_decimal(quantity * factor)
    if converted <= ZERO:
        raise InventoryValidationError("The converted inventory quantity must be positive.")
    return InventoryQuantitySnapshot(quantity, source, factor, converted, base)
