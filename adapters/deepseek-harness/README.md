# DeepSeek Harness native adapter

DeepSeek Harness (`dsh`) is a distinct coding-agent host, not the DeepSeek model API. This adapter uses its native Cordis `systemPrompt.section()` API. API contract: upstream **0.2.2-rc.3**, checked 2026-11-13; Harness is pre-stable and later releases may change this API. Node.js 24.9+ is required by that Harness release. The optimizer itself adds no dependencies or extra model calls.

Native service validation exercised **Cordis 4.1.0 + SystemPrompt 0.2.2-rc.3**: plugin dependency activation, exact model section assembly, existing host-policy preservation, complete-prompt precedence and unload cleanup. This was an isolated keyless service run, not a full Harness app launch or a provider-model test.

## Install and activate

From the extracted optimizer release:

```bash
python install.py --agents deepseek-harness --auto --scope project --project /path/to/project --yes
cd /path/to/project
dsh --profile web --patch .dsh/prompt-optimizer.patch.yml
```

Windows PowerShell: use `py -3` instead of `python`. `--agents dsh` and `--agents deepseek` are installer aliases. Install Harness separately through its [official instructions](https://github.com/deepseek-ai/deepseek-harness#run); this installer never downloads Harness, invokes `npx`/pnpm, starts it, or changes credentials.

`--patch` is a Harness launcher option: put it **before app arguments**, for example:

```bash
dsh --profile web --patch .dsh/prompt-optimizer.patch.yml --no-open
dsh --profile headless --patch .dsh/prompt-optimizer.patch.yml "Fix the failing test"
dsh --profile web --patch .dsh/prompt-optimizer.patch.yml --dump-config
```

The first two commands launch Harness; headless execution makes normal model calls. `--dump-config` inspects the composed rows without booting plugins or calling a model, but Harness may initialize missing profile files.

The automatic installer creates only these adapter-owned paths beneath the target project (or current user's home for `--scope global`):

- `.dsh/plugins/prompt-optimizer/index.mjs` — native plugin;
- `.dsh/skills/prompt-optimizer/` — canonical skill, model registry and profile references;
- `.dsh/prompt-optimizer.patch.yml` — explicit plugin-loading overlay.

Existing shared `.agents/skills/prompt-optimizer` installation remains available to other adapters. A `--no-auto` install supplies native/shared skills without installing a plugin or overlay. With the default Harness filesystem-skill provider, the native skill is discoverable for manual invocation; no OpenCode slash commands are installed in Harness.

For global installation, use `--scope global`, then pass the **absolute** path of `~/.dsh/prompt-optimizer.patch.yml` on every launch (PowerShell: `--patch "$HOME/.dsh/prompt-optimizer.patch.yml"`). The overlay path is independent of `DSH_HOME`; a custom Harness home does not relocate optimizer-installed files. For manual skill discovery with a custom `DSH_HOME`, retain the default shared `~/.agents` root or configure Harness's skill roots explicitly. Custom `DSH_AGENTS_HOME`/skill-root settings are not changed by the installer.

**No implicit plugin discovery is claimed.** Installation never edits the home `cordis.patch.yml`, any profile patch, `package.json`, bundle list or package-manager lock. Continue passing `--patch` after restarting Harness. Reinstall into the same scope to update; `--dry-run` shows planned writes. Standard `uninstall.py` removes the optimizer installation for that scope while preserving unrelated Harness files; stop passing the overlay after removal.

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
