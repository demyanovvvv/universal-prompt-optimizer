# DeepSeek V4 harness notes

Snapshot: `DeepSeek-V4.1-Flash-1017` (checked 2026-11-13), served as `deepseek-flash`. Context 1M, max output 384K.

- Thinking mode is enabled by default in the current DeepSeek API; default effort is `high`.
- Supported requested effort is `low`, `high`, `max`; the official mapping sends `minimal` to `low` and `medium`/`xhigh` to `high`. The Responses API additionally accepts `effort: "none"` to disable thinking. Open-weights/self-host exposure accepts an integer 1–100 (`low`=50, `high`=75, `max`=100).
- In thinking mode, `temperature`, `presence_penalty` and `frequency_penalty` are accepted but have no effect, so do not try to compensate in prompt text. `deepseek-flash` `top_p` only takes effect in thinking mode and is clamped to the 0.95–1.0 range; outside thinking mode it is fixed at 1.0 and ignored.
- With tool calling, pass back `reasoning_content` for **all** previous turns, including turns with no tool call, or the API returns HTTP 400. Without a `tools` declaration it is ignored and not concatenated. Keep assistant/tool message structure intact and tool results in `tool_calls` order; malformed history can fail requests or degrade behavior.
- Mid-conversation `system` messages are supported in Chat Completions; inserting tool calls mid-conversation requires the Anthropic or Responses API.
- The Responses API is stateless: `previous_response_id`, `store`, `truncation`, `context_management` and `include` are unsupported, `parallel_tool_calls` is always on, and context overflow returns 400.
- `strict` tool schemas are beta (`/beta` base URL) and require every property in `required` plus `additionalProperties: false`.
- JSON output needs `response_format: json_object`, the literal word `json`, an example object and adequate `max_tokens`; unparsable output is replaced with spaces, so a blank `content` with `finish_reason: stop` is a harness-level retry case, not a prompt fix.
- Vision: images infer-resize to about 1300×1300 and cost at most 1024 tokens each; `detail: low` is 512×512; images in assistant messages are rejected.
- `deepseek-v4-pro` remains its own model (`DeepSeek-V4-Pro-0813`) without vision support; do not fold it into this snapshot. DeepSeek asks for DeepSeek Harness 0.2.1-rc.1 or later with the 1017 model.
- DeepSeek Harness records append-only session state; Minimal mode uses a persistent shell plus file editor, illustrating that tool descriptions can stay lean.

Sources:
https://api-docs.deepseek.com/guides/thinking_mode/
https://api-docs.deepseek.com/guides/tool_calls/
https://api-docs.deepseek.com/guides/responses_api
https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/raw/main/encoding/README.md
https://www.deepseek.com/harness/en/
