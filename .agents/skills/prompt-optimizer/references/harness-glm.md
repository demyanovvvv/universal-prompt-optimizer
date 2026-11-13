# GLM harness notes

Keep runtime thinking/sampling separate from prompt shaping.

- GLM-5.3 uses native reasoning; current Z.ai docs expose `low`, `high`, `max`, with reasoning not treated as a textual CoT instruction.
- GLM-5.3-Flash examples use native thinking/reasoning controls and can stream tool output; visual feedback loops belong in task workflow, not hidden-reasoning requests.
- **GLM-5.3-FlashX:** same 320B/18B Flash base and 1M-context/128K-output spec, but its own model code and price tier; treat it as a speed-optimized sibling, not an alias for GLM-5.3-Flash.
- **GLM-5.3-FlashX thinking:** `thinking.type` accepts only `enabled`; thinking cannot be disabled. `reasoning_effort` is `low`, `high` or `max` with default `max`. For agent/coding turns, `clear_thinking: false` enables preserved thinking and requires returning complete, unmodified, correctly ordered `reasoning_content` — never reorder or edit prior thinking blocks.
- **GLM-5.3-FlashX streaming/tools:** prefer `stream: true` with `tool_stream: true` and concatenate `delta.tool_calls[*].function.arguments`; handle `delta.reasoning_content` separately from `delta.content`. On the first-party API `tool_choice` supports `auto` only; other values are rejected.
- **GLM-5.3-FlashX sampling:** `temperature=1`, `top_p=0.95`; tune only one of them. Context caching is automatic, so put static prefixes first. These are host settings, not prompt text.
- GLM-5.2 examples may use high/max reasoning for demanding engineering, but do not force benchmark/runtime settings into every prompt.
- Provider-compatible layers can expose different parameter names/mappings; follow the endpoint's actual schema.

Sources:
https://docs.z.ai/guides/llm/glm-5.3
https://docs.z.ai/guides/vlm/glm-5.3-flash
https://docs.bigmodel.cn/cn/guide/models/text/glm-5.2
https://docs.z.ai/guides/capabilities/thinking-mode
https://docs.z.ai/guides/capabilities/function-calling
