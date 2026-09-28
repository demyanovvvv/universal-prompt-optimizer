# Changelog

## 5.10 — 2026-09-28

- Added a compact, color-coded OpenCode TUI status chip for AUTO, PREVIEW, OFF,
  GENERIC, and invalid-configuration states.
- Added native `Ctrl+P` → `Prompt Optimizer · Settings` controls with
  session, project, and global save targets.
- Added atomic, symlink-aware configuration writes that preserve unknown JSON
  fields and keep malformed configuration fail-safe.
- Added a per-session settings bridge shared by the TUI and OpenCode server
  plugin without triggering an extra model turn.
- Added `README.ru.md` and expanded OpenCode configuration documentation.

## 5.9 — 2026-09-27

- Reduced the user-facing command surface to `/prompt`, `/prompt-only`, and
  `/prompt-optimizer` for OpenCode.
- Removed model-specific OpenCode slash commands and manual model skills from
  user installations; model profiles remain available internally for exact
  automatic routing.
- Consolidated Pi session controls into `/prompt-optimizer auto|preview|off|status`.
- Made the neutral structured fallback the default for unknown or unavailable
  models, without guessing a vendor-specific profile.
- Added safe migration cleanup for unchanged legacy model commands and skills
  while preserving user-modified and third-party files.
- Updated installer, compatibility, README, and conformance documentation.

## 5.8 — 2026-09-27

- Fixed OpenCode server-plugin registration for nested local plugins so the
  native integration is loaded by OpenCode v1 while preserving user plugins.
- Fixed non-automatic installs so they do not silently install or register the
  native OpenCode server/TUI integration.
- Hardened uninstall for OpenCode plugin entries with options and separated
  server-plugin cleanup from owner-aware TUI cleanup.
- Added the `/prompt-optimizer` settings command, stable plugin IDs, bounded GPT-6 Sol
  repository-analysis guidance, and explicit advisory PREVIEW documentation.
- Added installer, lifecycle, metadata, runtime, and OpenCode regression tests.
- Reduced user-facing commands to general-purpose controls and removed model-specific
  slash commands and skills from installations. Exact model profiles remain internal
  routing data; unknown or unavailable models use the neutral structured fallback.
- Pi now exposes one `/prompt-optimizer auto|preview|off|status` settings command.
- Completed the v5.8 version alignment across capability metadata, manual
  profile skills, installer expectations, and adapter documentation so Ubuntu
  and Windows CI verify the same release contract.

## 5.7 — 2026-09-24

- Added the DeepSeek V4.1 Flash profile (`deepseek-v4.1-flash`, `deepseek-flash`)
  with official thinking/tool-call/JSON/vision guidance, generation-safe
  OpenCode/Pi routing ahead of the legacy V4 Flash regex, eval coverage, and a
  manual override skill/command. Preserved V4 Flash and V4 Pro profiles and
  aliases for compatibility.

## 5.6 — 2026-09-24

- Rebuilt the installer around a single declarative planner/executor shared by
  every adapter for project and global scopes, split into the `installer` package
  (`planning`, `executor`, `lifecycle`, `content`, `transaction`, `locking`,
  `catalog`).
- Made `uninstall` declarative via `build_uninstall_plan` and fully transactional,
  so a failure rolls back partial removals instead of leaving a half-removed
  installation; `doctor` gained authoritative config and managed-block diagnostics
  backed by the same managed-path map.
- Consolidated package verification into `tools/selfcheck.py` with thin bash and
  Node entry points, and reported corrupted managed JSON as a localized error
  instead of a raw traceback.
- Added the Claude Opus 5.5 profile, exact `claude-opus-5-5` routing, Claude Code best-practice guidance, and separate Opus 5.5 manual/OpenCode overrides while preserving Opus 5 compatibility.

- Added GPT-6 Sol and GPT-6 Luna as the standard `sol`/`luna` profiles and
  updated their prompting guidance from the GPT-6 family guide. Preserved
  versioned GPT-5.6 Sol/Luna profiles and aliases for compatibility, added
  generation-safe OpenCode/Pi routing, and documented GPT-6 runtime settings.

- Added versioned deterministic/provider/matrix/comparison report schemas and a
  dependency-free saved-report validator.
- Added deterministic required/forbidden phrase rubrics, quality pass rates,
  bounded token/cost metrics, p50/p95 latency, and regression gates for quality,
  reliability, latency, cost, and fixture changes.
- Added recursive report redaction, an explicit OpenAI-compatible opt-in adapter,
  a local mock provider matrix command, and a manual mock-provider CI workflow.
- Consolidated package verification into the canonical Node 22 CI workflow,
  prevented Python bytecode from breaking archive hygiene, and aligned runtime
  TypeScript tests with the Node16 module resolver.
- Tightened OpenCode model routing to registry aliases only, preserving approved
  suffixes while refusing near-version and provider-name false matches.
- Preserved all ordered text parts from multipart user messages and delayed
  `scope=first` consumption until a supported model turn is actually processed.
- Added consequence-aware task signals for destructive/external work, plan-only
  intent, English/Russian migration and security terms, and explicit verification
  requests.
- Kept `qualityGate` string semantics consistent across native and legacy adapters;
   added executable decision contracts to the runtime evaluation suite.
- Added structured eval coverage reports and strict safety coverage checks to the
  package verification path and Linux/Windows GitHub Actions workflow.
