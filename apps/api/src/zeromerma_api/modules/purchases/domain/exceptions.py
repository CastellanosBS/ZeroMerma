class PurchaseNotFoundError(Exception):
    """Raised when a purchase document or related receipt cannot be found."""


class PurchaseValidationError(Exception):
    """Raised when a purchase operation violates procurement or inventory rules."""
