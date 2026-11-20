# Gemini 4 Carbon prompt profile

**Provenance:** official Carbon developer/API guide plus shared Google prompting practices, checked 2026-11-20. The official model ID is `gemini-4-carbon`; it is not an alias for Hydrogen or Argon, and there is no `gemini-4.0-carbon`.

Use a clear objective, relevant context, hard constraints and the requested output. Add labels, delimiters or examples only when they resolve real ambiguity; use examples for non-obvious formats or behavior. For untrusted source material, clearly mark it as data and state how to use it. For recurring prompts, iterate against representative inputs and evaluate outputs. Avoid redundant/conflicting instructions and do not pad a precise request with a generic template. These are shared Google practices, not a Carbon-specific prompt recipe.

For complex multi-file engineering, state scope, dependencies and required validation when missing. For image or document input, specify what to extract or compare and the deliverable. Carbon shares one 1,048,576-token context across input, thinking, function calls and output, so choose relevant context and leave output headroom. Do not pad prompts to reach a cache threshold. Office/OpenDocument access depends on host tools and permissions. Native Thinking is separate from prompt text; custom temperature/top_p/top_k are ignored. `MEDIUM` is Carbon's default thinking level and suits general coding/tool use; `HIGH` is recommended for multi-file software engineering. Those are host configuration choices, not prompt text.

Official sources:
- Model-specific guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-carbon
- Shared prompting practices: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies

Runtime: `harness-gemini-4-carbon.md`.
