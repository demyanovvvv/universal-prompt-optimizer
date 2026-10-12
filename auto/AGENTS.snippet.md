<!-- prompt-optimizer:auto:start -->
## Prompt Optimizer v5.14 preflight

Before automatic preflight, read the project `.prompt-optimizer.json` if present, otherwise the global `~/.config/prompt-optimizer/config.json`; current settings override the installer defaults below. Invalid settings disable automatic preflight. OFF skips it. For an unknown model, `unsupportedModel=skip` skips preflight and `generic` enables neutral shaping. Respect `scope=first` only for the first eligible user-turn; do not infer an exact model or session identity. Resolve the canonical skill from the installed project or global skills tree.
For each eligible user task, use `.agents/skills/prompt-optimizer/SKILL.md` as the canonical adaptive preflight unless a native Prompt Optimizer adapter already handles this turn. The native adapter wins. `qualityGate=pass` forces the leanest normalization; `light` adds only a missing high-value field; `full` builds a concise task-relevant execution brief; only `adaptive` selects PASS/LIGHT/FULL according to task need.

Preserve user intent, exact literals, hard constraints, project rules, required checks, output requirements and approval boundaries. Do not invent requirements. Resolve conversational shorthand from relevant context only. Apply the exact active-model profile when the runtime exposes an unambiguous model; otherwise use the model-neutral structured fallback rather than guessing. Keep prompt shaping separate from runtime reasoning/tool-history settings.

Load the PREVIEW workflow only when the adapter/config says PREVIEW. AUTO executes silently; OFF skips automatic preflight. User instructions override this block.
<!-- prompt-optimizer:auto:end -->
