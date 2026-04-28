from __future__ import annotations


class TicketError(Exception):
    """Base tickets error."""


class TicketNotFoundError(TicketError):
    """Raised when a ticket cannot be resolved in the current branch context."""


class TicketValidationError(TicketError):
    """Raised when a ticket request is invalid for the current workflow."""


class TicketConflictError(TicketError):
    """Raised when the cashier cannot operate tickets in the current session state."""

