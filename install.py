#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path

from installer.catalog import load_catalog
from installer.content import merge_json as _merge_json, merge_managed_block as _merge_managed_block
from installer.filesystem import atomic_write_bytes as _atomic_write_bytes
from installer.transaction import InstallTransaction, record_path as _record_path
from installer.locking import InstallLock as _InstallLock
from installer.domain import InstallRequest as _InstallRequest
from installer.planning import plan_install as _plan_install
from installer.executor import execute_plan as _execute_plan
from installer.lifecycle import (
    build_uninstall_plan as _build_uninstall_plan,
    diagnose as _diagnose,
    managed_file_map as _managed_file_map,
    uninstall_targets as _uninstall_targets,
)

from config_contract import (
    SCHEMA_VERSION,
    invalid_fields,
    managed_config,
)

PACKAGE_ROOT = Path(__file__).resolve().parent
UI_LANG = 'en'
VERSION = (PACKAGE_ROOT / 'VERSION').read_text(encoding='utf-8').strip()
CONFIG_SCHEMA_VERSION = SCHEMA_VERSION

ADAPTER_MANIFEST = json.loads((PACKAGE_ROOT / 'adapters' / 'manifest.json').read_text(encoding='utf-8'))
AGENTS = load_catalog(PACKAGE_ROOT).ids

def L(en: str, ru: str) -> str:
    return ru if UI_LANG == 'ru' else en

SKILLS_SRC = PACKAGE_ROOT / ".agents" / "skills"
START = "<!-- prompt-optimizer:auto:start -->"
END = "<!-- prompt-optimizer:auto:end -->"
MANAGED_HOOK_NAME = 'prompt-optimizer'
MANAGED_HOOK_OWNER = 'universal-prompt-optimizer'
_PLANNED_AUTO_ADAPTERS = frozenset({'opencode', 'pi', 'cursor', 'gemini', 'claude', 'codex', 'copilot', 'windsurf'})
IGNORE_START = '# prompt-optimizer:runtime:start'
IGNORE_END = '# prompt-optimizer:runtime:end'


def text(rel: str) -> str:
    return (PACKAGE_ROOT / rel).read_text(encoding="utf-8")

def fail(message: str) -> None:
    raise SystemExit(message)

def record_path(path: Path) -> None:
    _record_path(path)

class InstallLock(_InstallLock):
    """Compatibility wrapper retaining localized CLI errors."""
    def __init__(self, path: Path) -> None:
        super().__init__(path, reject_symlink_components)

    def __enter__(self):
        try:
            return super().__enter__()
        except RuntimeError:
            fail(L(f"Another installation is already running: {self.path}", f"Другая установка уже выполняется: {self.path}"))

def reject_symlink(path: Path) -> None:
    if path.is_symlink():
        fail(L(f"Refusing to write through symlink: {path}", f"Отказано: запись через символическую ссылку запрещена: {path}"))

def reject_symlink_components(path: Path) -> None:
    for component in (path, *path.parents):
        if component.is_symlink():
            fail(L(f"Refusing to write through symlink path component: {component}", f"Отказано: компонент пути является символической ссылкой: {component}"))

def atomic_write_bytes(path: Path, value: bytes) -> None:
    reject_symlink_components(path)
    try:
        _atomic_write_bytes(path, value)
    except ValueError as exc:
        fail(L(str(exc), str(exc)))

def atomic_write_text(path: Path, value: str) -> None:
    atomic_write_bytes(path, value.encode('utf-8'))

def atomic_copy(src: Path, dst: Path) -> None:
    reject_symlink_components(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f'.{dst.name}.', suffix='.tmp', dir=str(dst.parent))
    os.close(fd)
    temp = Path(temp_name)
    try:
        shutil.copy2(src, temp)
        os.replace(temp, dst)
    finally:
        if temp.exists():
            temp.unlink()

def load_json_object(path: Path, label: str) -> dict:
    reject_symlink_components(path)
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(L(f"Invalid {label} JSON at {path}: {exc}", f"Некорректный JSON ({label}) в {path}: {exc}"))
    if not isinstance(loaded, dict):
        fail(L(f"{label} must contain a JSON object: {path}", f"{label} должен содержать JSON-объект: {path}"))
    return loaded

def validate_managed_config(data: dict, path: Path, label: str) -> None:
    invalid = invalid_fields(data)
    if invalid:
        fields = ", ".join(sorted(invalid))
        fail(L(f"Invalid {fields} in {label}: {path}", f"Некорректные поля {fields} в {label}: {path}"))

def is_managed_hook(item) -> bool:
    if not isinstance(item, dict):
        return False
    if item.get('owner') == MANAGED_HOOK_OWNER:
        return True
    name = item.get('name')
    command = str(item.get('command', ''))
    return (
        isinstance(name, str) and name.startswith('prompt-optimizer-v') and 'prompt-preflight.py' in command
        or command.endswith('.cursor/hooks/prompt-optimizer-state.py')
    )

def clean_managed_hooks(items: list) -> tuple[list, bool]:
    cleaned = []
    changed = False
    for item in items:
        if is_managed_hook(item):
            changed = True
            continue
        nested = item.get('hooks') if isinstance(item, dict) else None
        if not isinstance(nested, list):
            cleaned.append(item)
            continue
        remaining, nested_changed = clean_managed_hooks(nested)
        if nested_changed:
            changed = True
            if not remaining:
                continue
            item = dict(item)
            item['hooks'] = remaining
        cleaned.append(item)
    return cleaned, changed

def hook_command(python_bin: str, script: str) -> str:
    args = [python_bin, '-B', script]
    if os.name == 'nt':
        return subprocess.list2cmdline(args)
    return ' '.join(shlex.quote(arg) for arg in args)

def python_hook_command(python_bin: str, root_expression: str) -> str:
    code = (
        "import os,runpy;"
        f"runpy.run_path(os.path.join({root_expression},'.gemini','hooks','prompt-preflight.py'),run_name='__main__')"
    )
    args = [python_bin, '-B', '-c', code]
    if os.name == 'nt':
        return subprocess.list2cmdline(args)
    return ' '.join(shlex.quote(arg) for arg in args)

