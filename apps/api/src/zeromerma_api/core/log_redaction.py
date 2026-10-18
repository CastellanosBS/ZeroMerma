"""Redact credential-bearing strings and structured log fields at the output boundary."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_SENSITIVE = re.compile(
    r"password|passwd|secret|token|authorization|cookie|csrf|credential|recovery_material",
    re.IGNORECASE,
)
_URL_CREDENTIAL = re.compile(r"([a-z][a-z0-9+.-]*://)[^\s/@]+(?::[^\s/@]*)?@", re.IGNORECASE)
_QUERY = re.compile(r"((?:https?://[^\s?]+|/[\w/.-]+)\?)[^\s\"']+", re.IGNORECASE)
_BEARER = re.compile(r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_COOKIE_HEADER = re.compile(r"(\b(?:set-cookie|cookie)\s*[:=]\s*)[^\r\n]+", re.IGNORECASE)
_KEY_VALUE = re.compile(
    r"((?:password|passwd|secret|token|authorization|cookie|csrf|credential|recovery_material)"
    r"[\w-]*[\"']?\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
    re.IGNORECASE,
)


def redact_log(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _SENSITIVE.search(str(key)) else redact_log(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact_log(item) for item in value]
    if isinstance(value, str):
        value = _COOKIE_HEADER.sub(r"\1[REDACTED]", value)
        value = _URL_CREDENTIAL.sub(r"\1[REDACTED]@", value)
        value = _QUERY.sub(r"\1[REDACTED]", value)
        value = _BEARER.sub(r"\1 [REDACTED]", value)
        return _KEY_VALUE.sub(r"\1[REDACTED]", value)
    if isinstance(value, int | float | bool) or value is None:
        return value
    return redact_log(str(value))
