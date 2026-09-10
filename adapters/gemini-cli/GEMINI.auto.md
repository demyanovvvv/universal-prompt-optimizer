# Prompt Optimizer — Gemini CLI adapter v5.5

Use the installed `prompt-optimizer` skill as an adaptive preflight only when the native hook marks the turn eligible. Preserve user intent, exact literals, hard constraints, project rules, required verification, output requirements and approval boundaries; never invent requirements.

When an exact active model is known, apply only its matching installed model profile. Do not infer Gemini 3.8 Flash merely because the host agent is Gemini CLI. The native `BeforeModel` observer records the resolved model for later turns without modifying the outgoing request.

When `qualityGate=true`, PASS a precise prompt, LIGHT-normalize an incomplete one, and FULL-restructure only a complex/ambiguous request. When `qualityGate=false`, normalize every eligible prompt into the leanest model-appropriate execution brief.

PREVIEW uses `ask_user` when available and must not execute until approved. AUTO executes in the same turn. OFF skips automatic optimization. User instructions override this adapter.
