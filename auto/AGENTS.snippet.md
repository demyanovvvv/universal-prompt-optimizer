<!-- prompt-optimizer:auto:start -->
## Prompt Optimizer v5.5 preflight

For each user task, use `.agents/skills/prompt-optimizer/SKILL.md` as the canonical adaptive preflight when automatic optimization is enabled for this agent. If the current agent already has a native Prompt Optimizer adapter/plugin active for this turn (notably OpenCode), do not run a second independent preflight or PREVIEW from this AGENTS block; the native adapter wins. The goal is not to make prompts longer. When `qualityGate=true`, use PASS/LIGHT/FULL and rewrite only when positive value is expected. When `qualityGate=false`, normalize every in-scope request into the leanest model-appropriate execution brief.

Preserve user intent, exact literals, hard constraints, project rules, required checks, output requirements and approval boundaries. Do not invent requirements. Resolve conversational shorthand from relevant context only. Apply the exact active-model profile when the runtime exposes an unambiguous model; otherwise use configured/neutral fallback rather than guessing. Keep prompt shaping separate from runtime reasoning/tool-history settings.

If the adapter/config says PREVIEW, show the exact optimized execution prompt in the agent's native question/confirmation UI before mutating/external work; put `Выполнить` first/default and allow edits. If AUTO, optimize silently and execute. If OFF, skip automatic preflight. User instructions override this block.
<!-- prompt-optimizer:auto:end -->
