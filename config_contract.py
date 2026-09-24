"""Shared configuration contract for the Python installer and hooks.

This module deliberately contains only pure validation/normalization helpers.
Host adapters may layer source precedence and diagnostics on top of it.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1
BEHAVIORS = frozenset({"auto", "preview", "off"})
SCOPES = frozenset({"first", "all"})
QUALITY_GATES = frozenset({"pass", "light", "full", "adaptive"})
UNSUPPORTED_MODELS = frozenset({"skip", "generic"})
LEGACY_MODES = frozenset({"first", "all", "off"})

DEFAULTS: dict[str, Any] = {
    "schemaVersion": SCHEMA_VERSION,
    "behavior": "auto",
    "scope": "all",
    "qualityGate": "adaptive",
    "unsupportedModel": "skip",
}


def normalize_quality_gate(value: Any) -> str | None:
    """Normalize the v4 boolean quality gate without accepting bad values."""
    if isinstance(value, bool):
        return "adaptive" if value else "pass"
    return value if isinstance(value, str) and value in QUALITY_GATES else None


def invalid_fields(value: Any) -> set[str]:
    """Return managed fields that violate the public schema contract."""
    if not isinstance(value, dict):
        return {"<object>"}
    invalid: set[str] = set()
    checks = {
        "schemaVersion": lambda item: isinstance(item, int) and not isinstance(item, bool) and item == SCHEMA_VERSION,
        "behavior": lambda item: isinstance(item, str) and item in BEHAVIORS,
        "scope": lambda item: isinstance(item, str) and item in SCOPES,
        "qualityGate": lambda item: normalize_quality_gate(item) is not None,
        "unsupportedModel": lambda item: isinstance(item, str) and item in UNSUPPORTED_MODELS,
        "mode": lambda item: isinstance(item, str) and item in LEGACY_MODES,
    }
    for key, check in checks.items():
        if key in value and not check(value[key]):
            invalid.add(key)
    return invalid


def validate_object(value: Any) -> dict[str, Any]:
    """Validate a managed config and return the original object unchanged."""
    errors = invalid_fields(value)
    if errors:
        raise ValueError("invalid configuration fields: " + ", ".join(sorted(errors)))
    return dict(value)


def normalize(value: Any, *, include_schema: bool = False) -> dict[str, Any]:
    """Apply defaults and legacy quality-gate normalization.

    Unknown fields are preserved by design. Invalid managed fields are rejected
    instead of silently falling back, allowing callers to fail safe.
    """
    source = validate_object(value)
    result = dict(DEFAULTS)
    result.update(source)
    result["qualityGate"] = normalize_quality_gate(result["qualityGate"])
    if not include_schema:
        result.pop("schemaVersion", None)
    return result


def managed_config(behavior: str, scope: str, unsupported_model: str, quality_gate: str | bool) -> dict[str, Any]:
    """Build the managed fields written by the installer."""
    value = {
        "schemaVersion": SCHEMA_VERSION,
        "behavior": behavior,
        "scope": scope,
        "qualityGate": quality_gate,
        "unsupportedModel": unsupported_model,
    }
    validate_object(value)
    return value
