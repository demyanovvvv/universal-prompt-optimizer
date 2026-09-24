"""Validated catalog of deployable adapter identifiers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AdapterCatalog:
    ids: frozenset[str]
    root: Path | None = None

    def require(self, requested: set[str] | frozenset[str]) -> frozenset[str]:
        unknown = set(requested) - self.ids
        if unknown:
            raise ValueError(f"unknown adapter(s): {', '.join(sorted(unknown))}")
        return frozenset(requested)

    def snippet(self, relative: str) -> str:
        if self.root is None:
            raise ValueError("adapter catalog has no package root for snippet lookup")
        path = self.root / relative
        try:
            return path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"missing package snippet: {path}") from exc


def load_catalog(root: Path) -> AdapterCatalog:
    path = root / "adapters" / "manifest.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid adapter manifest: {path}") from exc
    if value.get("schemaVersion") != 1 or not isinstance(value.get("adapters"), list):
        raise ValueError("adapter manifest must have schemaVersion=1 and an adapters array")
    ids = value["adapters"]
    if not ids or any(not isinstance(item, str) or not item.strip() for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("adapter manifest contains invalid or duplicate IDs")
    return AdapterCatalog(frozenset(ids), root)
