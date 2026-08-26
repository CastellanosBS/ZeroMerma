from __future__ import annotations


class AuditAdminError(Exception):
    """Base exception for administrative audit read operations."""


class AuditEventNotFoundError(AuditAdminError):
    """Raised when an audit event cannot be found."""
