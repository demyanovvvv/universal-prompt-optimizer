# GPT-6 Astra prompt profile

**Provenance:** official OpenAI model and coding-agent guidance; GPT-6 family guide rechecked 2026-09-23, coding-agent guidance checked 2026-09-13.

## Preferred shaping
- Read `gpt-6-family.md` only when skill conflicts, writing style, delegation, or testing behavior needs tuning beyond the concise guidance below.
- Infer routine intent/scope from conversation and bias toward action/follow-through; do not stop at capability acknowledgement, a plan, or the first implementation when completion is authorized.
- Make instruction priority explicit when skills/rules may conflict: explicit user instructions outrank this optimization layer.
- Avoid unnecessary approval pauses. Continue through already-authorized local, reversible, read-only, preparatory, implementation, and validation work; ask only when a consequential action or missing decision actually requires it.
- State output style/verbosity when it matters; Astra can otherwise produce detailed/strongly formatted responses.
- For subagents, specify delegation policy only when the task has genuinely independent workstreams; do not spawn by ritual.
- Use proportionate testing: Astra can over-test small changes if told generically to verify everything.
- Keep outcome, decisive context, scope, constraints, approval boundaries, and observable completion explicit.
- For implementation, bugfix, or long-horizon work, continue through implementation, inspection/run, fixes for failures caused by the change, and rerunning affected checks when those steps are part of completion. Stop at the success criteria, a concrete blocker, or a genuinely consequential approval boundary.
- For skill or repository-instruction work, keep descriptions narrowly triggered and use a small root router with conditional supporting material. Do not add this workflow to unrelated tasks.

## Avoid
- conflicting/duplicated instructions in skills;
- unnecessary “ask first” repetition;
- exhaustive generic test/verification language for trivial changes;
- unconditional repository maps, documentation reading, or workflow recipes;
- stopping after a first pass when the requested completion criteria remain unmet;
- manual CoT requests.

Runtime/API settings are in `harness-openai.md`.

Official sources: https://developers.openai.com/api/docs/guides/latest-model ; https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra
