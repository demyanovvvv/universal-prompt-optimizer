# GPT-6 Astra prompt profile

**Provenance:** official OpenAI model guidance, checked 2026-09-06.

## Preferred shaping
- Infer routine intent/scope from conversation and bias toward action/follow-through; do not stop at capability acknowledgement or a plan when implementation is authorized.
- Make instruction priority explicit when skills/rules may conflict: explicit user instructions outrank this optimization layer.
- Avoid unnecessary approval pauses. Do already-authorized read-only/reversible/preparatory work before asking for consequential approval.
- State output style/verbosity when it matters; Astra can otherwise produce detailed/strongly formatted responses.
- For subagents, specify delegation policy only when the task has genuinely independent workstreams; do not spawn by ritual.
- Use proportionate testing: Astra can over-test small changes if told generically to verify everything.
- Keep outcome, decisive context, scope, constraints, approval boundaries, and success criteria explicit.

## Avoid
- conflicting/duplicated instructions in skills;
- unnecessary “ask first” repetition;
- exhaustive generic test/verification language for trivial changes;
- manual CoT requests.

Runtime/API settings are in `harness-openai.md`.

Official source: https://developers.openai.com/api/docs/guides/latest-model
