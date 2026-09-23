# GPT-6 Sol prompt profile

**Provenance:** official GPT-6 family prompting guidance and official Sol positioning (strong reasoning for demanding tasks), checked 2026-09-23. The guide describes behavior observed on Astra and recommends these prompts as a starting point across GPT-6; validate them on Sol and the chosen workload.

## Preferred shaping
- Preserve the outcome, decisive context, scope, hard constraints, approval boundaries, and observable completion criteria in a lean brief.
- For authorized implementation or bugfix work, infer routine intent and continue through implementation and affected validation until complete or concretely blocked. A plan alone is sufficient only when that is the requested deliverable.
- Ask focused questions when a missing decision materially changes the result; continue independently authorized work while it is unresolved.
- Read `gpt-6-family.md` only when skill conflicts, writing style, delegation, or testing behavior needs tuning. Add only the relevant guidance once.

## Avoid
- Importing GPT-5.6 tier assumptions or claiming Astra's observed tendencies have been measured on Sol.
- Prescribing every reasoning step, generic “think harder” text, or compressing away correctness-critical context.

Official source: https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices
Runtime settings: `harness-openai.md`.
