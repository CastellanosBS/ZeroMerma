class ProductionError(Exception):
    """Base exception for production administration."""


class ProductionNotFoundError(ProductionError):
    """Raised when a production batch is not available."""


class ProductionValidationError(ProductionError):
    """Raised when a production command violates business rules."""
