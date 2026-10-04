"""Pure install planning over explicit inputs and adapter catalog data."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

from .catalog import AdapterCatalog
from .content import configured_snippet_block, merge_json
from .domain import InstallPlan, InstallRequest, Operation
from config_contract import BEHAVIORS, SCOPES, UNSUPPORTED_MODELS, normalize_quality_gate
from config_contract import managed_config


def shell_command(args: list[str], *, platform: str | None = None) -> str:
    return subprocess.list2cmdline(args) if (platform or os.name) == 'nt' else shlex.join(args)


def plan_config_write(path: Path, updates: dict, *, existing: str | None = None) -> Operation:
    if existing is not None:
        return Operation("write", path, merge_json(existing, updates).encode("utf-8"), label="managed configuration")
    return Operation("merge", path, json.dumps(updates, ensure_ascii=False).encode("utf-8"), label="managed configuration")


def validate_request(request: InstallRequest, catalog: AdapterCatalog) -> InstallRequest:
    catalog.require(request.adapters)
    if not isinstance(request.root, Path):
        raise ValueError("root must be a pathlib.Path")
    if request.scope not in {"project", "global"}:
        raise ValueError("scope must be project or global")
    if request.behavior not in BEHAVIORS:
        raise ValueError("behavior must be auto, preview, or off")
    if request.prompt_scope not in SCOPES:
        raise ValueError("prompt_scope must be first or all")
    if normalize_quality_gate(request.quality_gate) is None:
        raise ValueError("quality_gate must be pass, light, full, or adaptive")
    if request.unsupported_model not in UNSUPPORTED_MODELS:
        raise ValueError("unsupported_model must be skip or generic")
    if not isinstance(request.automatic, bool) or not isinstance(request.dry_run, bool) or not isinstance(request.backup, bool):
        raise ValueError("automatic, dry_run, and backup must be booleans")
    if not isinstance(request.python_bin, str) or not request.python_bin.strip():
        raise ValueError("python_bin must be a non-empty string")
    return request


def plan_install(request: InstallRequest, catalog: AdapterCatalog) -> InstallPlan:
    validate_request(request, catalog)
    operations: list[Operation] = []
    root = request.root
    package_root = catalog.root
    if package_root is not None:
        registry_path = package_root / ".agents/skills/prompt-optimizer/references/model-registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        model_skills = [f"prompt-{item['id'].replace('.', '-')}" for item in registry.get("profiles", [])]
        if model_skills:
            for skill_name in model_skills:
                operations.append(Operation("delete_legacy_model_skill", root / ".agents/skills" / skill_name,
                                            label="obsolete model skill", params={"name": skill_name}))
            if "claude" in request.adapters:
                for skill_name in model_skills:
                    operations.append(Operation("delete_legacy_model_skill", root / ".claude/skills" / skill_name,
                                                label="obsolete Claude model skill", params={"name": skill_name}))
    skill_params = {"include": ["prompt-optimizer"]}
    operations.append(Operation("copy_tree", root / ".agents/skills", source=Path(".agents/skills"), label="shared skills", params=skill_params))
    if "claude" in request.adapters:
        operations.append(Operation("copy_tree", root / ".claude/skills", source=Path(".agents/skills"), label="Claude skills", params=skill_params))
    if "opencode" in request.adapters:
        commands_dest = root / (".opencode/commands" if request.scope == "project" else ".config/opencode/commands")
        if package_root is not None:
            for command in [*model_skills, "po-status"]:
                operations.append(Operation("delete_legacy_model_command", commands_dest / f"{command}.md",
                                            label="obsolete OpenCode command"))
        operations.append(Operation("copy_files", commands_dest, source=Path("adapters/opencode/commands"), label="OpenCode commands",
                                    params={"include": ["prompt.md", "prompt-only.md", "prompt-optimizer.md"]}))
        opencode_base = root / (".opencode" if request.scope == "project" else ".config/opencode")
        if request.automatic:
            operations.append(Operation("copy_tree", opencode_base / "plugins/prompt-optimizer",
                                        source=Path("adapters/opencode/plugin"), label="OpenCode plugin"))
            operations.append(Operation("merge_json_plugin_specs", opencode_base / "opencode.json",
                                        content=json.dumps({"plugin": "./plugins/prompt-optimizer/index.ts"}).encode("utf-8"),
                                        label="OpenCode server plugin registration"))
            tui_base = root / (".opencode" if request.scope == "project" else ".config/opencode")
            tui_plugin = tui_base / "plugins/prompt-optimizer-tui/prompt-optimizer.tsx"
            operations.append(Operation("copy_owned_file", tui_plugin, source=Path("adapters/opencode/tui/prompt-optimizer.tsx"), label="OpenCode TUI plugin"))
            operations.append(Operation("merge_tui", tui_base / "tui.json", content=json.dumps({"plugin": "./plugins/prompt-optimizer-tui/prompt-optimizer.tsx"}).encode("utf-8"), label="OpenCode TUI config"))
            owner_marker = {"schema": 1, "owned": True, "path": tui_plugin.name}
            operations.append(Operation("write", tui_plugin.parent / ".prompt-optimizer-owner.json", content=json.dumps(owner_marker).encode("utf-8"), label="OpenCode TUI ownership marker"))
    if request.automatic:
        shared_config_path = root / (".prompt-optimizer.json" if request.scope == "project" else ".config/prompt-optimizer/config.json")
        operations.append(plan_config_write(shared_config_path, managed_config(
            request.behavior, request.prompt_scope, request.unsupported_model, request.quality_gate
        )))
        markdown_blocks = (
            ("gemini", "auto/GEMINI.snippet.md", "GEMINI.md", ".gemini/GEMINI.md", "Gemini managed block"),
            ("claude", "auto/CLAUDE.snippet.md", "CLAUDE.md", ".claude/CLAUDE.md", "Claude managed block"),
            ("codex", "auto/AGENTS.snippet.md", "AGENTS.md", ".codex/AGENTS.md", "Codex managed block"),
            ("copilot", "auto/AGENTS.snippet.md", ".github/copilot-instructions.md", ".copilot/copilot-instructions.md", "Copilot managed block"),
        )
        for adapter, snippet_rel, project_rel, global_rel, label in markdown_blocks:
            if adapter not in request.adapters:
                continue
            block = configured_snippet_block(
                catalog.snippet(snippet_rel),
                request.behavior,
                request.prompt_scope,
                request.unsupported_model,
                request.quality_gate,
            )
            relative = project_rel if request.scope == "project" else global_rel
            operations.append(Operation("merge_block", root / relative, content=block.encode("utf-8"), label=label))
        if "windsurf" in request.adapters:
            if request.scope == "project":
                operations.append(Operation(
                    "copy_file",
                    root / ".windsurf/rules/prompt-optimizer.md",
                    source=Path("adapters/windsurf/prompt-optimizer-rule.md"),
                    label="Windsurf rule",
                ))
            else:
                block = configured_snippet_block(
                    catalog.snippet("auto/AGENTS.snippet.md"),
                    request.behavior,
                    request.prompt_scope,
                    request.unsupported_model,
                    request.quality_gate,
                )
                operations.append(Operation(
                    "merge_block",
                    root / ".codeium/windsurf/memories/global_rules.md",
                    content=block.encode("utf-8"),
                    label="Windsurf managed block",
                ))
    if "opencode" in request.adapters:
        config_path = opencode_base / "prompt-optimizer.json"
        updates = {"schemaVersion": 1, "behavior": request.behavior, "scope": request.prompt_scope,
                   "qualityGate": request.quality_gate, "unsupportedModel": request.unsupported_model}
        operations.append(plan_config_write(config_path, updates))
    if "pi" in request.adapters:
        base = root / (".pi/extensions" if request.scope == "project" else ".pi/agent/extensions")
        operations.append(Operation("copy_tree", base, source=Path("adapters/pi/extensions"), label="Pi extension"))
    runtime_ignores: list[str] = []
    if request.automatic and request.scope == "project" and "cursor" in request.adapters:
        operations.extend((
            Operation("copy_file", root / ".cursor/hooks/prompt-optimizer-state.py", source=Path("adapters/cursor/hooks/prompt-optimizer-state.py"), label="Cursor model-state hook"),
            Operation("copy_file", root / ".cursor/rules/prompt-optimizer.mdc", source=Path("adapters/cursor/rules/prompt-optimizer.mdc"), label="Cursor always rule"),
        ))
        command = shell_command([request.python_bin, "-B", ".cursor/hooks/prompt-optimizer-state.py"])
        hook = {"name": "prompt-optimizer", "owner": "universal-prompt-optimizer", "command": command}
        operations.append(_hook_operation(root / ".cursor/hooks.json", "beforeSubmitPrompt", hook))
        runtime_ignores.extend([
            ".cursor/.prompt-optimizer-runtime.json",
            ".cursor/.prompt-optimizer-session-state.json",
            ".cursor/*.prompt-optimizer-*.json.lock",
        ])
    if request.automatic and "gemini" in request.adapters:
        operations.append(Operation("copy_file", root / ".gemini/hooks/prompt-preflight.py", source=Path("adapters/gemini-cli/hooks/prompt-preflight.py"), label="Gemini CLI hook"))
        script_root = "os.path.expanduser('~')" if request.scope == 'global' else "os.environ.get('GEMINI_PROJECT_DIR') or os.getcwd()"
        code = f"import os,runpy;runpy.run_path(os.path.join({script_root},'.gemini','hooks','prompt-preflight.py'),run_name='__main__')"
        command = shell_command([request.python_bin, "-B", "-c", code])
        hook = {"hooks": [{"name": "prompt-optimizer", "owner": "universal-prompt-optimizer", "type": "command", "command": command, "timeout": 5000}]}
        settings = root / ".gemini/settings.json"
        operations.extend((_hook_operation(settings, "BeforeAgent", hook), _hook_operation(settings, "BeforeModel", hook)))
        runtime_ignores.extend([
            ".gemini/.prompt-optimizer-model-state.json",
            ".gemini/.prompt-optimizer-session-state.json",
            ".gemini/*.prompt-optimizer-*.json.lock",
        ])
    if runtime_ignores:
        operations.append(Operation("merge_ignore", root / ".gitignore", content=json.dumps(runtime_ignores).encode("utf-8"), label="Runtime ignores"))
    return InstallPlan(tuple(operations))


def _hook_operation(path: Path, event: str, hook: dict) -> Operation:
    return Operation("merge_hook", path, json.dumps({"event": event, "hook": hook}, ensure_ascii=False).encode("utf-8"), label=f"{event} hook")
