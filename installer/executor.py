"""Apply installer plans with explicit source roots and rollback support."""

from __future__ import annotations

from pathlib import Path
import json
import re

from .content import merge_json
from .domain import InstallPlan, Operation
from .filesystem import atomic_write_bytes
from .transaction import InstallTransaction


def _reject_symlink(path: Path) -> None:
    current = path
    while current != current.parent:
        if current.is_symlink():
            raise ValueError(f"refusing to write through symlink: {current}")
        current = current.parent


def _backup_once(path: Path, transaction: InstallTransaction, enabled: bool) -> None:
    if not enabled or not path.exists():
        return
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"cannot back up non-file destination: {path}")
    backup = path.with_name(path.name + ".prompt-optimizer.bak")
    if backup.exists():
        return
    _reject_symlink(backup)
    transaction.record(backup)
    atomic_write_bytes(backup, path.read_bytes())


def _copy_tree(operation: Operation, source_root: Path, transaction: InstallTransaction, backup: bool) -> None:
    if operation.source is None:
        raise ValueError(f"copy_tree operation has no source: {operation.path}")
    source = operation.source if operation.source.is_absolute() else source_root / operation.source
    if source.is_symlink() or not source.is_dir():
        raise ValueError(f"missing package directory: {source}")
    if operation.path.resolve() == source.resolve():
        raise ValueError(f"source and destination are the same: {operation.path}")
    try:
        operation.path.resolve().relative_to(source.resolve())
    except ValueError:
        pass
    else:
        raise ValueError(f"destination is inside source tree: {operation.path}")
    _reject_symlink(operation.path)
    if operation.path.exists() and not operation.path.is_dir():
        raise ValueError(f"destination is not a directory: {operation.path}")
    operation.path.mkdir(parents=True, exist_ok=True)
    include = set(operation.params.get("include", ())) if operation.params else None
    for source_file in source.rglob("*"):
        if source_file.is_symlink():
            raise ValueError(f"package tree contains symlink: {source_file}")
        if not source_file.is_file():
            continue
        relative = source_file.relative_to(source)
        if include is not None and (relative.parts[0] if relative.parts else "") not in include:
            continue
        destination = operation.path / relative
        _reject_symlink(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        _backup_once(destination, transaction, backup)
        transaction.record(destination)
        atomic_write_bytes(destination, source_file.read_bytes())


def _source_file(operation: Operation, source_root: Path) -> Path:
    if operation.source is None:
        raise ValueError(f"copy_file operation has no source: {operation.path}")
    source = operation.source if operation.source.is_absolute() else source_root / operation.source
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"missing package file: {source}")
    if source.resolve() == operation.path.resolve():
        raise ValueError(f"source and destination are the same: {operation.path}")
    return source


