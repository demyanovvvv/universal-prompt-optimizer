# Gemini CLI adapter — v5.8

The adapter registers the same observation/preflight script for two native Gemini CLI events:

- `BeforeAgent`: injects the per-turn Prompt Optimizer preflight and implements `scope=first` when `session_id` is available.
- `BeforeModel`: **observation only**. It reads the resolved `llm_request.model`, stores that model ID for the current session, and returns no request override. It never reconstructs or replaces the outgoing multimodal request.

## Model routing

The adapter never assumes that “Gemini CLI” means Gemini 3.8 Flash.

Before the first model call it can safely use only an explicit model visible to the hook, in this order:

1. `GEMINI_MODEL`;
2. project `.gemini/settings.json` → `model.name`;
3. user `~/.gemini/settings.json` → `model.name`.

Gemini CLI command-line `--model` has higher precedence but is not exposed to `BeforeAgent`. As soon as `BeforeModel` fires, the exact resolved `llm_request.model` is stored for that session and takes precedence on later user turns.

Only an unambiguous `gemini-3.8-flash` ID selects the installed Gemini 3.8 Flash profile. Aliases such as `auto`, `pro`, or `flash` are not guessed. Unknown models follow the configured `unsupportedModel=skip|generic` behavior.

## PREVIEW

When `behavior=preview`, the injected preflight asks the model to use Gemini CLI's built-in `ask_user` tool. If that tool is unavailable, it must show the exact optimized prompt and wait for explicit confirmation.

Runtime/model parameters remain separate from prompt optimization.