def reject_tree_overlap(src: Path, dst: Path) -> None:
    source = src.resolve()
    destination = dst.resolve()
    try:
        destination.relative_to(source)
    except ValueError:
        return
    fail(L(f"Destination is inside package source tree: {dst}", f"Назначение находится внутри исходного дерева: {dst}"))

def validate_project_root(root: Path) -> None:
    package_root = PACKAGE_ROOT.resolve()
    try:
        root.resolve().relative_to(package_root)
    except ValueError:
        return
    fail(L(
        f"Refusing to install inside the package source tree: {root}",
        f"Отказано: установка внутри исходного каталога пакета запрещена: {root}",
    ))

def parse_agents(value: str) -> set[str]:
    vals={v.strip().lower() for v in value.split(',') if v.strip()}
    if not vals or 'all' in vals: return set(AGENTS)
    aliases={'claude-code':'claude','gemini-cli':'gemini','github-copilot':'copilot','github-copilot-cli':'copilot','openai-codex':'codex'}
    vals={aliases.get(v,v) for v in vals}
    unknown=vals-AGENTS
    if unknown: raise SystemExit(L(f"Unknown agent(s): {', '.join(sorted(unknown))}", f"Неизвестные агенты: {', '.join(sorted(unknown))}"))
    return vals

def backup_once(path: Path) -> None:
    if not path.exists(): return
    reject_symlink(path)
    b=path.with_name(path.name+'.prompt-optimizer.bak')
    if not b.exists():
        record_path(b)
        b.parent.mkdir(parents=True, exist_ok=True); atomic_copy(path,b)

def merge_block(path: Path, block: str, *, backup=True, dry_run=False) -> str:
    path=path.expanduser(); reject_symlink_components(path); current=path.read_text(encoding='utf-8') if path.exists() else ''
    try:
        new = _merge_managed_block(current, block, START, END)
    except ValueError:
        fail(L(f"Incomplete managed block in {path}", f"Неполный управляемый блок в {path}"))
    action = L('updated','обновлено') if START in current else (L('created','создано') if not path.exists() else L('merged','объединено'))
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        record_path(path)
        if backup: backup_once(path)
        atomic_write_text(path, new)
    return f"{action}: {path}"

def legacy_quality_gate_enabled(quality_gate: str | bool) -> bool:
    """Map the richer gate setting to the legacy adapters' boolean contract."""
    return quality_gate is not False and quality_gate != 'pass'

def configured_block(rel: str, behavior: str, scope: str, quality_gate: str | bool, unsupported: str) -> str:
    block=text(rel).rstrip()
    marker=END
    q = quality_gate if isinstance(quality_gate, str) else ('adaptive' if quality_gate else 'pass')
    line=f"\nConfigured by installer: `behavior={behavior}`, `scope={scope}`, `qualityGate={q}`, `unsupportedModel={unsupported}`. These are fallback defaults; current project/global settings override them. If a native adapter injects a newer per-turn setting, the native adapter wins.\n"
    return block.replace(marker, line+marker)

def merge_runtime_ignores(path: Path, entries: list[str], *, backup=True, dry_run=False) -> str:
    reject_symlink_components(path)
    current = path.read_text(encoding='utf-8') if path.exists() else ''
    if (IGNORE_START in current) != (IGNORE_END in current):
        fail(L(f"Incomplete runtime ignore block in {path}", f"Неполный блок runtime ignore в {path}"))
    existing_entries: list[str] = []
    if IGNORE_START in current:
        _, managed = current.split(IGNORE_START, 1)
        managed, _ = managed.split(IGNORE_END, 1)
        existing_entries = [line.strip() for line in managed.splitlines() if line.strip() and not line.strip().startswith('#')]
    merged_entries = list(dict.fromkeys(existing_entries + entries))
    block = IGNORE_START + '\n' + '\n'.join(merged_entries) + '\n' + IGNORE_END
    if IGNORE_START in current:
        before, rest = current.split(IGNORE_START, 1)
        _, after = rest.split(IGNORE_END, 1)
        new = before.rstrip() + '\n\n' + block + '\n' + after.lstrip('\n')
        action = L('updated', 'обновлено')
    else:
        new = current.rstrip() + ('\n\n' if current.strip() else '') + block + '\n'
        action = L('created', 'создано') if not path.exists() else L('merged', 'объединено')
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        record_path(path)
        if backup: backup_once(path)
        atomic_write_text(path, new)
    return f'{action}: {path}'

def remove_managed_block(path: Path, *, dry_run=False) -> str:
    """Remove only the package-owned block and keep surrounding user text."""
    reject_symlink_components(path)
    if not path.exists():
        return L(f'absent: {path}', f'отсутствует: {path}')
    current = path.read_text(encoding='utf-8')
    has_start, has_end = START in current, END in current
    if not has_start and not has_end:
        return L(f'unchanged (no managed block): {path}', f'без изменений (управляемый блок не найден): {path}')
    if has_start != has_end:
        fail(L(f'Incomplete managed block in {path}', f'Неполный управляемый блок в {path}'))
    before, rest = current.split(START, 1)
    _, after = rest.split(END, 1)
    before, after = before.rstrip(), after.lstrip('\n')
    new = before + ('\n\n' if before and after else '') + after
    if before and not after:
        new += '\n'
    if not dry_run:
        record_path(path)
        if new:
            atomic_write_text(path, new)
        else:
            path.unlink()
    return L(f'removed managed block: {path}', f'удален управляемый блок: {path}')

def remove_runtime_ignores(path: Path, *, dry_run=False) -> str:
    reject_symlink_components(path)
    if not path.exists():
        return L(f'absent: {path}', f'отсутствует: {path}')
    current = path.read_text(encoding='utf-8')
    has_start, has_end = IGNORE_START in current, IGNORE_END in current
    if not has_start and not has_end:
        return L(f'unchanged (no runtime ignore block): {path}', f'без изменений (runtime ignore блок не найден): {path}')
    if has_start != has_end:
        fail(L(f'Incomplete runtime ignore block in {path}', f'Неполный блок runtime ignore в {path}'))
    before, rest = current.split(IGNORE_START, 1)
    _, after = rest.split(IGNORE_END, 1)
    before, after = before.rstrip(), after.lstrip('\n')
    new = before + ('\n\n' if before and after else '') + after
    if before and not after:
        new += '\n'
    if not dry_run:
        record_path(path)
        if new:
            atomic_write_text(path, new)
        else:
            path.unlink()
    return L(f'removed runtime ignore block: {path}', f'удален runtime ignore блок: {path}')

