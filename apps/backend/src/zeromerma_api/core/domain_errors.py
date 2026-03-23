# apps/backend/src/zeromerma_api/core/domain_errors.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(eq=False)
class DomainError(Exception):
    """
    Base class for predictable business/domain failures.

    Why this exists:
    - Services should express domain failures explicitly.
    - Routers should not need to infer intent from ValueError/LookupError.
    - main.py can translate these errors into the standard API error envelope.
    """

    message: str
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


class DomainValidationError(DomainError):
    """
    The request is structurally valid, but violates a domain/business rule.

    Typical examples:
    - payment amount <= 0
    - invalid payment method
    - production run with no outputs
    """


class DomainNotFoundError(DomainError):
    """
    A required domain entity does not exist.

    Typical examples:
    - sale not found
    - product not found
    - cash session not found
    """


class DomainConflictError(DomainError):
    """
    The request conflicts with current persisted state.

    Typical examples:
    - overpayment
    - insufficient stock
    - trying to close an already closed cash session
    - trying to operate on a closed sale
    """


class DomainAuthorizationError(DomainError):
    """
    The caller is authenticated but not authorized to perform the operation.
    """


class DomainInvariantError(DomainError):
    """
    An internal invariant that should always hold was violated.

    This is usually more serious than a normal validation error and should be
    rare. It often indicates a programming error or corrupted state.
    """
