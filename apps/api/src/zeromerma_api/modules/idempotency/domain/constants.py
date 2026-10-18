from enum import StrEnum


class IdempotencyStatus(StrEnum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"
