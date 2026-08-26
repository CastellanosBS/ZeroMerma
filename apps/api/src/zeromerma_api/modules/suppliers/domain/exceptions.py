class SupplierError(Exception):
    """Base exception for Backoffice supplier administration."""


class SupplierNotFoundError(SupplierError):
    """Raised when a supplier or related entity is not available."""


class SupplierValidationError(SupplierError):
    """Raised when a supplier command violates business rules."""
