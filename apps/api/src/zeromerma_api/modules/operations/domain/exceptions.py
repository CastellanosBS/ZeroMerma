class OperationError(Exception):
    """Base physical operation error."""


class OperationValidationError(OperationError):
    """Raised when an operation request is invalid."""


class OperationDocumentNotFoundError(OperationError):
    """Raised when an operation document is not found or is not accessible."""


class WasteReasonNotFoundError(OperationError):
    """Raised when a waste reason is invalid."""


class OpenShiftOperationRequiredError(OperationError):
    """Raised when a workstation shift is required for a physical operation."""

