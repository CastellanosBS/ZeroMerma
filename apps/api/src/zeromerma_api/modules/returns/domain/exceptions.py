from __future__ import annotations


class SaleReturnError(Exception):
    """Base sale return error."""


class SaleReturnNotFoundError(SaleReturnError):
    """Raised when the requested sale or return cannot be found."""


class SaleReturnValidationError(SaleReturnError):
    """Raised when the return request violates workflow rules."""


class SaleReturnConflictError(SaleReturnError):
    """Raised when the workstation or session state makes returns unsafe."""

