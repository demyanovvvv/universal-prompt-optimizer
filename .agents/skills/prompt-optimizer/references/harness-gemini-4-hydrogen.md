# Gemini 4 Hydrogen harness notes

**Provenance:** official Hydrogen developer guide, checked 2026-11-13. These are API facts for host configuration, not prompt text or authorization to change host settings.

- Exact model ID: `gemini-4-hydrogen`. It is a distinct model from `gemini-4-carbon` and `gemini-4-argon`; none of the three is an alias for another.
- `thinking_level`: `LOW`, `MEDIUM`, `HIGH` (default), `XHIGH`. Google recommends MEDIUM as the latency/quality balance for general coding, HIGH for multi-step agentic tool loops and refactoring, and XHIGH for the most complex multi-file, proof or scientific work. `thinking_budget` and `MINIMAL` return HTTP 400.
- Custom `temperature`, `top_p`, and `top_k` are ignored. `frequency_penalty`, `presence_penalty`, and `candidate_count` > 1 return HTTP 400. Use the host's supported `response_schema` for structured output where appropriate.
- The 1,048,576-token limit is shared by input and output, including thinking and function calls. Foreground output is 65,536 tokens for both streaming and non-streaming requests.
- Long decode uses a `continuation_token` on Agent Platform v1beta1: preserve the original input, system instruction and tools, do not append the partial output, and do not ask the model to "continue". Complete the segment chain before starting a new user turn. Host SDK/provider support is required.
- With continuations, cumulative billed counts are not the live context size. Use `initial_input_tokens` / `initial_prompt_token_count` and compact only after decode completion.
- Explicit context caching is unsupported. Implicit prefix caching applies to shared prefixes of at least 4,096 tokens; put static content before dynamic content without padding prompts to hit the threshold. The 6,144-token value belongs to the older Gemini 3.8 Flash migration comparison, not a confirmed previous Hydrogen limit.
- Tool history: preserve every `thought_signature` inside its original `Part` across all previous turns, for both function-call and text parts. For parallel calls, only the first `functionCall` part carries the signature: do not duplicate it onto sibling calls. Keep all calls in one model turn and all matching results in one user turn, matching `id`, `name` and order. A same-model signature binds the system/tools/history prefix: changing that prefix returns HTTP 400 by default. `prefix_mismatch_behavior="DROP"` is a documented host-side option for actual compaction or editing, not a prompt workaround; the optimizer does not set it.
- Host transport must support these replay/prefix rules before reusing signed history with changing preflight instructions. A profile match proves routing, not that the host's provider adapter preserves signatures or uses a compatible update mechanism.

Official sources:
https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-hydrogen
https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies
