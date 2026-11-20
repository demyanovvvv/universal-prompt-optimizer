# Gemini 4 Hydrogen prompt profile

**Provenance:** official Hydrogen developer/API guide plus shared Google prompting practices, checked 2026-11-20. The official model ID is `gemini-4-hydrogen`; there is no `gemini-4.0-hydrogen` and no bare `gemini-4` alias.

Use a clear objective, relevant context, hard constraints and the requested output. Add labels, delimiters or examples only when they resolve real ambiguity; use examples for non-obvious formats or behavior. For untrusted source material, clearly mark it as data and state how to use it. For recurring prompts, iterate against representative inputs and evaluate outputs. Avoid redundant/conflicting instructions and do not pad a precise request with a generic template. These are shared Google practices, not a Hydrogen-specific prompt recipe.

For complex multi-file work, state scope, dependencies and required verification when missing. Hydrogen's unified context includes input, thinking, function calls and final output, and thinking is part of the answer budget, so select relevant context and leave room for the result. Do not pad prompts to reach a cache threshold. Keep prompt shaping separate from runtime reasoning; do not add manual chain-of-thought scaffolding.

`HIGH` is Hydrogen's default thinking level; `MEDIUM` is the latency-balanced choice for general coding, and `XHIGH` is reserved for the most complex multi-file, proof or scientific work. Those are host settings, not prompt text.

Official sources:
- Model-specific guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-hydrogen
- Shared prompting practices: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies
- Model family: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-argon

Runtime: `harness-gemini-4-hydrogen.md`.
