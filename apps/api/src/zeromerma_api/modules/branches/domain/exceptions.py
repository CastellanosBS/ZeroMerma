class BranchAccessError(Exception):
    """Base error for workstation and branch access violations."""


class WorkstationNotFoundError(BranchAccessError):
    """Raised when a workstation code does not exist."""


class BranchInactiveError(BranchAccessError):
    """Raised when a branch is inactive."""


class WorkstationInactiveError(BranchAccessError):
    """Raised when a workstation is inactive."""


class BranchAssignmentRequiredError(BranchAccessError):
    """Raised when a user is not assigned to the workstation branch."""


class BranchAdminError(Exception):
    """Base error for administrative branch management."""


class BranchNotFoundError(BranchAdminError):
    """Raised when an administrative branch lookup cannot find the branch."""


class BrandNotFoundError(BranchAdminError):
    """Raised when an administrative branch command references an unknown brand."""


class BranchValidationError(BranchAdminError):
    """Raised when an administrative branch command violates branch rules."""


class BranchConflictError(BranchAdminError):
    """Raised when an administrative branch command conflicts with operations."""


class WorkstationAdminNotFoundError(BranchAdminError):
    """Raised when an administrative workstation lookup cannot find the station."""


class WorkstationValidationError(BranchAdminError):
    """Raised when an administrative workstation command violates station rules."""


class WorkstationConflictError(BranchAdminError):
    """Raised when an administrative workstation command conflicts with operations."""
