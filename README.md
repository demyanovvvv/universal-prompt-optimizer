# Universal Prompt Optimizer v5.4

Model-aware adaptive Agent Skill that lets you write normal short human prompts while the active agent silently converts them **only when useful** into the prompt shape recommended for the selected model.

Primary goals: higher first-pass success, fewer misunderstandings/scope errors, fewer repair iterations and lower total tokens per completed task — not merely fewer tokens in the first prompt.

## v5.4 — final consolidated build

This release consolidates every v5.0–v5.3 change and adds a full consistency/runtime audit.

- `./install.sh` remains the only normal human-facing installer. English is default; `./install.sh --ru` / `./install.sh ru` runs the complete Russian wizard.
- Auto-detection runs first, with **detected / ALL / manual multi-select / re-scan** and a no-detection fallback. Windows/Git Bash detection now also checks common Cursor/Windsurf locations.
- Every current setting is available in-console: project/global location, automatic/native integration, AUTO/PREVIEW/OFF, all/first scope, PASS/LIGHT/FULL quality gate, unknown-model SKIP/GENERIC, backups, dry-run, and final review navigation.
- Installer updates preserve unrelated existing JSON fields instead of replacing whole config objects.
- Pi `scope=first` state is session-scoped instead of process-global.
- Gemini CLI no longer assumes Gemini 3.8 Flash. `BeforeModel` now observes the exact resolved `llm_request.model` without modifying the request; first-turn routing uses only explicit `GEMINI_MODEL` / `model.name` when visible and otherwise follows SKIP/GENERIC without guessing.
- Stale v5.2/v5.3 runtime IDs were removed; version identity is centralized in `VERSION`.
- `verify.sh` performs package self-checks for Bash/Python/JSON/JSONL/TypeScript, registry/profile alignment, archive hygiene, installer smoke tests, state handling, and config preservation.
- 20 model profiles and 20 manual override skills remain developer-guidance-first, with prompt shaping kept separate from runtime reasoning/thinking/tool-loop configuration.
- Installation updates managed files atomically, preserves unrelated files in existing skill/command directories, rejects malformed managed JSON, and refuses to install inside the package source tree.

### Quick start

```bash
chmod +x install.sh verify.sh
./install.sh          # English wizard
./install.sh --ru     # Russian wizard
./verify.sh --ru      # optional package self-check
```

## Models

### OpenAI
GPT-6 Astra; GPT-5.6 Sol (`gpt-5.6` alias), Terra, Luna.

### Z.ai / GLM
GLM-5.2; GLM-5.3; GLM-5.3-Flash.

### DeepSeek
DeepSeek V4 Flash; DeepSeek V4 Pro.

### Anthropic / Claude
Claude Fable 5.1; Fable 5; Opus 5; Opus 4.8; Sonnet 5.

### Other
Kimi K3; Muse Spark 1.3; Hy4-preview; Qwen3.8-Max (including 0902/dated aliases); Gemini 3.8 Flash; Grok 4.6.

## Modes

Shared config (project):

`.prompt-optimizer.json`

### AUTO — recommended
```json
{
  "behavior": "auto",
  "scope": "all",
  "qualityGate": true,
  "unsupportedModel": "skip"
}
```

### PREVIEW
```json
{
  "behavior": "preview",
  "scope": "all",
  "qualityGate": true,
  "unsupportedModel": "skip"
}
```

### OFF
```json
{
  "behavior": "off",
  "scope": "all",
  "qualityGate": true,
  "unsupportedModel": "skip"
}
```

`scope: "first"` restores first-user-turn-only behavior from v4.

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
6. **Adaptive quality gate** — ON (`PASS → LIGHT → FULL`) / OFF (normalize every eligible prompt).
7. **Unknown model** — SKIP model-specific adaptation / use GENERIC neutral profile.
8. **Backups** — ON / OFF.
9. **Dry-run** — write normally / show changes without writing.

The final review screen shows the complete configuration and lets you return to **agent selection**, **settings**, or **installation location** before pressing Enter to install.

### AUTO / PREVIEW / OFF

- **AUTO** — adapt silently only when useful, then execute.
- **PREVIEW** — show the optimized prompt first and request confirmation where the agent exposes a confirmation UI. This is a host-enforced execution barrier only when the selected agent explicitly provides one; otherwise it is model-guided and must be treated as advisory.
- **OFF** — keep the adapter installed but disable automatic optimization.

This is separate from **Automatic/native integration = OFF**, which installs only the shared skills/commands and does not install automatic hooks/plugins/rules at all.

### Optional advanced/CI flags

Normal users do not need these. They are retained for repeatable automation and CI only:

```bash
./install.sh --detect-agents --auto --behavior auto --yes
./install.sh --agents opencode,cursor,pi --behavior preview --yes
./install.sh --agents all --quality-gate on --yes
```

Run `./install.sh --help` for the automation interface.

`install.py` is an internal backend; the supported human-facing entry point is `install.sh`.

## Manual model override skills

`prompt-astra`, `prompt-sol`, `prompt-terra`, `prompt-luna`, `prompt-glm-5-2`, `prompt-glm-5-3`, `prompt-glm-5-3-flash`, `prompt-deepseek-v4-flash`, `prompt-deepseek-v4-pro`, `prompt-claude-fable-5-1`, `prompt-claude-fable-5`, `prompt-claude-opus-5`, `prompt-claude-opus-4-8`, `prompt-claude-sonnet-5`, `prompt-kimi-k3`, `prompt-muse-spark-1-3`, `prompt-hy4-preview`, `prompt-qwen3-8-max`, `prompt-gemini-3-8-flash`, `prompt-grok-4-6`.

## Developer-practice principle

Profiles follow `official model-specific > official family > official API/harness > explicitly marked derived heuristic`. See `SOURCES.md` and each profile. A model's reasoning effort or cache/history setting is not faked with prompt phrases; use the `harness-*.md` files.

## Agent capability details

See `COMPATIBILITY.md` and each `adapters/<agent>/README.md`.
