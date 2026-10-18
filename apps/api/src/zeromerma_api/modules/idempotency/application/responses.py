from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, SecretBytes, SecretStr

from zeromerma_api.modules.idempotency.application.canonicalization import (
    reject_sensitive_alias,
    reject_sensitive_key,
)
from zeromerma_api.modules.idempotency.application.schemas import ResponsePolicy
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError


def response_fingerprint(payload: dict[str, Any]) -> str:
    """Retain exact logical response identity even after its snapshot is purged."""
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _check_values(value: object) -> None:
    if isinstance(value, SecretStr | SecretBytes):
        raise IdempotencyBoundaryError("Response secrets cannot be persisted.")
    if isinstance(value, BaseModel):
        if type(value).model_config.get("extra") != "forbid":
            raise IdempotencyBoundaryError("Snapshot models must explicitly forbid extra fields.")
        for name, field in type(value).model_fields.items():
            reject_sensitive_key(name)
            for alias in (field.alias, field.serialization_alias, field.validation_alias):
                reject_sensitive_alias(alias)
            _check_values(getattr(value, name))
    elif isinstance(value, Mapping):
        for key, child in value.items():
            reject_sensitive_key(str(key))
            _check_values(child)
    elif isinstance(value, list | tuple):
        for child in value:
            _check_values(child)


def validate_policy(policy: ResponsePolicy) -> None:
    if not policy.schema_version or len(policy.schema_version) > 40:
        raise IdempotencyBoundaryError("A stable response schema version is required.")
    for model in (policy.snapshot_model, policy.reference_model, policy.rejection_model):
        if model is not None and model.model_config.get("extra") != "forbid":
            raise IdempotencyBoundaryError("Response models must forbid extra fields.")
    if (policy.reference_model is None) != (policy.restore is None):
        raise IdempotencyBoundaryError("References require an immutable result resolver.")
    if policy.payload_retention is not None and (
        policy.payload_retention.total_seconds() <= 0 or policy.restore is None
    ):
        raise IdempotencyBoundaryError("Payload retention requires a reconstructible result.")


def safe_snapshot(value: BaseModel, model: type[BaseModel] | None) -> dict[str, Any]:
    if model is None or type(value) is not model:
        raise IdempotencyBoundaryError("The response has no explicit snapshot policy.")
    _check_values(value)
    validated = model.model_validate(value.model_dump(mode="python"))
    result = validated.model_dump(mode="json")
    _check_values(result)
    return result
