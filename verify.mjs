#!/usr/bin/env node
/**
 * Portable self-check for Universal Prompt Optimizer.
 *
 * Mirrors the coverage of verify.sh without requiring bash or WSL: it uses only
 * Node and a Python 3 interpreter. Bash-only checks (shell syntax, the bash
 * installer wrapper) run when bash is available and are reported as skipped
 * otherwise, so the same command is meaningful on Windows, macOS, and Linux.
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const LANG_UI = process.argv.includes("--ru") || process.argv.includes("ru") ? "ru" : "en";
const t = (en, ru) => (LANG_UI === "ru" ? ru : en);

let failures = 0;
const ok = (en, ru) => console.log(`[OK] ${t(en, ru)}`);
const warn = (en, ru) => console.log(`[WARN] ${t(en, ru)}`);
const fail = (en, ru) => {
  failures += 1;
  console.error(`[FAIL] ${t(en, ru)}`);
};

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", ...(options.env ?? {}) },
    input: options.input,
    maxBuffer: 64 * 1024 * 1024,
  });
  return result;
}

function checkPython() {
  for (const candidate of [process.env.PYTHON_BIN, "python3", "python", "py"].filter(Boolean)) {
    const probe = run(candidate, ["-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"]);
    if (probe.status === 0) return candidate;
  }
  return null;
}

function hasBash() {
  const probe = run("bash", ["-c", "exit 0"]);
  return probe.status === 0;
}

const VERSION = readFileSync(join(ROOT, "VERSION"), "utf8").trim();
console.log(`Universal Prompt Optimizer v${VERSION} — self-check (portable)`);

const PYTHON = checkPython();
if (!PYTHON) {
  fail("Python 3 is required", "Требуется Python 3");
  process.exit(1);
}

// 1. Bash syntax when bash is available.
if (hasBash()) {
  const bashSyntax = run("bash", ["-n", "install.sh", "verify.sh"]);
  if (bashSyntax.status === 0) ok("Bash syntax", "Синтаксис Bash");
  else fail(`Bash syntax error: ${bashSyntax.stderr}`, `Ошибка синтаксиса Bash: ${bashSyntax.stderr}`);
} else {
  warn("bash not found — Bash syntax check skipped", "bash не найден — проверка синтаксиса Bash пропущена");
}

// 2. Python syntax.
const pythonSyntax = run(PYTHON, ["-B", "-c", [
  "import ast",
  "from pathlib import Path",
  "for name in ['install.py','adapters/cursor/hooks/prompt-optimizer-state.py','adapters/gemini-cli/hooks/prompt-preflight.py']:",
  "    ast.parse(Path(name).read_text(encoding='utf-8'), filename=name)",
].join("\n")]);
if (pythonSyntax.status === 0) ok("Python syntax", "Синтаксис Python");
else fail(`Python syntax error: ${pythonSyntax.stderr}`, `Ошибка синтаксиса Python: ${pythonSyntax.stderr}`);

// 3. JSON/JSONL, registry, version alignment, archive hygiene.
const hygiene = run(PYTHON, ["-B", "-c", hygieneScript()]);
if (hygiene.status === 0) {
  ok(
    "JSON, registry, 20 profiles/override skills, version alignment and package hygiene",
    "JSON, registry, 20 профилей/override skills, версии и чистота пакета",
  );
} else {
  fail(`Package hygiene: ${hygiene.stdout}${hygiene.stderr}`, `Гигиена пакета: ${hygiene.stdout}${hygiene.stderr}`);
}

// 4. Registry/adapter conformance.
const registry = run(PYTHON, ["-B", "tests/registry_conformance.py"]);
if (registry.status === 0) ok("Registry and adapter conformance", "Согласованность registry и адаптеров");
else fail(`Registry conformance: ${registry.stdout}${registry.stderr}`, `Согласованность registry: ${registry.stdout}${registry.stderr}`);

// 5. Adapter capability matrix conformance.
const adapters = run(PYTHON, ["-B", "tests/adapter_conformance.py"]);
if (adapters.status === 0) ok("Adapter capability matrix conformance", "Согласованность adapter capability matrix");
else fail(`Adapter conformance: ${adapters.stdout}${adapters.stderr}`, `Согласованность адаптеров: ${adapters.stdout}${adapters.stderr}`);

// 6. Static evaluation matrix.
const evals = run(PYTHON, ["-B", "evals/run.py", "--strict-coverage"]);
if (evals.status === 0) ok("Static evaluation matrix", "Статическая матрица evals");
else fail(`Evaluation matrix: ${evals.stdout}${evals.stderr}`, `Матрица evals: ${evals.stdout}${evals.stderr}`);

// 7. Unit tests.
const unit = run(PYTHON, ["-B", "-m", "unittest", "discover", "-s", "tests"]);
if (unit.status === 0) ok("Installer, registry and eval unit tests", "Unit-тесты installer, registry и evals");
else fail(`Unit tests: ${unit.stdout}${unit.stderr}`, `Unit-тесты: ${unit.stdout}${unit.stderr}`);

// 8. TypeScript syntax and OpenCode runtime behavior.
const tsc = findTsc();
if (tsc) {
  const verifyTs = runTsc(tsc, ["-p", "tsconfig.verify.json"]);
  if (verifyTs.status === 0) ok("TypeScript syntax", "Синтаксис TypeScript");
  else fail(`TypeScript verify: ${verifyTs.stdout}${verifyTs.stderr}`, `TypeScript verify: ${verifyTs.stdout}${verifyTs.stderr}`);
  const testTs = runTsc(tsc, ["-p", "tsconfig.test.json"]);
  if (testTs.status === 0) {
    const runtime = run(process.execPath, [
      "--test",
      ".tmp-tests/opencode/tests/opencode-runtime.test.js",
      ".tmp-tests/opencode/tests/eval-contract.test.js",
    ]);
    if (runtime.status === 0) ok("OpenCode runtime behavior tests", "Поведенческие тесты OpenCode runtime");
    else fail(`OpenCode runtime tests: ${runtime.stdout}${runtime.stderr}`, `Поведенческие тесты OpenCode: ${runtime.stdout}${runtime.stderr}`);
  } else {
    fail(`TypeScript test build: ${testTs.stdout}${testTs.stderr}`, `TypeScript test build: ${testTs.stdout}${testTs.stderr}`);
  }
} else {
  warn("tsc not found — TypeScript syntax check skipped", "tsc не найден — проверка синтаксиса TypeScript пропущена");
}

// 9. Installer lifecycle smoke tests using install.py directly.
const tmp = mkdtempSync(join(tmpdir(), "upo-verify-"));
try {
  runInstall(["--agents", "all", "--scope", "project", "--project", join(tmp, "project"), "--auto",
    "--behavior", "auto", "--prompt-scope", "all", "--quality-gate", "on",
    "--unsupported-model", "skip", "--dry-run"], { expect: 0, label: t("All-eight-agent installation dry-run", "Dry-run установки всех 8 агентов") });

  cursorSmoke(join(tmp, "cursor"));
  geminiSmoke(join(tmp, "gemini"));
  realInstallSmoke(join(tmp, "real"));
  safetySmoke(join(tmp, "safety"));
  rollbackSmoke(join(tmp, "rollback"));
  lifecycleSmoke(join(tmp, "lifecycle"));
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

if (failures === 0) {
  console.log(t("All checks passed.", "Все проверки завершены успешно."));
  process.exit(0);
}
console.error(t(`${failures} check(s) failed.`, `${failures} проверок завершились неудачно.`));
process.exit(1);

function findTsc() {
  const local = join(ROOT, "node_modules", "typescript", "bin", "tsc");
  if (existsSync(local)) return { command: local, kind: "node" };
  const localCmd = join(ROOT, "node_modules", ".bin", "tsc.cmd");
  if (process.platform === "win32" && existsSync(localCmd)) return { command: localCmd, kind: "cmd" };
  const probe = run("tsc", ["--version"]);
  if (probe.status === 0) return { command: "tsc", kind: "bin" };
  return null;
}

function runTsc(tsc, args) {
  if (tsc.kind === "node") return run(process.execPath, [tsc.command, ...args]);
  if (tsc.kind === "cmd") return run("cmd.exe", ["/d", "/s", "/c", tsc.command, ...args]);
  return run(tsc.command, args);
}

function runInstall(args, { expect = 0, label = "" } = {}) {
  const result = run(PYTHON, ["-B", "install.py", ...args]);
  const matched = expect === null ? result.status !== 0 : result.status === expect;
  if (matched) {
    if (label) ok(label, label);
  } else {
    const wanted = expect === null ? "a non-zero exit" : `exit ${expect}`;
    fail(`${label || args.join(" ")}: expected ${wanted}, got ${result.status}: ${result.stdout}${result.stderr}`,
      `${label || args.join(" ")}: ожидался ${wanted}, получен ${result.status}: ${result.stdout}${result.stderr}`);
  }
  return result;
}

function cursorSmoke(dir) {
  mkdirSync(join(dir, ".cursor"), { recursive: true });
  writeFileSync(join(dir, ".prompt-optimizer.json"),
    '{"behavior":"auto","scope":"first","qualityGate":true,"unsupportedModel":"skip"}\n');
  const hook = join(ROOT, "adapters/cursor/hooks/prompt-optimizer-state.py");
  const payload = (generation) => JSON.stringify({
    conversation_id: "c1", generation_id: generation, model: "claude-opus-5",
    model_id: "claude-opus-5", model_params: [], workspace_roots: [join(dir)],
  }) + "\n";
  run(PYTHON, ["-B", hook], { input: payload("g1") });
  let state = JSON.parse(readFileSync(join(dir, ".cursor/.prompt-optimizer-runtime.json"), "utf8"));
  if (state.active !== true) return fail("Cursor scope=first: first turn not active", "Cursor scope=first: первый turn не активен");
  run(PYTHON, ["-B", hook], { input: payload("g2") });
  state = JSON.parse(readFileSync(join(dir, ".cursor/.prompt-optimizer-runtime.json"), "utf8"));
  if (state.active !== false) return fail("Cursor scope=first: second turn still active", "Cursor scope=first: второй turn активен");
  if (state.sessions?.c1?.generation_id !== "g2") return fail("Cursor scope=first: state not updated", "Cursor scope=first: state не обновлён");
  ok("Cursor scope=first", "Cursor scope=first");
}

function geminiSmoke(dir) {
  mkdirSync(join(dir, ".gemini"), { recursive: true });
  const hook = join(ROOT, "adapters/gemini-cli/hooks/prompt-preflight.py");
  writeFileSync(join(dir, ".prompt-optimizer.json"),
    '{"behavior":"auto","scope":"all","qualityGate":true,"unsupportedModel":"skip"}\n');
  const beforeAgent = (session, prompt) => JSON.stringify({ session_id: session, cwd: dir, hook_event_name: "BeforeAgent", prompt }) + "\n";
  let result = run(PYTHON, ["-B", hook], { input: beforeAgent("gs1", "Fix it") });
  let out = JSON.parse(result.stdout);
  if (out.hookSpecificOutput.additionalContext !== "") return fail("Gemini SKIP: unknown model injected context", "Gemini SKIP: неизвестная модель добавила контекст");
  const beforeModel = JSON.stringify({ session_id: "gs1", cwd: dir, hook_event_name: "BeforeModel", llm_request: { model: "gemini-3.8-flash", messages: [], config: {} } }) + "\n";
  result = run(PYTHON, ["-B", hook], { input: beforeModel });
  out = JSON.parse(result.stdout);
  if (out.hookSpecificOutput?.llm_request) return fail("Gemini BeforeModel: overrode request", "Gemini BeforeModel: переопределил request");
  const state = JSON.parse(readFileSync(join(dir, ".gemini/.prompt-optimizer-model-state.json"), "utf8"));
  if (state.gs1.model !== "gemini-3.8-flash") return fail("Gemini BeforeModel: model not recorded", "Gemini BeforeModel: модель не записана");
  result = run(PYTHON, ["-B", hook], { input: beforeAgent("gs1", "Fix it") });
  out = JSON.parse(result.stdout);
  if (!out.hookSpecificOutput.additionalContext.includes("Gemini 3.8 Flash")) return fail("Gemini exact model not resolved", "Gemini точная модель не определена");
  writeFileSync(join(dir, ".prompt-optimizer.json"),
    '{"behavior":"auto","scope":"all","qualityGate":true,"unsupportedModel":"generic"}\n');
  result = run(PYTHON, ["-B", hook], { input: beforeAgent("gs2", "Fix it") });
  out = JSON.parse(result.stdout);
  if (!out.hookSpecificOutput.additionalContext.includes("neutral model-agnostic optimizer profile")) {
    return fail("Gemini GENERIC: neutral context missing", "Gemini GENERIC: нейтральный контекст отсутствует");
  }
  ok("Gemini CLI: exact BeforeModel observation plus SKIP/GENERIC", "Gemini CLI: точная модель через BeforeModel, SKIP/GENERIC");

  rmSync(join(dir, ".gemini/.prompt-optimizer-session-state.json"), { force: true });
  rmSync(join(dir, ".gemini/.prompt-optimizer-model-state.json"), { force: true });
  writeFileSync(join(dir, ".prompt-optimizer.json"),
    '{"behavior":"auto","scope":"first","qualityGate":true,"unsupportedModel":"skip"}\n');
  const env = { GEMINI_MODEL: "gemini-3.8-flash" };
  const first = run(PYTHON, ["-B", hook], { input: beforeAgent("gf1", "Fix it"), env });
  const second = run(PYTHON, ["-B", hook], { input: beforeAgent("gf1", "Again"), env });
  const firstText = JSON.parse(first.stdout).hookSpecificOutput.additionalContext;
  const secondText = JSON.parse(second.stdout).hookSpecificOutput.additionalContext;
  if (!firstText.includes("Gemini 3.8 Flash") || secondText !== "") {
    return fail("Gemini scope=first incorrect", "Gemini scope=first работает неверно");
  }
  ok("Gemini scope=first consumes only eligible turns", "Gemini scope=first расходуется только eligible turn");

  writeFileSync(join(dir, ".prompt-optimizer.json"), "{broken\n");
  result = run(PYTHON, ["-B", hook], { input: beforeAgent("bad1", "Do not optimize") });
  out = JSON.parse(result.stdout);
  if (out.hookSpecificOutput.additionalContext !== "") return fail("Malformed config did not fail safe", "Повреждённый config не отключил hook");
  writeFileSync(join(dir, ".prompt-optimizer.json"),
    '{"behavior":"auto","scope":"all","qualityGate":true,"unsupportedModel":"skip"}\n');
  ok("Malformed runtime config fails safe", "Поврежденный runtime config отключает hook");
}

function realInstallSmoke(dir) {
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, ".prompt-optimizer.json"), '{"customField":"keep-me","behavior":"off"}\n');
  const install = runInstall(["--agents", "all", "--scope", "project", "--project", dir, "--auto",
    "--behavior", "auto", "--prompt-scope", "all", "--quality-gate", "on", "--unsupported-model", "skip"]);
  if (install.status !== 0) return;
  const cfg = JSON.parse(readFileSync(join(dir, ".prompt-optimizer.json"), "utf8"));
  if (cfg.customField !== "keep-me" || cfg.behavior !== "auto") {
    return fail("Install did not preserve custom JSON fields", "Установка не сохранила пользовательские JSON-поля");
  }
  const expected = [
    ".agents/skills/prompt-optimizer/SKILL.md", ".opencode/plugins/prompt-optimizer/index.ts",
    ".cursor/hooks.json", ".pi/extensions/prompt-optimizer.ts", ".gemini/settings.json",
    "CLAUDE.md", ".github/copilot-instructions.md", ".windsurf/rules/prompt-optimizer.md", "AGENTS.md",
  ].map((rel) => join(dir, rel));
  const missing = expected.filter((p) => !existsSync(p));
  if (missing.length) return fail(`Install missing files: ${missing.join(", ")}`, `Установка не создала файлы: ${missing.join(", ")}`);
  const gemini = JSON.parse(readFileSync(join(dir, ".gemini/settings.json"), "utf8"));
  if (!gemini.hooks?.BeforeAgent || !gemini.hooks?.BeforeModel) {
    return fail("Gemini hooks not registered", "Gemini hooks не зарегистрированы");
  }
  ok("Real all-eight-agent install and JSON-field preservation", "Реальная установка всех 8 агентов и сохранение JSON-полей");
}

function safetySmoke(dir) {
  const packageRootError = run(PYTHON, ["-B", "install.py", "--agents", "all", "--scope", "project", "--project", ROOT, "--auto"]);
  if (packageRootError.status === 0) {
    fail("Package-root installation was not rejected", "Установка в исходный каталог не была отклонена");
  } else if (!/package source tree|исходного каталога пакета/.test(packageRootError.stderr)) {
    fail("Package-root guard message missing", "Сообщение защиты package root отсутствует");
  }

  mkdirSync(join(dir, ".agents/skills/custom"), { recursive: true });
  mkdirSync(join(dir, ".opencode/commands"), { recursive: true });
  writeFileSync(join(dir, ".agents/skills/custom/SKILL.md"), "user skill must survive\n");
  writeFileSync(join(dir, ".opencode/commands/user-command.md"), "user command must survive\n");
  writeFileSync(join(dir, ".prompt-optimizer.json"), "{not valid json\n");
  const malformed = runInstall(["--agents", "opencode", "--scope", "project", "--project", dir, "--auto"], { expect: null });
  if (malformed.status === 0) fail("Malformed JSON was not rejected", "Некорректный JSON не был отклонён");
  if (readFileSync(join(dir, ".prompt-optimizer.json"), "utf8") !== "{not valid json\n") {
    fail("Malformed JSON was overwritten", "Поврежденный JSON был перезаписан");
  }

  writeFileSync(join(dir, ".prompt-optimizer.json"), "{}\n");
  runInstall(["--agents", "opencode,cursor,gemini", "--scope", "project", "--project", dir, "--auto", "--python-bin", PYTHON]);
  if (!existsSync(join(dir, ".agents/skills/custom/SKILL.md"))) fail("User skill was removed", "Пользовательский skill удален");
  if (readFileSync(join(dir, ".opencode/commands/user-command.md"), "utf8") !== "user command must survive\n") {
    fail("User command was removed", "Пользовательская команда удалена");
  }
  const configs = [join(dir, ".cursor/hooks.json"), join(dir, ".gemini/settings.json")];
  for (const name of configs) {
    const values = readFileSync(name, "utf8");
    if (!values.includes("prompt-optimizer")) fail(`Managed hook missing in ${name}`, `Управляемый hook отсутствует в ${name}`);
    if (values.includes("$HOME") || values.includes("$GEMINI_PROJECT_DIR")) fail(`Unexpanded variable in ${name}`, `Неразвёрнутая переменная в ${name}`);
  }
  runInstall(["--agents", "opencode,cursor,gemini", "--scope", "project", "--project", dir, "--auto", "--python-bin", PYTHON]);
  if (!existsSync(join(dir, ".agents/skills/custom/SKILL.md"))) fail("Repeat install removed user skill", "Повторная установка удалила пользовательский skill");
  ok("Installer safety, user-file preservation and idempotence", "Безопасность, сохранение пользовательских файлов и повторная установка");
}

function rollbackSmoke(dir) {
  mkdirSync(join(dir, ".gemini"), { recursive: true });
  writeFileSync(join(dir, ".prompt-optimizer.json"), "{}\n");
  writeFileSync(join(dir, ".gemini/settings.json"), "{broken\n");
  const result = runInstall(["--agents", "opencode,gemini", "--scope", "project", "--project", dir, "--auto"], { expect: null });
  if (result.status === 0) return fail("Failed install did not roll back", "Ошибка установки не вызвала rollback");
  if (existsSync(join(dir, ".agents/skills/prompt-optimizer/SKILL.md"))) fail("Rollback left installed skill", "Rollback оставил skill");
  if (existsSync(join(dir, ".prompt-optimizer-install.lock"))) fail("Rollback left install lock", "Rollback оставил install lock");
  if (readFileSync(join(dir, ".gemini/settings.json"), "utf8") !== "{broken\n") fail("Rollback changed original JSON", "Rollback изменил исходный JSON");
  ok("Rollback after partial installation", "Rollback после частичной установки");
}

function lifecycleSmoke(dir) {
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "AGENTS.md"), "# user content\n");
  runInstall(["--agents", "opencode,cursor,gemini", "--scope", "project", "--project", dir, "--auto", "--python-bin", PYTHON]);
  runInstall(["--scope", "project", "--project", dir, "--doctor"]);
  const both = runInstall(["--scope", "project", "--project", dir, "--doctor", "--uninstall"], { expect: null });
  if (both.status === 0) fail("Doctor accepted --uninstall together", "Doctor принял --uninstall вместе");
  runInstall(["--agents", "all", "--scope", "project", "--project", dir, "--uninstall", "--dry-run"]);
  runInstall(["--agents", "all", "--scope", "project", "--project", dir, "--uninstall"]);
  runInstall(["--agents", "all", "--scope", "project", "--project", dir, "--uninstall"]);
  if (readFileSync(join(dir, "AGENTS.md"), "utf8") !== "# user content\n") fail("Uninstall removed user text", "Uninstall удалил пользовательский текст");
  if (existsSync(join(dir, ".agents/skills/prompt-optimizer/SKILL.md"))) fail("Uninstall left shared skill", "Uninstall оставил shared skill");
  if (existsSync(join(dir, ".opencode/plugins/prompt-optimizer/index.ts"))) fail("Uninstall left OpenCode plugin", "Uninstall оставил OpenCode plugin");
  ok("Doctor, uninstall and dry-run", "Doctor, uninstall и dry-run");
}

function hygieneScript() {
  return `
import json, pathlib, re
root = pathlib.Path('.')
for p in root.rglob('*.json'):
    json.loads(p.read_text(encoding='utf-8'))
for p in root.rglob('*.jsonl'):
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.strip():
            json.loads(line)
reg = json.loads((root/'.agents/skills/prompt-optimizer/references/model-registry.json').read_text(encoding='utf-8'))
profiles = reg.get('profiles', [])
if len(profiles) != 20:
    raise SystemExit(f'expected 20 profiles, got {len(profiles)}')
ids = [x['id'] for x in profiles]
if len(set(ids)) != len(ids):
    raise SystemExit('duplicate profile IDs')
for x in profiles:
    ref = root/'.agents/skills/prompt-optimizer/references'/x['file']
    if not ref.is_file():
        raise SystemExit(f"missing reference: {x['file']}")
    text = ref.read_text(encoding='utf-8')
    if 'Provenance' not in text or ('Official source' not in text and 'Official sources' not in text):
        raise SystemExit(f"profile missing provenance/source: {x['file']}")
skill_root = root/'.agents/skills'
expected_overrides = {f"prompt-{item['id'].replace('.', '-')}" for item in profiles}
overrides = [p for p in skill_root.iterdir() if p.is_dir() and p.name in expected_overrides]
if len(overrides) != 20:
    raise SystemExit(f'expected 20 override skills, got {len(overrides)}')
for name in expected_overrides:
    if not (skill_root/name/'SKILL.md').is_file():
        raise SystemExit(f'missing {skill_root/name}/SKILL.md')
text = (root/'adapters/opencode/plugin/index.ts').read_text(encoding='utf-8')
block = text.split('type Profile =', 1)[1].split('type Settings', 1)[0]
router_ids = set(re.findall(r'"([^"]+)"', block))
missing = set(ids) - router_ids
extra = router_ids - set(ids)
if missing or extra:
    raise SystemExit(f'OpenCode profile mismatch missing={sorted(missing)} extra={sorted(extra)}')
ver = (root/'VERSION').read_text().strip()
package = json.loads((root/'package.json').read_text(encoding='utf-8'))
lock = json.loads((root/'package-lock.json').read_text(encoding='utf-8'))
if package.get('version') != f'{ver}.0' or lock.get('version') != f'{ver}.0':
    raise SystemExit(f'npm version mismatch for VERSION={ver}')
checks = [
    root/'.agents/skills/prompt-optimizer/SKILL.md',
    root/'adapters/opencode/plugin/index.ts',
    root/'adapters/pi/extensions/prompt-optimizer.ts',
    root/'adapters/gemini-cli/hooks/prompt-preflight.py',
    root/'auto/AGENTS.snippet.md',
    root/'auto/CLAUDE.snippet.md',
    root/'auto/GEMINI.snippet.md',
]
for p in checks:
    content = p.read_text(encoding='utf-8')
    if f'v{ver}' not in content and f'version: "{ver}"' not in content:
        raise SystemExit(f'version marker missing/outdated in {p}')
for p in list((root/'adapters').rglob('*')) + list((root/'auto').rglob('*')):
    if p.is_file():
        content = p.read_text(encoding='utf-8', errors='ignore')
        if any(stale in content for stale in ('prompt-optimizer-v5-2', 'prompt-optimizer-v5-3', 'prompt-optimizer-v5-4')):
            raise SystemExit(f'stale hook/plugin id in {p}')
bad = [p for p in root.rglob('*') if p.name == '__pycache__' or p.suffix == '.pyc']
if bad:
    raise SystemExit('archive hygiene: ' + ', '.join(map(str, bad)))
print('OK')
`;
}
