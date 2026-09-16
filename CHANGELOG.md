# Changelog

## Unreleased

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
