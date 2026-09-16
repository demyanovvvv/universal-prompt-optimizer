"""Small recursive redaction helper for evaluation artifacts."""

from __future__ import annotations

import re
from typing import Any


_SECRET_PATTERNS = (
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(api[_ -]?key\s*[=:]\s*)[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(sk-[A-Za-z0-9_-]{8,})"), "[REDACTED]"),
)
_SENSITIVE_KEYS = {"api_key", "apikey", "authorization", "access_token", "refresh_token", "secret", "password"}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, str):
        for pattern, replacement in _SECRET_PATTERNS:
            value = pattern.sub(replacement, value)
        return value
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if isinstance(key, str) and key.casefold().replace("-", "_") in _SENSITIVE_KEYS else redact_sensitive(item)
            for key, item in value.items()
        }
    return value
