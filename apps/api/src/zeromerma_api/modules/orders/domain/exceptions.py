class OrderError(Exception):
    """Base exception for the orders module."""


class OrderValidationError(OrderError):
    """Raised when an order command is structurally invalid."""


class OrderNotFoundError(OrderError):
    """Raised when an order is not visible from the current branch context."""


class OrderStateConflictError(OrderError):
    """Raised when an order lifecycle transition is not allowed."""
