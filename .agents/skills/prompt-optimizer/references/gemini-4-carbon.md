# Gemini 4 Carbon prompt profile

**Provenance:** official model-specific developer/API guide plus official Google family prompting guidance, checked 2026-11-13. The official model ID is `gemini-4-carbon`; it is not an alias for Hydrogen or Argon, and there is no `gemini-4.0-carbon`.

Use clear, specific instructions: preserve the goal, relevant context, constraints, expected output and observable completion criteria. Add labels, delimiters or examples only where they remove real ambiguity. These are shared Google prompting practices applied to Carbon, not a newly prescribed Carbon prompt template.

For complex multi-file software engineering, make scope, dependencies and the required validation explicit when missing. Preserve a precise short request unchanged; do not import Gemini 3.8 Flash's aggressive PASS/LIGHT preference as a Carbon-specific rule.

Keep prompt shaping separate from runtime reasoning. Do not add manual chain-of-thought scaffolding or invent sampling settings: Google's shared guide recommends native Thinking without explicit step-by-step instructions, and custom temperature/top_p/top_k are ignored. Carbon shares one 1,048,576-token context across input, thinking, function calls and output, so choose relevant context and leave output headroom rather than filling the window. Do not pad prompts to reach a cache threshold.

`MEDIUM` is Carbon's default thinking level and suits general coding/tool use; `HIGH` is the recommended setting for multi-file software engineering. Those are host configuration choices, not prompt text. For document/image inputs, state what to extract or compare and the desired deliverable; access to Office/OpenDocument content still depends on the host's own tools and permissions.

Official sources:
- Model-specific guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-carbon
- Shared prompting practices: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies

Runtime: `harness-gemini-4-carbon.md`.
