# Using Universal Prompt Optimizer

**Language:** English · [Русский](USAGE.ru.md)

Model-aware optimization of coding-agent prompts. Preserves user intent and
constraints without extra model calls.

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

For OMP, replace `--agents opencode` with `--agents omp`, enable `--auto`, and restart OMP. `/prompt-optimizer status` inspects the extension; `/prompt-optimizer auto|preview|off` changes session-only behavior. See the [OMP guide](adapters/omp/README.md) for loading paths and PREVIEW limitations.

For DeepSeek Harness (`dsh`), install and start from the selected project:

```bash
python install.py --agents deepseek-harness --auto --scope project --project /path/to/project --yes
cd /path/to/project
dsh --profile web --patch .dsh/prompt-optimizer.patch.yml
```

Harness must already be installed; this installer does not download it or run its package manager. For Desktop, use `python install.py --scope global --agents deepseek-harness --auto --yes`: the plugin is registered in **Plugins**, with its icon and English/Russian title and description selected by the interface language. The Components row uses the short ID `prompt-optimizer`; package and profile dependency remain `universal-prompt-optimizer`. Restart Harness if it does not apply the changed profile live. Uninstall removes only Harness entries recorded as installer-owned. Project CLI `--patch` must precede app arguments. Configuration uses the same shared JSON below; PREVIEW is textual and advisory. See the [Harness guide](adapters/deepseek-harness/README.md) for lifecycle and privacy boundaries.

## 2. Send a normal task

Select the model in your host/provider; the optimizer does not switch it. All supported adapters share the [canonical profiles and aliases](.agents/skills/prompt-optimizer/references/model-registry.json), including Gemini 4 Hydrogen/Carbon/Argon, Fable 5.2, GLM-5.3-FlashX, Kimi K3.1 Pro, MiniMax M3.1 Flash and Muse Wonder. Automatic routing uses the exact model ID where observable, including provider-qualified IDs; otherwise name the exact profile when invoking the skill. DeepSeek V4.1 Flash and its `-1017` snapshot use one profile. Unknown variants still follow `skip`/`generic`. Thinking, sampling, cache and tool-history settings remain host-controlled; see each profile's linked harness notes and [source provenance](SOURCES.md).

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

```bash
# Update an existing project installation to this release, keeping its settings
python install.py --scope project --project /path/to/project --yes
# Update the current user's global installation
python install.py --scope global --yes
```

On Windows, replace `python` with `py -3`. Global installation without `--agents`
auto-detects agents and adds them to the recorded adapter set while preserving
settings. Project updates keep their recorded adapter set. Use `--list-agents` to
inspect detection without writes, `--agents` for an explicit selection, or
`--agents all` to install all adapters. No detected/recorded agents means no install;
the installer does not download missing agents. The previous and target versions are displayed.

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
