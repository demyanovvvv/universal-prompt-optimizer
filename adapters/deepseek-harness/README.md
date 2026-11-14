# DeepSeek Harness native adapter

DeepSeek Harness (`dsh`) is a distinct coding-agent host, not the DeepSeek model API. This adapter uses its native Cordis `systemPrompt.section()` API. API contract: upstream **0.2.2-rc.3**, checked 2026-11-13; Harness is pre-stable and later releases may change this API. Node.js 24.9+ is required by that Harness release. The optimizer itself adds no dependencies or extra model calls.

Native service validation exercised **Cordis 4.1.0 + SystemPrompt 0.2.2-rc.3**: plugin dependency activation, exact model section assembly, existing host-policy preservation, complete-prompt precedence and unload cleanup. This was an isolated keyless service run, not a full Harness app launch or a provider-model test.

## Install and activate

### Desktop: native plugin

From the extracted optimizer release:

```bash
python install.py --scope global --agents deepseek-harness --auto --yes
```

Global installation without `--agents` also selects a detected Harness automatically.
Windows PowerShell: use `py -3` instead of `python`; `dsh` and `deepseek` are installer aliases.
Open Desktop's **Plugins** page after installation. The native bundle exposes its icon,
title and description through Harness metadata: Russian for a Russian interface,
English for an English interface, with English fallback for other locales. No separate
language setting or locale-detection heuristic is installed.
The component row uses the short ID `prompt-optimizer`; the npm package and profile
dependency remain named `universal-prompt-optimizer`.

Automatic global installation writes a self-contained local bundle to
`~/.dsh/plugins/prompt-optimizer` and its installed package to
`~/.dsh/profiles/desktop/node_modules/universal-prompt-optimizer`. Both include the
canonical skill. It adds only the local dependency and the ordered bundle selection
to `profiles/desktop/package.json`. The local source keeps native file-dependency
reinstallation available without downloading a package. No npm/pnpm command runs.

The first installation enables the bundle; reinstalling preserves a bundle you
disabled in Harness. Existing dependencies, bundle order, profile preferences and
`cordis.patch.yml` are preserved. Without live profile reload, restart Desktop to
activate the saved change. The installer does not restart it or call any model.

Windows discovery reads the registered application's `InstallLocation` or `DisplayIcon`
and verifies `DeepSeek Harness.exe`. No drive-wide scan, registry write, PATH change,
credential access or application-directory write occurs. The application directory
is not the user's Harness home. Desktop shell **0.2.0-rc.2** currently carries CLI and
system-prompt API **0.2.2-rc.3**; compatibility follows the bundled runtime, not the
shell's version label. The bundle declares `engines.dsh` for 0.2.2-rc.3 through 0.2.x;
other runtime versions require explicit compatibility validation, not an exemption.

### Project CLI: explicit overlay

```bash
python install.py --agents deepseek-harness --auto --scope project --project /path/to/project --yes
cd /path/to/project
dsh --profile web --patch .dsh/prompt-optimizer.patch.yml
```

The project plugin lives at `.dsh/plugins/prompt-optimizer`; its canonical skill is
self-contained. `.dsh/skills/prompt-optimizer` also supports native manual discovery.
Project installation does not register a plugin in the machine's Desktop profile.
`--patch` is a launcher option and must precede app arguments:

```bash
dsh --profile web --patch .dsh/prompt-optimizer.patch.yml --no-open
dsh --profile headless --patch .dsh/prompt-optimizer.patch.yml "Fix the failing test"
```

These commands launch Harness; headless execution makes normal model calls. Install
Harness separately through its [official instructions](https://github.com/deepseek-ai/deepseek-harness#run).
The optimizer installer never downloads Harness or starts it.

### Updates and removal

`--no-auto` supplies shared/native manual skills only, without registering a new
Desktop bundle. Reinstall into the same scope to update; `--dry-run` is read-only.
Global native installation replaces the former global explicit-overlay workflow;
project CLI overlays remain supported. Standard `uninstall.py` removes the Harness
registration and payload only when valid installation state records the corresponding
ownership. Untracked or manually managed Harness entries and files are preserved.

Optimizer destinations use `<root>/.dsh`; setting `DSH_HOME` does not relocate them.
For a custom Harness home, do not assume this default Desktop profile is the active
one. Custom `DSH_AGENTS_HOME` and skill-root settings are not changed.

## Runtime behavior and configuration

Configuration is read on every assembly, global `~/.config/prompt-optimizer/config.json` followed by `.prompt-optimizer.json` in the session's active working directory. Valid project values override valid global values; malformed/unreadable JSON or invalid managed fields in **either** source disables automatic shaping. Unrelated fields are ignored. Native defaults without a config are AUTO / all / adaptive / skip; the installer writes its selected values.

```json
{
  "schemaVersion": 1,
  "behavior": "auto",
  "scope": "all",
  "qualityGate": "adaptive",
  "unsupportedModel": "skip"
}
```

- **AUTO:** add lean model-aware optimization instructions for the existing agent turn. No separate optimizer model is called.
- **PREVIEW:** instruct the model to display the exact optimized brief and wait for explicit user confirmation before mutating/external work. Read-only context resolution may happen first. This is textual and **advisory**, not a confirmation tool, sandbox or forced execution barrier. Harness's own permissions remain authoritative.
- **OFF:** return an empty optimizer section; manual skills remain available.
- `qualityGate`: `adaptive` selects PASS/LIGHT/FULL; `pass`, `light` and `full` select the corresponding shared behavior. Legacy boolean values remain accepted.
- `scope: "first"`: use the host's durable `lastTurn === 1`, including all tool steps in that turn. A first turn skipped for OFF or an unsupported model still counts; later resumed turns are not treated as first. No private session counter is persisted.

Only the captured assembly `modelSelection.model` selects a profile from the canonical registry. Provider labels do not select models. Exact aliases, provider-qualified IDs and supported `-latest` spellings follow the shared registry. Unknown or absent IDs use `skip` (no context) or explicit `generic` (neutral instructions), never a guessed sibling model. All installed canonical profiles are available without copying a second alias table into the adapter.

The plugin contributes one ordered, literal section. It does not replace the user's request or other prompt sections, rewrite previous history, change tools, model/provider selection, thinking, sampling, cache controls or approvals. A Harness preset using a `complete: true` system prompt intentionally suppresses cooperative sections, including this adapter. Custom profiles must provide `systemPrompt`, `agents` and `workingDirectory`; a profile without those services cannot activate it. The adapter supplies no status UI or `/prompt-optimizer` session command.

## Privacy boundary

The adapter performs local configuration/profile reads only: no network client, telemetry, credential collection, raw-prompt metrics or extra persistence. Delivered section text still travels through the host's normal request/history.

**Harness itself has separate session-log and telemetry policies.** Its base composition documents default DeepSeek session-log contribution and feedback-triggered OTel export. Installing this adapter does not enable, disable or reconfigure either. Review Harness's [shared deployment behavior](https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/reference/README.md#shared-deployment-behavior) and its General privacy settings before using sensitive data.

## Maintenance

Edit canonical model files under `.agents/skills/prompt-optimizer`, not an installed copy. Validate with `node --test tests/deepseek-harness-runtime.test.mjs`, `python -B -m unittest discover -s tests -p test_deepseek_harness_install.py -v`, `npm run test:adapters` and the change matrix in [TESTING.md](../../TESTING.md). Deterministic service-contract tests are not a claim of real-provider transport compatibility or stronger PREVIEW enforcement.
