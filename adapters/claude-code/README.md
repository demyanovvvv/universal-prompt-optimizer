# Claude Code adapter — v5

Claude Code receives the canonical skills copied to `.claude/skills/` plus a persistent CLAUDE.md preflight. Because Claude Code runs Claude-family models, the agent should select the exact current Claude profile when the runtime exposes it; otherwise an explicit `prompt-claude-*` override is available.

AUTO/PREVIEW/OFF are represented by the shared config/instruction layer. PREVIEW uses Claude Code's native user-question mechanism when available before mutating/external work; otherwise it prints the prompt and waits for confirmation.

Do not treat provider/runtime adaptive-thinking settings as prompt text; see `harness-claude.md`.
