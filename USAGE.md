# Using Universal Prompt Optimizer

**Language:** English · [Русский](USAGE.ru.md)

Adaptive, model-aware prompt optimization for coding agents. Preserves user
intent and constraints, with no extra LLM calls.

## 1. Install and start

Download the current [release](https://github.com/demyanovvvv/universal-prompt-optimizer/releases/latest)
and extract it. Python 3.10+ is required. Run commands from that release folder.

```bash
./install.sh
```

Choose your agents, project/global scope, and automatic/native integration.
Keep AUTO and Adaptive for everyday use. On Windows PowerShell:

```powershell
py -3 install.py --agents opencode --auto
```

Python asks for scope and the project path in an interactive terminal. The full
settings wizard is available through Git Bash. Project scope affects the selected
project; global scope affects the current user. Restart your agent after installing.

For an unattended OpenCode installation, specify the target explicitly:

```bash
python install.py --agents opencode --auto --scope project --project /path/to/project --yes
```

Replace the path; use `py -3` instead of `python` on Windows. Use `--scope global`
for the current user. See [installation options](README.md#installation) for
multi-agent installation and dry-run commands.

## 2. Send a normal task

For Gemini 4 Argon, select `gemini-4-argon` in your host/provider. All eight adapters share its dedicated profile; automatic routing uses the exact ID where observable, otherwise name `gemini-4-argon` explicitly when invoking the skill. This selects prompt guidance, not a provider/model switch. Thinking and sampling settings remain host-controlled; see the [Argon harness notes](.agents/skills/prompt-optimizer/references/harness-gemini-4-argon.md).

With automatic integration enabled, write your request normally:

```text
Fix the failing login test. Preserve the public API and run the relevant tests.
```

Include real constraints, exact paths, and expected results when they matter.
The optimizer preserves them; it does not invent requirements or replace missing
project knowledge. A small task can remain small:

```text
Rename the heading “Setup” to “Installation” in README.md.
```

For a larger task, state boundaries explicitly:

```text
Add pagination to the existing search endpoint. Keep the response compatible,
reuse the current database layer, and add tests for empty and final pages.
```

Optimization happens within the active agent's turn. It does not launch a separate
rewriting model, and it does not guarantee that the resulting implementation is correct.

## 3. Use manual commands

OpenCode installs these commands:

| Command | Result |
|---|---|
| `/prompt <task>` | Optimize and execute the task |
| `/prompt-only <task>` | Return a reusable prompt without executing the task |
| `/prompt-optimizer` | Inspect or change settings |

Example:

```text
/prompt-only Review the authentication changes for regressions. Do not edit files.
```

Model profiles are selected internally; model-specific commands are unnecessary.
Other hosts expose different command/skill entry points: follow the matching
[adapter README](README.md#supported-agents), not OpenCode-specific instructions.

## 4. Choose behavior and quality

**Behavior controls execution:**

- **AUTO:** adapt when useful and proceed within the host's permissions.
- **PREVIEW:** show the proposed brief and request confirmation. Enforcement
  depends on the adapter. OpenCode v1 confirmation is advisory; Pi supports native
  confirmation. See the [compatibility matrix](COMPATIBILITY.md).
- **OFF:** disable automatic preflight; manual invocation remains available.

**Quality gate controls shaping:**

- **Adaptive:** select PASS, LIGHT, or FULL according to the task.
- **Pass:** use the leanest model-appropriate normalization.
- **Light:** add only a missing high-value field or boundary.
- **Full:** build a concise task-relevant execution brief.

Use Adaptive by default. FULL does not override user constraints or host approval.
`scope=all` applies to eligible user turns; `scope=first` limits automatic preflight
to the first eligible turn where the adapter can track it.

For an unknown or ambiguous model, **Skip** adds no optimizer guidance and
**Generic** uses neutral guidance. Neither guesses a different model variant.

## 5. Configure OpenCode

With native integration installed, open:

```text
Ctrl+P → command palette → Prompt Optimizer
```

Use `/po` or `Ctrl+Shift+P` for settings, and `/po-status` for the native status
dialog. Select Behavior, Scope, Quality gate, Unsupported model, and Save to.

- **Session:** a temporary override for the current session.
- **Project:** `.opencode/prompt-optimizer.json`.
- **Global:** `~/.config/opencode/prompt-optimizer.json`.

Session overrides can affect the effective value until reset. Environment overrides
also affect configuration; consult [OpenCode configuration](adapters/opencode/README.md).

Indicator states: `● PO AUTO`, `◐ PO PREVIEW`, `○ PO OFF`, `◇ PO GENERIC`,
and `! PO CONFIG` for invalid configuration. `*` indicates a session override.

For instruction-based adapters, project `.prompt-optimizer.json` takes precedence
over `~/.config/prompt-optimizer/config.json`. A typical shared config is:

```json
{
  "schemaVersion": 1,
  "behavior": "auto",
  "scope": "all",
  "qualityGate": "adaptive",
  "unsupportedModel": "skip"
}
```

See the [configuration guide](DECISION-GUIDE.md) for adapter-specific details.

## 6. Update or remove

To update, extract the new release and reinstall into the same scope and target.
Saved settings are preserved by Python/non-wizard updates; the Bash settings wizard
lets you choose new values. Restart the agent afterward.

Preview removal before applying it:

```bash
python uninstall.py --scope project --project /path/to/project --dry-run --yes
python uninstall.py --scope project --project /path/to/project --yes
```

Interactive alternatives are `bash ./uninstall.sh` and `py -3 uninstall.py`.
For global removal, use `--scope global`. Removal cleans up managed package files,
metadata, runtime state, and managed blocks while preserving unrelated content.
Review dry-run output for the selected installation, then restart the agent.

## 7. Troubleshoot

| Symptom | What to check |
|---|---|
| Commands are missing | Correct agent and scope selected; restart the host; check its adapter README |
| OpenCode indicator/menu is missing | Native server and TUI integration installed; restart OpenCode |
| Nothing appears to change | AUTO is silent; precise tasks stay lean; check OFF, first-turn scope, and unknown-model Skip |
| `! PO CONFIG` appears | Fix malformed or invalid settings; invalid config disables automatic preflight |
| A setting does not take effect | Inspect status, session overrides, environment variables, and project/global precedence |
| A model is not recognized | Verify its exact runtime ID; choose Generic if neutral shaping is desired |
| PREVIEW does not block execution | Check the adapter's confirmation capabilities; OpenCode v1 is advisory |

From the release folder, run `python install.py --help` or
`python uninstall.py --help` to inspect supported options. Package verification is
available through `python tools/selfcheck.py` or `./verify.sh`.

The optimizer adds no telemetry or hidden network calls and does not persist raw
prompts as metrics. Your coding host still makes its normal model calls and manages
its own history. See [Security](SECURITY.md).
