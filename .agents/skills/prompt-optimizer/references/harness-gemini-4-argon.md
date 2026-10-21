# Gemini 4 Argon harness notes

**Provenance:** official Argon developer guide, checked 2026-10-21. These are API facts for host configuration, not prompt text or authorization to change host settings.

- Exact model ID: `gemini-4-argon`. The separately documented `gemini-4-argon-cyber-permissive` variant is not an alias for this profile.
- `thinking_level`: `LOW`, `MEDIUM` (default), `HIGH`. Google recommends MEDIUM for general coding/tool use and HIGH for multi-file software engineering and architecture design. `thinking_budget` and `MINIMAL` return HTTP 400.
- Custom `temperature`, `top_p`, and `top_k` are ignored. `frequency_penalty`, `presence_penalty`, and `candidate_count` return HTTP 400. Use the host's supported `response_schema` for structured output where appropriate.
- The 1,048,576-token limit is shared by input and output, including thinking and function calls. Default single-request output is 65,536 tokens, or 32,768 for non-streaming direct HTTP requests. Long decode requires SDK continuation support or an explicit continuation loop; it is generally unnecessary for agents making many short tool turns.
- With SDK continuations, cumulative billed `prompt_token_count` is not the live context size. Use `initial_prompt_token_count` and wait for generation completion before compaction.
- Explicit context caching is unsupported. Implicit caching applies to shared prefixes of at least 6,144 tokens; when assembling requests, put static content before dynamic content. This is request-layout guidance, not an unconditional instruction to reorder user text.

Official sources:
https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-argon
https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start/get-started-with-gemini-4
