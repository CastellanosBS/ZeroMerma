from pydantic import BaseModel


class IdempotencyError(Exception):
    def __init__(self, code: str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.code, self.status_code, self.message = code, status_code, message


class IdempotencyKeyReused(IdempotencyError):
    def __init__(self) -> None:
        super().__init__("IDEMPOTENCY_KEY_REUSED", 409, "This key belongs to another command.")


class IdempotencyInProgress(IdempotencyError):
    def __init__(self) -> None:
        super().__init__("IDEMPOTENCY_IN_PROGRESS", 409, "The command is still being processed.")


class IdempotencyResultUnknown(IdempotencyError):
    def __init__(self) -> None:
        super().__init__(
            "IDEMPOTENCY_RESULT_UNKNOWN", 409, "The command outcome requires reconciliation."
        )


class IdempotencyBoundaryError(RuntimeError):
    """A caller violated the command's transaction or safe persistence contract."""


class DeterministicRejection(Exception):
    def __init__(
        self,
        *,
        code: str,
        status_code: int,
        message: str,
        snapshot: BaseModel,
        reference: BaseModel | None = None,
    ) -> None:
        super().__init__(message)
        if not 400 <= status_code < 500 or status_code in {401, 403, 429}:
            raise IdempotencyBoundaryError("This failure cannot consume an idempotency key.")
        self.code, self.status_code, self.message = code, status_code, message
        self.snapshot, self.reference = snapshot, reference