- Added a separate native OpenCode TUI plugin with compact status indicators,
  command-palette/slash controls, and `Ctrl+Shift+P` on-demand access.
- Added OpenCode task-aware `adaptive`, `pass`, `light`, and `full` quality gates
  with legacy boolean compatibility.
- Added privacy-safe bounded OpenCode session state, aggregate metrics, duplicate
  event protection, explain/status output, and ephemeral session overrides.
- Hardened installer TUI lifecycle cleanup and preserved legacy adapter boolean
  configuration while OpenCode receives the richer quality gate value.
- Added executable OpenCode runtime behavior tests for model resolution, task and
  quality-gate decisions, idempotent hook execution, scope, and bounded state.
- Added exact/pattern/unsupported model-resolution diagnostics, capped OpenCode
  process-local session state, explicit advisory PREVIEW reporting, and a TUI
  ownership marker for safe uninstall.

## 5.5 — 2026-09-11

- Added Linux/Windows GitHub Actions verification and a pinned npm/TypeScript
  development toolchain.
- Added safe `--doctor`/`--status` diagnostics and conservative `--uninstall`
  with dry-run, managed-hook cleanup, user-field preservation, and transactional
  rollback.
- Added configuration `schemaVersion: 1` and a public JSON Schema while keeping
  unrelated future/user fields intact.
- Added registry conformance, installer unit tests, and a deterministic 35-case
  eval runner with ambiguous-model, injection, destructive-action, and secret
  handling cases.
- Bounded Cursor and Gemini runtime state and added 30-day stale-session cleanup.
- Added MIT license, security/contribution guidance, and structured GitHub issue
  templates.

## 5.4 — 2026-09-06

- Consolidated all v5.0–v5.3 functionality into one fully audited release.
- Centralized package version in `VERSION`; removed stale v5.2/v5.3 runtime hook/plugin identifiers.
- Hardened `install.sh` auto-detection for Windows/Git Bash and refreshed detected-agent selection when project location changes.
- Installer now preserves unrelated/future fields in existing JSON configuration while updating Prompt Optimizer keys.
- Made Pi `scope=first` state session-scoped for parallel/resumed sessions.
- Reworked Gemini CLI routing so it never assumes Gemini 3.8 Flash: an observation-only `BeforeModel` hook records the resolved model, while `BeforeAgent` uses only trustworthy model identity and respects SKIP/GENERIC when unknown.
- Added review-screen warnings for agent-specific PREVIEW/FIRST/global-Cursor limitations.
- Added `verify.sh` package self-check and archive-hygiene checks.
- Removed the PowerShell installer from the final package; `install.sh` is the canonical interactive entry point.

## 5.3 — 2026-09-06

- Added full Russian localization for the `install.sh` visual wizard.
- `./install.sh --ru`, `./install.sh ru`, `-ru`, and `--lang ru` now launch/use Russian UI.
- Russian mode covers auto-detection, manual/all agent selection, settings, review, errors, and backend installation summary.
- English remains the default; `--en` / `--lang en` explicitly select English.

## 5.2 — 2026-09-06

- Reworked `install.sh` into a fully visual console wizard; CLI flags are no longer required for normal installation.
- Agent auto-detection now runs as the first interactive step. Detected agents are shown with `[x]` and are the default Enter action.
- Added explicit choices for **detected agents**, **ALL supported agents**, **manual multi-select**, and **re-scan**.
- If auto-detection finds nothing, the wizard automatically offers manual multi-select or ALL instead of failing.
- All installer settings are exposed interactively: project/global location, automatic/native integration, AUTO/PREVIEW/OFF, all/first prompt scope, PASS/LIGHT/FULL quality gate, unknown-model policy, backups, and dry-run.
- Added final review dashboard with the ability to return to agent selection, settings, or installation location before writing files.
- Kept optional CLI flags only for CI/repeatable automation.

## 5.1 — 2026-09-06

- `install.sh` is now the primary installer and launches an interactive setup wizard with no arguments.
- Agent selection supports auto-detect, all agents, or manual multi-select.
- Added installer-time settings for AUTO/PREVIEW/OFF, all/first scope, PASS/LIGHT/FULL quality gate, unknown-model fallback, backups, and dry-run.
- Added non-interactive flags (`--detect-agents`, `--agents`, `--quality-gate`, `--no-auto`, etc.) for scripts/CI.
- `qualityGate` is now persisted to shared/OpenCode config and honored by OpenCode, Pi, Cursor, Gemini CLI, and shared rule adapters.

## 5.0 — 2026-09-06
- Rebuilt optimizer around developer-guidance-first model profiles.
- Added Claude Fable 5.1 and refreshed all previously supported profiles.
- Added PASS/LIGHT/FULL positive-value quality gate.
- Replaced first-turn default with AUTO/all (first remains optional).
- Added AUTO / PREVIEW / OFF behavior.
- PREVIEW uses native confirmation where the agent exposes it and never assumes approval.
- Separated prompt shaping from reasoning/thinking/history/sampling/cache/tool-loop harness settings.
- Added exact runtime model routing for OpenCode and Pi; Cursor gets a per-generation exact-model state bridge.
- Added provenance registry and official-source inventory.
- Added v5 installer and migration guide.
- Expanded eval cases for prompt inflation, scope drift, required verification, preview safety and router precedence.
