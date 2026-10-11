# Universal Prompt Optimizer v5.12

**Language:** English · [Русский README](README.ru.md)

**Quick links:** [Installation](#installation) · [Commands](#universal-commands) · [OpenCode settings](#opencode-tui-controls) · [Compatibility](COMPATIBILITY.md) · [Configuration guide](DECISION-GUIDE.md) · [Changelog](CHANGELOG.md)

Model-aware prompt optimization for eight coding agents. Write a natural request;
the active agent applies only useful guidance for its resolved model, preserves
your intent and constraints, and executes in the same model turn.

The goal is higher first-pass success, fewer scope errors and repair iterations,
and lower total tokens per completed task. No separate optimizer LLM call is required.

## Core capabilities

- **Adaptive preflight:** PASS keeps precise requests lean, LIGHT adds a missing
  boundary, and FULL builds a concise brief for complex tasks.
- **Exact model routing:** 26 internal profiles cover supported OpenAI, Claude,
  DeepSeek, GLM, Gemini, and other models. Unknown or ambiguous IDs follow the
  configured `generic` or `skip` policy without guessing a model variant.
- **AUTO / PREVIEW / OFF:** choose silent adaptation, review before execution,
  or disabled automatic optimization. PREVIEW guarantees depend on the host;
  OpenCode v1 provides advisory confirmation.
- **OpenCode controls:** a compact status indicator, a native command-palette
  menu with current setting values, and session/project/global save targets.
- **Local-only operation:** no telemetry or hidden network calls; prompt text is
  not persisted as metrics. Host permissions and user constraints remain authoritative.
- **Repeatable installation:** project/global installs, atomic writes, rollback,
  read-only diagnostics, and cleanup of stock legacy model commands while
  preserving custom instructions and unrelated commands.

## Supported agents

OpenCode, Pi, Gemini CLI, Cursor, Claude Code, OpenAI Codex, GitHub Copilot CLI,
and Windsurf. Native model visibility and PREVIEW capabilities vary by adapter;
see the [compatibility matrix](COMPATIBILITY.md).

## Universal commands

| Command | Purpose |
|---|---|
| `/prompt <task>` | Detect the active model, optimize the request, and execute the task. |
| `/prompt-only <task>` | Return only the optimized reusable prompt. |
| `/prompt-optimizer` | Inspect or change optimizer settings. |

OpenCode installs only these three general-purpose command files. Native TUI
controls also expose `/po` and `/po-status`. Separate Opus, Fable, and other
model-specific commands are unnecessary: profiles are selected internally.
Reinstall in the same scope to clean up stock legacy command files, then restart
OpenCode to refresh the command list. User-modified and third-party commands are preserved.

## Quick start

```bash
chmod +x install.sh verify.sh
./install.sh          # English wizard
./install.sh --ru     # Russian wizard
./verify.sh --ru      # optional package self-check
```

## Models

### OpenAI
GPT-6 Astra, GPT-6.1 Sol (`gpt-6.1-sol`), GPT-6 Sol (`gpt-6-sol`, short alias `sol`), and GPT-6 Luna (`gpt-6-luna`, short alias `luna`). GPT-5.6 Terra remains `terra`; legacy GPT-5.6 Sol/Luna remain available as `gpt-5.6-sol` / `gpt-5.6-luna`, with `gpt-5.6` preserved as a GPT-5.6 Sol alias.

**Migration:** model-specific slash commands and manual override skills are no longer installed. Model aliases remain internal routing data for automatic exact-model selection. Unknown or unavailable models use the neutral structured fallback and do not get assigned a vendor-specific profile.

### Z.ai / GLM
GLM-5.2; GLM-5.3; GLM-5.3-Flash.

### DeepSeek
DeepSeek V4.1 Flash; DeepSeek V4 Flash; DeepSeek V4 Pro.

V4.1 Flash is the canonical `deepseek-flash` model. The retired `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` IDs still resolve to it on the official API, so they map to the V4.1 Flash profile for routing; `deepseek-v4-pro` remains its own profile. A bare `deepseek-v4` is ambiguous and follows the configured unsupported-model policy.

### Anthropic / Claude
  Claude Fable 5.1; Fable 5; Opus 5.5; Opus 5; Opus 4.8; Sonnet 5.5; Sonnet 5.

### Other
Kimi K3; Muse Spark 1.3; Hy4-preview; Qwen3.8-Max (including 0902/dated aliases); Gemini 3.8 Flash; Grok 4.6.

## Modes

Shared config (project):

`.prompt-optimizer.json`

### AUTO — recommended
```json
{
  "schemaVersion": 1,
  "behavior": "auto",
  "scope": "all",
  "qualityGate": "adaptive",
  "unsupportedModel": "generic"
}
```

### PREVIEW
```json
{
  "schemaVersion": 1,
  "behavior": "preview",
  "scope": "all",
  "qualityGate": "adaptive",
  "unsupportedModel": "generic"
}
```

### OFF
```json
{
  "schemaVersion": 1,
  "behavior": "off",
  "scope": "all",
  "qualityGate": "adaptive",
  "unsupportedModel": "generic"
}
```

`scope: "first"` restores first-user-turn-only behavior from v4.

Shared `.prompt-optimizer.json` and OpenCode config preserve the selected
`qualityGate=adaptive|pass|light|full`. Legacy boolean `true` remains accepted
as adaptive and `false` as force-normalize (`pass`). Instruction adapters read
current project settings before global settings, with installer defaults as
fallback. Gemini automatic preflight requires a per-turn hook eligibility signal.
Global Gemini hooks execute the home-installed script independently of project cwd.

For OpenCode, `adaptive` selects PASS for precise prompts, LIGHT for incomplete
or planning/research work, and FULL for complex, security-sensitive, migration,
or consequential work. `pass` is the legacy always-normalize mode; `light` and
`full` select those exact gate levels.

### OpenCode TUI controls

When automatic integration is enabled for OpenCode, the installer adds the
server plugin under `.opencode/plugins/prompt-optimizer/`, the native TUI plugin
under `.opencode/plugins/prompt-optimizer-tui/`, and registers the latter in
`.opencode/tui.json`. Global installation uses the corresponding paths under
`~/.config/opencode/`.

- `● PO AUTO`, `◐ PO PREVIEW`, `○ PO OFF`, and `◇ PO GENERIC` are compact,
  color-coded indicators. `! PO CONFIG` marks an invalid configuration and the
  safe OFF fallback. A trailing `*` marks a session override.
- `/prompt-optimizer status` shows resolved settings and privacy-safe counters.
- `/prompt-optimizer explain` shows the latest action and reason without prompt
  text or hidden reasoning.
- `/prompt-optimizer on|off|preview|first|all|pass|light|full|adaptive|reset`
  changes only the current OpenCode session; edit JSON explicitly for persistent
  configuration.
- `Ctrl+P` opens the OpenCode command palette, where the `Prompt Optimizer`
  group provides a structured menu, settings, and status. Each menu row shows the
  current value of that setting as a subtitle.
  `Ctrl+Shift+P` opens the settings dialog directly. Behavior, scope, quality gate, and
  unsupported-model handling can be saved to the current session, the project,
  or the global OpenCode configuration.

## How AUTO behaves

```text
natural user request
      ↓
resolved active model (where harness exposes it)
      ↓
quality gate: PASS / LIGHT / FULL
      ↓
model developer practices + task needs
      ↓
minimal optimized execution brief
      ↓
execute in the SAME model turn
```

No second “prompt rewriting model” call is required.

## Installation

### Commands at a glance

| Task | Linux / macOS | Windows PowerShell | Notes |
|---|---|---|---|
| English installation | `./install.sh` | `py -3 install.py --agents all --auto` | Choose local/project or global/current-user installation |
| Russian installation | `./install.sh --ru` | `py -3 install.ru.py --agents all --auto` | Same installer API and adapter contents |
| Non-interactive installation | `./install.sh --scope project --agents all --auto --yes` | `py -3 install.py --scope project --agents all --auto --yes` | Suitable for CI and scripts |
| Preview / dry-run | `./install.sh --agents all --dry-run --yes` | `py -3 install.py --agents all --dry-run --yes` | Shows planned changes without writing |
| Uninstall | `bash ./uninstall.sh` | `py -3 uninstall.py` | Choose local/global; removes package files, backups, state and managed blocks |
| Verification | `./verify.sh` | `py -3 tools/selfcheck.py` | Full project self-check; see checks below |

Python 3.10 or newer is required. On Linux and macOS, the shell launcher is
the recommended interactive entry point; on Windows, Python installation and
uninstallation ask for local/global scope and the project path. Explicit
`--scope project|global` or `--yes` skips that question; without a terminal the
default is project scope. To use the full settings wizard on Windows, run
`./install.sh` from Git Bash. Add `--lang ru` to `install.py` when a script
needs to select the Russian UI without using the dedicated wrapper.

### Updating and removing an installation

Re-run the installer from the new release folder in the **same scope** to update
to that folder's `VERSION`. It displays the previous and target versions and
replaces package files, including obsolete files recorded by earlier installs.
Python and non-wizard Bash runs retain installed adapters, native integration,
and current shared-config settings unless explicitly overridden. The full Bash
wizard applies the choices made in its review screen. No release is downloaded.

Installation metadata contains version, adapters, settings and package file
paths, never prompts: `.prompt-optimizer-install.json` in projects, or
`~/.config/prompt-optimizer/install.json` globally. Older installs without this
metadata are supported; their version is reported as not recorded until reinstall.

```bash
# Update the global installation from this release folder
bash ./install.sh --scope global --yes
# Remove the global installation without questions
bash ./uninstall.sh --scope global --yes
# Preview removal from a particular project
python install.py --uninstall --scope project --project /path/to/project --dry-run
```

On Windows use `py -3 install.py --scope global` to update and
`py -3 uninstall.py --scope global` to remove. Add `--lang ru` for Russian output.
Uninstall removes modified package-owned files, registrations, managed blocks,
installer backups, runtime state/locks, metadata and empty installation directories.
Unrelated files, hooks, JSON fields and text outside managed blocks are preserved.
Files created by the installer that contain only JSON scaffolding are removed;
pre-existing shared configuration files are retained. Repeated removal is safe.

### Normal installation — no flags

```bash
chmod +x install.sh
./install.sh
```

The wizard performs agent auto-detection first. A typical screen is:

```text
1/4  Agent auto-detection
------------------------------------------------------------
  [x] OpenCode               detected
  [ ] OpenAI Codex           not detected
  [x] Cursor                 detected
  [ ] Pi                     not detected
  [x] Claude Code            detected
  ...

Found: OpenCode, Cursor, Claude Code

  1) Install for detected agents  [recommended / Enter]
  2) Install for ALL supported agents
  3) Choose agents manually (multi-select)
  4) Re-scan
  q) Cancel
>
```

So the common case is just **Enter**: all agents actually found on the machine are preselected automatically. If no supported agent is detected, the installer does not fail; it immediately offers manual multi-select or installation for all supported agents.

The launcher checks Python and the adapter manifest before the wizard presents
adapter detection/selection, installation location, settings and final review.
Installation then prints a result summary. Cancellation
at a prompt exits without applying changes. Re-running the installer is
idempotent: managed entries are merged without duplicating them and unrelated
user content is preserved. Use `--dry-run` to preview either a first or repeat
installation.

### Manual multi-select

```text
1) [x] OpenCode
2) [ ] OpenAI Codex
3) [x] Cursor
4) [ ] Pi
5) [ ] Claude Code
6) [ ] Gemini CLI
7) [ ] GitHub Copilot CLI
8) [ ] Windsurf

a) Select ALL
n) Clear ALL
d) Reset to auto-detected
Enter) Continue with checked agents
```

You can toggle several numbers at once, for example `1 3 5 8`.

### All settings are available inside `install.sh`

The console wizard exposes all current installer settings:

1. **Installation location** — Project / Global and project path.
2. **Agent set** — detected / ALL / manual multi-select / re-scan.
3. **Automatic/native integration** — ON or OFF (skills/commands only).
4. **Behavior** — AUTO / PREVIEW / OFF.
5. **Prompt scope** — every user turn / first user turn only.
6. **Quality gate** — Adaptive (`PASS → LIGHT → FULL`), Pass (always normalize), Light, or Full.
7. **Unknown model** — SKIP model-specific adaptation / use GENERIC neutral profile.
8. **Backups** — ON / OFF.
9. **Dry-run** — write normally / show changes without writing.

The final review screen shows the complete configuration and lets you return to **agent selection**, **settings**, or **installation location** before pressing Enter to install.

### AUTO / PREVIEW / OFF

- **AUTO** — adapt silently only when useful, then execute.
- **PREVIEW** — show the optimized prompt first and request confirmation where the agent exposes a confirmation UI. This is a host-enforced execution barrier only when the selected agent explicitly provides one; otherwise it is model-guided and must be treated as advisory. OpenCode v1 currently uses the advisory form.
- **OFF** — keep the adapter installed but disable automatic optimization.

This is separate from **Automatic/native integration = OFF**, which installs only the shared skills/commands and does not install automatic hooks/plugins/rules at all.

### Optional advanced/CI flags

Normal users do not need these. They are retained for repeatable automation and CI only:

```bash
./install.sh --detect-agents --auto --behavior auto --yes
./install.sh --agents opencode,cursor,pi --behavior preview --yes
./install.sh --agents all --quality-gate adaptive --yes
```

Run `./install.sh --help` for the automation interface.

`install.py` is the non-interactive backend; `install.sh` provides the wizard.
On Windows, `install.ru.py` is a localized direct entry point to the same API.

### Diagnose and uninstall

```bash
./install.sh --scope project --project . --doctor
./install.sh --scope project --project . --uninstall --dry-run --yes
./install.sh --scope project --project . --uninstall --yes
```

Uninstall removes installer-owned files even when their contents were edited,
including installer backups. Managed Markdown blocks and hook entries are
removed without deleting surrounding user content or unrelated JSON fields.
Ambiguous pre-existing config containers such as a version-only `settings.json`
are retained. The OpenCode TUI copy carries a local ownership marker so uninstall
does not claim a pre-existing plugin at the same conventional path. Re-running
install updates managed files to the current package version.

### Development checks

CI checks routing, adapter compatibility, installer lifecycle, and strict safety coverage
for synthetic prompt-injection, destructive-action, and secret-preservation fixtures.
See [TESTING.md](TESTING.md) for the full verification matrix.

```bash
npm install
npm run verify        # portable self-check (Node + Python, no bash/WSL needed)
npm run verify:bash   # canonical bash self-check (Linux/macOS/Git Bash)
npm test
npm run verify:ts
npm run test:runtime
python -B evals/run.py
```

### Choosing a configuration

See `DECISION-GUIDE.md` for a task-oriented guide to picking the agent,
behavior, quality gate, scope, and unknown-model policy, plus troubleshooting.
The machine-readable adapter contract is `adapters/capability-matrix.json`.

## Automatic model routing

Model profiles are selected automatically from the exact active model when the adapter exposes it. Unknown or unavailable models use the neutral structured fallback; they are never guessed into a vendor-specific profile. User installations expose only the general-purpose `prompt`, `prompt-only`, and `prompt-optimizer` commands.

## Developer-practice principle

Profiles follow `official model-specific > official family > official API/harness > explicitly marked derived heuristic`. See `SOURCES.md` and each profile. A model's reasoning effort or cache/history setting is not faked with prompt phrases; use the `harness-*.md` files.

## Agent capability details

See `COMPATIBILITY.md` and each `adapters/<agent>/README.md`.
