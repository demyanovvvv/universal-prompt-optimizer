# Claude Code adapter — v5

For setup, task examples, modes, updates, and removal, see [Usage](../../USAGE.md)
or [Руководство пользователя](../../USAGE.ru.md). This document covers host-specific integration.

Claude Code receives the canonical `prompt-optimizer` skill copied to `.claude/skills/` plus a persistent CLAUDE.md preflight. It selects an exact current model profile only when the runtime exposes an unambiguous ID; otherwise it uses the model-neutral structured fallback.

AUTO/PREVIEW/OFF are represented by the shared config/instruction layer. PREVIEW uses Claude Code's native user-question mechanism when available before mutating/external work; otherwise it prints the prompt and waits for confirmation.

Do not treat provider/runtime adaptive-thinking settings as prompt text; see `harness-claude.md`.

Keep persistent `CLAUDE.md` instructions short; put situational workflows in skills. For a substantial unfamiliar change, scope investigation before implementation, preserve exact decisions and verification state across compaction, and use a check with a readable pass/fail signal. `/goal`, Stop hooks, and fresh-context reviews are optional host mechanisms for long unattended work, not default prompt instructions. Follow the user's and host's permission boundaries; optimizer AUTO/PREVIEW/OFF is separate from Claude Code permission modes. Do not commit or open a PR unless requested.

Source: https://code.claude.com/docs/en/best-practices
