# OpenAI Codex adapter — v5

Codex uses the shared `.agents/skills/` tree and `AGENTS.md` instructions. The installed canonical skill performs PASS/LIGHT/FULL adaptive shaping and can be invoked explicitly as `$prompt-optimizer` or via a model-specific override.

Automatic model routing is exact only when the Codex runtime exposes the current model identity to the agent/instruction context. Otherwise do not guess: use the OpenAI-family/generic profile or an explicit override. This package does not claim a native pre-submit rewrite hook where one is not documented.

AUTO executes the internal preflight in the same turn; PREVIEW requests a native clarification/confirmation UI when available and otherwise stops with a textual preview; OFF disables the auto instruction block.
