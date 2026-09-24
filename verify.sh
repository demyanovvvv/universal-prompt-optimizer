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
  say "Universal Prompt Optimizer v${VERSION} — самопроверка (bash)"
else
  say "Universal Prompt Optimizer v${VERSION} — self-check (bash)"
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

export PYTHONDONTWRITEBYTECODE=1

# All cross-platform checks live in the shared Python self-check.
if ! "$PYTHON_BIN" -B tools/selfcheck.py all; then
  fail "Общая самопроверка завершилась неудачно" "Shared self-check failed"
fi

# TypeScript syntax and OpenCode runtime behavior (requires tsc).
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

if [[ "$LANG_UI" == ru ]]; then say "Все проверки завершены успешно."; else say "All checks passed."; fi
