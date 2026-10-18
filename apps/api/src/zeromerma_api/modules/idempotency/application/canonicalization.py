from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import RFC_4122, UUID

from pydantic import AliasChoices, AliasPath, BaseModel, SecretBytes, SecretStr

from zeromerma_api.modules.idempotency.application.schemas import CommandContext
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError

IDEMPOTENCY_KEY_PATTERN = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-7[0-9a-fA-F]{3}-"
    r"[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
_FORBIDDEN_KEY = re.compile(
    r"password|secret|credential|token|cookie|authorization|csrf|"
    r"(?:^|[_-])(?:request[_-]?id|idempotency[_-]?key)(?:$|[_-])",
    re.IGNORECASE,
)


def parse_idempotency_key(value: UUID | str) -> UUID:
    if (
        not isinstance(value, UUID | str)
        or re.fullmatch(IDEMPOTENCY_KEY_PATTERN, str(value)) is None
    ):
        raise ValueError("Idempotency-Key must be a canonical UUIDv7.")
    parsed = UUID(str(value))
    if parsed.version != 7 or parsed.variant != RFC_4122:
        raise ValueError("Idempotency-Key must be a canonical UUIDv7.")
    return parsed


def reject_sensitive_key(key: str) -> None:
    if _FORBIDDEN_KEY.search(key):
        raise IdempotencyBoundaryError("Sensitive or request-local fields cannot be persisted.")


def reject_sensitive_alias(alias: object) -> None:
    if alias is None:
        return
    if isinstance(alias, str):
        reject_sensitive_key(alias)
    elif isinstance(alias, AliasChoices):
        for choice in alias.choices:
            reject_sensitive_alias(choice)
    elif isinstance(alias, AliasPath):
        for segment in alias.path:
            if isinstance(segment, str):
                reject_sensitive_key(segment)
    else:
        raise IdempotencyBoundaryError("This alias has no inspectable persistence policy.")


def _decimal(value: Decimal, scale: int | None = None) -> str:
    if not value.is_finite():
        raise IdempotencyBoundaryError("Non-finite numbers are not canonical command values.")
    # Formatting is exact; normalize()/quantize() would use the caller's Decimal precision.
    rendered = format(value, "f")
    negative = rendered.startswith("-") and value != 0
    integer, _, fraction = rendered.lstrip("-").partition(".")
    integer = integer.lstrip("0") or "0"
    fraction = fraction.rstrip("0")
    if scale is not None:
        if len(fraction) > scale:
            raise IdempotencyBoundaryError("A decimal exceeds its contractual scale.")
        fraction = fraction.ljust(scale, "0")
    return ("-" if negative else "") + integer + ("." + fraction if fraction else "")


def _canonical(value: object, scale: int | None = None) -> Any:
    if isinstance(value, SecretStr | SecretBytes):
        raise IdempotencyBoundaryError("Secrets cannot participate in command persistence.")
    if isinstance(value, BaseModel):
        if type(value).model_config.get("extra") == "allow":
            raise IdempotencyBoundaryError("Command models cannot permit undeclared extra fields.")
        result = {}
        for key, field in type(value).model_fields.items():
            reject_sensitive_key(key)
            for alias in (field.alias, field.serialization_alias, field.validation_alias):
                reject_sensitive_alias(alias)
            decimal_scale = next(
                (
                    item.decimal_places
                    for item in field.metadata
                    if getattr(item, "decimal_places", None) is not None
                ),
                None,
            )
            result[key] = _canonical(getattr(value, key), decimal_scale)
        return ["object", result]
    if isinstance(value, Enum):
        return _canonical(value.value, scale)
    if isinstance(value, UUID):
        return ["string", str(value)]
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise IdempotencyBoundaryError("Command instants require an explicit timezone.")
        return ["string", value.astimezone(UTC).isoformat(timespec="microseconds")]
    if isinstance(value, date):
        return ["string", value.isoformat()]
    if isinstance(value, Decimal):
        return ["decimal", _decimal(value, scale)]
    if isinstance(value, Mapping):
        result = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise IdempotencyBoundaryError("JSON object keys must be strings.")
            reject_sensitive_key(key)
            result[key] = _canonical(child)
        return ["object", result]
    if isinstance(value, list | tuple):
        return ["array", [_canonical(child) for child in value]]
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["boolean", value]
    if isinstance(value, int):
        return ["number", str(value)]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise IdempotencyBoundaryError("Non-finite numbers are not canonical command values.")
        return ["number", _decimal(Decimal(str(value)))]
    if isinstance(value, str):
        return ["string", value]
    raise IdempotencyBoundaryError("This value has no declared canonical representation.")


def canonical_fingerprint(
    *,
    operation_code: str,
    context: CommandContext,
    payload: BaseModel | Mapping[str, object],
    fingerprint_version: int = 1,
) -> str:
    if fingerprint_version != 1:
        raise IdempotencyBoundaryError("Unsupported fingerprint version.")
    if not operation_code or len(operation_code) > 120:
        raise IdempotencyBoundaryError("A stable operation code is required.")
    normalized_context = context.model_copy(
        update={"related_branch_ids": tuple(sorted(set(context.related_branch_ids), key=str))}
    )
    canonical = {
        "version": fingerprint_version,
        "operation": operation_code,
        "context": _canonical(normalized_context),
        "payload": _canonical(payload),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
