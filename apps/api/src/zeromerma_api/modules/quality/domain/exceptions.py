from __future__ import annotations


class CleaningLogError(Exception):
    """Base error for cleaning log admin operations."""


class CleaningLogNotFoundError(CleaningLogError):
    """Raised when a cleaning log or template cannot be found."""


class CleaningLogValidationError(CleaningLogError):
    """Raised when a cleaning log command violates business rules."""


class SanitaryVerificationError(Exception):
    """Base error for sanitary verification admin operations."""


class SanitaryVerificationNotFoundError(SanitaryVerificationError):
    """Raised when a sanitary verification or template cannot be found."""


class SanitaryVerificationValidationError(SanitaryVerificationError):
    """Raised when a sanitary verification command violates business rules."""


class EquipmentMaintenanceError(Exception):
    """Base error for admin equipment maintenance operations."""


class EquipmentNotFoundError(EquipmentMaintenanceError):
    """Raised when an equipment asset is not found."""


class MaintenanceRecordNotFoundError(EquipmentMaintenanceError):
    """Raised when a maintenance record is not found."""


class EquipmentMaintenanceValidationError(EquipmentMaintenanceError):
    """Raised when an equipment maintenance command violates business rules."""


class IncidentError(Exception):
    """Base error for admin incident operations."""


class IncidentNotFoundError(IncidentError):
    """Raised when an incident cannot be found."""


class IncidentValidationError(IncidentError):
    """Raised when an incident command violates business rules."""
