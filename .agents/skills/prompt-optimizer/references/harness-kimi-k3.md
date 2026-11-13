# Kimi K3 harness notes

Checked 2026-11-13.

- Kimi K3 always has thinking enabled.
- `reasoning_effort`: `low`, `high`, `max`; official model card default is `max`, but benchmark/default is not a requirement to force max for every task.
- Kimi K3 was trained with preserved thinking history. For multi-turn/tool use, pass the complete assistant message back as-is, including `reasoning_content` and `tool_calls`, not only `content`.
- **Kimi K3.1 Pro:** thinking is always on and cannot be disabled; the `thinking` parameter is unsupported on the K3 series and K2.x `thinking` configuration must be removed. `reasoning_effort` is `low`/`high`/`max` with default `max`; decide effort before the conversation starts, because switching levels mid-session invalidates prefix-cache hits.
- **Kimi K3.1 Pro history:** `reasoning_content` is billed and occupies context; keep `max_tokens`/`max_completion_tokens` at 16000 or more and enable streaming, where `reasoning_content` deltas precede `content` deltas. In streaming, assemble `tool_calls` chunks correctly, give each call exactly one matching `role: "tool"` message with the exact `tool_call_id`, and append the returned `choice.message` as-is. The OpenAI SDK does not expose `reasoning_content` directly, so read it via attribute access.
- **Kimi K3.1 Pro parameters:** `temperature=1.0`, `top_p=0.95`, `n=1` and zero penalties are fixed; other values are rejected. The K3 series supports `tool_choice: auto|none|required`; use `required` only with a declared tool inventory, as in the documented first-turn `search_tools` retrieval pattern. This is not authorization for the optimizer to change tool choice.
- **Kimi K3.1 Pro caching:** context caching is automatic and block-based with a `5m` default or `1h` TTL via `prompt_cache_options.ttl`; a partially filled block is billed as a miss. Dynamic tool declarations appended at the end of `messages` keep the cached prefix; changing `tool_choice` does not invalidate it.
- **Kimi K3.1 Pro repeated calls:** after three consecutive identical tool-and-argument repeats with no progress, the client may append a `<system-reminder>` asking for a different approach, escalating at five and eight repeats. This is harness mitigation, not prompt text.
- `kimi-k3.1-pro-highspeed` is a separate model ID with the same intelligence and parameter constraints.

Sources:
https://github.com/MoonshotAI/Kimi-K3
https://platform.kimi.ai/docs/guide/kimi-k3-1-pro-quickstart
https://platform.kimi.ai/docs/guide/use-reasoning-effort
https://platform.kimi.ai/docs/guide/kimi-k3-tool-calling-best-practice
https://platform.kimi.ai/docs/guide/tool-call-repeat
