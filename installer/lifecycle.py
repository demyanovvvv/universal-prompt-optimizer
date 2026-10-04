"""Uninstall planning and read-only health diagnostics over managed paths.

The map in :func:`managed_file_map` is the single source of truth shared by the
install, uninstall and doctor paths. It mirrors the destinations produced by
:mod:`installer.planning` so that removal and diagnostics stay aligned with
installation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .domain import InstallPlan, Operation

Scope = Literal["project", "global"]

_BLOCK_LOGICAL = frozenset({"claude-block", "gemini-block", "copilot-block", "codex-block", "windsurf-block"})
_CONFIG_LOGICAL = frozenset({"shared-config", "opencode-config"})
_DIR_LOGICAL = frozenset({"shared-skills", "claude-skills", "opencode-commands", "opencode-plugin", "opencode-tui-plugin", "pi-extension"})


def managed_file_map(root: Path, package_root: Path, scope: str) -> dict[str, tuple[Path, Path]]:
    """Return logical managed files and their package source counterparts."""
    if scope not in {"project", "global"}:
        raise ValueError("scope must be project or global")
    project = scope == "project"
    return {
        "shared-skills": (package_root / ".agents/skills", root / ".agents/skills"),
        "claude-skills": (package_root / ".agents/skills", root / ".claude/skills"),
        "opencode-commands": (
            package_root / "adapters/opencode/commands",
            root / (".opencode/commands" if project else ".config/opencode/commands"),
        ),
        "shared-config": (
            package_root / "adapters/opencode/prompt-optimizer.auto.json",
            root / (".prompt-optimizer.json" if project else ".config/prompt-optimizer/config.json"),
        ),
        "opencode-plugin": (
            package_root / "adapters/opencode/plugin",
            root / (".opencode/plugins/prompt-optimizer" if project else ".config/opencode/plugins/prompt-optimizer"),
        ),
        "opencode-tui-plugin": (
            package_root / "adapters/opencode/tui",
            root / (".opencode/plugins/prompt-optimizer-tui" if project else ".config/opencode/plugins/prompt-optimizer-tui"),
        ),
        "opencode-config": (
            package_root / "adapters/opencode/prompt-optimizer.auto.json",
            root / (".opencode/prompt-optimizer.json" if project else ".config/opencode/prompt-optimizer.json"),
        ),
        "pi-extension": (
            package_root / "adapters/pi/extensions",
            root / (".pi/extensions" if project else ".pi/agent/extensions"),
        ),
        "cursor-hook": (
            package_root / "adapters/cursor/hooks/prompt-optimizer-state.py",
            root / ".cursor/hooks/prompt-optimizer-state.py",
        ),
        "cursor-rule": (
            package_root / "adapters/cursor/rules/prompt-optimizer.mdc",
            root / ".cursor/rules/prompt-optimizer.mdc",
        ),
        "gemini-hook": (
            package_root / "adapters/gemini-cli/hooks/prompt-preflight.py",
            root / ".gemini/hooks/prompt-preflight.py",
        ),
        "claude-block": (package_root / "auto/CLAUDE.snippet.md", root / ("CLAUDE.md" if project else ".claude/CLAUDE.md")),
        "gemini-block": (package_root / "auto/GEMINI.snippet.md", root / ("GEMINI.md" if project else ".gemini/GEMINI.md")),
        "copilot-block": (
            package_root / "auto/AGENTS.snippet.md",
            root / (".github/copilot-instructions.md" if project else ".copilot/copilot-instructions.md"),
        ),
        "codex-block": (package_root / "auto/AGENTS.snippet.md", root / ("AGENTS.md" if project else ".codex/AGENTS.md")),
        "windsurf-block": (
            package_root / ("adapters/windsurf/prompt-optimizer-rule.md" if project else "auto/AGENTS.snippet.md"),
            root / (".windsurf/rules/prompt-optimizer.md" if project else ".codeium/windsurf/memories/global_rules.md"),
        ),
    }


def uninstall_targets(root: Path, package_root: Path, scope: str) -> dict[str, tuple[Path, Path, str]]:
    """Classify managed entries by removal strategy for uninstall and doctor."""
    mapping = managed_file_map(root, package_root, scope)
    targets: dict[str, tuple[Path, Path, str]] = {}
    for logical, (source, destination) in mapping.items():
        if logical == 'windsurf-block' and scope == 'project':
            targets[logical] = (source, destination, "file")
        elif logical in _BLOCK_LOGICAL:
            targets[logical] = (source, destination, "block")
        elif logical in _CONFIG_LOGICAL:
            targets[logical] = (source, destination, "config")
        elif logical in _DIR_LOGICAL:
            targets[logical] = (source, destination, "dir")
        else:
            targets[logical] = (source, destination, "owned_file")
    return targets


_CONFIG_FIELDS = ("schemaVersion", "behavior", "scope", "qualityGate", "unsupportedModel")
_TUI_PLUGIN_NAME = "prompt-optimizer.tsx"
_TUI_PLUGIN_SPEC = "./plugins/prompt-optimizer-tui/prompt-optimizer.tsx"
_SERVER_PLUGIN_SPEC = "./plugins/prompt-optimizer/index.ts"


def build_uninstall_plan(root: Path, package_root: Path, scope: str) -> InstallPlan:
    """Return a declarative uninstall plan over managed destinations.

    Markdown entries use ``delete_block`` (removes only the installer-owned
    block), regular files use ``delete_owned_file`` (removes the installer
    artifact even if it was edited), directory trees remove only managed
    entries. Managed JSON config fields, hooks and the TUI registration are
    cleaned explicitly. Runtime state and gitignore cleanup are appended last.
    """
    targets = uninstall_targets(root, package_root, scope)
    operations: list[Operation] = []
    for logical, (source, destination, strategy) in targets.items():
        if strategy == "block":
            operations.append(Operation("delete_block", destination, source=source, label=logical))
        elif strategy == "config":
            operations.append(Operation("delete_json_fields", destination, source=source, label=logical,
                                        params={"fields": list(_CONFIG_FIELDS)}))
        elif strategy == "dir":
            if logical == "opencode-tui-plugin":
                tui_config = root / (".opencode/tui.json" if scope == "project" else ".config/opencode/tui.json")
                operations.append(Operation("delete_json_plugin_specs", tui_config, label="opencode-tui-registration",
                                            params={"specs": [_TUI_PLUGIN_SPEC]}))
            if logical == "opencode-plugin":
                opencode_config = root / (".opencode/opencode.json" if scope == "project" else ".config/opencode/opencode.json")
                operations.append(Operation("delete_json_plugin_specs", opencode_config, label="opencode-server-registration",
                                            params={"specs": [_SERVER_PLUGIN_SPEC]}))
                operations.append(Operation("delete_tree_if_matches", destination, source=source, label=logical,
                                            params={"remove_modified": True, "remove_unlisted": True}))
            if logical == "opencode-tui-plugin":
                operations.append(Operation("delete_tree_if_matches", destination, source=source, label=logical,
                                            params={"requires_owner": True, "owner_name": _TUI_PLUGIN_NAME,
                                                    "remove_modified": True, "remove_unlisted": True}))
                operations.append(Operation("delete_owned_file", destination / ".prompt-optimizer-owner.json",
                                            label="opencode-tui-owner"))
            elif logical != "opencode-plugin":
                params = {"remove_modified": True}
                if logical in {"shared-skills", "claude-skills"}:
                    params.update({"include": ["prompt-optimizer"], "remove_unlisted": True})
                elif logical == "opencode-commands":
                    params["include"] = ["prompt.md", "prompt-only.md", "prompt-optimizer.md"]
                operations.append(Operation("delete_tree_if_matches", destination, source=source, label=logical, params=params))
        else:
            operations.append(Operation("delete_owned_file", destination, source=source, label=logical))
    if scope == "project":
        operations.append(Operation("delete_json_hooks", root / ".cursor/hooks.json", label="cursor-hooks",
                                    params={"events": ["beforeSubmitPrompt"]}))
    operations.append(Operation("delete_json_hooks", root / ".gemini/settings.json", label="gemini-hooks",
                                params={"events": ["BeforeAgent", "BeforeModel"]}))
    operations.append(Operation("delete_block", root / ".gitignore", label="runtime ignores"))
    backup_paths = {operation.path for operation in operations if operation.kind != "delete_tree_if_matches"}
    for source, destination, strategy in targets.values():
        if strategy == "dir":
            for source_file in source.rglob("*"):
                if source_file.is_file():
                    relative = source_file.relative_to(source)
                    if destination.name == "skills" and relative.parts[0] != "prompt-optimizer":
                        continue
                    if destination.name == "commands" and relative.name not in {"prompt.md", "prompt-only.md", "prompt-optimizer.md"}:
                        continue
                    backup_paths.add(destination / relative)
    for path in sorted(backup_paths):
        operations.append(Operation("delete_owned_file", path.with_name(path.name + ".prompt-optimizer.bak"), label="installer backup"))
    for runtime in (
        root / ".cursor/.prompt-optimizer-runtime.json",
        root / ".cursor/.prompt-optimizer-session-state.json",
        root / ".gemini/.prompt-optimizer-model-state.json",
        root / ".gemini/.prompt-optimizer-session-state.json",
    ):
        operations.append(Operation("delete_owned_file", runtime, label="runtime state"))
    return InstallPlan(tuple(operations))


@dataclass(frozen=True)
class Diagnosis:
    found: int
    errors: tuple[str, ...]
    status: Literal["healthy", "not-installed", "invalid"]


def diagnose(root: Path, package_root: Path, scope: str) -> Diagnosis:
    """Perform a read-only inspection of managed config and markdown blocks."""
    errors: list[str] = []
    found = 0
    config_paths = [destination for _, destination, strategy in uninstall_targets(root, package_root, scope).values() if strategy == "config"]
    for path in config_paths:
        if not path.exists():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("configuration root must be a JSON object")
            behavior = value.get("behavior", "auto")
            if behavior not in {"auto", "preview", "off"}:
                raise ValueError(f"invalid behavior: {behavior}")
            found += 1
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid config {path}: {exc}")
    for _, destination, strategy in uninstall_targets(root, package_root, scope).values():
        if strategy != "block" or not destination.exists():
            continue
        try:
            text = destination.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"unreadable managed block {destination}: {exc}")
            continue
        has_start = "<!-- prompt-optimizer:auto:start -->" in text
        has_end = "<!-- prompt-optimizer:auto:end -->" in text
        if has_start != has_end:
            errors.append(f"incomplete managed block: {destination}")
        elif has_start:
            found += 1
    status: Literal["healthy", "not-installed", "invalid"]
    if errors:
        status = "invalid"
    elif found:
        status = "healthy"
    else:
        status = "not-installed"
    return Diagnosis(found=found, errors=tuple(errors), status=status)
