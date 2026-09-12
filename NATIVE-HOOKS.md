# Native integration notes — v5

## OpenCode
Use the v1 `chat.message` hook to admit and count a user turn, then
`experimental.chat.system.transform` for model-specific preflight because it
contains the resolved model. The plugin keeps bounded process-local state only;
it does not claim persistence across plugin reloads. PREVIEW is implemented as a
model instruction to call OpenCode's `question` tool once with the exact optimized
prompt; it is advisory, not a host-enforced execution barrier.

## Pi
`before_agent_start` has `ctx.model`, so routing is exact. PREVIEW registers a custom `prompt_optimizer_preview` tool backed by `ctx.ui.confirm` and `ctx.ui.editor`. Pi session commands can toggle behavior without reinstalling.

## Cursor
`beforeSubmitPrompt` includes `model`, `model_id`, `model_params` in the common hook schema but cannot inject arbitrary additional context. The hook records those values to `.cursor/.prompt-optimizer-runtime.json`; the always rule consumes it.

## Gemini CLI
`BeforeAgent` injects dynamic per-turn context and PREVIEW uses built-in `ask_user`. A second, observation-only `BeforeModel` registration reads the resolved `llm_request.model` and stores it per `session_id`; it returns no `llm_request` override, so the outgoing multimodal request remains untouched. Before the first model call, only explicit `GEMINI_MODEL`/`model.name` is trusted; otherwise model-specific routing is skipped/neutral according to `unsupportedModel`.

## GitHub Copilot CLI
Static hook output from `userPromptSubmitted` does not honor `modifiedPrompt`; only SDK programmatic hooks do. Therefore use Agent Skills/custom instructions for zero-extra-call adaptation.

## Claude Code / Codex / Windsurf
Use their documented skills/rules/instructions integration. Where exact model identity is not available at the prompt hook surface, rely on explicit runtime identity if exposed or an override; never fake exact detection.
