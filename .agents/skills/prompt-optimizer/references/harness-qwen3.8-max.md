# Qwen3.8-Max harness notes

- Hybrid thinking can be enabled/disabled; qwen3.8-max enables thinking by default on documented QwenCloud paths.
- `reasoning_effort`: `low`, `medium`, `xhigh`; default `xhigh`. Do not set it simultaneously with `thinking_budget`.
- `preserve_thinking` defaults to true for qwen3.8-max. Send historical `reasoning_content` back in the separate `reasoning_content` field; never concatenate it into `content`.
- In thinking mode, `tool_choice` supports `auto`/`none`; if you must force a specific tool and the provider requires it, disable thinking according to Qwen docs.
- Clear, specific function descriptions matter; parallelize only independent calls.

Sources:
https://docs.qwencloud.com/developer-guides/text-generation/thinking
https://docs.qwencloud.com/api-reference/chat/openai-chat
https://docs.qwencloud.com/developer-guides/tool-calling/function-calling
