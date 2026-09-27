"""Installer request and filesystem-operation value objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class InstallRequest:
    root: Path
    scope: Literal["project", "global"]
    adapters: frozenset[str]
    automatic: bool = False
    behavior: Literal["auto", "preview", "off"] = "auto"
    prompt_scope: Literal["first", "all"] = "all"
    quality_gate: str = "adaptive"
    unsupported_model: Literal["skip", "generic"] = "generic"
    dry_run: bool = False
    backup: bool = True
    python_bin: str = "python3"


@dataclass(frozen=True)
class Operation:
    kind: Literal[
        "write", "delete", "merge", "copy_tree", "copy_file", "copy_files",
        "merge_hook", "merge_block", "copy_owned_file", "merge_tui", "merge_ignore",
        "delete_owned_file", "delete_file_if_matches", "delete_tree_if_matches",
        "delete_legacy_model_skill", "delete_legacy_model_command",
        "delete_block", "delete_json_fields", "delete_json_hooks", "delete_json_plugin_specs",
        "merge_json_plugin_specs",
    ]
    path: Path
    content: bytes | None = None
    source: Path | None = None
    label: str = "file"
    params: dict | None = None


@dataclass(frozen=True)
class InstallPlan:
    operations: tuple[Operation, ...]
