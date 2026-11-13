# Muse Wonder harness notes

**Provenance:** official Meta Model API documentation and the Muse Wonder model card, checked 2026-11-13. These are API facts for host configuration, not prompt text or authorization to change host settings.

- Model API ID `muse-wonder-1.0`; OpenAI-compatible `base_url https://api.meta.ai/v1` with Responses, Chat Completions and Messages endpoints; 1,048,576-token context. Preview; Model API pay-as-you-go Standard mode only. Muse Wonder Full is subscription-only and has no Model API ID.
- `reasoning_effort`: `minimal`, `low`, `medium`, `high`, `xhigh`, `max`; default `max`, and `"none"` returns HTTP 400. Meta recommends starting agentic coding at `high` and reserving `xhigh`/`max` for the hardest problems. Chat Completions takes top-level `reasoning_effort`; Responses takes `reasoning.effort`.
- Reasoning is private: it does not appear in the response body, reasoning tokens count toward `max_tokens`/`max_output_tokens` and bill at output rates, and `logprobs` returns 400.
- **Multi-turn reasoning continuity differs by endpoint.** The Responses API preserves reasoning via `previous_response_id` or a stateless replay that sets `include: ["reasoning.encrypted_content"]` and replays the reasoning input item. On Chat Completions, assistant `reasoning_content` is redacted to empty before reaching an external caller, so each turn reasons from scratch; do not rely on it for continuity there, and keep long agentic flows on Responses.
- During built-in tool loops, reasoning items can appear with empty `content` but still carry `encrypted_content` for stateless replay. `reasoning.summary` (`auto`/`concise`/`detailed`) is Responses-only and not guaranteed.
- Tools: the Responses API is recommended for tool calling and multi-turn agents; flat tool objects on Responses, nested under `function` on Chat Completions, and the deprecated `functions`/`function_call` fields should not be used. `custom` tools are Responses-only. Function names match `^[a-zA-Z0-9_.-]+$` with at most one dot; tool results should stay in call order when history is built manually.
- Meta's shared Model API structured-output documentation describes constrained `json_schema` decoding and rejection of recursive schemas. Responses uses `text.format`; Chat Completions uses `response_format`. These are documented shared API facts, not a live Wonder endpoint test; do not silently change the user's schema or host protocol.
- Media serialization is documented on Meta's shared Model API page, whose examples name Muse Spark rather than Wonder: user-role images, string `input_image.image_url` on Responses versus an object on Chat Completions, and uploaded `file_id`/`input_file`/`file_url`. Treat these as shared API guidance, not separately verified Wonder-specific media behavior; verify the selected serving surface. Do not infer audio availability from another surface.
- Meta's shared computer-use API requires a host-supplied driver and deliberate handling of safety acknowledgements. The optimizer does not install a driver, acknowledge safety checks, change truncation or authorize GUI actions.
- Availability: not available in South Korea; contributor mode is not available for Muse Wonder.

Official sources:
https://dev.meta.ai/docs/muse-wonder
https://dev.meta.ai/docs/reasoning.md
https://dev.meta.ai/docs/tool-calling.md
https://dev.meta.ai/docs/structured-output.md
https://dev.meta.ai/docs/media-understanding.md
https://dev.meta.ai/docs/computer-use.md
