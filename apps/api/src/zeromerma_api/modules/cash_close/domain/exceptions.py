from zeromerma_api.modules.cash.domain.exceptions import CashSessionError


class CashCloseError(CashSessionError):
    """Base error for cash close operations."""


class CashCloseValidationError(CashCloseError):
    """Raised when cash close input is invalid."""


class CashCloseConflictError(CashCloseError):
    """Raised when close preview cannot proceed because the session context is invalid."""


class CashCloseNotFoundError(CashCloseError):
    """Raised when a cash close report was not found."""
