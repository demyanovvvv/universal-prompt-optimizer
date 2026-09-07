#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
UI_LANG = 'en'
VERSION = (PACKAGE_ROOT / 'VERSION').read_text(encoding='utf-8').strip()

def L(en: str, ru: str) -> str:
    return ru if UI_LANG == 'ru' else en

SKILLS_SRC = PACKAGE_ROOT / ".agents" / "skills"
START = "<!-- prompt-optimizer:auto:start -->"
END = "<!-- prompt-optimizer:auto:end -->"
AGENTS = {"opencode","codex","cursor","pi","claude","gemini","copilot","windsurf"}
MANAGED_HOOK_NAME = 'prompt-optimizer'
MANAGED_HOOK_OWNER = 'universal-prompt-optimizer'
ACTIVE_TRANSACTION = None
IGNORE_START = '# prompt-optimizer:runtime:start'
IGNORE_END = '# prompt-optimizer:runtime:end'


def text(rel: str) -> str:
    return (PACKAGE_ROOT / rel).read_text(encoding="utf-8")

def fail(message: str) -> None:
    raise SystemExit(message)

class InstallTransaction:
    """Keep file snapshots so a failed multi-agent install can be restored."""
    def __init__(self) -> None:
        self.snapshots: dict[Path, tuple[bytes, int] | None] = {}

    def record(self, path: Path) -> None:
        path = path.resolve()
        if path in self.snapshots:
            return
        if path.exists():
            if not path.is_file():
                fail(L(f"Expected a file destination: {path}", f"Ожидался файл назначения: {path}"))
            self.snapshots[path] = (path.read_bytes(), path.stat().st_mode)
        else:
            self.snapshots[path] = None

    def rollback(self) -> None:
        global ACTIVE_TRANSACTION
        previous = ACTIVE_TRANSACTION
        ACTIVE_TRANSACTION = None
        try:
            for path, snapshot in reversed(list(self.snapshots.items())):
                if snapshot is None:
                    if path.exists() and path.is_file():
                        path.unlink()
                    continue
                content, mode = snapshot
                atomic_write_bytes(path, content)
                path.chmod(mode)
        finally:
            ACTIVE_TRANSACTION = previous

def record_path(path: Path) -> None:
    if ACTIVE_TRANSACTION is not None:
        ACTIVE_TRANSACTION.record(path)

