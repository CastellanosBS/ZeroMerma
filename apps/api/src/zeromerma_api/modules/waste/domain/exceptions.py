class WasteError(Exception):
    """Base exception for Backoffice waste administration."""


class WasteNotFoundError(WasteError):
    """Raised when a waste record or related entity is not available."""


class WasteValidationError(WasteError):
    """Raised when a waste command violates business rules."""
