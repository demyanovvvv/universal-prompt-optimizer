<!-- prompt-optimizer:auto:start -->
## Prompt Optimizer v5.7 preflight

For each eligible user task, use `.agents/skills/prompt-optimizer/SKILL.md` as the canonical adaptive preflight unless a native Prompt Optimizer adapter already handles this turn. The native adapter wins. `qualityGate=pass` forces the leanest normalization; `light` adds only a missing high-value field; `full` builds a concise task-relevant execution brief; only `adaptive` selects PASS/LIGHT/FULL according to task need.

Preserve user intent, exact literals, hard constraints, project rules, required checks, output requirements and approval boundaries. Do not invent requirements. Resolve conversational shorthand from relevant context only. Apply the exact active-model profile when the runtime exposes an unambiguous model; otherwise use configured/neutral fallback rather than guessing. Keep prompt shaping separate from runtime reasoning/tool-history settings.

Load the PREVIEW workflow only when the adapter/config says PREVIEW. AUTO executes silently; OFF skips automatic preflight. User instructions override this block.
<!-- prompt-optimizer:auto:end -->
