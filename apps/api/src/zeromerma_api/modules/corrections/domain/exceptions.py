from zeromerma_api.modules.operations.domain.exceptions import OperationError


class CorrectionError(OperationError):
    """Base correction error."""


class CorrectionNotFoundError(CorrectionError):
    """Raised when a correction target does not exist."""


class CorrectionReasonNotFoundError(CorrectionError):
    """Raised when a correction reason is not available."""


class CorrectionValidationError(CorrectionError):
    """Raised when correction data is invalid."""


class CorrectionConflictError(CorrectionError):
    """Raised when workstation or session state makes corrections unsafe."""


class CorrectionIneligibleError(CorrectionError):
    """Raised when a target document cannot be corrected in its current state."""
