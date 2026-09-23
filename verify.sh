#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(tr -d '\r\n' < "$ROOT/VERSION")"
LANG_UI="en"
case "${1:-}" in ru|--ru|-ru) LANG_UI="ru" ;; esac
say(){ printf '%s\n' "$*"; }
ok(){ if [[ "$LANG_UI" == ru ]]; then say "[OK] $1"; else say "[OK] $2"; fi; }
warn(){ if [[ "$LANG_UI" == ru ]]; then say "[WARN] $1"; else say "[WARN] $2"; fi; }
fail(){ if [[ "$LANG_UI" == ru ]]; then say "[FAIL] $1" >&2; else say "[FAIL] $2" >&2; fi; exit 1; }

cd "$ROOT"
if [[ "$LANG_UI" == ru ]]; then
  say "Universal Prompt Optimizer v${VERSION} — самопроверка"
else
  say "Universal Prompt Optimizer v${VERSION} — self-check"
fi

bash -n install.sh verify.sh || fail "Ошибка синтаксиса Bash" "Bash syntax error"
ok "Синтаксис Bash" "Bash syntax"

PYTHON_BIN="${PYTHON_BIN:-}"
python_works(){ [[ -n "$1" ]] && command -v "$1" >/dev/null 2>&1 && "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; }
if ! python_works "$PYTHON_BIN"; then
  for candidate in python3 python py; do
    if python_works "$candidate"; then PYTHON_BIN="$candidate"; break; fi
  done
fi
[[ -n "$PYTHON_BIN" ]] || fail "Требуется Python 3" "Python 3 is required"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
TMP_WIN="$(cygpath -m "$TMP" 2>/dev/null || printf '%s' "$TMP")"
export PYTHONDONTWRITEBYTECODE=1
PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B - <<'PY'
import ast
from pathlib import Path
for name in [
    'install.py',
    'adapters/cursor/hooks/prompt-optimizer-state.py',
    'adapters/gemini-cli/hooks/prompt-preflight.py',
]:
    ast.parse(Path(name).read_text(encoding='utf-8'), filename=name)
PY
ok "Синтаксис Python" "Python syntax"

"$PYTHON_BIN" -B - <<'PY'
import json, pathlib, re, sys
root=pathlib.Path('.')
# JSON / JSONL
for p in root.rglob('*.json'):
    with p.open(encoding='utf-8') as f: json.load(f)
for p in root.rglob('*.jsonl'):
    for i,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
        if line.strip(): json.loads(line)
# registry
reg=json.loads((root/'.agents/skills/prompt-optimizer/references/model-registry.json').read_text(encoding='utf-8'))
profiles=reg.get('profiles',[])
if len(profiles)!=23: raise SystemExit(f'expected 23 profiles, got {len(profiles)}')
ids=[x['id'] for x in profiles]
if len(set(ids))!=len(ids): raise SystemExit('duplicate profile IDs')
for x in profiles:
    ref=root/'.agents/skills/prompt-optimizer/references'/x['file']
    if not ref.is_file():
        raise SystemExit(f"missing reference: {x['file']}")
    text=ref.read_text(encoding='utf-8')
    if 'Provenance' not in text or ('Official source' not in text and 'Official sources' not in text):
        raise SystemExit(f"profile missing provenance/source: {x['file']}")
# manual model override skills are the registry-derived names. Other project
# skills may also start with prompt- and must not be mistaken for model profiles.
skill_root=root/'.agents/skills'
expected_overrides={f"prompt-{item['id'].replace('.', '-')}" for item in profiles}
overrides=[p for p in skill_root.iterdir() if p.is_dir() and p.name in expected_overrides]
if len(overrides)!=23: raise SystemExit(f'expected 23 override skills, got {len(overrides)}')
for name in expected_overrides:
    if not (skill_root/name/'SKILL.md').is_file(): raise SystemExit(f'missing {skill_root/name}/SKILL.md')
# OpenCode profile type must cover registry IDs
text=(root/'adapters/opencode/plugin/index.ts').read_text(encoding='utf-8')
block=text.split('type Profile =',1)[1].split('type Settings',1)[0]
router_ids=set(re.findall(r'"([^"]+)"', block))
missing=set(ids)-router_ids
extra=router_ids-set(ids)
if missing or extra: raise SystemExit(f'OpenCode profile mismatch missing={sorted(missing)} extra={sorted(extra)}')
# Core package version alignment
ver=(root/'VERSION').read_text().strip()
package=json.loads((root/'package.json').read_text(encoding='utf-8'))
lock=json.loads((root/'package-lock.json').read_text(encoding='utf-8'))
if package.get('version') != f'{ver}.0' or lock.get('version') != f'{ver}.0':
    raise SystemExit(f'npm version mismatch for VERSION={ver}')
checks=[
    root/'.agents/skills/prompt-optimizer/SKILL.md',
    root/'adapters/opencode/plugin/index.ts',
    root/'adapters/pi/extensions/prompt-optimizer.ts',
    root/'adapters/gemini-cli/hooks/prompt-preflight.py',
    root/'auto/AGENTS.snippet.md',
    root/'auto/CLAUDE.snippet.md',
    root/'auto/GEMINI.snippet.md',
]
for p in checks:
    if f'v{ver}' not in p.read_text(encoding='utf-8') and f'version: "{ver}"' not in p.read_text(encoding='utf-8'):
        raise SystemExit(f'version marker missing/outdated in {p}')
# No stale runtime IDs from 5.2/5.3 outside historical docs
for p in list((root/'adapters').rglob('*')) + list((root/'auto').rglob('*')):
    if p.is_file():
        t=p.read_text(encoding='utf-8',errors='ignore')
        if any(stale in t for stale in ('prompt-optimizer-v5-2', 'prompt-optimizer-v5-3', 'prompt-optimizer-v5-4')):
            raise SystemExit(f'stale hook/plugin id in {p}')
# Archive hygiene
bad=[p for p in root.rglob('*') if p.name=='__pycache__' or p.suffix=='.pyc']
if bad: raise SystemExit('archive hygiene: '+', '.join(map(str,bad)))
print('OK')
PY
ok "JSON, registry, 23 профиля/override skills, версии и чистота пакета" "JSON, registry, 23 profiles/override skills, version alignment and package hygiene"

"$PYTHON_BIN" -B tests/registry_conformance.py
ok "Согласованность registry и адаптеров" "Registry and adapter conformance"

"$PYTHON_BIN" -B evals/run.py --strict-coverage >/dev/null
ok "Статическая матрица evals" "Static evaluation matrix"

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -B -m unittest discover -s tests >/dev/null
ok "Unit-тесты installer, registry и evals" "Installer, registry and eval unit tests"

TSC_BIN=""
if command -v tsc >/dev/null 2>&1; then
  TSC_BIN="$(command -v tsc)"
elif [[ -x node_modules/.bin/tsc ]]; then
  TSC_BIN="node_modules/.bin/tsc"
fi
if [[ -n "$TSC_BIN" ]]; then
  "$TSC_BIN" -p tsconfig.verify.json
  ok "Синтаксис TypeScript" "TypeScript syntax"
  "$TSC_BIN" -p tsconfig.test.json
   node --test .tmp-tests/opencode/tests/opencode-runtime.test.js .tmp-tests/opencode/tests/eval-contract.test.js .tmp-tests/opencode/tests/model-routing.test.js >/dev/null
  ok "Поведенческие тесты OpenCode runtime" "OpenCode runtime behavior tests"
else
  warn "tsc не найден — синтаксис TypeScript не проверен локально" "tsc not found — TypeScript syntax check skipped"
fi

./install.sh --agents all --scope project --project "$TMP/project" --auto --behavior auto \
  --prompt-scope all --quality-gate on --unsupported-model skip --dry-run --yes >/dev/null
ok "Dry-run установки всех 8 агентов" "All-eight-agent installation dry-run"

# Cursor first-turn state smoke test.
mkdir -p "$TMP/cursor/.cursor"
printf '{"behavior":"auto","scope":"first","qualityGate":true,"unsupportedModel":"skip"}\n' > "$TMP/cursor/.prompt-optimizer.json"
printf '%s\n' '{"conversation_id":"c1","generation_id":"g1","model":"claude-opus-5","model_id":"claude-opus-5","model_params":[],"workspace_roots":["'"$TMP_WIN"'/cursor"]}' \
  | "$PYTHON_BIN" -B adapters/cursor/hooks/prompt-optimizer-state.py >/dev/null
"$PYTHON_BIN" -B - "$TMP_WIN/cursor/.cursor/.prompt-optimizer-runtime.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))['active'] is True
PY
printf '%s\n' '{"conversation_id":"c1","generation_id":"g2","model":"claude-opus-5","model_id":"claude-opus-5","model_params":[],"workspace_roots":["'"$TMP_WIN"'/cursor"]}' \
  | "$PYTHON_BIN" -B adapters/cursor/hooks/prompt-optimizer-state.py >/dev/null
"$PYTHON_BIN" -B - "$TMP_WIN/cursor/.cursor/.prompt-optimizer-runtime.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))['active'] is False
PY
"$PYTHON_BIN" -B - "$TMP_WIN/cursor/.cursor/.prompt-optimizer-runtime.json" <<'PY'
import json,sys
runtime=json.load(open(sys.argv[1], encoding='utf-8'))
assert runtime['sessions']['c1']['generation_id']=='g2'
PY
ok "Cursor scope=first" "Cursor scope=first"

# Gemini CLI model observation and SKIP/GENERIC semantics.
mkdir -p "$TMP/gemini/.gemini"
printf '%s\n' '{"behavior":"auto","scope":"all","qualityGate":true,"unsupportedModel":"skip"}' > "$TMP/gemini/.prompt-optimizer.json"
# Unknown first turn + SKIP => no injected optimizer context.
printf '%s\n' '{"session_id":"gs1","cwd":"'"$TMP_WIN"'/gemini","hook_event_name":"BeforeAgent","prompt":"Fix it"}' \
  | "$PYTHON_BIN" -B adapters/gemini-cli/hooks/prompt-preflight.py > "$TMP/gemini-before.json"
"$PYTHON_BIN" -B - "$TMP_WIN/gemini-before.json" <<'PY'
import json,sys
o=json.load(open(sys.argv[1]))
assert o['hookSpecificOutput']['additionalContext']==''
PY
# BeforeModel records the exact model but must not override the outgoing request.
printf '%s\n' '{"session_id":"gs1","cwd":"'"$TMP_WIN"'/gemini","hook_event_name":"BeforeModel","llm_request":{"model":"gemini-3.8-flash","messages":[],"config":{}}}' \
  | "$PYTHON_BIN" -B adapters/gemini-cli/hooks/prompt-preflight.py > "$TMP/gemini-model.json"
"$PYTHON_BIN" -B - "$TMP_WIN/gemini-model.json" "$TMP_WIN/gemini/.gemini/.prompt-optimizer-model-state.json" <<'PY'
import json,sys
o=json.load(open(sys.argv[1])); st=json.load(open(sys.argv[2]))
assert 'hookSpecificOutput' not in o or 'llm_request' not in o.get('hookSpecificOutput',{})
assert st['gs1']['model']=='gemini-3.8-flash'
assert isinstance(st['gs1']['updatedAt'], int)
PY
# Later turn in same session sees the exact supported profile.
printf '%s\n' '{"session_id":"gs1","cwd":"'"$TMP_WIN"'/gemini","hook_event_name":"BeforeAgent","prompt":"Fix it"}' \
  | "$PYTHON_BIN" -B adapters/gemini-cli/hooks/prompt-preflight.py > "$TMP/gemini-after.json"
"$PYTHON_BIN" -B - "$TMP_WIN/gemini-after.json" <<'PY'
import json,sys
t=json.load(open(sys.argv[1]))['hookSpecificOutput']['additionalContext']
assert 'Resolved model profile: Gemini 3.8 Flash' in t
PY
# GENERIC intentionally injects neutral context when model is unknown.
printf '%s\n' '{"behavior":"auto","scope":"all","qualityGate":true,"unsupportedModel":"generic"}' > "$TMP/gemini/.prompt-optimizer.json"
printf '%s\n' '{"session_id":"gs2","cwd":"'"$TMP_WIN"'/gemini","hook_event_name":"BeforeAgent","prompt":"Fix it"}' \
  | "$PYTHON_BIN" -B adapters/gemini-cli/hooks/prompt-preflight.py > "$TMP/gemini-generic.json"
"$PYTHON_BIN" -B - "$TMP_WIN/gemini-generic.json" <<'PY'
import json,sys
t=json.load(open(sys.argv[1]))['hookSpecificOutput']['additionalContext']
assert 'neutral model-agnostic optimizer profile' in t
PY
ok "Gemini CLI: точная модель через BeforeModel, SKIP/GENERIC" "Gemini CLI: exact BeforeModel observation plus SKIP/GENERIC"

# Gemini CLI scope=first smoke test using an explicit supported configured model.
rm -f "$TMP/gemini/.gemini/.prompt-optimizer-session-state.json"
printf '%s\n' '{"behavior":"auto","scope":"first","qualityGate":true,"unsupportedModel":"skip"}' > "$TMP/gemini/.prompt-optimizer.json"
GEMINI_MODEL=gemini-3.8-flash printf '%s\n' '{"session_id":"gf1","cwd":"'"$TMP_WIN"'/gemini","hook_event_name":"BeforeAgent","prompt":"Fix it"}' \
  | GEMINI_MODEL=gemini-3.8-flash "$PYTHON_BIN" -B adapters/gemini-cli/hooks/prompt-preflight.py > "$TMP/gemini-first.json"
GEMINI_MODEL=gemini-3.8-flash printf '%s\n' '{"session_id":"gf1","cwd":"'"$TMP_WIN"'/gemini","hook_event_name":"BeforeAgent","prompt":"Again"}' \
  | GEMINI_MODEL=gemini-3.8-flash "$PYTHON_BIN" -B adapters/gemini-cli/hooks/prompt-preflight.py > "$TMP/gemini-second.json"
"$PYTHON_BIN" -B - "$TMP_WIN/gemini-first.json" "$TMP_WIN/gemini-second.json" <<'PY'
import json,sys
a=json.load(open(sys.argv[1]))['hookSpecificOutput']['additionalContext']
b=json.load(open(sys.argv[2]))['hookSpecificOutput']['additionalContext']
assert 'Gemini 3.8 Flash' in a
assert b==''
PY
ok "Gemini CLI scope=first" "Gemini CLI scope=first"

# An ineligible unknown-model turn must not consume scope=first.
rm -f "$TMP/gemini/.gemini/.prompt-optimizer-session-state.json" "$TMP/gemini/.gemini/.prompt-optimizer-model-state.json"
printf '%s\n' '{"behavior":"auto","scope":"first","qualityGate":true,"unsupportedModel":"skip"}' > "$TMP/gemini/.prompt-optimizer.json"
printf '%s\n' '{"session_id":"ge1","cwd":"'"$TMP_WIN"'/gemini","hook_event_name":"BeforeAgent","prompt":"Unknown"}' \
  | "$PYTHON_BIN" -B adapters/gemini-cli/hooks/prompt-preflight.py > "$TMP/gemini-eligible-unknown.json"
printf '%s\n' '{"session_id":"ge1","cwd":"'"$TMP_WIN"'/gemini","hook_event_name":"BeforeModel","llm_request":{"model":"gemini-3.8-flash"}}' \
  | "$PYTHON_BIN" -B adapters/gemini-cli/hooks/prompt-preflight.py > "$TMP/gemini-eligible-model.json"
printf '%s\n' '{"session_id":"ge1","cwd":"'"$TMP_WIN"'/gemini","hook_event_name":"BeforeAgent","prompt":"Supported"}' \
  | "$PYTHON_BIN" -B adapters/gemini-cli/hooks/prompt-preflight.py > "$TMP/gemini-eligible-supported.json"
"$PYTHON_BIN" -B - "$TMP_WIN/gemini-eligible-unknown.json" "$TMP_WIN/gemini-eligible-supported.json" <<'PY'
import json, sys
unknown=json.load(open(sys.argv[1], encoding='utf-8'))['hookSpecificOutput']['additionalContext']
supported=json.load(open(sys.argv[2], encoding='utf-8'))['hookSpecificOutput']['additionalContext']
assert unknown == ''
assert 'Gemini 3.8 Flash' in supported
PY
ok "Gemini scope=first расходуется только eligible turn" "Gemini scope=first consumes only eligible turns"

# Native hooks fail safe when a managed config is malformed.
printf '%s\n' '{broken' > "$TMP/gemini/.prompt-optimizer.json"
printf '%s\n' '{"session_id":"bad1","cwd":"'"$TMP_WIN"'/gemini","hook_event_name":"BeforeAgent","prompt":"Do not optimize"}' \
  | "$PYTHON_BIN" -B adapters/gemini-cli/hooks/prompt-preflight.py > "$TMP/gemini-invalid-config.json"
"$PYTHON_BIN" -B - "$TMP_WIN/gemini-invalid-config.json" <<'PY'
import json, sys
assert json.load(open(sys.argv[1], encoding='utf-8'))['hookSpecificOutput']['additionalContext'] == ''
PY
ok "Поврежденный runtime config отключает hook" "Malformed runtime config fails safe"
printf '%s\n' '{"behavior":"auto","scope":"all","qualityGate":true,"unsupportedModel":"skip"}' > "$TMP/gemini/.prompt-optimizer.json"

# Real all-agent project install + config preservation.
REAL="$TMP/real"
mkdir -p "$REAL"
printf '%s\n' '{"customField":"keep-me","behavior":"off"}' > "$REAL/.prompt-optimizer.json"
./install.sh --agents all --scope project --project "$REAL" --auto --behavior auto \
  --prompt-scope all --quality-gate on --unsupported-model skip --yes >/dev/null
"$PYTHON_BIN" -B - "$TMP_WIN/real" <<'PY'
import json, pathlib, sys
r=pathlib.Path(sys.argv[1])
cfg=json.loads((r/'.prompt-optimizer.json').read_text())
assert cfg['customField']=='keep-me' and cfg['behavior']=='auto'
expected=[
 r/'.agents/skills/prompt-optimizer/SKILL.md',
 r/'.opencode/plugins/prompt-optimizer/index.ts',
 r/'.cursor/hooks.json',
 r/'.pi/extensions/prompt-optimizer.ts',
 r/'.gemini/settings.json',
 r/'CLAUDE.md',
 r/'.github/copilot-instructions.md',
 r/'.windsurf/rules/prompt-optimizer.md',
 r/'AGENTS.md',
]
missing=[str(p) for p in expected if not p.exists()]
assert not missing, missing
g=json.loads((r/'.gemini/settings.json').read_text())
assert 'BeforeAgent' in g.get('hooks',{}) and 'BeforeModel' in g.get('hooks',{})
PY
ok "Реальная установка всех 8 агентов и сохранение JSON-полей" "Real all-eight-agent install and JSON-field preservation"

# Safety and idempotence regressions.
PACKAGE_ROOT_ERROR="$TMP/package-root-error.txt"
if "$PYTHON_BIN" -B install.py --agents all --scope project --project "$ROOT" --auto > /dev/null 2> "$PACKAGE_ROOT_ERROR"; then
  fail "Установка в исходный каталог не была отклонена" "Package-root installation was not rejected"
fi
grep -q 'package source tree\|исходного каталога пакета' "$PACKAGE_ROOT_ERROR" || fail "Package-root тест завершился не из-за защиты пути" "Package-root test did not fail because of the path guard"
[[ -z "$(find . -type f -name '*.prompt-optimizer.bak' -print -quit)" ]] || fail "Проверка package root создала backup" "Package-root check created a backup"
mkdir -p "$TMP/safety/.agents/skills/custom" "$TMP/safety/.opencode/commands"
printf '%s\n' 'user skill must survive' > "$TMP/safety/.agents/skills/custom/SKILL.md"
printf '%s\n' 'user command must survive' > "$TMP/safety/.opencode/commands/user-command.md"
printf '%s\n' '{not valid json' > "$TMP/safety/.prompt-optimizer.json"
if ./install.sh --agents opencode --scope project --project "$TMP/safety" --auto --yes >/dev/null 2>&1; then
  fail "Некорректный JSON не был отклонен" "Malformed JSON was not rejected"
fi
[[ "$(cat "$TMP/safety/.prompt-optimizer.json")" == '{not valid json' ]] || fail "Поврежденный JSON был перезаписан" "Malformed JSON was overwritten"
printf '%s\n' '{}' > "$TMP/safety/.prompt-optimizer.json"
./install.sh --agents opencode,cursor,gemini --scope project --project "$TMP/safety" --auto --yes --python-bin "$PYTHON_BIN" >/dev/null
[[ -f "$TMP/safety/.agents/skills/custom/SKILL.md" ]] || fail "Пользовательский skill удален" "User skill was removed"
[[ "$(cat "$TMP/safety/.opencode/commands/user-command.md")" == 'user command must survive' ]] || fail "Пользовательская команда удалена" "User command was removed"
printf '%s\n' '# user ignore' >> "$TMP/safety/.gitignore"
"$PYTHON_BIN" -B - "$TMP_WIN/safety/.cursor/hooks.json" "$TMP_WIN/safety/.gemini/settings.json" "$PYTHON_BIN" <<'PY'
import json, sys
for name in sys.argv[1:3]:
    data=json.load(open(name, encoding='utf-8'))
    values=json.dumps(data)
    assert 'prompt-optimizer' in values
    assert '$HOME' not in values and '$GEMINI_PROJECT_DIR' not in values
assert sys.argv[3] in json.dumps(json.load(open(sys.argv[1], encoding='utf-8')))
PY
grep -q '^# user ignore$' "$TMP/safety/.gitignore" || fail "Пользовательский gitignore изменен" "User gitignore was not preserved"
./install.sh --agents opencode,cursor,gemini --scope project --project "$TMP/safety" --auto --yes --python-bin "$PYTHON_BIN" >/dev/null
[[ -f "$TMP/safety/.agents/skills/custom/SKILL.md" ]] || fail "Повторная установка удалила пользовательский skill" "Repeat install removed user skill"
ok "Безопасность, сохранение пользовательских файлов и повторная установка" "Installer safety, user-file preservation and idempotence"

# Hook ownership must not collide with user names or remove sibling hooks.
"$PYTHON_BIN" -B - "$TMP_WIN/hook-ownership.json" <<'PY'
import importlib.util, json, pathlib, sys
spec=importlib.util.spec_from_file_location('installer','install.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
path=pathlib.Path(sys.argv[1])
path.write_text(json.dumps({'hooks': {'BeforeAgent': [
    {'name':'prompt-optimizer','command':'user-command'},
    {'hooks': [
        {'name':'prompt-optimizer','command':'user-sibling'},
        {'name':'prompt-optimizer','owner':'universal-prompt-optimizer','command':'managed'},
    ]},
]}}, indent=2), encoding='utf-8')
module.merge_json_hook(path, 'BeforeAgent', {'hooks': [{'name':'prompt-optimizer','owner':'universal-prompt-optimizer','command':'new-managed'}]}, backup=False)
data=json.loads(path.read_text(encoding='utf-8'))
items=data['hooks']['BeforeAgent']
assert any(item.get('command') == 'user-command' for item in items)
groups=[item for item in items if isinstance(item,dict) and isinstance(item.get('hooks'),list)]
assert groups and any(child.get('command') == 'user-sibling' for child in groups[0]['hooks'])
assert any(child.get('command') == 'new-managed' for child in items[-1]['hooks'])
PY
ok "Ownership hook не удаляет пользовательские entries" "Hook ownership preserves user entries"

# A failure after initial writes must roll back the completed portion.
mkdir -p "$TMP/rollback/.gemini"
printf '%s\n' '{}' > "$TMP/rollback/.prompt-optimizer.json"
printf '%s\n' '{broken' > "$TMP/rollback/.gemini/settings.json"
if ./install.sh --agents opencode,gemini --scope project --project "$TMP/rollback" --auto --yes >/dev/null 2>&1; then
  fail "Ошибка установки не вызвала rollback" "Failed install did not roll back"
fi
[[ ! -e "$TMP/rollback/.agents/skills/prompt-optimizer/SKILL.md" ]] || fail "Rollback оставил skill" "Rollback left installed skill"
[[ ! -e "$TMP/rollback/.prompt-optimizer-install.lock" ]] || fail "Rollback оставил install lock" "Rollback left install lock"
[[ "$(cat "$TMP/rollback/.gemini/settings.json")" == '{broken' ]] || fail "Rollback изменил исходный JSON" "Rollback changed original JSON"
ok "Rollback после частичной установки" "Rollback after partial installation"

# Doctor is read-only and uninstall removes only package-owned material.
LIFECYCLE="$TMP/lifecycle"
mkdir -p "$LIFECYCLE"
printf '%s\n' '# user content' > "$LIFECYCLE/AGENTS.md"
./install.sh --agents opencode,cursor,gemini --scope project --project "$LIFECYCLE" --auto --yes --python-bin "$PYTHON_BIN" >/dev/null
./install.sh --scope project --project "$LIFECYCLE" --doctor >/dev/null
if ./install.sh --scope project --project "$LIFECYCLE" --doctor --uninstall >/dev/null 2>&1; then
  fail "Doctor accepted --uninstall вместе" "Doctor accepted --uninstall together"
fi
./install.sh --agents all --scope project --project "$LIFECYCLE" --uninstall --dry-run --yes >/dev/null
./install.sh --agents all --scope project --project "$LIFECYCLE" --uninstall --yes >/dev/null
./install.sh --agents all --scope project --project "$LIFECYCLE" --uninstall --yes >/dev/null
grep -q '^# user content$' "$LIFECYCLE/AGENTS.md" || fail "Uninstall удалил пользовательский текст" "Uninstall removed user text"
[[ ! -e "$LIFECYCLE/.agents/skills/prompt-optimizer/SKILL.md" ]] || fail "Uninstall оставил shared skill" "Uninstall left shared skill"
[[ ! -e "$LIFECYCLE/.opencode/plugins/prompt-optimizer/index.ts" ]] || fail "Uninstall оставил OpenCode plugin" "Uninstall left OpenCode plugin"
ok "Doctor, uninstall и dry-run" "Doctor, uninstall and dry-run"

if [[ "$LANG_UI" == ru ]]; then say "Все проверки завершены успешно."; else say "All checks passed."; fi
