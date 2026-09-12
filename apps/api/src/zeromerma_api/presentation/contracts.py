from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from fastapi import FastAPI

CONTRACT_SCHEMA_VERSION = "1.0.0"
DECIMAL_PATTERN = r"^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$"
_DECIMAL_PATTERN_PREFIX = r"^(?!^[-+.]*$)[+-]?0*"
_HTTP_METHODS = {"delete", "get", "head", "options", "patch", "post", "put", "trace"}


def is_decimal_schema(value: Mapping[str, Any]) -> bool:
    """Recognize Pydantic's unconstrained and digits/scale-constrained Decimal patterns."""
    pattern = value.get("pattern")
    return isinstance(pattern, str) and pattern.startswith(_DECIMAL_PATTERN_PREFIX)


def is_decimal_input_union(value: Mapping[str, Any]) -> bool:
    alternatives = value.get("anyOf", [])
    return any(isinstance(item, dict) and is_decimal_schema(item) for item in alternatives) and any(
        isinstance(item, dict) and item.get("type") == "number" for item in alternatives
    )


def _annotate_wire_types(value: Any) -> None:
    if isinstance(value, dict):
        if value.get("format") == "date-time":
            value["x-zeromerma-instant-format"] = "ISO8601_DATETIME"
        elif value.get("format") == "date":
            value["x-zeromerma-date-format"] = "ISO8601_CALENDAR_DATE"
        elif value.get("format") == "uuid":
            value["x-zeromerma-id-representation"] = "JSON_STRING"

        if value.get("type") == "string" and is_decimal_schema(value):
            value["x-zeromerma-decimal-representation"] = "JSON_STRING"
        if is_decimal_input_union(value):
            value["x-zeromerma-decimal-input-representation"] = "JSON_NUMBER_OR_STRING"

        for child in value.values():
            _annotate_wire_types(child)
    elif isinstance(value, list):
        for child in value:
            _annotate_wire_types(child)


def normalize_contract_schema(schema: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(schema)
    normalized["x-zeromerma-contract-schema-version"] = CONTRACT_SCHEMA_VERSION
    normalized["x-zeromerma-source"] = "FASTAPI_PYDANTIC"
    for path_item in normalized.get("paths", {}).values():
        for method, operation in path_item.items():
            if method in _HTTP_METHODS and isinstance(operation, dict):
                operation["x-zeromerma-operation-id-policy"] = "FASTAPI_STABLE_GENERATED"
    _annotate_wire_types(normalized)
    return normalized


def install_contract_openapi(app: FastAPI) -> None:
    default_openapi = app.openapi

    def contract_openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = normalize_contract_schema(default_openapi())
        return app.openapi_schema

    app.openapi = contract_openapi  # type: ignore[method-assign]
