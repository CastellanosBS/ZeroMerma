class SaleError(Exception):
    """Base sale error."""


class SaleNotFoundError(SaleError):
    """Raised when a sale is not found or is not accessible."""


class SaleValidationError(SaleError):
    """Raised when a sale confirmation request is invalid."""


class OpenCashSessionRequiredError(SaleError):
    """Raised when the operator does not have an open cash session."""


class UnsupportedPaymentMethodError(SaleError):
    """Raised when the request uses a payment method not supported in this phase."""


class InsufficientCashPaymentError(SaleError):
    """Raised when cash tendered does not cover the sale total."""