def _copy_files(operation: Operation, source_root: Path, transaction: InstallTransaction, backup: bool) -> None:
    if operation.source is None:
        raise ValueError(f"copy_files operation has no source: {operation.path}")
    source = operation.source if operation.source.is_absolute() else source_root / operation.source
    if source.is_symlink() or not source.is_dir():
        raise ValueError(f"missing package directory: {source}")
    _reject_symlink(operation.path)
    if operation.path.exists() and not operation.path.is_dir():
        raise ValueError(f"destination is not a directory: {operation.path}")
    include = set(operation.params.get("include", ())) if operation.params else None
    for source_file in source.glob("*.md"):
        if source_file.is_symlink() or not source_file.is_file():
            raise ValueError(f"invalid package file: {source_file}")
        if include is not None and source_file.name not in include:
            continue
        destination = operation.path / source_file.name
        _reject_symlink(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        _backup_once(destination, transaction, backup)
        transaction.record(destination)
        atomic_write_bytes(destination, source_file.read_bytes())


def _is_owned_by_marker(directory: Path, name: str) -> bool:
    marker_path = directory / ".prompt-optimizer-owner.json"
    if not marker_path.exists():
        return False
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return marker.get("schema") == 1 and marker.get("owned") is True and marker.get("path") == name


def _copy_owned_file(operation: Operation, source_root: Path, transaction: InstallTransaction, backup: bool) -> None:
    source = _source_file(operation, source_root)
    owned = _is_owned_by_marker(operation.path.parent, operation.path.name)
    if operation.path.exists() and not owned and operation.path.read_bytes() != source.read_bytes():
        raise ValueError(f"refusing to overwrite user-owned file: {operation.path}")
    _reject_symlink(operation.path)
    operation.path.parent.mkdir(parents=True, exist_ok=True)
    _backup_once(operation.path, transaction, backup)
    transaction.record(operation.path)
    atomic_write_bytes(operation.path, source.read_bytes())


def _merge_block(operation: Operation, transaction: InstallTransaction, backup: bool) -> None:
    if operation.content is None:
        raise ValueError(f"merge_block operation has no content: {operation.path}")
    _reject_symlink(operation.path)
    current = operation.path.read_text(encoding="utf-8") if operation.path.exists() else ""
    block = operation.content.decode("utf-8").strip()
    start, end = "<!-- prompt-optimizer:auto:start -->", "<!-- prompt-optimizer:auto:end -->"
    if (start in current) != (end in current):
        raise ValueError(f"incomplete managed block: {operation.path}")
    if start in current:
        before, rest = current.split(start, 1)
        _, after = rest.split(end, 1)
        prefix = before.rstrip()
        suffix = after.lstrip("\n")
        value = prefix + ("\n\n" if prefix else "") + block + "\n" + suffix
    else:
        value = current.rstrip() + ("\n\n" if current.strip() else "") + block + "\n"
    _backup_once(operation.path, transaction, backup)
    transaction.record(operation.path)
    atomic_write_bytes(operation.path, value.encode("utf-8"))


def _merge_tui(operation: Operation, transaction: InstallTransaction, backup: bool) -> None:
    if operation.content is None:
        raise ValueError(f"merge_tui operation has no content: {operation.path}")
    _reject_symlink(operation.path)
    try:
        current = json.loads(operation.path.read_text(encoding="utf-8")) if operation.path.exists() else {}
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid TUI JSON configuration: {operation.path}") from exc
    if not isinstance(current, dict):
        raise ValueError(f"TUI config root must be an object: {operation.path}")
    try:
        spec = json.loads(operation.content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"merge_tui operation contains invalid JSON: {operation.path}") from exc
    plugins = current.get("plugin", [])
    if not isinstance(plugins, list):
        raise ValueError(f"plugin must be an array: {operation.path}")
    if spec["plugin"] not in plugins:
        plugins.append(spec["plugin"])
    current.setdefault("$schema", "https://opencode.ai/tui.json")
    current["plugin"] = plugins
    _backup_once(operation.path, transaction, backup)
    transaction.record(operation.path)
    atomic_write_bytes(operation.path, (json.dumps(current, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _merge_ignore(operation: Operation, transaction: InstallTransaction, backup: bool) -> None:
    if operation.content is None:
        raise ValueError(f"merge_ignore operation has no content: {operation.path}")
    entries = json.loads(operation.content.decode("utf-8"))
    if not isinstance(entries, list) or any(not isinstance(item, str) or not item.strip() for item in entries):
        raise ValueError(f"ignore entries must be non-empty strings: {operation.path}")
    _reject_symlink(operation.path)
    current = operation.path.read_text(encoding="utf-8") if operation.path.exists() else ""
    start, end = "# prompt-optimizer:runtime:start", "# prompt-optimizer:runtime:end"
    if (start in current) != (end in current):
        raise ValueError(f"incomplete runtime ignore block: {operation.path}")
    prior = []
    if start in current:
        _, section = current.split(start, 1)
        section, _ = section.split(end, 1)
        prior = [line.strip() for line in section.splitlines() if line.strip() and not line.strip().startswith("#")]
    managed = list(dict.fromkeys([*prior, *entries]))
    block = start + "\n" + "\n".join(managed) + "\n" + end
    if start in current:
        before, rest = current.split(start, 1)
        _, after = rest.split(end, 1)
        prefix = before.rstrip()
        suffix = after.lstrip("\n")
        value = prefix + ("\n\n" if prefix else "") + block + "\n" + suffix
    else:
        value = current.rstrip() + ("\n\n" if current.strip() else "") + block + "\n"
    _backup_once(operation.path, transaction, backup)
    transaction.record(operation.path)
    atomic_write_bytes(operation.path, value.encode("utf-8"))


def _apply_hook(operation: Operation, transaction: InstallTransaction, backup: bool) -> None:
    if operation.content is None:
        raise ValueError(f"merge_hook operation has no content: {operation.path}")
    _reject_symlink(operation.path)
    try:
        spec = json.loads(operation.content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"merge_hook operation contains invalid JSON: {operation.path}") from exc
    event, hook = spec.get("event"), spec.get("hook")
    if not isinstance(event, str) or not isinstance(hook, dict):
        raise ValueError(f"invalid hook operation: {operation.path}")
    try:
        current = json.loads(operation.path.read_text(encoding="utf-8")) if operation.path.exists() else {}
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON configuration: {operation.path}") from exc
    if not isinstance(current, dict):
        raise ValueError(f"hook config root must be an object: {operation.path}")
    current.setdefault("version", 1)
    hooks = current.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"hooks must be an object: {operation.path}")
    entries = hooks.setdefault(event, [])
    if not isinstance(entries, list):
        raise ValueError(f"{event} hooks must be an array: {operation.path}")
    entries[:] = [entry for entry in entries if not (isinstance(entry, dict) and entry.get("owner") == "universal-prompt-optimizer" and entry.get("name") == "prompt-optimizer")]
    entries.append(hook)
    _backup_once(operation.path, transaction, backup)
    transaction.record(operation.path)
    atomic_write_bytes(operation.path, (json.dumps(current, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


_BLOCK_START = "<!-- prompt-optimizer:auto:start -->"
_BLOCK_END = "<!-- prompt-optimizer:auto:end -->"
_MANAGED_HOOK_NAME = "prompt-optimizer"
_MANAGED_HOOK_OWNER = "universal-prompt-optimizer"


def _load_json(path: Path, description: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON configuration: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{description} root must be an object: {path}")
    return value


def _delete_block(operation: Operation, transaction: InstallTransaction) -> None:
    if not operation.path.exists():
        return
    _reject_symlink(operation.path)
    current = operation.path.read_text(encoding="utf-8")
    start, end = _BLOCK_START, _BLOCK_END
    if operation.params:
        start = operation.params.get("start", start)
        end = operation.params.get("end", end)
    if (start in current) != (end in current):
        raise ValueError(f"incomplete managed block: {operation.path}")
    if start not in current:
        return
    before, remainder = current.split(start, 1)
    _, after = remainder.split(end, 1)
    before, after = before.rstrip(), after.lstrip("\n")
    new = before + ("\n\n" if before and after else "") + after
    if before and not after:
        new += "\n"
    transaction.record(operation.path)
    if new.strip():
        atomic_write_bytes(operation.path, new.encode("utf-8"))
    else:
        operation.path.unlink()


def _delete_owned_file(operation: Operation, transaction: InstallTransaction) -> None:
    if not operation.path.exists():
        return
    _reject_symlink(operation.path)
    if not operation.path.is_file():
        raise ValueError(f"expected a file destination: {operation.path}")
    transaction.record(operation.path)
    operation.path.unlink()


def _delete_file_if_matches(operation: Operation, source_root: Path, transaction: InstallTransaction) -> None:
    if not operation.path.exists():
        return
    source = _source_file(operation, source_root)
    _reject_symlink(operation.path)
    if not operation.path.is_file():
        raise ValueError(f"expected a file destination: {operation.path}")
    if operation.path.read_bytes() != source.read_bytes():
        return
    transaction.record(operation.path)
    operation.path.unlink()


def _delete_tree_if_matches(operation: Operation, source_root: Path, transaction: InstallTransaction) -> None:
    if operation.source is None:
        raise ValueError(f"delete_tree_if_matches operation has no source: {operation.path}")
    source = operation.source if operation.source.is_absolute() else source_root / operation.source
    if not operation.path.exists():
        return
    if not operation.path.is_dir():
        raise ValueError(f"destination is not a directory: {operation.path}")
    if operation.params and operation.params.get("requires_owner"):
        if not _is_owned_by_marker(operation.path, operation.params.get("owner_name", operation.path.name)):
            return
        owned_name = operation.params.get("owner_name")
        owned_path = operation.path / owned_name if isinstance(owned_name, str) else None
        if owned_path is not None and owned_path.exists():
            _reject_symlink(owned_path)
            transaction.record(owned_path)
            owned_path.unlink()
    include = set(operation.params["include"]) if operation.params and "include" in operation.params else None
    remove_modified = bool(operation.params and operation.params.get("remove_modified"))
    remove_unlisted = bool(operation.params and operation.params.get("remove_unlisted"))
    candidates = []
    if remove_unlisted:
        for destination in operation.path.rglob("*"):
            if destination.is_file():
                relative = destination.relative_to(operation.path)
                if include is None or (relative.parts and relative.parts[0] in include):
                    candidates.append((None, relative, destination))
    for source_file in sorted(source.rglob("*")):
        if not source_file.is_file():
            continue
        relative = source_file.relative_to(source)
        if include is not None and (relative.parts[0] if relative.parts else "") not in include:
            continue
        candidates.append((source_file, relative, operation.path / relative))
    for source_file, relative, destination in candidates:
        if not destination.exists() or not destination.is_file():
            continue
        if source_file is not None and not remove_modified and destination.read_bytes() != source_file.read_bytes():
            continue
        _reject_symlink(destination)
        transaction.record(destination)
        destination.unlink()
    for directory in sorted((p for p in operation.path.rglob("*") if p.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    try:
        operation.path.rmdir()
    except OSError:
        pass


def _delete_legacy_model_skill(operation: Operation, transaction: InstallTransaction) -> None:
    if not operation.path.is_dir():
        return
    skill = operation.path / "SKILL.md"
    if not skill.is_file():
        return
    expected = operation.params.get("name") if operation.params else None
    text = skill.read_text(encoding="utf-8")
    if not isinstance(expected, str) or f"name: {expected}" not in text or "Activate the canonical `prompt-optimizer` skill" not in text:
        return
    transaction.record(skill)
    skill.unlink()
    try:
        operation.path.rmdir()
    except OSError:
        pass


def _delete_legacy_model_command(operation: Operation, transaction: InstallTransaction) -> None:
    if not operation.path.is_file():
        return
    text = operation.path.read_text(encoding="utf-8")
    legacy_status = """---
description: Show Prompt Optimizer status for the current OpenCode session.
---
Use the Prompt Optimizer server plugin state for this session. Report the
resolved mode, scope, quality gate, model/profile and privacy-safe counters.
Do not edit persistent configuration and do not reveal hidden reasoning.
"""
    command_name = re.escape(operation.params["name"] if operation.params else operation.path.stem)
    legacy_model_templates = (
        r"---\ndescription: Optimize this task for [^\n]+, then execute it\.\n---\n"
        rf"Use the `{command_name}` skill for this request\.\n\n\$ARGUMENTS\n",
        r"---\ndescription: Optimize and execute with the [^\n]+ profile\n---\n"
        rf"Use the `{command_name}` skill for the following task\. Preserve the user's language and constraints, "
        r"then execute it unless the user requests prompt-only mode\.\n\n\$ARGUMENTS\n",
    )
    if text != legacy_status and not any(re.fullmatch(template, text) for template in legacy_model_templates):
        return
    transaction.record(operation.path)
    operation.path.unlink()


def _delete_json_fields(operation: Operation, transaction: InstallTransaction) -> None:
    fields = set(operation.params.get("fields", ())) if operation.params else set()
    if not operation.path.exists():
        return
    current = _load_json(operation.path, "managed config")
    changed = False
    for field in fields:
        if field in current:
            current.pop(field)
            changed = True
    if not changed:
        return
    if not current:
        _delete_owned_file(operation, transaction)
        return
    transaction.record(operation.path)
    atomic_write_bytes(operation.path, (json.dumps(current, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _clean_managed_hooks(entries: list) -> tuple[list, bool]:
    remaining = []
    changed = False
    for entry in entries:
        if isinstance(entry, dict) and entry.get("owner") == _MANAGED_HOOK_OWNER and entry.get("name") == _MANAGED_HOOK_NAME:
            changed = True
            continue
        nested = entry.get("hooks") if isinstance(entry, dict) else None
        if isinstance(nested, list):
            cleaned, nested_changed = _clean_managed_hooks(nested)
            if nested_changed:
                changed = True
                if not cleaned:
                    continue
                entry = {**entry, "hooks": cleaned}
        remaining.append(entry)
    return remaining, changed


def _delete_json_hooks(operation: Operation, transaction: InstallTransaction) -> None:
    events = set(operation.params.get("events", ())) if operation.params else set()
    if not operation.path.exists():
        return
    current = _load_json(operation.path, "hook config")
    hooks = current.get("hooks")
    if not isinstance(hooks, dict):
        return
    changed = False
    for event in events:
        entries = hooks.get(event)
        if not isinstance(entries, list):
            continue
        remaining, event_changed = _clean_managed_hooks(entries)
        if event_changed:
            hooks[event] = remaining
            changed = True
    if not changed:
        return
    for event in list(hooks):
        if hooks[event] == []:
            hooks.pop(event)
    if not hooks:
        current.pop("hooks", None)
    if not current:
        _delete_owned_file(operation, transaction)
        return
    transaction.record(operation.path)
    atomic_write_bytes(operation.path, (json.dumps(current, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _delete_json_plugin_specs(operation: Operation, transaction: InstallTransaction) -> None:
    specs = list(operation.params.get("specs", ())) if operation.params else []
    if not operation.path.exists():
        return
    current = _load_json(operation.path, "TUI config")
    plugins = current.get("plugin")
    if plugins is None:
        return
    if not isinstance(plugins, list):
        raise ValueError(f"plugin must be an array: {operation.path}")
    remaining = [item for item in plugins if all(item != spec for spec in specs)]
    if remaining == plugins:
        return
    if remaining:
        current["plugin"] = remaining
    else:
        current.pop("plugin", None)
    if not current:
        _delete_owned_file(operation, transaction)
        return
    transaction.record(operation.path)
    atomic_write_bytes(operation.path, (json.dumps(current, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _merge_json_plugin_specs(operation: Operation, transaction: InstallTransaction, backup: bool) -> None:
    if operation.content is None:
        raise ValueError(f"merge_json_plugin_specs operation has no content: {operation.path}")
    _reject_symlink(operation.path)
    current = _load_json(operation.path, "OpenCode config") if operation.path.exists() else {}
    plugins = current.get("plugin", [])
    if not isinstance(plugins, list):
        raise ValueError(f"plugin must be an array: {operation.path}")
    update = json.loads(operation.content.decode("utf-8"))
    spec = update.get("plugin") if isinstance(update, dict) else None
    if not isinstance(spec, str) or not spec:
        raise ValueError(f"plugin registration must contain a non-empty string: {operation.path}")
    if spec in plugins:
        return
    plugins.append(spec)
    current["plugin"] = plugins
    _backup_once(operation.path, transaction, backup)
    transaction.record(operation.path)
    atomic_write_bytes(operation.path, (json.dumps(current, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _apply(operation: Operation, source_root: Path, transaction: InstallTransaction, backup: bool) -> None:
    if operation.kind == "delete_json_scaffold":
        if operation.path.exists():
            current = _load_json(operation.path, "installer-created configuration")
            if current in ({}, {"version": 1}, {"$schema": "https://opencode.ai/tui.json"}, {"version": 1, "$schema": "https://opencode.ai/tui.json"}):
                _delete_owned_file(operation, transaction)
        return
    if operation.kind == "prune_empty":
        _reject_symlink(operation.path)
        if operation.path.is_dir():
            try:
                operation.path.rmdir()
            except OSError:
                pass
        return
    if operation.kind == "write":
        if operation.content is None:
            raise ValueError(f"write operation has no content: {operation.path}")
        _reject_symlink(operation.path)
        _backup_once(operation.path, transaction, backup)
        transaction.record(operation.path)
        atomic_write_bytes(operation.path, operation.content)
        return
    if operation.kind == "merge":
        if operation.content is None:
            raise ValueError(f"merge operation has no content: {operation.path}")
        _reject_symlink(operation.path)
        try:
            updates = json.loads(operation.content.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"merge operation contains invalid JSON: {operation.path}") from exc
        if not isinstance(updates, dict):
            raise ValueError(f"merge operation must contain a JSON object: {operation.path}")
        existing = operation.path.read_text(encoding="utf-8") if operation.path.exists() else None
        try:
            payload = merge_json(existing, updates).encode("utf-8")
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid managed JSON configuration: {operation.path}") from exc
        _backup_once(operation.path, transaction, backup)
        transaction.record(operation.path)
        atomic_write_bytes(operation.path, payload)
        return
    if operation.kind == "copy_tree":
        _copy_tree(operation, source_root, transaction, backup)
        return
    if operation.kind == "copy_file":
        source = _source_file(operation, source_root)
        _reject_symlink(operation.path)
        operation.path.parent.mkdir(parents=True, exist_ok=True)
        _backup_once(operation.path, transaction, backup)
        transaction.record(operation.path)
        atomic_write_bytes(operation.path, source.read_bytes())
        return
    if operation.kind == "copy_files":
        _copy_files(operation, source_root, transaction, backup)
        return
    if operation.kind == "copy_owned_file":
        _copy_owned_file(operation, source_root, transaction, backup)
        return
    if operation.kind == "merge_block":
        _merge_block(operation, transaction, backup)
        return
    if operation.kind == "merge_tui":
        _merge_tui(operation, transaction, backup)
        return
    if operation.kind == "merge_json_plugin_specs":
        _merge_json_plugin_specs(operation, transaction, backup)
        return
    if operation.kind == "merge_ignore":
        _merge_ignore(operation, transaction, backup)
        return
    if operation.kind == "merge_hook":
        _apply_hook(operation, transaction, backup)
        return
    if operation.kind == "delete":
        _delete_owned_file(operation, transaction)
        return
    if operation.kind == "delete_owned_file":
        _delete_owned_file(operation, transaction)
        return
    if operation.kind == "delete_block":
        _delete_block(operation, transaction)
        return
    if operation.kind == "delete_file_if_matches":
        _delete_file_if_matches(operation, source_root, transaction)
        return
    if operation.kind == "delete_tree_if_matches":
        _delete_tree_if_matches(operation, source_root, transaction)
        return
    if operation.kind == "delete_legacy_model_skill":
        _delete_legacy_model_skill(operation, transaction)
        return
    if operation.kind == "delete_legacy_model_command":
        _delete_legacy_model_command(operation, transaction)
        return
    if operation.kind == "delete_json_fields":
        _delete_json_fields(operation, transaction)
        return
    if operation.kind == "delete_json_hooks":
        _delete_json_hooks(operation, transaction)
        return
    if operation.kind == "delete_json_plugin_specs":
        _delete_json_plugin_specs(operation, transaction)
        return
    raise ValueError(f"unsupported operation kind: {operation.kind}")


def execute_plan(plan: InstallPlan, *, source_root: Path, dry_run: bool = False, backup: bool = True) -> tuple[Path, ...]:
    """Apply a plan atomically and return affected paths.

    Dry-run performs validation of operation inputs but never creates or changes
    destination files. A failed real execution rolls back all recorded files.
    """
    affected = tuple(operation.path for operation in plan.operations)
    if dry_run:
        for operation in plan.operations:
            if operation.kind == "copy_tree":
                if operation.source is None:
                    raise ValueError(f"copy_tree operation has no source: {operation.path}")
                source = operation.source if operation.source.is_absolute() else source_root / operation.source
                if source.is_symlink() or not source.is_dir():
                    raise ValueError(f"missing package directory: {source}")
            elif operation.kind == "copy_file":
                _source_file(operation, source_root)
            elif operation.kind == "copy_files":
                if operation.source is None:
                    raise ValueError(f"copy_files operation has no source: {operation.path}")
                source = operation.source if operation.source.is_absolute() else source_root / operation.source
                if source.is_symlink() or not source.is_dir():
                    raise ValueError(f"missing package directory: {source}")
            elif operation.kind == "copy_owned_file":
                _source_file(operation, source_root)
            elif operation.kind in {"merge_block", "merge_tui", "merge_json_plugin_specs"} and operation.content is None:
                raise ValueError(f"{operation.kind} operation has no content: {operation.path}")
            elif operation.kind == "merge_ignore" and operation.content is None:
                raise ValueError("merge_ignore operation has no content")
            elif operation.kind == "merge_hook":
                if operation.content is None:
                    raise ValueError(f"merge_hook operation has no content: {operation.path}")
            elif operation.kind in {"write", "merge"} and operation.content is None:
                raise ValueError(f"{operation.kind} operation has no content: {operation.path}")
            elif operation.kind in {"delete_file_if_matches", "delete_tree_if_matches"}:
                if operation.source is None:
                    raise ValueError(f"{operation.kind} operation has no source: {operation.path}")
                source = operation.source if operation.source.is_absolute() else source_root / operation.source
                if source.is_symlink() or not (source.is_file() if operation.kind == "delete_file_if_matches" else source.is_dir()):
                    raise ValueError(f"missing package {'file' if operation.kind == 'delete_file_if_matches' else 'directory'}: {source}")
            elif operation.kind not in {
                "write", "merge", "copy_tree", "copy_file", "copy_files", "merge_hook",
                "merge_block", "copy_owned_file", "merge_tui", "merge_json_plugin_specs", "merge_ignore", "delete",
                "delete_owned_file", "delete_file_if_matches", "delete_tree_if_matches",
                "delete_legacy_model_skill", "delete_legacy_model_command",
                "delete_block", "delete_json_fields", "delete_json_hooks", "delete_json_plugin_specs", "prune_empty", "delete_json_scaffold",
            }:
                raise ValueError(f"unsupported operation kind: {operation.kind}")
        return affected
    with InstallTransaction() as transaction:
        for operation in plan.operations:
            _apply(operation, source_root, transaction, backup)
    return affected
