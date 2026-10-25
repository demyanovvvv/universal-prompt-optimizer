# Pi adapter — v5

For setup, task examples, modes, updates, and removal, see [Usage](../../USAGE.md)
or [Руководство пользователя](../../USAGE.ru.md). This document covers host-specific integration.

Pi has a native extension in `extensions/prompt-optimizer.ts`.

- Exact active model routing uses `ctx.model` (`provider/id`) on each `before_agent_start`.
- AUTO/PREVIEW/OFF are supported.
- PREVIEW registers `prompt_optimizer_preview`, which opens `ctx.ui.confirm`; rejection opens the multi-line editor with the generated prompt prefilled. Without an interactive UI, the tool returns an unavailable result asking the model to wait for explicit confirmation. This model-mediated workflow does not block other tools or cancel the agent loop; host approvals remain authoritative.
- Session command: `/prompt-optimizer auto|preview|off|status`.
- Project/global shared config: `.prompt-optimizer.json` / `~/.config/prompt-optimizer/config.json`.
- Session state is capped at 200 sessions and cleaned on the SDK's `session_shutdown` event.
- No extra rewrite model call.
- The entry delegates to `extensions/prompt-optimizer/runtime.ts`; session maps are factory-local so child factories cannot share overrides. First scope counts all agent-start turns, including OFF or unsupported-model turns.
