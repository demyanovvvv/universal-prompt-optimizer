#!/usr/bin/env node
/**
 * Portable self-check for Universal Prompt Optimizer.
 *
 * This is a thin Node launcher. All cross-platform checks live in a single
 * source of truth, `tools/selfcheck.py`, which is also used by `verify.sh`.
 * This launcher adds only the environment-specific steps that Python cannot do
 * portably: the Bash syntax check (when bash is present) and the TypeScript
 * build plus OpenCode runtime tests (when tsc is present).
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
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
  return spawnSync(command, args, {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", ...(options.env ?? {}) },
    input: options.input,
    maxBuffer: 64 * 1024 * 1024,
  });
}

function checkPython() {
  for (const candidate of [process.env.PYTHON_BIN, "python3", "python", "py"].filter(Boolean)) {
    const probe = run(candidate, ["-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"]);
    if (probe.status === 0) return candidate;
  }
  return null;
}

function hasBash() {
  return run("bash", ["-c", "exit 0"]).status === 0;
}

function findTsc() {
  const local = join(ROOT, "node_modules", "typescript", "bin", "tsc");
  if (existsSync(local)) return { command: local, kind: "node" };
  const localCmd = join(ROOT, "node_modules", ".bin", "tsc.cmd");
  if (process.platform === "win32" && existsSync(localCmd)) return { command: localCmd, kind: "cmd" };
  if (run("tsc", ["--version"]).status === 0) return { command: "tsc", kind: "bin" };
  return null;
}

function runTsc(tsc, args) {
  if (tsc.kind === "node") return run(process.execPath, [tsc.command, ...args]);
  if (tsc.kind === "cmd") return run("cmd.exe", ["/d", "/s", "/c", tsc.command, ...args]);
  return run(tsc.command, args);
}

const VERSION = run(process.execPath, ["-e", "process.stdout.write(require('fs').readFileSync('VERSION','utf8').trim())"]).stdout;
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

// 2. Shared cross-platform checks (single source of truth).
const SHARED_CHECKS = [
  ["python-syntax", "Python syntax", "Синтаксис Python"],
  ["package-hygiene", "JSON, registry, 24 profiles/override skills, version alignment and package hygiene",
    "JSON, registry, 24 профиля/override skills, версии и чистота пакета"],
  ["generated-registry", "Generated model registry artifacts", "Сгенерированные model registry artifacts"],
  ["registry-conformance", "Registry and adapter conformance", "Согласованность registry и адаптеров"],
  ["adapter-conformance", "Adapter capability matrix conformance", "Согласованность adapter capability matrix"],
  ["evaluation-matrix", "Static evaluation matrix", "Статическая матрица evals"],
  ["unit-tests", "Installer, registry and eval unit tests", "Unit-тесты installer, registry и evals"],
  ["installer-lifecycle", "Installer and lifecycle smoke tests", "Smoke-тесты installer и lifecycle"],
];
for (const [name, en, ru] of SHARED_CHECKS) {
  const result = run(PYTHON, ["-B", "tools/selfcheck.py", name]);
  if (result.status === 0) ok(en, ru);
  else fail(`selfcheck ${name}: ${result.stdout}${result.stderr}`, `selfcheck ${name}: ${result.stdout}${result.stderr}`);
}

// 3. TypeScript syntax and OpenCode runtime behavior (requires tsc).
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
      ".tmp-tests/opencode/tests/model-routing.test.js",
    ]);
    if (runtime.status === 0) ok("OpenCode runtime behavior tests", "Поведенческие тесты OpenCode runtime");
    else fail(`OpenCode runtime tests: ${runtime.stdout}${runtime.stderr}`, `Поведенческие тесты OpenCode: ${runtime.stdout}${runtime.stderr}`);
  } else {
    fail(`TypeScript test build: ${testTs.stdout}${testTs.stderr}`, `TypeScript test build: ${testTs.stdout}${testTs.stderr}`);
  }
} else {
  warn("tsc not found — TypeScript syntax check skipped", "tsc не найден — проверка синтаксиса TypeScript пропущена");
}

if (failures === 0) {
  console.log(t("All checks passed.", "Все проверки завершены успешно."));
  process.exit(0);
}
console.error(t(`${failures} check(s) failed.`, `${failures} проверок завершились неудачно.`));
process.exit(1);
