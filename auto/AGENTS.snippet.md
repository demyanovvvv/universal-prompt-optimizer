<!-- prompt-optimizer:auto:start -->
## Prompt Optimizer v5.5 preflight

For each eligible user task, use `.agents/skills/prompt-optimizer/SKILL.md` as the canonical adaptive preflight unless a native Prompt Optimizer adapter already handles this turn. The native adapter wins. PASS a clear request unchanged; use LIGHT for a small missing boundary and load the conditional FULL workflow only for genuinely complex work. When `qualityGate=false`, normalize into the leanest model-appropriate execution brief.

Preserve user intent, exact literals, hard constraints, project rules, required checks, output requirements and approval boundaries. Do not invent requirements. Resolve conversational shorthand from relevant context only. Apply the exact active-model profile when the runtime exposes an unambiguous model; otherwise use configured/neutral fallback rather than guessing. Keep prompt shaping separate from runtime reasoning/tool-history settings.

Load the PREVIEW workflow only when the adapter/config says PREVIEW. AUTO executes silently; OFF skips automatic preflight. User instructions override this block.
<!-- prompt-optimizer:auto:end -->
