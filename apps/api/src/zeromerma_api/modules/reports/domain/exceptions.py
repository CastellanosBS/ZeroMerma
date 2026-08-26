class ReportError(Exception):
    """Base class for admin report errors."""


class ReportNotFoundError(ReportError):
    """Raised when a report definition does not exist."""


class ReportUnavailableError(ReportError):
    """Raised when a report definition is not backed by a preview endpoint."""


class ReportValidationError(ReportError):
    """Raised when report filters or export options are invalid."""
