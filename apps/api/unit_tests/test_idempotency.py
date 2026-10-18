from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from enum import StrEnum
from uuid import UUID, uuid4

import pytest
from pydantic import AliasChoices, AliasPath, BaseModel, ConfigDict, Field, SecretStr

from zeromerma_api.modules.idempotency.application.canonicalization import (
    canonical_fingerprint,
    parse_idempotency_key,
)
from zeromerma_api.modules.idempotency.application.responses import safe_snapshot, validate_policy
from zeromerma_api.modules.idempotency.application.schemas import CommandContext, ResponsePolicy
from zeromerma_api.modules.idempotency.domain.exceptions import (
    DeterministicRejection,
    IdempotencyBoundaryError,
)

_CONTEXT = CommandContext(actor_user_id=UUID(int=1), surface="POS", branch_id=UUID(int=2))
_KEY = "019a7a40-7000-7000-8000-000000000001"


class _Mode(StrEnum):
    PRODUCT = "PRODUCT"


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(decimal_places=2)
    entity_id: UUID
    occurred_at: datetime
    mode: _Mode = _Mode.PRODUCT
    notes: str | None = None


class _Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: UUID
    amount: Decimal


def _fingerprint(payload: BaseModel | dict[str, object]) -> str:
    return canonical_fingerprint(operation_code="sale.confirm", context=_CONTEXT, payload=payload)


@pytest.mark.parametrize("value", ["", " ", _KEY + " ", str(uuid4()), "x" * 400])
def test_idempotency_key_rejects_non_uuid7_and_noncanonical_length(value: str) -> None:
    with pytest.raises(ValueError, match="UUIDv7"):
        parse_idempotency_key(value)


def test_idempotency_key_normalizes_case_without_changing_identity() -> None:
    assert parse_idempotency_key(_KEY.upper()) == UUID(_KEY)
    assert parse_idempotency_key(UUID(_KEY)) == UUID(_KEY)


def test_validated_payload_normalizes_defaults_decimal_uuid_enum_and_utc() -> None:
    first = _Payload(
        amount="1.0",
        entity_id=str(UUID(int=3)).upper(),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    equivalent = _Payload(
        amount="1.00",
        entity_id=UUID(int=3),
        occurred_at=datetime(2025, 12, 31, 17, tzinfo=timezone(timedelta(hours=-7))),
        mode="PRODUCT",
        notes=None,
    )
    assert _fingerprint(first) == _fingerprint(equivalent)


def test_mapping_order_is_irrelevant_but_null_absence_and_array_order_are_distinct() -> None:
    assert _fingerprint({"a": 1, "b": 2}) == _fingerprint({"b": 2, "a": 1})
    assert _fingerprint({}) != _fingerprint({"a": None})
    assert _fingerprint({"items": [1, 2]}) != _fingerprint({"items": [2, 1]})
    assert _fingerprint({"n": Decimal("1")}) != _fingerprint({"n": "1"})


def test_decimal_fingerprints_are_exact_and_independent_of_ambient_precision() -> None:
    precise = Decimal("1.00000000000000000000000000001")
    with localcontext() as context:
        context.prec = 2
        low_precision = _fingerprint({"n": precise})
        assert low_precision != _fingerprint({"n": Decimal("1")})
    with localcontext() as context:
        context.prec = 60
        assert _fingerprint({"n": precise}) == low_precision
    assert _fingerprint({"n": Decimal("-0.000")}) == _fingerprint({"n": Decimal("0")})


@pytest.mark.parametrize(
    "payload",
    [{"password": "value"}, {"nested": {"csrf_token": "value"}}, {"x": SecretStr("value")}],
)
def test_fingerprint_rejects_secrets_recursively(payload: dict[str, object]) -> None:
    with pytest.raises(IdempotencyBoundaryError):
        _fingerprint(payload)


@pytest.mark.parametrize("extra", [{"business_value": 1}, {"password": "value"}])
def test_permissive_models_cannot_omit_business_or_secret_extras(extra: dict[str, object]) -> None:
    class Permissive(BaseModel):
        model_config = ConfigDict(extra="allow")
        amount: Decimal

    with pytest.raises(IdempotencyBoundaryError, match="extra"):
        _fingerprint(Permissive.model_validate({"amount": "1", **extra}))


def test_context_and_operation_are_part_of_identity_but_related_branches_form_a_set() -> None:
    first = _CONTEXT.model_copy(update={"related_branch_ids": (UUID(int=3), UUID(int=4))})
    reordered = first.model_copy(
        update={"related_branch_ids": (UUID(int=4), UUID(int=3), UUID(int=3))}
    )
    assert canonical_fingerprint(
        operation_code="sale.confirm", context=first, payload={}
    ) == canonical_fingerprint(operation_code="sale.confirm", context=reordered, payload={})
    assert _fingerprint({}) != canonical_fingerprint(
        operation_code="sale.cancel", context=_CONTEXT, payload={}
    )
    assert _fingerprint({}) != canonical_fingerprint(
        operation_code="sale.confirm",
        context=_CONTEXT.model_copy(update={"actor_user_id": UUID(int=9)}),
        payload={},
    )


def test_snapshot_requires_explicit_strict_schema_and_refuses_sensitive_fields() -> None:
    class Unsafe(BaseModel):
        model_config = ConfigDict(extra="forbid")
        reset_token: str

    with pytest.raises(IdempotencyBoundaryError):
        safe_snapshot(Unsafe(reset_token="value"), Unsafe)
    with pytest.raises(IdempotencyBoundaryError):
        safe_snapshot(_Snapshot(resource_id=UUID(int=1), amount=Decimal("1")), Unsafe)
    assert (
        safe_snapshot(_Snapshot(resource_id=UUID(int=1), amount=Decimal("1")), _Snapshot)["amount"]
        == "1"
    )


def test_snapshot_and_fingerprint_reject_secret_aliases() -> None:
    class AliasedSecret(BaseModel):
        model_config = ConfigDict(extra="forbid", populate_by_name=True)
        value: str = Field(alias="password")

    secret = AliasedSecret(value="sensitive")
    with pytest.raises(IdempotencyBoundaryError):
        safe_snapshot(secret, AliasedSecret)
    with pytest.raises(IdempotencyBoundaryError):
        _fingerprint(secret)


@pytest.mark.parametrize(
    "alias", ["password", AliasPath("credentials", "value"), AliasChoices("value", "reset_token")]
)
def test_snapshot_and_fingerprint_inspect_validation_aliases(
    alias: str | AliasPath | AliasChoices,
) -> None:
    class AliasedSecret(BaseModel):
        model_config = ConfigDict(extra="forbid", populate_by_name=True)
        value: str = Field(validation_alias=alias)

    secret = AliasedSecret(value="sensitive")
    with pytest.raises(IdempotencyBoundaryError):
        safe_snapshot(secret, AliasedSecret)
    with pytest.raises(IdempotencyBoundaryError):
        _fingerprint(secret)


def test_retention_never_expunges_a_result_without_immutable_reference_policy() -> None:
    with pytest.raises(IdempotencyBoundaryError, match="reconstructible"):
        validate_policy(ResponsePolicy(_Snapshot, payload_retention=timedelta(days=1)))


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_authentication_and_transient_errors_cannot_be_terminal_rejections(status: int) -> None:
    with pytest.raises(IdempotencyBoundaryError):
        DeterministicRejection(
            code="REJECTED",
            status_code=status,
            message="Rejected",
            snapshot=_Snapshot(resource_id=UUID(int=1), amount=Decimal("1")),
        )
