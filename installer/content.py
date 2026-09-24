"""Pure, deterministic managed-content transformations."""

from __future__ import annotations

import json
from typing import Any


def merge_json(current_text: str | None, updates: dict[str, Any]) -> str:
    if current_text is None or not current_text.strip():
        current: dict[str, Any] = {}
    else:
        value = json.loads(current_text)
        if not isinstance(value, dict):
            raise ValueError("configuration root must be a JSON object")
        current = value
    current.update(updates)
    return json.dumps(current, ensure_ascii=False, indent=2) + "\n"


def configured_snippet_block(snippet: str, behavior: str, scope: str, unsupported_model: str, quality_gate: str | bool) -> str:
    """Inject the installer-config line into a shared markdown snippet."""
    marker = "<!-- prompt-optimizer:auto:end -->"
    if marker not in snippet:
        raise ValueError("managed snippet is missing its end marker")
    if isinstance(quality_gate, str):
        gate = quality_gate
    else:
        gate = "adaptive" if quality_gate else "pass"
    line = (
        f"\nConfigured by installer: `behavior={behavior}`, `scope={scope}`, "
        f"`qualityGate={gate}`, `unsupportedModel={unsupported_model}`. "
        "If a native adapter injects a newer per-turn setting, the native adapter wins.\n"
    )
    return snippet.replace(marker, line + marker)


def merge_managed_block(current: str, block: str, start: str, end: str) -> str:
    has_start, has_end = start in current, end in current
    if has_start != has_end:
        raise ValueError("incomplete managed block")
    if has_start:
        before, remainder = current.split(start, 1)
        _, after = remainder.split(end, 1)
        return before.rstrip() + "\n\n" + block.strip() + "\n" + after.lstrip("\n")
    return current.rstrip() + ("\n\n" if current.strip() else "") + block.strip() + "\n"
