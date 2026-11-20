# Gemini 4 Neon harness notes

**Provenance:** official Neon developer guide, checked 2026-11-20. These are API/host facts, not prompt text or authorization to change host settings.

- Exact model ID: `gemini-4-neon`; it is distinct from Hydrogen, Carbon and Argon.
- `thinking_level`: `LOW`, `MEDIUM`, `HIGH` (default), and `XHIGH`. These are host settings, not prompt instructions.
- Neon has a unified 1,048,576-token input/output limit, including thinking, function calls and the final response. Leave room for output and select relevant context.
- Long decodes support continuation up to the remaining unified context limit; SDK continuation or host-managed continuation is required. This is generally unnecessary for agents making short tool turns.
- Implicit caching applies to shared prefixes of 4,096 tokens or more; durable caching is enabled by default and explicit context caching is unsupported. Do not add prompt padding for caching.
- Office/OpenDocument files are supported by the model, but access still depends on the host tools and permissions. Agentic video understanding is off by default.
- Neon can plan/verify a multi-step workflow and hand scoped worker steps to Hydrogen using the Interactions API. This is provider orchestration, not a prompt optimizer routing behavior.

Official sources:
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-neon
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies
