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
