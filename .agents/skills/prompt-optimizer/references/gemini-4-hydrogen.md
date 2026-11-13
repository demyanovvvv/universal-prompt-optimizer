# Gemini 4 Hydrogen prompt profile

**Provenance:** official model-specific developer/API guide plus official Google family prompting guidance, checked 2026-11-13. The official model ID is `gemini-4-hydrogen`; there is no `gemini-4.0-hydrogen` and no bare `gemini-4` alias.

Use clear, specific instructions: preserve the goal, relevant context, constraints, expected output and observable completion criteria. Add labels, delimiters or examples only where they remove real ambiguity. These are shared Google prompting practices applied to Hydrogen, not a newly prescribed Hydrogen prompt template.

For complex multi-file work, make scope, dependencies and required verification explicit when missing. Preserve a precise short request unchanged: this is the optimizer's lean quality gate, not a claim from the Hydrogen guide.

Keep prompt shaping separate from runtime reasoning. Do not add manual chain-of-thought scaffolding: Google's shared guide recommends trying the model's native Thinking without explicit step-by-step instructions. Hydrogen's unified context includes input, thinking, function calls and final output, and thinking is part of the answer budget, so select relevant context and leave room for the result instead of filling the window. Do not pad prompts to reach a cache threshold.

`HIGH` is Hydrogen's default thinking level; `MEDIUM` is the latency-balanced choice for general coding, and `XHIGH` is reserved for the most complex multi-file, proof or scientific work. Those are host settings, not prompt text.

Official sources:
- Model-specific guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-hydrogen
- Shared prompting practices: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies
- Model family: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-argon

Runtime: `harness-gemini-4-hydrogen.md`.
