from zeromerma_api.modules.operations.domain.exceptions import OperationError


class TransferError(OperationError):
    """Base transfer error."""


class TransferValidationError(TransferError):
    """Raised when transfer data is invalid."""


class TransferNotFoundError(TransferError):
    """Raised when a transfer is not found or is not accessible."""


class TransferAlreadyReceivedError(TransferError):
    """Raised when a transfer is no longer receivable."""

