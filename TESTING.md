# v5.6 build verification

Verified on **2026-09-16** after the lifecycle, CI, schema, conformance, and eval audit.

## Interactive installer

- Bare `./install.sh` starts the English visual wizard.
- `./install.sh --ru`, `./install.sh ru`, `-ru`, and `--lang ru` select Russian; `--en` / `--lang en` force English.
- Agent auto-detection is the first step and detected agents are the default Enter selection.
- Zero-detection fallback automatically offers manual multi-select or ALL.
- Manual selection supports multiple numbers, `a` (all), `n` (none), `d` (reset to detected), and re-scan.
- Project/global location, automatic/native integration, AUTO/PREVIEW/OFF, all/first scope, quality gate, SKIP/GENERIC, backups, and dry-run are all configurable in-console.
- Final Review can return to agent selection, settings, or location before installation.

## Package/runtime checks

The managed adapter list lives in `adapters/manifest.json`; Python managed
configuration rules live in `config_contract.py`, with an equivalent pure
TypeScript contract in `adapters/opencode/plugin/config-contract.ts`.
`npm run check:model-registry` checks that the installed OpenCode routing data
was generated from `.agents/skills/prompt-optimizer/references/model-registry.json`.

The CI-equivalent local sequence is:

```bash
npm ci
npm run check:model-registry
npm test
npm run verify:ts
npm run test:registry
npm run test:adapters
npm run test:evals:strict
npm run test:evals:mock
npm run test:evals:baseline
npm run verify          # portable: Node + Python only
npm run verify:bash     # canonical bash script (Linux/macOS/Git Bash)
```

Both `verify.mjs` and `verify.sh` are thin launchers over a single source of
truth, `tools/selfcheck.py`, which holds every cross-platform check. Each
launcher only adds its environment-specific step: the Node launcher adds the
TypeScript build and OpenCode runtime tests, the Bash launcher adds `bash -n`.
`npm run verify` therefore runs identically on Windows without WSL; bash-only
checks are skipped with a warning when bash is unavailable and run under
`npm run verify:bash`. Shared checks can also be run directly, for example
`python tools/selfcheck.py installer-lifecycle`.

The canonical `CI` GitHub Actions workflow runs the same checks on Ubuntu and
Windows. It sets `PYTHONDONTWRITEBYTECODE=1` before Python checks so archive
hygiene remains deterministic. Windows runs the portable self-check; Linux runs
both the portable and bash self-checks.

- Bash syntax: `install.sh`, `verify.sh`.
- Python syntax: installer, Cursor hook, Gemini CLI hook.
- JSON and JSONL syntax: every package file.
- TypeScript compile check: OpenCode plugin and Pi extension via the pinned local `tsc`
  when dependencies are installed, or a compatible global `tsc`.
- Registry alignment: exactly 23 model profiles and 23 manual override skills; OpenCode profile union matches registry IDs.
- Archive hygiene: no `__pycache__` / `.pyc`.
- Stale runtime IDs from v5.2/v5.3 rejected.
- All-eight-agent installation dry-run.

## Provider evaluation workflow

The manual mock workflow produces a validated `matrix.json` artifact without
network access or secrets. It then compares that matrix against the committed
golden baseline (`evals/baselines/matrix.json`) with `evals.baseline_gate`, so a
regression in fixture coverage, mode joining, quality scoring, or report assembly
fails the workflow. Because the mock matrix is deterministic, the baseline stores
a duration-free fingerprint: per case and mode it keeps status, quality counts,
and a SHA-256 of the response instead of the response text, plus the aggregate
run/quality/metrics/trace blocks and the fixture digest. Regenerate it only for
intentional changes with `npm run update:evals:baseline`.

The manual real-provider workflow accepts that artifact name and its workflow run
ID as the baseline, then writes the candidate report to the same `matrix.json`
path before comparing the selected mode.
- Real project-scope installation for all eight agents.
- Existing Prompt Optimizer JSON plus unrelated custom fields survives an update.
- Cursor `scope=first`: first generation active, second inactive.
- Pi session state is keyed by session ID.
- Gemini CLI `scope=first`: first BeforeAgent active, subsequent user turn suppressed.
- Gemini CLI model observation: BeforeModel stores the exact `llm_request.model` without returning an `llm_request` override; a later BeforeAgent in the same session applies Gemini 3.8 Flash rules only on an unambiguous exact match.
- Gemini CLI unknown-model SKIP produces no optimizer context; GENERIC opts into neutral context.
 - OpenCode router precedence includes all 23 profiles, GPT-6 `sol`/`luna`, versioned GPT-5.6 Sol/Luna, Opus 5.5 before Opus 5, Fable 5.1 before Fable 5, GLM Flash before GLM 5.3, and no guess for bare `deepseek-v4`.
 - Registry conformance covers all 23 profiles, manual skills, OpenCode commands,
  OpenCode profile/hint maps, Pi model tokens, and canonical skill references.
- Twelve deterministic Python unit tests cover project/global lifecycle,
  managed blocks/hooks, modified
  file preservation, custom JSON
  preservation, schema versions, registry consistency, and eval fixtures.
 - The static eval runner validates 50 cases, including GPT-6 defaults and versioned
  GPT-5.6 compatibility, Astra completion, zero-context PASS, progressive disclosure,
  and required adversarial coverage. Executable OpenCode and Pi hook tests verify
  generation separation, supported aliases and `-latest`, and rejection of
  unknown variants and provider-name matches.
- The runtime eval suite executes machine-checkable routing, task-signal, gate,
  and action contracts for the adversarial fixtures through the OpenCode runtime;
  it does not claim to score provider model answers.
- `--doctor` is read-only; uninstall and uninstall dry-run are exercised after a
  real multi-agent installation and preserve surrounding user content.
- Cursor/Gemini runtime session maps are bounded and expire stale entries.
- OpenCode TUI install/uninstall preserves user plugins and unrelated `tui.json`
  fields; uninstall dry-run leaves the config and managed tree unchanged while
  reporting the planned cleanup.
- OpenCode quality gates preserve exact `adaptive/pass/light/full` values while
  shared/legacy adapter config remains boolean-compatible.
- OpenCode session duplicate protection does not discard a new turn merely because
  its text matches the previous turn; the current prompt is reserved before the
  context hook and only committed as processed after the decision.

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
./install.sh --agents opencode,cursor,pi --behavior preview --quality-gate adaptive --dry-run --yes
./install.sh --agents all --behavior auto --prompt-scope all --quality-gate adaptive --dry-run --yes
./install.sh --scope project --project . --doctor
./install.sh --scope project --project /tmp/upo-test --uninstall --dry-run --yes
npm test
npm run verify:ts
python -B evals/run.py
```
