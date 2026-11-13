# Gemini 4 Carbon harness notes

**Provenance:** official Carbon developer guide, checked 2026-11-13. These are API facts for host configuration, not prompt text or authorization to change host settings.

- Exact model ID: `gemini-4-carbon`. It is a distinct model from `gemini-4-hydrogen` and `gemini-4-argon`.
- `thinking_level`: `LOW`, `MEDIUM` (default), `HIGH`. Google recommends MEDIUM for general coding/tool use and HIGH for multi-file software engineering. `thinking_budget` and `MINIMAL` return HTTP 400.
- Custom `temperature`, `top_p`, and `top_k` are ignored. `frequency_penalty`, `presence_penalty`, and `candidate_count` > 1 return HTTP 400. Use the host's supported `response_schema` for structured output where appropriate.
- The 1,048,576-token limit is shared by input and output, including thinking and function calls. Foreground output is 65,536 tokens for streaming requests and 32,768 for non-streaming direct HTTP requests.
- Long decode requires SDK continuation support or an explicit continuation loop; it is generally unnecessary for agents making many short tool turns.
- With SDK continuations, cumulative billed `prompt_token_count` is not the live context size. Use `initial_prompt_token_count` and wait for generation completion before compaction.
- Explicit context caching is unsupported. Implicit prefix caching applies to shared prefixes of at least 4,096 tokens; put static content before dynamic content, and do not pad prompts to hit the threshold.
- Tool history: match response `id`/`name`/order to the preceding function calls, prefer sequential tool-loop turns, and keep pre-tool text formatting separated by blank lines. Do not prefill a model turn and do not let history end with a model turn.
- Carbon supports Office/OpenDocument content, but actual access is governed by the host's native tools and permissions. Verified-enterprise and select-region availability are provider facts; this profile does not unlock them.

Official sources:
https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-carbon
https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies
