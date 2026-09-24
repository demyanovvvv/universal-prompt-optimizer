#!/usr/bin/env python3
"""Shared portable self-checks for Universal Prompt Optimizer.

This module is the single source of truth for the cross-platform verification
steps used by both ``verify.mjs`` (Node launcher) and ``verify.sh`` (Bash
launcher). Each launcher only adds its own language-specific syntax check; all
package, conformance, runtime, installer and lifecycle checks live here.

Run ``python tools/selfcheck.py --help`` for the available subcommands, or
``python tools/selfcheck.py all`` to run every check in order.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORE_START = "<!-- prompt-optimizer:auto:start -->"
IGNORE_END = "<!-- prompt-optimizer:auto:end -->"


def _say(label: str, passed: bool, detail: str = "") -> int:
    stream = sys.stdout if passed else sys.stderr
    status = "[OK]" if passed else "[FAIL]"
    print(f"{status} {label}", file=stream)
    if not passed and detail:
        print(detail, file=stream)
    return 0 if passed else 1


def _run(command: list[str], *, input_text: str | None = None, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        command, cwd=cwd, env=env, input=input_text, capture_output=True, text=True,
    )


def _python() -> str:
    for candidate in (os.environ.get("PYTHON_BIN"), "python3", "python", "py"):
        if not candidate:
            continue
        probe = _run([candidate, "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"])
        if probe.returncode == 0:
            return candidate
    raise SystemExit("Python 3.10+ is required")


PYTHON = _python()


def python_syntax() -> tuple[bool, str]:
    import ast

    targets = [
        ROOT / "config_contract.py",
        ROOT / "install.py",
        ROOT / "tools/sync_model_registry.py",
        *sorted((ROOT / "installer").glob("*.py")),
        *sorted((ROOT / "evals").glob("*.py")),
        *sorted((ROOT / "tools").glob("*.py")),
        ROOT / "adapters/cursor/hooks/prompt-optimizer-state.py",
        ROOT / "adapters/gemini-cli/hooks/prompt-preflight.py",
    ]
    for path in targets:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path.relative_to(ROOT)))
    return True, ""


def package_hygiene() -> tuple[bool, str]:
    for path in ROOT.rglob("*.json"):
        if "node_modules" in path.parts:
            continue
        json.loads(path.read_text(encoding="utf-8"))
    for path in ROOT.rglob("*.jsonl"):
        if "node_modules" in path.parts:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                json.loads(line)
    manifest = json.loads((ROOT / "adapters/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1 or not isinstance(manifest.get("adapters"), list):
        return False, "invalid adapter manifest"
    if len(manifest["adapters"]) != 8 or len(set(manifest["adapters"])) != 8:
        return False, "adapter manifest must contain eight unique adapters"
    registry = json.loads((ROOT / ".agents/skills/prompt-optimizer/references/model-registry.json").read_text(encoding="utf-8"))
    profiles = registry.get("profiles", [])
    if len(profiles) != 24:
        return False, f"expected 24 profiles, got {len(profiles)}"
    ids = [item["id"] for item in profiles]
    if len(set(ids)) != len(ids):
        return False, "duplicate profile IDs"
    references = ROOT / ".agents/skills/prompt-optimizer/references"
    for item in profiles:
        reference = references / item["file"]
        if not reference.is_file():
            return False, f"missing reference: {item['file']}"
        text = reference.read_text(encoding="utf-8")
        if "Provenance" not in text or ("Official source" not in text and "Official sources" not in text):
            return False, f"profile missing provenance/source: {item['file']}"
    skill_root = ROOT / ".agents/skills"
    expected_overrides = {f"prompt-{item['id'].replace('.', '-')}" for item in profiles}
    overrides = [p for p in skill_root.iterdir() if p.is_dir() and p.name in expected_overrides]
    if len(overrides) != 24:
        return False, f"expected 24 override skills, got {len(overrides)}"
    for name in expected_overrides:
        if not (skill_root / name / "SKILL.md").is_file():
            return False, f"missing {skill_root / name}/SKILL.md"
    contract = json.loads((ROOT / "adapters/opencode/plugin/profile-contract.json").read_text(encoding="utf-8"))
    expected_contract = [{"id": item["id"], "aliases": item["aliases"]} for item in profiles]
    if contract.get("schemaVersion") != 1 or contract.get("profiles") != expected_contract:
        return False, "OpenCode profile contract mismatch"
    routing = (ROOT / "adapters/opencode/plugin/model-registry.ts").read_text(encoding="utf-8")
    if "Generated by tools/sync_model_registry.py" not in routing:
        return False, "OpenCode model routing artifact is not generated"
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    if package.get("version") != f"{version}.0" or lock.get("version") != f"{version}.0":
        return False, f"npm version mismatch for VERSION={version}"
    version_markers = [
        ROOT / ".agents/skills/prompt-optimizer/SKILL.md",
        ROOT / "adapters/opencode/plugin/index.ts",
        ROOT / "adapters/pi/extensions/prompt-optimizer.ts",
        ROOT / "adapters/gemini-cli/hooks/prompt-preflight.py",
        ROOT / "auto/AGENTS.snippet.md",
        ROOT / "auto/CLAUDE.snippet.md",
        ROOT / "auto/GEMINI.snippet.md",
    ]
    for path in version_markers:
        text = path.read_text(encoding="utf-8")
        if f"v{version}" not in text and f'version: "{version}"' not in text:
            return False, f"version marker missing/outdated in {path.relative_to(ROOT)}"
    for path in list((ROOT / "adapters").rglob("*")) + list((ROOT / "auto").rglob("*")):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(stale in text for stale in ("prompt-optimizer-v5-2", "prompt-optimizer-v5-3", "prompt-optimizer-v5-4")):
                return False, f"stale hook/plugin id in {path.relative_to(ROOT)}"
    bad = [p for p in ROOT.rglob("*") if p.name == "__pycache__" or p.suffix == ".pyc"]
    if bad:
        return False, "archive hygiene: " + ", ".join(str(p.relative_to(ROOT)) for p in bad)
    return True, ""


def generated_registry() -> tuple[bool, str]:
    result = _run([PYTHON, "-B", "tools/sync_model_registry.py", "--check"])
    return result.returncode == 0, result.stdout + result.stderr


def registry_conformance() -> tuple[bool, str]:
    result = _run([PYTHON, "-B", "tests/registry_conformance.py"])
    return result.returncode == 0, result.stdout + result.stderr


def adapter_conformance() -> tuple[bool, str]:
    result = _run([PYTHON, "-B", "tests/adapter_conformance.py"])
    return result.returncode == 0, result.stdout + result.stderr


def evaluation_matrix() -> tuple[bool, str]:
    result = _run([PYTHON, "-B", "evals/run.py", "--strict-coverage"])
    return result.returncode == 0, result.stdout + result.stderr


def unit_tests() -> tuple[bool, str]:
    result = _run([PYTHON, "-B", "-m", "unittest", "discover", "-s", "tests"])
    return result.returncode == 0, result.stdout + result.stderr


def _install(args: list[str]) -> subprocess.CompletedProcess:
    return _run([PYTHON, "-B", "install.py", *args])


def cursor_smoke(directory: Path) -> tuple[bool, str]:
    (directory / ".cursor").mkdir(parents=True, exist_ok=True)
    (directory / ".prompt-optimizer.json").write_text(
        '{"behavior":"auto","scope":"first","qualityGate":true,"unsupportedModel":"skip"}\n', encoding="utf-8")
    hook = ROOT / "adapters/cursor/hooks/prompt-optimizer-state.py"

    def payload(generation: str) -> str:
        return json.dumps({
            "conversation_id": "c1", "generation_id": generation, "model": "claude-opus-5",
            "model_id": "claude-opus-5", "model_params": [], "workspace_roots": [str(directory)],
        }) + "\n"

    _run([PYTHON, "-B", str(hook)], input_text=payload("g1"))
    state = json.loads((directory / ".cursor/.prompt-optimizer-runtime.json").read_text(encoding="utf-8"))
    if state.get("active") is not True:
        return False, "Cursor scope=first: first turn not active"
    _run([PYTHON, "-B", str(hook)], input_text=payload("g2"))
    state = json.loads((directory / ".cursor/.prompt-optimizer-runtime.json").read_text(encoding="utf-8"))
    if state.get("active") is not False:
        return False, "Cursor scope=first: second turn still active"
    if state.get("sessions", {}).get("c1", {}).get("generation_id") != "g2":
        return False, "Cursor scope=first: state not updated"
    return True, ""


def gemini_smoke(directory: Path) -> tuple[bool, str]:
    (directory / ".gemini").mkdir(parents=True, exist_ok=True)
    hook = ROOT / "adapters/gemini-cli/hooks/prompt-preflight.py"
    config = directory / ".prompt-optimizer.json"

    def before_agent(session: str, prompt: str) -> str:
        return json.dumps({"session_id": session, "cwd": str(directory), "hook_event_name": "BeforeAgent", "prompt": prompt}) + "\n"

    config.write_text('{"behavior":"auto","scope":"all","qualityGate":true,"unsupportedModel":"skip"}\n', encoding="utf-8")
    result = _run([PYTHON, "-B", str(hook)], input_text=before_agent("gs1", "Fix it"))
    out = json.loads(result.stdout)
    if out["hookSpecificOutput"]["additionalContext"] != "":
        return False, "Gemini SKIP: unknown model injected context"
    before_model = json.dumps({"session_id": "gs1", "cwd": str(directory), "hook_event_name": "BeforeModel",
                               "llm_request": {"model": "gemini-3.8-flash", "messages": [], "config": {}}}) + "\n"
    result = _run([PYTHON, "-B", str(hook)], input_text=before_model)
    out = json.loads(result.stdout)
    if out.get("hookSpecificOutput", {}).get("llm_request"):
        return False, "Gemini BeforeModel: overrode request"
    state = json.loads((directory / ".gemini/.prompt-optimizer-model-state.json").read_text(encoding="utf-8"))
    if state["gs1"]["model"] != "gemini-3.8-flash":
        return False, "Gemini BeforeModel: model not recorded"
    result = _run([PYTHON, "-B", str(hook)], input_text=before_agent("gs1", "Fix it"))
    out = json.loads(result.stdout)
    if "Gemini 3.8 Flash" not in out["hookSpecificOutput"]["additionalContext"]:
        return False, "Gemini exact model not resolved"
    config.write_text('{"behavior":"auto","scope":"all","qualityGate":true,"unsupportedModel":"generic"}\n', encoding="utf-8")
    result = _run([PYTHON, "-B", str(hook)], input_text=before_agent("gs2", "Fix it"))
    out = json.loads(result.stdout)
    if "neutral model-agnostic optimizer profile" not in out["hookSpecificOutput"]["additionalContext"]:
        return False, "Gemini GENERIC: neutral context missing"

    (directory / ".gemini/.prompt-optimizer-session-state.json").unlink(missing_ok=True)
    (directory / ".gemini/.prompt-optimizer-model-state.json").unlink(missing_ok=True)
    config.write_text('{"behavior":"auto","scope":"first","qualityGate":true,"unsupportedModel":"skip"}\n', encoding="utf-8")
    env = {**_environ(), "GEMINI_MODEL": "gemini-3.8-flash"}
    first = _run_env([PYTHON, "-B", str(hook)], env, before_agent("gf1", "Fix it"))
    second = _run_env([PYTHON, "-B", str(hook)], env, before_agent("gf1", "Again"))
    first_text = json.loads(first.stdout)["hookSpecificOutput"]["additionalContext"]
    second_text = json.loads(second.stdout)["hookSpecificOutput"]["additionalContext"]
    if "Gemini 3.8 Flash" not in first_text or second_text != "":
        return False, "Gemini scope=first incorrect"

    config.write_text("{broken\n", encoding="utf-8")
    result = _run([PYTHON, "-B", str(hook)], input_text=before_agent("bad1", "Do not optimize"))
    out = json.loads(result.stdout)
    if out["hookSpecificOutput"]["additionalContext"] != "":
        return False, "Malformed config did not fail safe"
    return True, ""


def _environ() -> dict[str, str]:
    return {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def _run_env(command: list[str], env: dict[str, str], input_text: str) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, env=env, input=input_text, capture_output=True, text=True)


def install_dry_run() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as raw:
        result = _install(["--agents", "all", "--scope", "project", "--project", str(Path(raw) / "project"),
                           "--auto", "--behavior", "auto", "--prompt-scope", "all", "--quality-gate", "on",
                           "--unsupported-model", "skip", "--dry-run"])
        return result.returncode == 0, result.stdout + result.stderr


def _runtime_smoke() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        for check, name in ((cursor_smoke, "cursor"), (gemini_smoke, "gemini")):
            passed, detail = check(base / name)
            if not passed:
                return False, detail
    return True, ""


def real_install_smoke() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw) / "real"
        directory.mkdir(parents=True)
        config = directory / ".prompt-optimizer.json"
        config.write_text('{"customField":"keep-me","behavior":"off"}\n', encoding="utf-8")
        result = _install(["--agents", "all", "--scope", "project", "--project", str(directory), "--auto",
                           "--behavior", "auto", "--prompt-scope", "all", "--quality-gate", "on",
                           "--unsupported-model", "skip"])
        if result.returncode != 0:
            return False, result.stdout + result.stderr
        value = json.loads(config.read_text(encoding="utf-8"))
        if value.get("customField") != "keep-me" or value.get("behavior") != "auto":
            return False, "Install did not preserve custom JSON fields"
        expected = [
            ".agents/skills/prompt-optimizer/SKILL.md", ".opencode/plugins/prompt-optimizer/index.ts",
            ".cursor/hooks.json", ".pi/extensions/prompt-optimizer.ts", ".gemini/settings.json",
            "CLAUDE.md", ".github/copilot-instructions.md", ".windsurf/rules/prompt-optimizer.md", "AGENTS.md",
        ]
        missing = [rel for rel in expected if not (directory / rel).exists()]
        if missing:
            return False, f"Install missing files: {', '.join(missing)}"
        gemini = json.loads((directory / ".gemini/settings.json").read_text(encoding="utf-8"))
        if not gemini.get("hooks", {}).get("BeforeAgent") or not gemini.get("hooks", {}).get("BeforeModel"):
            return False, "Gemini hooks not registered"
    return True, ""


def safety_smoke() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw) / "safety"
        package_root = _install(["--agents", "all", "--scope", "project", "--project", str(ROOT), "--auto"])
        if package_root.returncode == 0:
            return False, "Package-root installation was not rejected"
        if not re.search("package source tree|исходного каталога пакета", package_root.stderr):
            return False, "Package-root guard message missing"
        (directory / ".agents/skills/custom").mkdir(parents=True)
        (directory / ".opencode/commands").mkdir(parents=True)
        (directory / ".agents/skills/custom/SKILL.md").write_text("user skill must survive\n", encoding="utf-8")
        (directory / ".opencode/commands/user-command.md").write_text("user command must survive\n", encoding="utf-8")
        config = directory / ".prompt-optimizer.json"
        config.write_text("{not valid json\n", encoding="utf-8")
        malformed = _install(["--agents", "opencode", "--scope", "project", "--project", str(directory), "--auto"])
        if malformed.returncode == 0:
            return False, "Malformed JSON was not rejected"
        if config.read_text(encoding="utf-8") != "{not valid json\n":
            return False, "Malformed JSON was overwritten"
        config.write_text("{}\n", encoding="utf-8")
        _install(["--agents", "opencode,cursor,gemini", "--scope", "project", "--project", str(directory), "--auto", "--python-bin", PYTHON])
        if not (directory / ".agents/skills/custom/SKILL.md").exists():
            return False, "User skill was removed"
        if (directory / ".opencode/commands/user-command.md").read_text(encoding="utf-8") != "user command must survive\n":
            return False, "User command was removed"
        for name in (".cursor/hooks.json", ".gemini/settings.json"):
            values = (directory / name).read_text(encoding="utf-8")
            if "prompt-optimizer" not in values:
                return False, f"Managed hook missing in {name}"
            if "$HOME" in values or "$GEMINI_PROJECT_DIR" in values:
                return False, f"Unexpanded variable in {name}"
        _install(["--agents", "opencode,cursor,gemini", "--scope", "project", "--project", str(directory), "--auto", "--python-bin", PYTHON])
        if not (directory / ".agents/skills/custom/SKILL.md").exists():
            return False, "Repeat install removed user skill"
    return True, ""


def rollback_smoke() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw) / "rollback"
        (directory / ".gemini").mkdir(parents=True)
        (directory / ".prompt-optimizer.json").write_text("{}\n", encoding="utf-8")
        settings = directory / ".gemini/settings.json"
        settings.write_text("{broken\n", encoding="utf-8")
        result = _install(["--agents", "opencode,gemini", "--scope", "project", "--project", str(directory), "--auto"])
        if result.returncode == 0:
            return False, "Failed install did not roll back"
        if (directory / ".agents/skills/prompt-optimizer/SKILL.md").exists():
            return False, "Rollback left installed skill"
        if (directory / ".prompt-optimizer-install.lock").exists():
            return False, "Rollback left install lock"
        if settings.read_text(encoding="utf-8") != "{broken\n":
            return False, "Rollback changed original JSON"
    return True, ""


def lifecycle_smoke() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw) / "lifecycle"
        directory.mkdir(parents=True)
        (directory / "AGENTS.md").write_text("# user content\n", encoding="utf-8")
        _install(["--agents", "opencode,cursor,gemini", "--scope", "project", "--project", str(directory), "--auto", "--python-bin", PYTHON])
        _install(["--scope", "project", "--project", str(directory), "--doctor"])
        both = _install(["--scope", "project", "--project", str(directory), "--doctor", "--uninstall"])
        if both.returncode == 0:
            return False, "Doctor accepted --uninstall together"
        _install(["--agents", "all", "--scope", "project", "--project", str(directory), "--uninstall", "--dry-run"])
        _install(["--agents", "all", "--scope", "project", "--project", str(directory), "--uninstall"])
        _install(["--agents", "all", "--scope", "project", "--project", str(directory), "--uninstall"])
        if "# user content" not in (directory / "AGENTS.md").read_text(encoding="utf-8"):
            return False, "Uninstall removed user text"
        if (directory / ".agents/skills/prompt-optimizer/SKILL.md").exists():
            return False, "Uninstall left shared skill"
        if (directory / ".opencode/plugins/prompt-optimizer/index.ts").exists():
            return False, "Uninstall left OpenCode plugin"
    return True, ""


def installer_lifecycle() -> tuple[bool, str]:
    for check in (install_dry_run, _runtime_smoke, real_install_smoke, safety_smoke, rollback_smoke, lifecycle_smoke):
        passed, detail = check()
        if not passed:
            return False, detail
    return True, ""


ALL_CHECKS = {
    "python-syntax": python_syntax,
    "package-hygiene": package_hygiene,
    "generated-registry": generated_registry,
    "registry-conformance": registry_conformance,
    "adapter-conformance": adapter_conformance,
    "evaluation-matrix": evaluation_matrix,
    "unit-tests": unit_tests,
    "installer-lifecycle": installer_lifecycle,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Universal Prompt Optimizer shared self-check")
    parser.add_argument("check", nargs="?", default="all", choices=[*ALL_CHECKS, "all"])
    args = parser.parse_args(argv)
    names = list(ALL_CHECKS) if args.check == "all" else [args.check]
    failed = 0
    for name in names:
        passed, detail = ALL_CHECKS[name]()
        failed += _say(name, passed, detail)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
