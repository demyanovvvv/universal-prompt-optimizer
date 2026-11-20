# Gemini 4 Neon prompt profile

**Provenance:** official Neon developer/API guide plus shared Google prompting practices, checked 2026-11-20. The exact model ID is `gemini-4-neon`; it is a distinct Gemini 4 profile.

Use a clear objective, relevant context, hard constraints and the requested output. Add labels, delimiters or examples only when they resolve real ambiguity; use examples for non-obvious formats or behavior. For untrusted source material, clearly mark it as data and state how to use it. For recurring prompts, iterate against representative inputs and evaluate outputs. Avoid redundant/conflicting instructions and do not inflate a precise request with a generic template. These shared Google practices are not a Neon-specific prompt recipe.

For complex work, make scope, dependencies and required verification explicit when missing. For image or document input, state what to extract or compare and the desired deliverable. Select relevant context and leave output headroom in Neon's unified 1,048,576-token input/output context. Implicit caching applies to shared prefixes of 4,096 tokens or more, so do not add prompt padding for caching. Keep prompt shaping separate from native reasoning and runtime settings; do not request hidden reasoning or generic step-by-step text.

Official sources:
- Model-specific guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-neon
- Shared prompting practices: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies
- Gemini 4 family overview: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start/get-started-with-gemini-4

Runtime: `harness-gemini-4-neon.md`.
