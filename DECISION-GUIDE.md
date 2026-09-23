# Choosing a configuration — v5.5

This is the decision guide for the three user-facing questions: **which agent**,
**which behavior**, and **which quality gate**. For the raw capability table see
`COMPATIBILITY.md`; for the machine-readable contract see
`adapters/capability-matrix.json`.

## 1. Which agent should I install for?

All eight agents share the same 64 skills and 20 model profiles. They differ only
in how reliably the adapter can (a) discover the exact active model before the
first call and (b) enforce an approval barrier in PREVIEW.

| Your priority | Recommended agent | Why |
|---|---|---|
| Exact model routing with zero extra provider calls | **OpenCode** or **Pi** | The native extension hook exposes the resolved model before execution. |
| Exact routing plus a real approval tool | **Pi** | `prompt_optimizer_preview` is backed by `ctx.ui.confirm` / `ctx.ui.editor`. |
| Exact routing inside an editor you already use | **Cursor** | Hook input carries `model` / `model_id`; a small runtime state file bridges it to the rule. |
| Exact routing after the first turn, no native plugin | **Gemini CLI** | `BeforeModel` observes the exact model; first-turn routing needs `GEMINI_MODEL`. |
| Instructions-only, no hooks at all | **Claude Code**, **Copilot CLI**, **Codex**, **Windsurf** | Shared skills plus documented instruction files. |

You can install several at once; the shared skills are identical and only the
adapter integration differs.

## 2. Which behavior?

```bash
./install.sh --behavior auto      # recommended default
./install.sh --behavior preview   # show first, then run
./install.sh --behavior off       # installed but inactive
```

- **AUTO** — optimize silently only when it helps, then execute. Best default.
- **PREVIEW** — present the optimized prompt and ask for confirmation. Treat it
  as advisory on OpenCode, Cursor, Gemini CLI, and the instructions-only agents:
  the confirmation is a model instruction unless the host blocks mutating tools.
  Pi is the one adapter with a host-provided confirmation tool.
- **OFF** — keep everything installed but stop automatic optimization. Useful for
  A/B comparison and for temporarily disabling without uninstalling.

If you are unsure, start with AUTO. Switch to PREVIEW only if you need to audit
the rewrite before it runs and accept the extra round trip.

## 3. Which quality gate?

```bash
./install.sh --quality-gate adaptive   # recommended default
./install.sh --quality-gate pass
./install.sh --quality-gate light
./install.sh --quality-gate full
```

| Gate | Behavior | Use when |
|---|---|---|
| `adaptive` | Escalates `PASS → LIGHT → FULL` based on the prompt | Default. Best balance. |
| `pass` | Leaves an already-good prompt essentially unchanged | You trust your prompts and want minimal intervention. |
| `light` | Adds only missing high-value structure | Your prompts are usually short but underspecified. |
| `full` | Always normalizes to the full model profile | You want maximum consistency and accept longer prompts. |

`on`/`off` remain accepted for v4 compatibility: `on` maps to `adaptive`, `off`
maps to `pass`.

## 4. Which scope and unknown-model policy?

- `--prompt-scope first` optimizes only the first user turn of a session;
  `--prompt-scope all` (default) evaluates every turn.
- `--unsupported-model skip` (default) injects nothing when the exact model is
  unknown; `generic` injects a neutral model-agnostic profile instead.

## Recommended starting points

```bash
# Individual developer on OpenCode, lowest friction
./install.sh --agents opencode --auto --behavior auto --quality-gate adaptive

# Team-wide project install, audit rewrites before they run
./install.sh --agents all --scope project --project . --auto --behavior preview

# CI / non-interactive, no unknown-model guessing
./install.sh --agents all --scope project --project . --auto \
  --behavior auto --quality-gate adaptive --unsupported-model skip --yes
```

## Troubleshooting

**Nothing is being optimized.**
1. Run `./install.sh --scope project --project . --doctor` and confirm `behavior`
   is not `off` and the expected adapter files are `current`.
2. Check the model is one of the 20 profiles; an unknown model with
   `unsupportedModel: skip` intentionally injects nothing. Set `generic` to opt
   into neutral context.
3. For Gemini CLI first-turn routing, set `GEMINI_MODEL` or rely on the
   `BeforeModel` observation from the second turn onward.

**PREVIEW ran the task without asking.**
PREVIEW is advisory on every adapter except Pi. The host must block mutating
tools for it to be a hard barrier. Use Pi, or switch to AUTO and review prompts
from your own git diff.

**Cursor/Gemini state looks stale.**
Runtime state files are bounded and expire after 30 days. Delete
`.cursor/.prompt-optimizer-runtime.json` or
`.gemini/.prompt-optimizer-*-state.json` to reset, or re-run the installer.

**A user file or custom config was changed.**
`--uninstall` and updates preserve user text, custom JSON fields, hooks, and
modified files. Run `./install.sh --uninstall --dry-run --yes` to see exactly
what would be removed before removing it.

**Config file is rejected.**
Malformed JSON fails safe and is never overwritten. Fix the syntax in
`.prompt-optimizer.json` (contract: `prompt-optimizer.schema.json`) and re-run.
