---
trigger: always_on
---
# Prompt Optimizer v5.13

Use the installed `.agents/skills/prompt-optimizer/SKILL.md` as the canonical adaptive preflight when automatic optimization is enabled. Read the project's `.prompt-optimizer.json`, otherwise global `~/.config/prompt-optimizer/config.json`; invalid settings or OFF disable automatic preflight. Respect scope first/all. For unknown models, `unsupportedModel=skip` skips preflight; only `generic` permits neutral fallback. Resolve skills from the installed project or global skills tree.

When `qualityGate=pass`, normalize every in-scope request into the leanest model-appropriate execution brief. For `light`, add only a missing high-value boundary, constraint, done criterion, approval boundary, or output shape. For `full`, build a concise execution brief from task-relevant context. Only `adaptive` selects PASS/LIGHT/FULL from the request. Preserve user intent, exact literals, hard constraints, project rules, required checks, output requirements and approval boundaries. Never invent requirements.

Apply an exact model profile, including GPT-6.1 Sol and Claude Sonnet 5.5, only when the active model can be identified unambiguously; otherwise use the model-neutral structured fallback rather than guessing. Keep prompt shaping separate from runtime reasoning/tool-history settings.

Load the PREVIEW workflow only when PREVIEW is active; AUTO executes silently and OFF skips automatic preflight. User instructions override this rule.
