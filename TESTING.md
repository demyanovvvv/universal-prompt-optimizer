# v5.5 build verification

Verified on **2026-09-11** after the lifecycle, CI, schema, conformance, and eval audit.

## Interactive installer

- Bare `./install.sh` starts the English visual wizard.
- `./install.sh --ru`, `./install.sh ru`, `-ru`, and `--lang ru` select Russian; `--en` / `--lang en` force English.
- Agent auto-detection is the first step and detected agents are the default Enter selection.
- Zero-detection fallback automatically offers manual multi-select or ALL.
- Manual selection supports multiple numbers, `a` (all), `n` (none), `d` (reset to detected), and re-scan.
- Project/global location, automatic/native integration, AUTO/PREVIEW/OFF, all/first scope, quality gate, SKIP/GENERIC, backups, and dry-run are all configurable in-console.
- Final Review can return to agent selection, settings, or location before installation.

## Package/runtime checks

- Bash syntax: `install.sh`, `verify.sh`.
- Python syntax: installer, Cursor hook, Gemini CLI hook.
- JSON and JSONL syntax: every package file.
- TypeScript compile check: OpenCode plugin and Pi extension via the pinned local `tsc`
  when dependencies are installed, or a compatible global `tsc`.
- Registry alignment: exactly 20 model profiles and 20 manual override skills; OpenCode profile union matches registry IDs.
- Archive hygiene: no `__pycache__` / `.pyc`.
- Stale runtime IDs from v5.2/v5.3 rejected.
- All-eight-agent installation dry-run.
- Real project-scope installation for all eight agents.
- Existing Prompt Optimizer JSON plus unrelated custom fields survives an update.
- Cursor `scope=first`: first generation active, second inactive.
- Pi session state is keyed by session ID.
- Gemini CLI `scope=first`: first BeforeAgent active, subsequent user turn suppressed.
- Gemini CLI model observation: BeforeModel stores the exact `llm_request.model` without returning an `llm_request` override; a later BeforeAgent in the same session applies Gemini 3.8 Flash rules only on an unambiguous exact match.
- Gemini CLI unknown-model SKIP produces no optimizer context; GENERIC opts into neutral context.
- OpenCode router precedence includes all 20 profiles, `gpt-5.6 -> Sol`, Fable 5.1 before Fable 5, GLM Flash before GLM 5.3, and no guess for bare `deepseek-v4`.
- Registry conformance covers all 20 profiles, manual skills, OpenCode commands,
  OpenCode profile/hint maps, Pi model tokens, and canonical skill references.
- Twelve deterministic Python unit tests cover project/global lifecycle,
  managed blocks/hooks, modified
  file preservation, custom JSON
  preservation, schema versions, registry consistency, and eval fixtures.
- The static eval runner validates 35 cases and required adversarial coverage.
- `--doctor` is read-only; uninstall and uninstall dry-run are exercised after a
  real multi-agent installation and preserve surrounding user content.
- Cursor/Gemini runtime session maps are bounded and expire stale entries.

## One-command self-check

```bash
./verify.sh
./verify.sh --ru
```

## Representative installer checks

```bash
./install.sh --help
./install.sh --list-agents
./install.sh --detect-agents --dry-run --yes
./install.sh --agents opencode,cursor,pi --behavior preview --quality-gate on --dry-run --yes
./install.sh --agents all --behavior auto --prompt-scope all --quality-gate on --dry-run --yes
./install.sh --scope project --project . --doctor
./install.sh --scope project --project /tmp/upo-test --uninstall --dry-run --yes
npm test
npm run verify:ts
python -B evals/run.py
```