def remove_owned_file(path: Path, *, dry_run=False) -> str:
    reject_symlink_components(path)
    if not path.exists():
        return L(f'absent: {path}', f'отсутствует: {path}')
    if not path.is_file():
        fail(L(f'Expected a file destination: {path}', f'Ожидался файл назначения: {path}'))
    if not dry_run:
        record_path(path)
        path.unlink()
    return L(f'removed: {path}', f'удален: {path}')

def remove_file_if_matches(src: Path, dst: Path, *, dry_run=False) -> str:
    reject_symlink_components(dst)
    if not dst.exists():
        return L(f'absent: {dst}', f'отсутствует: {dst}')
    if not dst.is_file():
        fail(L(f'Expected a file destination: {dst}', f'Ожидался файл назначения: {dst}'))
    if dst.read_bytes() != src.read_bytes():
        return L(f'preserved user-modified file: {dst}', f'сохранен измененный пользователем файл: {dst}')
    return remove_owned_file(dst, dry_run=dry_run)

def remove_tree_if_matches(src: Path, dst: Path, *, dry_run=False) -> list[str]:
    """Remove only unchanged package files from a copied tree."""
    if not dst.exists():
        return [L(f'absent: {dst}', f'отсутствует: {dst}')]
    if not dst.is_dir():
        fail(L(f'Destination is not a directory: {dst}', f'Назначение не является каталогом: {dst}'))
    out = []
    for source_file in sorted(src.rglob('*')):
        if not source_file.is_file():
            continue
        relative = source_file.relative_to(src)
        out.append(remove_file_if_matches(source_file, dst / relative, dry_run=dry_run))
    if not dry_run:
        for directory in sorted([p for p in dst.rglob('*') if p.is_dir()], reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
        try:
            dst.rmdir()
        except OSError:
            pass
    return out

def remove_json_fields(path: Path, fields: set[str], *, dry_run=False) -> str:
    if not path.exists():
        return L(f'absent: {path}', f'отсутствует: {path}')
    current = load_json_object(path, 'Prompt Optimizer config')
    changed = False
    for field in fields:
        if field in current:
            current.pop(field)
            changed = True
    if not changed:
        return L(f'unchanged: {path}', f'без изменений: {path}')
    if not current:
        return remove_owned_file(path, dry_run=dry_run)
    return write_json(path, current, backup=False, dry_run=dry_run, label='Prompt Optimizer config')

def remove_json_plugin_specs(path: Path, specs: set[str], *, dry_run=False) -> str:
    """Remove only exact package-owned TUI plugin specs from an existing config."""
    if not path.exists():
        return L(f'absent: {path}', f'отсутствует: {path}')
    current = load_json_object(path, 'OpenCode TUI config')
    plugins = current.get('plugin')
    if plugins is None:
        return L(f'unchanged (no managed TUI plugin): {path}', f'без изменений (управляемый TUI plugin не найден): {path}')
    if not isinstance(plugins, list):
        fail(L(f'plugin must be an array in {path}', f'Поле plugin должно быть массивом в {path}'))
    remaining = [item for item in plugins if item not in specs]
    if remaining == plugins:
        return L(f'unchanged (no managed TUI plugin): {path}', f'без изменений (управляемый TUI plugin не найден): {path}')
    if remaining:
        current['plugin'] = remaining
    else:
        current.pop('plugin', None)
    if not current:
        return remove_owned_file(path, dry_run=dry_run)
    return write_json(path, current, backup=False, dry_run=dry_run, label='OpenCode TUI config cleanup')

def remove_json_hooks(path: Path, events: set[str], *, dry_run=False) -> list[str]:
    if not path.exists():
        return [L(f'absent: {path}', f'отсутствует: {path}')]
    current = load_json_object(path, 'hook config')
    hooks = current.get('hooks')
    if not isinstance(hooks, dict):
        return [L(f'unchanged (no hooks object): {path}', f'без изменений (нет объекта hooks): {path}')]
    changed = False
    for event in events:
        entries = hooks.get(event)
        if not isinstance(entries, list):
            continue
        remaining, event_changed = clean_managed_hooks(entries)
        if event_changed:
            hooks[event] = remaining
            changed = True
    if not changed:
        return [L(f'unchanged (no managed hooks): {path}', f'без изменений (управляемые hooks не найдены): {path}')]
    for event in list(hooks):
        if hooks[event] == []:
            hooks.pop(event)
    if not hooks:
        current.pop('hooks', None)
    if not current:
        return [remove_owned_file(path, dry_run=dry_run)]
    return [write_json(path, current, backup=False, dry_run=dry_run, label='hook config')]

def installed_file_map(root: Path, scope: str) -> dict[str, tuple[Path, Path]]:
    """Return logical managed files and their package source counterparts."""
    return _managed_file_map(root, PACKAGE_ROOT, scope)

def doctor(root: Path, scope: str) -> int:
    """Print a read-only installation diagnostic; return non-zero on errors."""
    print(f'Universal Prompt Optimizer v{VERSION} doctor')
    print(f'scope: {scope}')
    print(f'root: {root}')
    errors = []
    found = 0
    config_paths = [root / '.prompt-optimizer.json'] if scope == 'project' else [root / '.config/prompt-optimizer/config.json']
    config_paths += [destination for logical, (_, destination) in installed_file_map(root, scope).items() if logical in {'opencode-config'}]
    for path in config_paths:
        if not path.exists():
            print(f'config: absent ({path})')
            continue
        try:
            value = load_json_object(path, 'Prompt Optimizer config')
            validate_managed_config(value, path, 'Prompt Optimizer config')
            print(f'config: valid ({path})')
            if {'schemaVersion', 'behavior', 'scope', 'qualityGate', 'unsupportedModel'} & set(value):
                found += 1
        except SystemExit as exc:
            errors.append(str(exc))
            print(f'config: invalid ({path})')
    hook_specs = []
    if scope == 'project':
        hook_specs.append((root / '.cursor/hooks.json', {'beforeSubmitPrompt'}))
    hook_specs.append((root / '.gemini/settings.json', {'BeforeAgent', 'BeforeModel'}))
    for path, events in hook_specs:
        if not path.exists():
            continue
        try:
            value = load_json_object(path, 'hook config')
            hooks = value.get('hooks')
            if hooks is not None and not isinstance(hooks, dict):
                raise ValueError('hooks must be an object')
            owned = 0
            if isinstance(hooks, dict):
                for event in events:
                    entries = hooks.get(event, [])
                    if not isinstance(entries, list):
                        raise ValueError(f'{event} hooks must be an array')
                    _, changed = clean_managed_hooks(entries)
                    owned += 1 if changed else 0
            print(f'hooks: valid, {owned} managed event(s) ({path})')
            found += owned
        except (SystemExit, ValueError) as exc:
            errors.append(f'invalid hook config {path}: {exc}')
            print(f'hooks: invalid ({path})')
    lock = root / '.prompt-optimizer-install.lock'
    print(f'installer lock: {"present" if lock.exists() else "clear"}')
    if lock.exists():
        errors.append(f'stale or active installer lock: {lock}')
    for logical, (source, destination) in installed_file_map(root, scope).items():
        if logical in {'shared-config', 'opencode-config'}:
            continue
        if destination.is_dir():
            package_files = list(source.rglob('*')) if source.is_dir() else []
            present = sum(1 for item in package_files if item.is_file() and (destination / item.relative_to(source)).exists())
            current = sum(1 for item in package_files if item.is_file() and (destination / item.relative_to(source)).is_file() and (destination / item.relative_to(source)).read_bytes() == item.read_bytes())
            total = sum(1 for item in package_files if item.is_file())
            print(f'{logical}: {present}/{total} present, {current}/{total} current ({destination})')
            found += present
        elif destination.exists():
            if logical.endswith('-block'):
                text_value = destination.read_text(encoding='utf-8')
                managed = START in text_value and END in text_value
                print(f'{logical}: {"managed block present" if managed else "no managed block"} ({destination})')
                found += 1 if managed else 0
            else:
                current = source.is_file() and destination.is_file() and source.read_bytes() == destination.read_bytes()
                print(f'{logical}: {"current" if current else "present but modified/outdated"} ({destination})')
                found += 1
        else:
            print(f'{logical}: absent ({destination})')
    runtime = [root / '.cursor/.prompt-optimizer-runtime.json', root / '.gemini/.prompt-optimizer-model-state.json']
    for path in runtime:
        if path.exists():
            try:
                json.loads(path.read_text(encoding='utf-8'))
                print(f'runtime state: valid ({path})')
            except (OSError, UnicodeError, json.JSONDecodeError):
                errors.append(f'invalid runtime state: {path}')
                print(f'runtime state: invalid ({path})')
    report = _diagnose(root, PACKAGE_ROOT, scope)
    for error in report.errors:
        if error not in errors:
            errors.append(error)
    print(f'managed entries found: {max(found, report.found)}')
    if errors:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print('status: healthy' if found else 'status: not installed')
    return 0

def _describe_uninstall_operation(operation) -> str:
    kind = operation.kind
    if kind == 'delete_block':
        return L(f'removed managed block: {operation.path}', f'удален управляемый блок: {operation.path}')
    if kind == 'delete_json_fields':
        return L(f'write managed config: {operation.path}', f'запись managed config: {operation.path}')
    if kind == 'delete_json_hooks':
        return L(f'write hook config: {operation.path}', f'запись hook config: {operation.path}')
    if kind == 'delete_json_plugin_specs':
        return L(f'write TUI config: {operation.path}', f'запись TUI config: {operation.path}')
    if kind == 'delete_tree_if_matches':
        return L(f'removed managed tree: {operation.path}', f'удалено управляемое дерево: {operation.path}')
    return L(f'removed: {operation.path}', f'удален: {operation.path}')

def uninstall(root: Path, scope: str, *, dry_run=False) -> list[str]:
    """Remove the installation while preserving unrelated user content."""
    plan = _build_uninstall_plan(root, PACKAGE_ROOT, scope)
    try:
        _execute_plan(plan, source_root=PACKAGE_ROOT, dry_run=dry_run, backup=False)
    except json.JSONDecodeError as exc:
        fail(L(f"invalid managed JSON configuration: {exc}", f"некорректный managed JSON-конфиг: {exc}"))
    except ValueError as exc:
        fail(L(str(exc), str(exc)))
    return [_describe_uninstall_operation(operation) for operation in plan.operations]

def copy_file(src: Path, dst: Path, *, backup=True, dry_run=False, executable=False, label='file') -> str:
    if dry_run: return L(f"would install {label}: {dst}", f"будет установлено {label}: {dst}")
    if src.is_symlink() or not src.is_file():
        fail(L(f"Missing package file: {src}", f"Отсутствует файл пакета: {src}"))
    if src.resolve() == dst.resolve():
        fail(L(f"Source and destination are the same: {dst}", f"Источник и назначение совпадают: {dst}"))
    reject_symlink_components(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    record_path(dst)
    if backup: backup_once(dst)
    atomic_copy(src,dst)
    if executable: dst.chmod(dst.stat().st_mode | 0o111)
    return L(f"installed {label}: {dst}", f"установлено {label}: {dst}")

def copy_tree(src: Path, dst: Path, *, backup=True, dry_run=False, label='tree') -> str:
    if dry_run: return L(f"would install {label}: {dst}", f"будет установлено {label}: {dst}")
    if src.is_symlink() or not src.is_dir():
        fail(L(f"Missing package directory: {src}", f"Отсутствует каталог пакета: {src}"))
    if src.resolve() == dst.resolve():
        fail(L(f"Source and destination are the same: {dst}", f"Источник и назначение совпадают: {dst}"))
    reject_tree_overlap(src, dst)
    if dst.exists() and not dst.is_dir():
        fail(L(f"Destination is not a directory: {dst}", f"Назначение не является каталогом: {dst}"))
    reject_symlink_components(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for source_file in src.rglob('*'):
        if source_file.is_symlink():
            fail(L(f"Package tree contains an unexpected symlink: {source_file}", f"В дереве пакета обнаружена неожиданная символическая ссылка: {source_file}"))
        if source_file.is_file():
            relative = source_file.relative_to(src)
            copy_file(source_file, dst / relative, backup=backup, label=f'{label} file')
    return L(f"installed {label}: {dst}", f"установлено {label}: {dst}")

def copy_skills(dst: Path, *, backup=True, dry_run=False) -> str:
    if dry_run: return L(f"would install skills: {dst}", f"будут установлены skills: {dst}")
    if SKILLS_SRC.resolve() == dst.resolve():
        fail(L(f"Refusing to overwrite package skills: {dst}", f"Отказано: нельзя перезаписывать skills самого пакета: {dst}"))
    if dst.exists() and not dst.is_dir():
        fail(L(f"Skills destination is not a directory: {dst}", f"Назначение skills не является каталогом: {dst}"))
    reject_symlink_components(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for child in SKILLS_SRC.iterdir():
        if not child.is_dir(): continue
        if child.name != 'prompt-optimizer': continue
        target=dst/child.name
        copy_tree(child, target, backup=backup, label=f'skill {child.name}')
    return L(f"installed skills: {dst}", f"установлены skills: {dst}")

def copy_commands(src: Path, dst: Path, *, backup=True, dry_run=False) -> str:
    if dry_run: return L(f"would install OpenCode commands: {dst}", f"будут установлены команды OpenCode: {dst}")
    if dst.exists() and not dst.is_dir():
        fail(L(f"Commands destination is not a directory: {dst}", f"Назначение команд не является каталогом: {dst}"))
    reject_symlink_components(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.glob('*.md'):
        if p.name in {'prompt.md', 'prompt-only.md', 'prompt-optimizer.md'}:
            copy_file(p,dst/p.name,backup=backup,label='OpenCode command')
    return L(f"installed OpenCode commands: {dst}", f"установлены команды OpenCode: {dst}")

def install_opencode_tui(base: Path, *, backup=True, dry_run=False) -> list[str]:
    """Install the separate OpenCode TUI target and register it in tui.json."""
    source = PACKAGE_ROOT / 'adapters/opencode/tui/prompt-optimizer.tsx'
    destination = base / 'plugins/prompt-optimizer-tui/prompt-optimizer.tsx'
    owner = destination.parent / '.prompt-optimizer-owner.json'
    had_destination = destination.exists()
    owned_destination = False
    if owner.exists():
        marker = load_json_object(owner, 'OpenCode TUI ownership marker')
        owned_destination = marker.get('schema') == 1 and marker.get('owned') is True and marker.get('path') == destination.name
    if had_destination and not owned_destination and destination.read_bytes() != source.read_bytes():
        fail(L(
            f'Refusing to overwrite a user-owned OpenCode TUI plugin: {destination}',
            f'Отказано: пользовательский OpenCode TUI plugin не будет перезаписан: {destination}',
        ))
    out = [copy_file(source, destination, backup=backup, dry_run=dry_run, label='OpenCode TUI plugin')]
    if not dry_run and (not had_destination or owned_destination):
        write_json(owner, {
            'schema': 1,
            'owned': True,
            'path': destination.name,
            'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        }, backup=backup, dry_run=dry_run, label='OpenCode TUI ownership marker')
    tui_config = base / 'tui.json'
    current = load_json_object(tui_config, 'OpenCode TUI config')
    plugins = current.get('plugin', [])
    if not isinstance(plugins, list):
        fail(L(f'plugin must be an array in {tui_config}', f'Поле plugin должно быть массивом в {tui_config}'))
    spec = './plugins/prompt-optimizer-tui/prompt-optimizer.tsx'
    if spec not in plugins:
        plugins = [*plugins, spec]
    current['$schema'] = current.get('$schema', 'https://opencode.ai/tui.json')
    current['plugin'] = plugins
    out.append(write_json(tui_config, current, backup=backup, dry_run=dry_run, label='OpenCode TUI config'))
    return out

def write_json(path: Path, obj: dict, *, backup=True, dry_run=False, label='config') -> str:
    if dry_run: return L(f"would write {label}: {path}", f"будет записано {label}: {path}")
    reject_symlink_components(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record_path(path)
    if backup: backup_once(path)
    atomic_write_text(path, json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    return L(f"wrote {label}: {path}", f"записано {label}: {path}")

def merge_json_object(path: Path, updates: dict, *, backup=True, dry_run=False, label='config') -> str:
    """Merge our settings into an existing JSON object without deleting unrelated future/user fields."""
    current = load_json_object(path, label)
    validate_managed_config(current, path, label)
    return write_json(path,json.loads(_merge_json(json.dumps(current), updates)),backup=backup,dry_run=dry_run,label=label)

def merge_json_hook(path: Path, event: str, hook: dict, *, backup=True, dry_run=False) -> str:
    current=load_json_object(path, f'{event} hook config')
    current.setdefault('version',1)
    hooks=current.get('hooks')
    if hooks is None:
        hooks={}; current['hooks']=hooks
    elif not isinstance(hooks,dict):
        fail(L(f"hooks must be an object in {path}", f"Поле hooks должно быть объектом в {path}"))
    arr=hooks.get(event)
    if arr is None:
        arr=[]; hooks[event]=arr
    elif not isinstance(arr,list):
        fail(L(f"{event} hooks must be an array in {path}", f"Hooks {event} должны быть массивом в {path}"))
    # Remove only entries owned by this package, not arbitrary user hooks whose
    # command or display text happens to contain a similar string.
    arr[:], _ = clean_managed_hooks(arr)
    arr.append(hook)
    return write_json(path,current,backup=backup,dry_run=dry_run,label=f'{event} hook config')

def write_shared_config(path: Path, behavior: str, scope: str, unsupported: str, quality_gate: str | bool, *, backup=True, dry_run=False) -> str:
    return merge_json_object(path, managed_config(behavior, scope, unsupported, quality_gate), backup=backup, dry_run=dry_run, label='shared prompt-optimizer config')

def install_opencode(base: Path, behavior: str, scope: str, unsupported: str, quality_gate: str | bool, *, backup=True, dry_run=False) -> list[str]:
    out=[copy_tree(PACKAGE_ROOT/'adapters/opencode/plugin',base/'plugins/prompt-optimizer',backup=backup,dry_run=dry_run,label='OpenCode native plugin')]
    config = load_json_object(base/'opencode.json', 'OpenCode config')
    plugins = config.get('plugin', [])
    if not isinstance(plugins, list):
        fail(L(f'plugin must be an array in {base / "opencode.json"}', f'Поле plugin должно быть массивом в {base / "opencode.json"}'))
    spec = './plugins/prompt-optimizer/index.ts'
    if spec not in plugins:
        plugins = [*plugins, spec]
    config['plugin'] = plugins
    out.append(write_json(base/'opencode.json', config, backup=backup, dry_run=dry_run, label='OpenCode server plugin registration'))
    out.append(merge_json_object(base/'prompt-optimizer.json', managed_config(behavior, scope, unsupported, quality_gate), backup=backup, dry_run=dry_run, label='OpenCode prompt-optimizer config'))
    return out

def install_pi(base: Path, *, backup=True, dry_run=False) -> list[str]:
    return [copy_tree(PACKAGE_ROOT/'adapters/pi/extensions',base/'extensions',backup=backup,dry_run=dry_run,label='Pi native extension')]

def install_cursor(root: Path, python_bin: str, *, backup=True, dry_run=False) -> list[str]:
    out=[copy_file(PACKAGE_ROOT/'adapters/cursor/hooks/prompt-optimizer-state.py',root/'.cursor/hooks/prompt-optimizer-state.py',backup=backup,dry_run=dry_run,executable=True,label='Cursor model-state hook'),
         copy_file(PACKAGE_ROOT/'adapters/cursor/rules/prompt-optimizer.mdc',root/'.cursor/rules/prompt-optimizer.mdc',backup=backup,dry_run=dry_run,label='Cursor always rule')]
    hook={'name':MANAGED_HOOK_NAME,'owner':MANAGED_HOOK_OWNER,'command':hook_command(python_bin, '.cursor/hooks/prompt-optimizer-state.py')}
    out.append(merge_json_hook(root/'.cursor/hooks.json','beforeSubmitPrompt',hook,backup=backup,dry_run=dry_run))
    return out

def install_gemini(root: Path, python_bin: str, *, backup=True, dry_run=False) -> list[str]:
    out=[copy_file(PACKAGE_ROOT/'adapters/gemini-cli/hooks/prompt-preflight.py',root/'.gemini/hooks/prompt-preflight.py',backup=backup,dry_run=dry_run,executable=True,label='Gemini CLI BeforeAgent/BeforeModel hook')]
    hook={'hooks':[{'name':MANAGED_HOOK_NAME,'owner':MANAGED_HOOK_OWNER,'type':'command','command':python_hook_command(python_bin, "os.environ.get('GEMINI_PROJECT_DIR') or os.getcwd()"),'timeout':5000}]}
    out.append(merge_json_hook(root/'.gemini/settings.json','BeforeAgent',hook,backup=backup,dry_run=dry_run))
    out.append(merge_json_hook(root/'.gemini/settings.json','BeforeModel',hook,backup=backup,dry_run=dry_run))
    return out

def _execute_plan_checked(plan, *, dry_run: bool, backup: bool) -> None:
    """Execute a plan, converting data errors into a localized CLI failure."""
    try:
        _execute_plan(plan, source_root=PACKAGE_ROOT, dry_run=dry_run, backup=backup)
    except json.JSONDecodeError as exc:
        fail(L(f"invalid managed JSON configuration: {exc}", f"некорректный managed JSON-конфиг: {exc}"))
    except ValueError as exc:
        fail(L(str(exc), str(exc)))

def install_project(root: Path, selected: set[str], auto: bool, behavior: str, scope: str, unsupported: str, quality_gate: str | bool, backup: bool, dry_run: bool, python_bin: str) -> list[str]:
    validate_project_root(root)
    if auto and selected <= _PLANNED_AUTO_ADAPTERS:
        request = _InstallRequest(root, "project", frozenset(selected), automatic=True, behavior=behavior,
                                  prompt_scope=scope, quality_gate=quality_gate, unsupported_model=unsupported,
                                  dry_run=dry_run, backup=backup, python_bin=python_bin)
        plan = _plan_install(request, load_catalog(PACKAGE_ROOT))
        _execute_plan_checked(plan, dry_run=dry_run, backup=backup)
        return [f"installed composable plan: {operation.path}" for operation in plan.operations]
    if not auto and selected <= {"opencode", "claude"}:
        request = _InstallRequest(root, "project", frozenset(selected), automatic=False, behavior=behavior,
                                  prompt_scope=scope, quality_gate=quality_gate, unsupported_model=unsupported,
                                  dry_run=dry_run, backup=backup, python_bin=python_bin)
        plan = _plan_install(request, load_catalog(PACKAGE_ROOT))
        _execute_plan_checked(plan, dry_run=dry_run, backup=backup)
        return [f"installed composable plan: {operation.path}" for operation in plan.operations]
    out=[copy_skills(root/'.agents/skills',backup=backup,dry_run=dry_run)]
    if 'claude' in selected: out.append(copy_skills(root/'.claude/skills',backup=backup,dry_run=dry_run))
    if 'opencode' in selected:
        out.append(copy_commands(PACKAGE_ROOT/'adapters/opencode/commands',root/'.opencode/commands',backup=backup,dry_run=dry_run))
        if auto: out.extend(install_opencode_tui(root/'.opencode',backup=backup,dry_run=dry_run))
    if not auto: return out
    out.append(write_shared_config(root/'.prompt-optimizer.json',behavior,scope,unsupported,quality_gate,backup=backup,dry_run=dry_run))
    if 'opencode' in selected: out.extend(install_opencode(root/'.opencode',behavior,scope,unsupported,quality_gate,backup=backup,dry_run=dry_run))
    if 'pi' in selected: out.extend(install_pi(root/'.pi',backup=backup,dry_run=dry_run))
    if 'cursor' in selected: out.extend(install_cursor(root,python_bin,backup=backup,dry_run=dry_run))
    if 'gemini' in selected:
        out.extend(install_gemini(root,python_bin,backup=backup,dry_run=dry_run))
        out.append(merge_block(root/'GEMINI.md',configured_block('auto/GEMINI.snippet.md',behavior,scope,quality_gate,unsupported),backup=backup,dry_run=dry_run))
    if auto and ({'cursor', 'gemini'} & selected):
        ignores=[]
        if 'cursor' in selected:
            ignores.extend(['.cursor/.prompt-optimizer-runtime.json', '.cursor/.prompt-optimizer-session-state.json', '.cursor/*.prompt-optimizer-*.json.lock'])
        if 'gemini' in selected:
            ignores.extend(['.gemini/.prompt-optimizer-model-state.json', '.gemini/.prompt-optimizer-session-state.json', '.gemini/*.prompt-optimizer-*.json.lock'])
        out.append(merge_runtime_ignores(root/'.gitignore', ignores, backup=backup, dry_run=dry_run))
    if 'claude' in selected: out.append(merge_block(root/'CLAUDE.md',configured_block('auto/CLAUDE.snippet.md',behavior,scope,quality_gate,unsupported),backup=backup,dry_run=dry_run))
    if 'copilot' in selected: out.append(merge_block(root/'.github/copilot-instructions.md',configured_block('auto/AGENTS.snippet.md',behavior,scope,quality_gate,unsupported),backup=backup,dry_run=dry_run))
    if 'windsurf' in selected:
        out.append(copy_file(PACKAGE_ROOT/'adapters/windsurf/prompt-optimizer-rule.md',root/'.windsurf/rules/prompt-optimizer.md',backup=backup,dry_run=dry_run,label='Windsurf workspace rule'))
    if 'codex' in selected:
        out.append(merge_block(root/'AGENTS.md',configured_block('auto/AGENTS.snippet.md',behavior,scope,quality_gate,unsupported),backup=backup,dry_run=dry_run))
    return out

_GLOBAL_PLANNED_AUTO_ADAPTERS = _PLANNED_AUTO_ADAPTERS - {'cursor'}

def install_global(home: Path, selected: set[str], auto: bool, behavior: str, scope: str, unsupported: str, quality_gate: str | bool, backup: bool, dry_run: bool, python_bin: str) -> list[str]:
    if auto and selected <= _GLOBAL_PLANNED_AUTO_ADAPTERS:
        request = _InstallRequest(home, "global", frozenset(selected), automatic=True, behavior=behavior,
                                  prompt_scope=scope, quality_gate=quality_gate, unsupported_model=unsupported,
                                  dry_run=dry_run, backup=backup, python_bin=python_bin)
        plan = _plan_install(request, load_catalog(PACKAGE_ROOT))
        _execute_plan(plan, source_root=PACKAGE_ROOT, dry_run=dry_run, backup=backup)
        out = [f"installed composable plan: {operation.path}" for operation in plan.operations]
        if 'cursor' in selected:
            out.append(L('Cursor global hook/rule installation is intentionally not automated because global hooks/rules are user-environment specific; use adapters/cursor/README.md or project install', 'Глобальная установка hook/rule для Cursor намеренно не автоматизируется, потому что глобальные hooks/rules зависят от окружения пользователя; используйте adapters/cursor/README.md или установку в проект'))
        return out
    if not auto and selected <= {"opencode", "claude"}:
        request = _InstallRequest(home, "global", frozenset(selected), automatic=False, behavior=behavior,
                                  prompt_scope=scope, quality_gate=quality_gate, unsupported_model=unsupported,
                                  dry_run=dry_run, backup=backup, python_bin=python_bin)
        plan = _plan_install(request, load_catalog(PACKAGE_ROOT))
        _execute_plan(plan, source_root=PACKAGE_ROOT, dry_run=dry_run, backup=backup)
        return [f"installed composable plan: {operation.path}" for operation in plan.operations]
    out=[copy_skills(home/'.agents/skills',backup=backup,dry_run=dry_run)]
    if 'claude' in selected: out.append(copy_skills(home/'.claude/skills',backup=backup,dry_run=dry_run))
    if 'opencode' in selected:
        out.append(copy_commands(PACKAGE_ROOT/'adapters/opencode/commands',home/'.config/opencode/commands',backup=backup,dry_run=dry_run))
        if auto: out.extend(install_opencode_tui(home/'.config/opencode',backup=backup,dry_run=dry_run))
    if not auto: return out
    out.append(write_shared_config(home/'.config/prompt-optimizer/config.json',behavior,scope,unsupported,quality_gate,backup=backup,dry_run=dry_run))
    if 'opencode' in selected: out.extend(install_opencode(home/'.config/opencode',behavior,scope,unsupported,quality_gate,backup=backup,dry_run=dry_run))
    if 'pi' in selected: out.extend(install_pi(home/'.pi/agent',backup=backup,dry_run=dry_run))
    if 'claude' in selected: out.append(merge_block(home/'.claude/CLAUDE.md',configured_block('auto/CLAUDE.snippet.md',behavior,scope,quality_gate,unsupported),backup=backup,dry_run=dry_run))
    if 'gemini' in selected:
        # Global Gemini hooks use a home-relative command instead of GEMINI_PROJECT_DIR.
        src=PACKAGE_ROOT/'adapters/gemini-cli/hooks/prompt-preflight.py'; dst=home/'.gemini/hooks/prompt-preflight.py'
        out.append(copy_file(src,dst,backup=backup,dry_run=dry_run,executable=True,label='Gemini CLI global BeforeAgent/BeforeModel hook'))
        hook={'hooks':[{'name':MANAGED_HOOK_NAME,'owner':MANAGED_HOOK_OWNER,'type':'command','command':python_hook_command(python_bin, "os.path.expanduser('~')"),'timeout':5000}]}
        out.append(merge_json_hook(home/'.gemini/settings.json','BeforeAgent',hook,backup=backup,dry_run=dry_run))
        out.append(merge_json_hook(home/'.gemini/settings.json','BeforeModel',hook,backup=backup,dry_run=dry_run))
        out.append(merge_block(home/'.gemini/GEMINI.md',configured_block('auto/GEMINI.snippet.md',behavior,scope,quality_gate,unsupported),backup=backup,dry_run=dry_run))
    if 'copilot' in selected: out.append(merge_block(home/'.copilot/copilot-instructions.md',configured_block('auto/AGENTS.snippet.md',behavior,scope,quality_gate,unsupported),backup=backup,dry_run=dry_run))
    if 'codex' in selected: out.append(merge_block(home/'.codex/AGENTS.md',configured_block('auto/AGENTS.snippet.md',behavior,scope,quality_gate,unsupported),backup=backup,dry_run=dry_run))
    if 'windsurf' in selected: out.append(merge_block(home/'.codeium/windsurf/memories/global_rules.md',configured_block('auto/AGENTS.snippet.md',behavior,scope,quality_gate,unsupported),backup=backup,dry_run=dry_run))
    if 'cursor' in selected: out.append(L('Cursor global hook/rule installation is intentionally not automated because global hooks/rules are user-environment specific; use adapters/cursor/README.md or project install', 'Глобальная установка hook/rule для Cursor намеренно не автоматизируется, потому что глобальные hooks/rules зависят от окружения пользователя; используйте adapters/cursor/README.md или установку в проект'))
    return out

def main():
    ap=argparse.ArgumentParser(description=f'Install Universal Prompt Optimizer v{VERSION}')
    ap.add_argument('--lang',choices=['en','ru'],default='en',help='Installer output language')
    ap.add_argument('--scope',choices=['project','global'],default='project')
    ap.add_argument('--project',default='.')
    ap.add_argument('--agents',default='all',help='opencode,codex,cursor,pi,claude,gemini,copilot,windsurf,all')
    ap.add_argument('--auto',action='store_true',help='Install automatic/preview/off adapter integration in addition to skills')
    ap.add_argument('--behavior',choices=['auto','preview','off'],default='auto')
    ap.add_argument('--prompt-scope',choices=['first','all'],default='all')
    ap.add_argument('--quality-gate',choices=['on','off','pass','light','full','adaptive'],default='adaptive',help='Quality gate: adaptive, pass, light, full, or legacy on/off')
    ap.add_argument('--unsupported-model',choices=['skip','generic'],default='generic')
    ap.add_argument('--python-bin',default=sys.executable,help='Python command used by generated hooks')
    ap.add_argument('--opencode-mode',choices=['first','all','off'],help='Deprecated v4 compatibility: first/all map to behavior=auto and corresponding scope; off maps to behavior=off')
    ap.add_argument('--no-backup',action='store_true')
    ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--doctor',action='store_true',help='Read-only installation and configuration diagnostic')
    ap.add_argument('--uninstall',action='store_true',help='Remove only unchanged package-owned files and managed blocks')
    args=ap.parse_args()
    global UI_LANG
    UI_LANG=args.lang
    behavior=args.behavior; scope=args.prompt_scope
    if args.opencode_mode:
        if args.opencode_mode=='off': behavior='off'
        else: behavior='auto'; scope=args.opencode_mode
    selected=parse_agents(args.agents); backup=not args.no_backup
    quality_gate = {'on': 'adaptive', 'off': 'pass'}.get(args.quality_gate, args.quality_gate)
    if args.scope == 'project':
        root = Path(args.project).expanduser().resolve()
        if not args.doctor:
            validate_project_root(root)
    else:
        root = Path.home()
    if args.doctor and args.uninstall:
        fail(L('Choose either --doctor or --uninstall, not both', 'Выберите либо --doctor, либо --uninstall, но не оба параметра'))
    if args.doctor:
        raise SystemExit(doctor(root, args.scope))
    if args.uninstall:
        validate_project_root(root)
        if selected != AGENTS:
            fail(L('Uninstall removes the complete Prompt Optimizer installation; omit --agents or use --agents all', 'Uninstall удаляет всю установку Prompt Optimizer; не указывайте --agents или используйте --agents all'))
    lock = InstallLock(root / '.prompt-optimizer-install.lock')
    with (nullcontext() if args.dry_run else lock):
        with (nullcontext() if args.dry_run else InstallTransaction()):
            if args.uninstall:
                results=uninstall(root,args.scope,dry_run=args.dry_run)
            elif args.scope=='project':
                results=install_project(root,selected,args.auto,behavior,scope,args.unsupported_model,quality_gate,backup,args.dry_run,args.python_bin)
            else:
                results=install_global(root,selected,args.auto,behavior,scope,args.unsupported_model,quality_gate,backup,args.dry_run,args.python_bin)
    print(f'Universal Prompt Optimizer v{VERSION}')
    if UI_LANG == 'ru':
        print(f'область установки: {"проект" if args.scope == "project" else "глобально"}')
        print(f'агенты: {", ".join(sorted(selected))}')
        print(f'автоматическая интеграция: {"вкл" if args.auto else "выкл"}')
        if args.auto: print(f'режим: {behavior}; запросы: {scope}; quality gate: {args.quality_gate}; неизвестная модель: {args.unsupported_model}')
    else:
        print(f'scope: {args.scope}')
        print(f'agents: {", ".join(sorted(selected))}')
        print(f'auto integration: {"on" if args.auto else "off"}')
        if args.auto: print(f'behavior: {behavior}; prompt scope: {scope}; quality gate: {args.quality_gate}; unsupported model: {args.unsupported_model}')
    for line in results: print(f'- {line}')

if __name__=='__main__': main()
