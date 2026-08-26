class InventoryError(Exception):
    """Base error for inventory operations."""


class InventoryNotFoundError(InventoryError):
    """Raised when an inventory resource cannot be found."""


class InventoryValidationError(InventoryError):
    """Raised when an inventory command violates inventory rules."""
