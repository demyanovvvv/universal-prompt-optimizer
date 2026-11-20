# Gemini 4 Argon prompt profile

**Provenance:** official Argon developer/API guide plus shared Google prompting practices, checked 2026-11-20. The official model ID is `gemini-4-argon`, not `gemini-4.0-argon`.

Use a clear objective, relevant context, hard constraints and the requested output. Add labels, delimiters or examples only when they resolve real ambiguity; use examples for non-obvious formats or behavior. For untrusted source material, clearly mark it as data and state how to use it. For recurring prompts, iterate against representative inputs and evaluate outputs. Avoid redundant/conflicting instructions and do not pad a precise request with a generic template. These are shared Google practices, not an Argon-specific prompt recipe.

For complex multi-file work, state scope, dependencies and required verification when missing. Argon's unified context limit includes input, thinking, function calls and final output, so select relevant context and leave room for the result. Keep prompt shaping separate from runtime reasoning; do not add manual chain-of-thought scaffolding or invent sampling settings.

Official sources:
- Model-specific guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-argon
- Model: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/4-argon
- Shared prompting practices: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies

Runtime: `harness-gemini-4-argon.md`.
