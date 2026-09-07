# Kimi K3 harness notes

- Kimi K3 always has thinking enabled.
- `reasoning_effort`: `low`, `high`, `max`; official model card default is `max`, but benchmark/default is not a requirement to force max for every task.
- Kimi K3 was trained with preserved thinking history. For multi-turn/tool use, pass the complete assistant message back as-is, including `reasoning_content` and `tool_calls`, not only `content`.

Source: https://github.com/MoonshotAI/Kimi-K3
