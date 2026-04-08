class CashSessionError(Exception):
    """Base error for cash session operations."""


class CashSessionConflictError(CashSessionError):
    """Raised when a cash session invariant is violated."""
