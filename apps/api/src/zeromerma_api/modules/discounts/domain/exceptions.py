class OperationalDiscountError(Exception):
    """Base class for operational discount errors."""


class OperationalDiscountNotFoundError(OperationalDiscountError):
    """Raised when the requested discount record was not found."""


class OperationalDiscountConflictError(OperationalDiscountError):
    """Raised when the current session context prevents the discount operation."""


class OperationalDiscountValidationError(OperationalDiscountError):
    """Raised when the discount payload violates business rules."""
