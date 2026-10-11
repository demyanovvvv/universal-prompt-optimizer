# OpenAI Codex adapter — v5

For setup, task examples, modes, updates, and removal, see [Usage](../../USAGE.md)
or [Руководство пользователя](../../USAGE.ru.md). This document covers host-specific integration.

Codex uses the shared `.agents/skills/` tree and `AGENTS.md` instructions. The installed canonical skill performs PASS/LIGHT/FULL adaptive shaping and automatically selects an exact model profile when the runtime exposes one, including GPT-6.1 Sol; otherwise it uses the model-neutral structured fallback.

Automatic model routing is exact only when the Codex runtime exposes the current model identity to the agent/instruction context. Otherwise do not guess: use the OpenAI-family/generic profile or an explicit override. This package does not claim a native pre-submit rewrite hook where one is not documented.

AUTO executes the internal preflight in the same turn; PREVIEW requests a native clarification/confirmation UI when available and otherwise stops with a textual preview; OFF disables the auto instruction block.
