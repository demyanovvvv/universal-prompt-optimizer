# Prompt Optimizer — Gemini CLI adapter v5.11

Use the installed `prompt-optimizer` skill as an adaptive preflight only when the native hook marks the turn eligible. Preserve user intent, exact literals, hard constraints, project rules, required verification, output requirements and approval boundaries; never invent requirements.

When an exact active model is known, apply only its matching installed model profile. Do not infer Gemini 3.8 Flash merely because the host agent is Gemini CLI. The native `BeforeModel` observer records the resolved model for later turns without modifying the outgoing request.

On Gemini CLI, `qualityGate=pass` is the legacy force-normalize mode; `light`, `full`, and `adaptive` use the host's adaptive gate guidance. The native hook preserves this richer value even though the host still performs prompt shaping through instructions.

PREVIEW uses `ask_user` when available and must not execute until approved. AUTO executes in the same turn. OFF skips automatic optimization. User instructions override this adapter.