class InstallLock:
    """Prevent two installers from interleaving writes in one scope."""
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def __enter__(self):
        reject_symlink_components(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            fail(L(f"Another installation is already running: {self.path}", f"Другая установка уже выполняется: {self.path}"))
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(f'{os.getpid()}\n')
            handle.flush()
            os.fsync(handle.fileno())
        self.acquired = True
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        if self.acquired:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass

def reject_symlink(path: Path) -> None:
    if path.is_symlink():
        fail(L(f"Refusing to write through symlink: {path}", f"Отказано: запись через символическую ссылку запрещена: {path}"))

def reject_symlink_components(path: Path) -> None:
    for component in (path, *path.parents):
        if component.is_symlink():
            fail(L(f"Refusing to write through symlink path component: {component}", f"Отказано: компонент пути является символической ссылкой: {component}"))

def atomic_write_bytes(path: Path, value: bytes) -> None:
    reject_symlink_components(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()

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
    def one_of(value, choices):
        return isinstance(value, str) and value in choices

    validators = {
        'behavior': lambda value: one_of(value, {'auto', 'preview', 'off'}),
        'scope': lambda value: one_of(value, {'first', 'all'}),
        'qualityGate': lambda value: isinstance(value, bool),
        'unsupportedModel': lambda value: one_of(value, {'skip', 'generic'}),
        'mode': lambda value: one_of(value, {'first', 'all', 'off'}),
    }
    for key, validator in validators.items():
        if key in data and not validator(data[key]):
            fail(L(f"Invalid {key} in {label}: {path}", f"Некорректное поле {key} в {label}: {path}"))

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
    if (START in current) != (END in current):
        fail(L(f"Incomplete managed block in {path}", f"Неполный управляемый блок в {path}"))
    if START in current and END in current:
        before,rest=current.split(START,1); _,after=rest.split(END,1)
        new=before.rstrip()+"\n\n"+block.strip()+"\n"+after.lstrip('\n'); action=L('updated','обновлено')
    else:
        new=current.rstrip()+("\n\n" if current.strip() else '')+block.strip()+"\n"; action=L('created','создано') if not path.exists() else L('merged','объединено')
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        record_path(path)
        if backup: backup_once(path)
        atomic_write_text(path, new)
    return f"{action}: {path}"

def configured_block(rel: str, behavior: str, scope: str, quality_gate: bool, unsupported: str) -> str:
    block=text(rel).rstrip()
    marker=END
    q='on' if quality_gate else 'off'
    line=f"\nConfigured by installer: `behavior={behavior}`, `scope={scope}`, `qualityGate={q}`, `unsupportedModel={unsupported}`. If a native adapter injects a newer per-turn setting, the native adapter wins.\n"
    return block.replace(marker, line+marker)

def merge_runtime_ignores(path: Path, entries: list[str], *, backup=True, dry_run=False) -> str:
    reject_symlink_components(path)
    current = path.read_text(encoding='utf-8') if path.exists() else ''
    if (IGNORE_START in current) != (IGNORE_END in current):
        fail(L(f"Incomplete runtime ignore block in {path}", f"Неполный блок runtime ignore в {path}"))
    block = IGNORE_START + '\n' + '\n'.join(entries) + '\n' + IGNORE_END
    if IGNORE_START in current:
        before, rest = current.split(IGNORE_START, 1)
        _, after = rest.split(IGNORE_END, 1)
        new = before.rstrip() + '\n\n' + block + after.lstrip('\n')
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
        target=dst/child.name
        copy_tree(child, target, backup=backup, label=f'skill {child.name}')
    return L(f"installed skills: {dst}", f"установлены skills: {dst}")

def copy_commands(src: Path, dst: Path, *, backup=True, dry_run=False) -> str:
    if dry_run: return L(f"would install OpenCode commands: {dst}", f"будут установлены команды OpenCode: {dst}")
    if dst.exists() and not dst.is_dir():
        fail(L(f"Commands destination is not a directory: {dst}", f"Назначение команд не является каталогом: {dst}"))
    reject_symlink_components(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.glob('*.md'): copy_file(p,dst/p.name,backup=backup,label='OpenCode command')
    return L(f"installed OpenCode commands: {dst}", f"установлены команды OpenCode: {dst}")

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
    current.update(updates)
    return write_json(path,current,backup=backup,dry_run=dry_run,label=label)

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
    def managed_item(item):
        if not isinstance(item,dict): return False
        if item.get('owner') == MANAGED_HOOK_OWNER:
            return True
        name=item.get('name')
        command=str(item.get('command',''))
        return (
            isinstance(name,str) and name.startswith('prompt-optimizer-v') and 'prompt-preflight.py' in command
            or command.endswith('.cursor/hooks/prompt-optimizer-state.py')
        )
    cleaned=[]
    for item in arr:
        if managed_item(item):
            continue
        nested=item.get('hooks') if isinstance(item,dict) else None
        if not isinstance(nested,list):
            cleaned.append(item)
            continue
        remaining=[child for child in nested if not managed_item(child)]
        if remaining:
            if len(remaining) != len(nested):
                item=dict(item)
                item['hooks']=remaining
            cleaned.append(item)
    arr[:]=cleaned
    arr.append(hook)
    return write_json(path,current,backup=backup,dry_run=dry_run,label=f'{event} hook config')

def write_shared_config(path: Path, behavior: str, scope: str, unsupported: str, quality_gate: bool, *, backup=True, dry_run=False) -> str:
    return merge_json_object(path,{'behavior':behavior,'scope':scope,'qualityGate':quality_gate,'unsupportedModel':unsupported},backup=backup,dry_run=dry_run,label='shared prompt-optimizer config')

def install_opencode(base: Path, behavior: str, scope: str, unsupported: str, quality_gate: bool, *, backup=True, dry_run=False) -> list[str]:
    out=[copy_tree(PACKAGE_ROOT/'adapters/opencode/plugin',base/'plugins/prompt-optimizer',backup=backup,dry_run=dry_run,label='OpenCode native plugin')]
    out.append(merge_json_object(base/'prompt-optimizer.json',{'behavior':behavior,'scope':scope,'qualityGate':quality_gate,'unsupportedModel':unsupported},backup=backup,dry_run=dry_run,label='OpenCode prompt-optimizer config'))
    return out

def install_pi(base: Path, *, backup=True, dry_run=False) -> list[str]:
    return [copy_file(PACKAGE_ROOT/'adapters/pi/extensions/prompt-optimizer.ts',base/'extensions/prompt-optimizer.ts',backup=backup,dry_run=dry_run,label='Pi native extension')]

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

def install_project(root: Path, selected: set[str], auto: bool, behavior: str, scope: str, unsupported: str, quality_gate: bool, backup: bool, dry_run: bool, python_bin: str) -> list[str]:
    validate_project_root(root)
    out=[copy_skills(root/'.agents/skills',backup=backup,dry_run=dry_run)]
    if 'claude' in selected: out.append(copy_skills(root/'.claude/skills',backup=backup,dry_run=dry_run))
    if 'opencode' in selected: out.append(copy_commands(PACKAGE_ROOT/'adapters/opencode/commands',root/'.opencode/commands',backup=backup,dry_run=dry_run))
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

def install_global(home: Path, selected: set[str], auto: bool, behavior: str, scope: str, unsupported: str, quality_gate: bool, backup: bool, dry_run: bool, python_bin: str) -> list[str]:
    out=[copy_skills(home/'.agents/skills',backup=backup,dry_run=dry_run)]
    if 'claude' in selected: out.append(copy_skills(home/'.claude/skills',backup=backup,dry_run=dry_run))
    if 'opencode' in selected: out.append(copy_commands(PACKAGE_ROOT/'adapters/opencode/commands',home/'.config/opencode/commands',backup=backup,dry_run=dry_run))
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
    ap=argparse.ArgumentParser(description='Install Universal Prompt Optimizer v5.4')
    ap.add_argument('--lang',choices=['en','ru'],default='en',help='Installer output language')
    ap.add_argument('--scope',choices=['project','global'],default='project')
    ap.add_argument('--project',default='.')
    ap.add_argument('--agents',default='all',help='opencode,codex,cursor,pi,claude,gemini,copilot,windsurf,all')
    ap.add_argument('--auto',action='store_true',help='Install automatic/preview/off adapter integration in addition to skills')
    ap.add_argument('--behavior',choices=['auto','preview','off'],default='auto')
    ap.add_argument('--prompt-scope',choices=['first','all'],default='all')
    ap.add_argument('--quality-gate',choices=['on','off'],default='on',help='Enable PASS/LIGHT/FULL adaptive rewrite gate')
    ap.add_argument('--unsupported-model',choices=['skip','generic'],default='skip')
    ap.add_argument('--python-bin',default=sys.executable,help='Python command used by generated hooks')
    ap.add_argument('--opencode-mode',choices=['first','all','off'],help='Deprecated v4 compatibility: first/all map to behavior=auto and corresponding scope; off maps to behavior=off')
    ap.add_argument('--no-backup',action='store_true')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    global UI_LANG
    UI_LANG=args.lang
    behavior=args.behavior; scope=args.prompt_scope
    if args.opencode_mode:
        if args.opencode_mode=='off': behavior='off'
        else: behavior='auto'; scope=args.opencode_mode
    selected=parse_agents(args.agents); backup=not args.no_backup; quality_gate=args.quality_gate=='on'
    if args.scope == 'project':
        root = Path(args.project).expanduser().resolve()
        validate_project_root(root)
    else:
        root = Path.home()
    lock = InstallLock(root / '.prompt-optimizer-install.lock')
    transaction = None if args.dry_run else InstallTransaction()
    global ACTIVE_TRANSACTION
    try:
        with (nullcontext() if args.dry_run else lock):
            ACTIVE_TRANSACTION = transaction
            try:
                if args.scope=='project':
                    results=install_project(root,selected,args.auto,behavior,scope,args.unsupported_model,quality_gate,backup,args.dry_run,args.python_bin)
                else:
                    results=install_global(root,selected,args.auto,behavior,scope,args.unsupported_model,quality_gate,backup,args.dry_run,args.python_bin)
            except BaseException:
                if transaction is not None:
                    transaction.rollback()
                raise
    finally:
        ACTIVE_TRANSACTION = None
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
