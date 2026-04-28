class OperationalPaymentError(Exception):
    """Base class for operational payment errors."""


class OperationalPaymentNotFoundError(OperationalPaymentError):
    """Raised when the requested payment was not found."""


class OperationalPaymentConflictError(OperationalPaymentError):
    """Raised when the current session context prevents the payment operation."""


class OperationalPaymentValidationError(OperationalPaymentError):
    """Raised when the payment payload violates business rules."""
