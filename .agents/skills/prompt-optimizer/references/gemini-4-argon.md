# Gemini 4 Argon prompt profile

**Provenance:** official model-specific developer/API guide plus official Google family prompting guidance, checked 2026-10-21. The official model ID is `gemini-4-argon`, not `gemini-4.0-argon`.

Use clear, specific instructions: preserve the goal, relevant context, constraints, expected output and observable completion criteria. Add structure or examples only when they resolve ambiguity. These are shared Google prompting practices, not a newly prescribed Argon prompt template.

For complex multi-file work, make scope, dependencies and required verification explicit when missing. Preserve a precise short request unchanged; do not import Gemini 3.8 Flash's aggressive PASS/LIGHT preference as an Argon-specific rule. This lean quality gate is the optimizer's operational heuristic, not a claim from the Argon guide.

Keep prompt shaping separate from runtime reasoning. Do not add manual chain-of-thought scaffolding or invent sampling settings. Argon's unified context limit includes input, thinking, function calls and final output: select relevant context and leave room for the result rather than filling the entire window.

Official sources:
- Model-specific guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-argon
- Model: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/4-argon
- Shared prompting practices: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies

Runtime: `harness-gemini-4-argon.md`.
