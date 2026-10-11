"""Local installation metadata; never stores prompts or runtime history."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from .domain import InstallPlan, InstallRequest, Operation


def state_path(root: Path, scope: str) -> Path:
    if scope not in {"project", "global"}:
        raise ValueError("scope must be project or global")
    return root / (".prompt-optimizer-install.json" if scope == "project" else ".config/prompt-optimizer/install.json")


def owned_path(root: Path, scope: str, relative: str) -> Path:
    from .lifecycle import managed_file_map
    if not isinstance(relative, str) or "\\" in relative:
        raise ValueError("invalid installation inventory path")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or ":" in relative or parts.as_posix() != relative:
        raise ValueError(f"invalid installation inventory path: {relative}")
    path = root / relative
    mapping = managed_file_map(root, root, scope)
    trees = [mapping["shared-skills"][1] / "prompt-optimizer",
             mapping["claude-skills"][1] / "prompt-optimizer", mapping["opencode-plugin"][1]]
    if any(tree in path.parents for tree in trees):
        return path
    files = {mapping[key][1] for key in ("cursor-hook", "cursor-rule", "gemini-hook")}
    if scope == "project":
        files.add(root / ".windsurf/rules/prompt-optimizer.md")
    files.update(mapping["opencode-commands"][1] / name for name in ("prompt.md", "prompt-only.md", "prompt-optimizer.md"))
    files.update(mapping["opencode-tui-plugin"][1] / name for name in ("prompt-optimizer.tsx", ".prompt-optimizer-owner.json"))
    # Pi shares its extension directory with user extensions.
    files.update(mapping["pi-extension"][1] / name for name in ("prompt-optimizer.ts", "model-registry.ts"))
    if path not in files:
        raise ValueError(f"inventory path is not package-owned: {relative}")
    return path


def read_state(root: Path, scope: str) -> dict | None:
    from .catalog import load_catalog
    path = state_path(root, scope)
    current = path
    while current != current.parent:
        if current.is_symlink():
            raise ValueError(f"refusing installation metadata through symlink: {current}")
        current = current.parent
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(value, dict) or value.get("schema") != 1 or value.get("scope") != scope
            or not isinstance(value.get("version"), str) or not isinstance(value.get("files"), list)
            or not isinstance(value.get("adapters"), list) or not isinstance(value.get("automatic"), bool)):
        raise ValueError(f"invalid installation metadata: {path}")
    load_catalog(Path(__file__).resolve().parents[1]).require(value["adapters"])
    from config_contract import BEHAVIORS, SCOPES, UNSUPPORTED_MODELS, normalize_quality_gate
    settings = value.get("settings", {})
    if (not isinstance(settings, dict)
            or ("behavior" in settings and settings["behavior"] not in BEHAVIORS)
            or ("prompt_scope" in settings and settings["prompt_scope"] not in SCOPES)
            or ("unsupported_model" in settings and settings["unsupported_model"] not in UNSUPPORTED_MODELS)
            or ("quality_gate" in settings and normalize_quality_gate(settings["quality_gate"]) is None)):
        raise ValueError(f"invalid installation settings: {path}")
    for relative in value["files"]:
        owned_path(root, scope, relative)
    allowed = config_paths(root, scope)
    if not isinstance(value.get('created_configs', []), list) or any(item not in allowed for item in value.get('created_configs', [])):
        raise ValueError(f"invalid installation configuration inventory: {path}")
    return value


def config_paths(root: Path, scope: str) -> set[str]:
    base = '.opencode' if scope == 'project' else '.config/opencode'
    return {f'{base}/tui.json', f'{base}/opencode.json', '.cursor/hooks.json', '.gemini/settings.json'}


def with_install_state(plan: InstallPlan, request: InstallRequest, package_root: Path) -> InstallPlan:
    files: set[str] = set()
    for op in plan.operations:
        if op.kind in {"copy_file", "copy_owned_file", "write"}:
            files.add(op.path.relative_to(request.root).as_posix())
        elif op.kind in {"copy_tree", "copy_files"}:
            if op.source is None:
                raise ValueError(f"missing package source: {op.path}")
            source = package_root / op.source
            include = set(op.params.get("include", ())) if op.params else None
            for item in source.rglob("*"):
                relative = item.relative_to(source)
                if not item.is_file() or (include is not None and relative.parts[0] not in include):
                    continue
                files.add((op.path / relative).relative_to(request.root).as_posix())
    for relative in files:
        owned_path(request.root, request.scope, relative)
    previous = read_state(request.root, request.scope)
    created_configs = set(previous.get('created_configs', [])) if previous else set()
    allowed_configs = config_paths(request.root, request.scope)
    for op in plan.operations:
        relative = op.path.relative_to(request.root).as_posix()
        if relative in allowed_configs and not op.path.exists():
            created_configs.add(relative)
    operations = []
    # Keep adapters installed by earlier partial installs in the same scope.
    retained = set(previous["files"]) if previous else set()
    for relative in retained - files:
        path = owned_path(request.root, request.scope, relative)
        # A file disappears only when its destination tree is being refreshed.
        if any(op.kind == "copy_tree" and op.path in path.parents
               and (not op.params or not op.params.get("include") or path.relative_to(op.path).parts[0] in op.params["include"])
               for op in plan.operations):
            operations.extend((Operation("delete_owned_file", path, label="obsolete package file"),
                               Operation("delete_owned_file", path.with_name(path.name + ".prompt-optimizer.bak"), label="obsolete backup")))
            retained.discard(relative)
    settings = {"behavior": request.behavior, "prompt_scope": request.prompt_scope,
                "quality_gate": request.quality_gate, "unsupported_model": request.unsupported_model}
    value = {"schema": 1, "scope": request.scope,
             "version": (package_root / "VERSION").read_text(encoding="utf-8").strip(),
             "adapters": sorted(set(request.adapters) | set(previous["adapters"] if previous else [])),
             "automatic": request.automatic or bool(previous and previous["automatic"]),
             "settings": settings, "files": sorted(files | retained), "created_configs": sorted(created_configs)}
    operations.extend(plan.operations)
    operations.append(Operation("write", state_path(request.root, request.scope),
                                content=(json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode(),
                                label="installation version"))
    return InstallPlan(tuple(operations))
