# DeepSeek V4 harness notes

- Thinking mode is enabled by default in the current DeepSeek API; default effort is `high`.
- Supported requested effort is `low`, `high`, `max`; OpenAI-style `medium/high/xhigh` may map to DeepSeek `high` according to the official mapping.
- In thinking mode, API sampling controls such as temperature/top-p may be ignored depending on the official endpoint; do not try to compensate in prompt text.
- With tool calling, preserve the assistant's `reasoning_content` correctly through the tool loop. Keep assistant/tool message structure intact; malformed history can fail requests or degrade behavior.
- DeepSeek Harness records append-only session state; Minimal mode uses a persistent shell plus file editor, illustrating that tool descriptions can stay lean.

Sources:
https://api-docs.deepseek.com/guides/thinking_mode/
https://api-docs.deepseek.com/guides/tool_calls/
https://www.deepseek.com/harness/en/
